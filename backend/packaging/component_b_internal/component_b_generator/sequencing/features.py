"""Per-candidate sequencing feature computation (Phase B4.2).

Three bounded ``[0,1]`` features per candidate, computed from the BKT *estimate* only (never
hidden true mastery) and the existing catalogue prerequisite structure (never a new DAG type).
This slice computes features only — no weighted score, no selection (B4.3), no task-instance
wiring (B4.4).

**Prerequisite DAG source.** ``dag`` is the existing :class:`models.catalogue.LoadedCatalogue`
already loaded elsewhere in the pipeline. A template's prerequisites
(``template.prerequisite_nodes``) are ``curriculum_node_id`` references; this module resolves
each to its owning template's ``skill_id`` via the catalogue -- no new DAG structure is invented.

**Soft prerequisites (B-Q4).** ``prerequisite_readiness`` is a scoring *signal* only; nothing in
this module excludes a candidate on unmet prerequisites (that remains B4.1's job, unchanged).
"""

from __future__ import annotations

from typing import Mapping, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..bkt.config import BBKTConfig
from ..bkt.state import BBKTSkillState
from ..models.catalogue import LoadedCatalogue
from .models import SequencingCandidate

# Deterministic spacing transform (documented, no external dependency, no RNG): spacing_due
# rises linearly with "sessions since last practice" and saturates at 1.0 once that gap reaches
# this many sessions. A never-practised skill is maximally due (1.0) regardless of the cap.
SPACING_DUE_SATURATION_SESSIONS = 4


class SequencingFeatures(BaseModel):
    """The three bounded ``[0,1]`` sequencing features for one candidate (Phase B4.2)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mastery_gap: float = Field(ge=0.0, le=1.0)
    prerequisite_readiness: float = Field(ge=0.0, le=1.0)
    spacing_due: float = Field(ge=0.0, le=1.0)


def _estimated_mastery(
    skill_id: str, mastery: Mapping[str, BBKTSkillState], config: BBKTConfig
) -> float:
    """The BKT estimate p(L) for ``skill_id`` -- never hidden true mastery. Missing state falls
    back to that skill's prior ``P(L0)`` from the config (SPEC: "missing mastery => P(L0)-level
    gap")."""
    state = mastery.get(skill_id)
    if state is not None:
        return state.p_l
    return config.skill_params[skill_id].p_l0


def _prerequisite_skill_ids(candidate: SequencingCandidate, dag: LoadedCatalogue) -> tuple[str, ...]:
    """Resolve the candidate's template's ``prerequisite_nodes`` (curriculum_node_id references)
    to their owning skills via the existing catalogue -- reuses the catalogue as the prerequisite
    DAG source rather than inventing a new one."""
    template = dag.by_id(candidate.item_template_id)
    if template is None or not template.prerequisite_nodes:
        return ()
    node_to_skill = {t.curriculum_node_id: t.skill_id for t in dag.templates}
    return tuple(
        node_to_skill[node] for node in template.prerequisite_nodes if node in node_to_skill
    )


def compute_features(
    candidate: SequencingCandidate,
    mastery: Mapping[str, BBKTSkillState],
    dag: LoadedCatalogue,
    history: Mapping[str, Optional[int]],
    config: BBKTConfig,
) -> SequencingFeatures:
    """Pure, deterministic per-candidate feature computation. No mutation of any input.

    - ``mastery_gap = 1 - estimated_mastery[candidate.skill_id]`` (missing => ``1 - P(L0)``).
    - ``prerequisite_readiness`` = mean estimated mastery across the candidate skill's
      prerequisite *skills* (resolved via ``dag``); ``1.0`` when there are none (soft signal
      only, B-Q4 -- never a hard gate).
    - ``spacing_due``: ``1.0`` when ``history[candidate.skill_id]`` is missing/``None`` (never
      practised); otherwise a deterministic, monotonically non-decreasing transform of "sessions
      since last practice" (see ``SPACING_DUE_SATURATION_SESSIONS``), bounded ``[0,1]``.
    """
    skill_id = candidate.skill_id

    mastery_gap = 1.0 - _estimated_mastery(skill_id, mastery, config)

    prereq_skills = _prerequisite_skill_ids(candidate, dag)
    if not prereq_skills:
        prerequisite_readiness = 1.0
    else:
        prerequisite_readiness = sum(
            _estimated_mastery(parent_skill, mastery, config) for parent_skill in prereq_skills
        ) / len(prereq_skills)

    sessions_since_practice = history.get(skill_id)
    if sessions_since_practice is None:
        spacing_due = 1.0
    else:
        spacing_due = min(1.0, max(0.0, sessions_since_practice) / SPACING_DUE_SATURATION_SESSIONS)

    return SequencingFeatures(
        mastery_gap=mastery_gap,
        prerequisite_readiness=prerequisite_readiness,
        spacing_due=spacing_due,
    )
