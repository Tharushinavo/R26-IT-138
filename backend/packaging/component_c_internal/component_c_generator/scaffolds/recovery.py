"""Recovery-task realization (SPEC §9, §10, §15) -- built THROUGH the committed C2.1
generation engine, never hand-rolled. A recovery task is always: difficulty level 1 (SPEC §10
cap "recovery -> 1"), scaffold state C4 (SPEC §15 "recovery_task"), time pressure removed, and
linked to its parent via ``recovery_parent_instance_id``. It never reads, writes, or emits B
mastery -- this module imports nothing from ``models.contracts`` and has no B-shaped parameter
anywhere, so there is no code path through which a B mastery value could enter or leave it.

SPEC §9 redirection precondition: "allowed only when a catalogue prerequisite relationship
exists AND the prerequisite mastery bucket is low, OR safety/recovery requires a reviewed
support task." This module does not itself derive prerequisite relationships from the catalogue
(the committed ``LoadedGameTaskTemplate`` carries no prerequisite field to derive them from --
see the module docstring note below); the precondition is instead an explicit, caller-supplied
assertion (``safety_required`` or a genuine ``PrerequisiteRedirectContext`` with a low mastery
bucket) that this function enforces structurally: calling it with neither raises
``RecoveryPreconditionError`` before any task is built. "Record requested vs. applied skill
internally; do not export prerequisite internals" (SPEC §9) -- the prerequisite node id is read
only to satisfy the precondition check and never appears on the returned ``GameTaskInstance``
(which has no field for it).
"""

from __future__ import annotations

from typing import Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict, field_validator

from ..catalogue.loaded_models import LoadedCatalogue, LoadedGameTaskTemplate
from ..eligibility import eligible_templates
from ..generation import build_task_instance
from ..generation_config import CGenerationConfig
from ..models.task_instance import GameTaskInstance
from ..seeds import CSeedLineage, rng_from
from .config import CRecoveryConfig

RECOVERY_BUILDER_VERSION = "c4.2-recovery-builder-1.0.0"

# SPEC §10/§15: frozen structural facts of what a recovery task IS, not tunable numbers.
RECOVERY_DIFFICULTY_LEVEL = 1
RECOVERY_SCAFFOLD_STATE: Literal["C4"] = "C4"
_RECOVERY_ROLE_PRIORITY: Tuple[Tuple[str, ...], ...] = (("RECOVERY_ONLY",), ("SUPPORT", "MAIN_SUPPORT"))

MasteryBucket = Literal["low", "medium", "high"]


class PrerequisiteRedirectContext(BaseModel):
    """A caller-asserted catalogue prerequisite relationship + mastery bucket (SPEC §9). The
    caller (a future C6/curriculum-aware orchestrator) is responsible for having verified the
    relationship against the authoritative curriculum DAG; this module only enforces that the
    bucket is genuinely ``"low"`` before treating it as license to redirect."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    prerequisite_curriculum_node_id: str  # internal-only; never placed on the returned instance
    prerequisite_mastery_bucket: MasteryBucket

    @field_validator("prerequisite_curriculum_node_id")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not str(v).strip():
            raise ValueError("prerequisite_curriculum_node_id must be non-empty")
        return v


class RecoveryPreconditionError(ValueError):
    """Raised when neither ``safety_required`` nor a low-mastery-bucket ``prerequisite_context``
    is supplied (SPEC §9 redirection precondition not met)."""


class NoEligibleRecoveryTemplateError(RuntimeError):
    """Raised when the catalogue has no eligible reviewed RECOVERY_ONLY/SUPPORT/MAIN_SUPPORT
    template for the requested skill+grade. Never invented -- the caller must resolve this
    (e.g. by choosing a different skill) rather than this module fabricating a template."""


def _eligible_recovery_candidates(
    catalogue: LoadedCatalogue,
    grade: int,
    skill_id: str,
    supported_template_ids: Tuple[str, ...],
) -> Tuple[LoadedGameTaskTemplate, ...]:
    """RECOVERY_ONLY templates first; if none exist for this skill+grade, fall back to a
    reviewed SUPPORT/MAIN_SUPPORT template (SPEC §4.2 build-agent brief: "RECOVERY_ONLY role if
    the catalogue provides one for the skill, else a SUPPORT-role reviewed template").

    Matches on ``template.primary_skill_ids[0] == skill_id`` (not "skill_id is anywhere in the
    tuple"): ``generation.build_task_instance`` always records ``skill_id =
    template.primary_skill_ids[0]`` on the built instance, so matching on anything looser would
    let a multi-skill template whose FIRST skill differs from the requested one slip in --
    producing a recovery instance whose own ``skill_id`` field silently disagrees with the
    skill it was supposedly built to recover.
    """
    pool = eligible_templates(catalogue, grade, supported_template_ids)
    for roles in _RECOVERY_ROLE_PRIORITY:
        candidates = tuple(
            sorted(
                (t for t in pool if t.primary_skill_ids[0] == skill_id and t.functional_role in roles),
                key=lambda t: t.game_task_template_id,
            )
        )
        if candidates:
            return candidates
    return ()


def build_recovery_task(
    parent_instance: GameTaskInstance,
    skill_id: str,
    task_index: int,
    catalogue: LoadedCatalogue,
    supported_template_ids: Tuple[str, ...],
    generation_config: CGenerationConfig,
    seed_lineage: CSeedLineage,
    recovery_config: CRecoveryConfig,
    *,
    safety_required: bool = False,
    prerequisite_context: Optional[PrerequisiteRedirectContext] = None,
) -> GameTaskInstance:
    """Build one recovery task instance for ``skill_id``, chained to ``parent_instance``.

    ``task_index`` is the recovery task's OWN position in the session's task sequence (caller-
    supplied, like every other task index in this codebase -- never invented here). It is
    deliberately a separate parameter from ``parent_instance.task_index`` so that repeated
    recovery calls (SPEC §15 "recovery may repeat") each get their own distinct
    ``game_task_instance_id`` rather than colliding on the parent's index.

    Enforces the SPEC §9 redirection precondition (``safety_required`` OR a genuinely
    low-mastery ``prerequisite_context``) before doing anything else. Built THROUGH
    ``generation.build_task_instance`` (the sole authority for task mathematical content) at
    ``difficulty_level=1``; the two recovery-specific fields (``scaffold_state``,
    ``recovery_parent_instance_id``) and the "time pressure removed" difficulty-vector marker
    are then applied via a full re-validating ``model_validate`` copy (standard pydantic API on
    the committed, unmodified ``GameTaskInstance`` model -- not a change to that model).
    """
    if not safety_required and not (
        prerequisite_context is not None and prerequisite_context.prerequisite_mastery_bucket == "low"
    ):
        raise RecoveryPreconditionError(
            "SPEC §9: recovery/redirection requires safety_required=True OR a "
            "prerequisite_context with prerequisite_mastery_bucket=='low'; neither was given."
        )

    grade = parent_instance.grade_scope
    candidates = _eligible_recovery_candidates(catalogue, grade, skill_id, supported_template_ids)
    if not candidates:
        raise NoEligibleRecoveryTemplateError(
            f"no eligible RECOVERY_ONLY/SUPPORT/MAIN_SUPPORT template exists for skill "
            f"{skill_id!r} at grade {grade} -- not fabricating one (SPEC §9)."
        )

    rng = rng_from(seed_lineage)
    template = candidates[rng.randrange(len(candidates))]

    base_instance = build_task_instance(
        template=template,
        seed_lineage=seed_lineage,
        grade=grade,
        difficulty_level=RECOVERY_DIFFICULTY_LEVEL,
        student_id=parent_instance.student_id,
        c_session_id=parent_instance.c_session_id,
        task_index=task_index,
        catalogue_version=catalogue.catalogue_version,
        config=generation_config,
    )

    recovery_difficulty_vector = dict(base_instance.difficulty_vector)
    recovery_difficulty_vector["time_pressure"] = "removed"  # SPEC §15: "C4 removes time pressure"

    recovery_payload = {
        **base_instance.model_dump(),
        "scaffold_state": RECOVERY_SCAFFOLD_STATE,
        "recovery_parent_instance_id": parent_instance.game_task_instance_id,
        "difficulty_vector": recovery_difficulty_vector,
    }
    return GameTaskInstance.model_validate(recovery_payload)
