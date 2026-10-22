"""Pure, seeded target-skill/template selection + initial-difficulty pick (Phase C4.0).

Implements SPEC §8 (session-mode handling), §9 (``lowest_mastery_then_coverage``), §10
(initial-difficulty clamp), and the cold-start assessment §5.3/§5.4 (familiarization gate).
Reuses (never reimplements) the committed C2.1 ``eligibility.eligible_templates`` /
``generation.build_task_instance`` to build the chosen instance -- this module only decides
*which* skill/template/difficulty, then hands off.

**Boundary purity (hard).** The only B-derived input anywhere in this module is
``mastery_payload: BToCMasteryPayload`` -- the frozen 7-scalar v2.1 contract. No B
observation-count, readiness state, or evidence mask is read, stored, or accepted by any
function here (there is no parameter through which one could be threaded) -- exactly the
primary recommendation of the cold-start assessment (§5, §5.2: "no B-derived readiness signal
is sent to C").
"""

from __future__ import annotations

import random
from typing import Annotated, Dict, Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator

from models.contracts import SKILLS, BToCMasteryPayload

from ..catalogue.loaded_models import LoadedCatalogue, LoadedGameTaskTemplate
from ..eligibility import eligible_templates
from ..generation import build_task_instance
from ..generation_config import CGenerationConfig
from ..models.enums import SessionPhase
from ..models.task_instance import GameTaskInstance
from ..seeds import CSeedLineage, derive_child_lineage, rng_from
from .config import CSelectionConfig

SELECTOR_VERSION = "c4.0-selector-1.0.0"

_SKILL_ORDER = {skill: idx for idx, skill in enumerate(SKILLS)}
_ALLOWED_SELECTION_ROLES = ("MAIN", "SUPPORT", "MAIN_SUPPORT")

MasteryContextMode = Literal["same_session_fresh", "unavailable_fallback"]


class SelectionInputError(ValueError):
    """Raised when ``session_mode``/``session_phase``/``mastery_payload`` disagree (SPEC §8)."""


class SelectionResult(BaseModel):
    """One selection outcome: chosen skill/template/difficulty + the built instance."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    session_phase: SessionPhase
    selected_skill_id: str
    selected_template_id: str
    initial_difficulty_level: Annotated[int, Field(ge=1, le=5)]
    mastery_context_mode: MasteryContextMode
    mastery_selected_skill: Optional[float] = None
    task_instance: GameTaskInstance

    @model_validator(mode="after")
    def _provenance_invariants(self) -> "SelectionResult":
        if self.session_phase == "mastery_driven" and self.mastery_selected_skill is None:
            raise ValueError("mastery_selected_skill must be set for mastery_driven selection")
        if self.session_phase in ("familiarization", "c_only") and self.mastery_selected_skill is not None:
            raise ValueError("mastery_selected_skill must be null for familiarization/c_only selection")
        if self.session_phase == "c_only" and self.mastery_context_mode != "unavailable_fallback":
            raise ValueError("c_only selection must carry mastery_context_mode='unavailable_fallback'")
        if self.session_phase != "c_only" and self.mastery_context_mode != "same_session_fresh":
            raise ValueError("combined-session selection must carry mastery_context_mode='same_session_fresh'")
        return self


def _grade_valid_skills(catalogue: LoadedCatalogue, grade: int, supported_template_ids: Tuple[str, ...]) -> Tuple[str, ...]:
    """The set of skills with at least one grade-eligible, generation-supported, active
    template (SPEC §8.2 bullet 1-2). Canonically ordered by the frozen 7-skill order."""
    present: set = set()
    for template in eligible_templates(catalogue, grade, supported_template_ids):
        present.update(template.primary_skill_ids)
    return tuple(sorted(present, key=lambda s: _SKILL_ORDER[s]))


def _candidate_templates(
    catalogue: LoadedCatalogue, grade: int, skill_id: str, supported_template_ids: Tuple[str, ...],
) -> Tuple[LoadedGameTaskTemplate, ...]:
    """Active MAIN/SUPPORT/MAIN_SUPPORT templates for one grade-valid skill (SPEC §8.2 bullet 5;
    RECOVERY_ONLY is excluded -- recovery routing is a later C4.1+ concern)."""
    candidates = [
        t for t in eligible_templates(catalogue, grade, supported_template_ids)
        if skill_id in t.primary_skill_ids and t.functional_role in _ALLOWED_SELECTION_ROLES
    ]
    if not candidates:
        raise SelectionInputError(f"no MAIN/SUPPORT template available for grade-valid skill {skill_id!r}")
    return tuple(sorted(candidates, key=lambda t: t.game_task_template_id))


def _mastery_by_skill(mastery_payload: BToCMasteryPayload) -> Dict[str, float]:
    """The exact seven B->C v2.1 scalars, keyed by skill id -- the ONLY B-derived read in this
    module. No other field of ``mastery_payload`` (there is none beyond the seven scalars +
    envelope) and no other B object is ever touched."""
    return {
        "counting": mastery_payload.mastery_counting,
        "number_sense": mastery_payload.mastery_number_sense,
        "place_value": mastery_payload.mastery_place_value,
        "addition": mastery_payload.mastery_addition,
        "subtraction": mastery_payload.mastery_subtraction,
        "multiplication": mastery_payload.mastery_multiplication,
        "division": mastery_payload.mastery_division,
    }


def _select_skill_familiarization(
    grade_valid_skills: Tuple[str, ...], task_index: int, rotation_rng: random.Random,
) -> str:
    """Deterministic, seeded ROTATION -- never ranked by mastery (assessment §5.4). The seed
    only determines the round-robin ORDER (a fair, session-stable permutation of the grade-valid
    skills); ``task_index`` walks that fixed order cyclically, guaranteeing full coverage before
    any skill repeats. Unobserved skills appear only as neutral rotation entries, never
    labelled "weakest" -- this function reads no mastery/observation signal at all."""
    order = list(grade_valid_skills)
    rotation_rng.shuffle(order)
    return order[(task_index - 1) % len(order)]


def _select_skill_mastery_driven(
    grade_valid_skills: Tuple[str, ...],
    mastery_payload: BToCMasteryPayload,
    sessions_since_last_practice: Dict[str, int],
    tie_break_rng: random.Random,
) -> str:
    """SPEC §9.1 ``lowest_mastery_then_coverage``: mastery ascending -> sessions-since-last-
    practice descending -> seeded tie-break."""
    mastery = _mastery_by_skill(mastery_payload)

    def sort_key(skill: str) -> Tuple[float, int]:
        return (mastery[skill], -sessions_since_last_practice.get(skill, 0))

    ordered = sorted(grade_valid_skills, key=sort_key)
    best_key = sort_key(ordered[0])
    tied = sorted(s for s in ordered if sort_key(s) == best_key)
    if len(tied) == 1:
        return tied[0]
    return tied[tie_break_rng.randrange(len(tied))]


def _select_skill_c_only_fallback(
    grade_valid_skills: Tuple[str, ...],
    sessions_since_last_practice: Dict[str, int],
    tie_break_rng: random.Random,
) -> str:
    """SPEC §8.2 fallback: rank by C-owned sessions-since-last-practice descending; seeded
    tie-break. NO mastery input -- ``mastery_payload`` is not even a parameter here."""

    def sort_key(skill: str) -> int:
        return -sessions_since_last_practice.get(skill, 0)

    ordered = sorted(grade_valid_skills, key=sort_key)
    best_key = sort_key(ordered[0])
    tied = sorted(s for s in ordered if sort_key(s) == best_key)
    if len(tied) == 1:
        return tied[0]
    return tied[tie_break_rng.randrange(len(tied))]


def _clamp_initial_difficulty(selected_skill_mastery: float) -> int:
    """SPEC §10: ``initial_level = clamp(round(1 + 4 * mastery_selected_skill), 1, 5)``."""
    raw = round(1 + 4 * selected_skill_mastery)
    return max(1, min(5, raw))


def select_task(
    *,
    session_mode: Literal["combined", "c_only"],
    session_phase: str,
    grade: int,
    catalogue: LoadedCatalogue,
    supported_template_ids: Tuple[str, ...],
    student_id: str,
    c_session_id: str,
    task_index: int,
    mastery_payload: Optional[BToCMasteryPayload],
    sessions_since_last_practice: Dict[str, int],
    component_c_session_lineage: CSeedLineage,
    task_opportunity_lineage: CSeedLineage,
    generation_config: CGenerationConfig,
    selection_config: CSelectionConfig,
) -> SelectionResult:
    """Select a grade-valid skill + active MAIN/SUPPORT template + initial difficulty for one
    task opportunity, then build the C2.1 instance for it.

    ``session_phase`` is caller-supplied, never recomputed here: for a combined session it must
    already be the output of ``phase.decide_session_phase(N, W)``; for a ``c_only`` session it
    must be exactly ``"c_only"``. This function never counts or increments the eligible-handoff
    clock N (that stays a C6/orchestrator responsibility, assessment §5.3).

    ``sessions_since_last_practice`` is a C-owned, per-skill counter supplied by the caller
    (not derived from any B signal, not read from ``CLocalLearnerState``) -- pure input, per
    SPEC §9.1/§8.2's "C-owned sessions-since-last-practice" wording.
    """
    if session_mode == "c_only":
        if session_phase != "c_only":
            raise SelectionInputError("session_mode='c_only' requires session_phase='c_only'")
        if mastery_payload is not None:
            raise SelectionInputError("session_mode='c_only' must not receive a B mastery payload (SF-043)")
    else:
        if session_phase not in ("familiarization", "mastery_driven"):
            raise SelectionInputError(
                f"session_mode='combined' requires session_phase in "
                f"('familiarization', 'mastery_driven'), got {session_phase!r}"
            )
        if session_phase == "mastery_driven" and mastery_payload is None:
            raise SelectionInputError("session_phase='mastery_driven' requires a B mastery payload")
        if mastery_payload is not None and mastery_payload.student_id != student_id:
            raise SelectionInputError("mastery_payload.student_id disagrees with the selection request")

    grade_valid_skills = _grade_valid_skills(catalogue, grade, supported_template_ids)
    if not grade_valid_skills:
        raise SelectionInputError(f"no grade-valid skill has an active template for grade {grade}")

    skill_lineage = derive_child_lineage(task_opportunity_lineage, "selection_skill", "1")
    template_lineage = derive_child_lineage(task_opportunity_lineage, "selection_template", "1")
    template_rng = rng_from(template_lineage)

    if session_phase == "familiarization":
        rotation_lineage = derive_child_lineage(component_c_session_lineage, "selection_rotation", "1")
        rotation_rng = rng_from(rotation_lineage)
        selected_skill = _select_skill_familiarization(grade_valid_skills, task_index, rotation_rng)
        initial_difficulty = selection_config.familiarization_difficulty_level
        mastery_context_mode: MasteryContextMode = "same_session_fresh"
        mastery_selected_skill = None
    elif session_phase == "mastery_driven":
        tie_break_rng = rng_from(skill_lineage)
        selected_skill = _select_skill_mastery_driven(
            grade_valid_skills, mastery_payload, sessions_since_last_practice, tie_break_rng,
        )
        mastery_selected_skill = _mastery_by_skill(mastery_payload)[selected_skill]
        initial_difficulty = _clamp_initial_difficulty(mastery_selected_skill)
        mastery_context_mode = "same_session_fresh"
    else:  # c_only
        tie_break_rng = rng_from(skill_lineage)
        selected_skill = _select_skill_c_only_fallback(grade_valid_skills, sessions_since_last_practice, tie_break_rng)
        initial_difficulty = selection_config.fallback_difficulty_level
        mastery_context_mode = "unavailable_fallback"
        mastery_selected_skill = None

    candidates = _candidate_templates(catalogue, grade, selected_skill, supported_template_ids)
    selected_template = candidates[template_rng.randrange(len(candidates))]

    task_instance = build_task_instance(
        template=selected_template,
        seed_lineage=task_opportunity_lineage,
        grade=grade,
        difficulty_level=initial_difficulty,
        student_id=student_id,
        c_session_id=c_session_id,
        task_index=task_index,
        catalogue_version=catalogue.catalogue_version,
        config=generation_config,
    )

    return SelectionResult(
        session_phase=session_phase,  # type: ignore[arg-type]
        selected_skill_id=selected_skill,
        selected_template_id=selected_template.game_task_template_id,
        initial_difficulty_level=initial_difficulty,
        mastery_context_mode=mastery_context_mode,
        mastery_selected_skill=mastery_selected_skill,
        task_instance=task_instance,
    )
