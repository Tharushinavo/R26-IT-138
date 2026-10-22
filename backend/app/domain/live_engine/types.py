"""Backend-owned domain types for the live-engine ports (BE3.1).

These are plain, immutable ``dataclasses`` — never the vendored package's Pydantic models.
Field sets are the subset the BE3 adapter and its tests need; they are not a 1:1 mirror of every
package model field. Later batches (BE3c, BE4) may extend these types as new capabilities are
wired, but must not reach for the package's own models to do it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Optional, Sequence

Grade = int  # 2 or 3, enforced by callers/validators at the boundary


# --------------------------------------------------------------------------------------
# Catalogue
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ItemTemplate:
    item_template_id: str
    skill_id: str
    curriculum_node_id: str
    difficulty_level: str
    task_type: str
    representation_type: str
    evidence_status: str
    eligible_grades: tuple[int, ...]
    grade_gate_status: str
    prerequisite_nodes: tuple[str, ...] = ()

    def is_eligible_for_grade(self, grade: Grade) -> bool:
        return grade in self.eligible_grades

    def is_active(self) -> bool:
        tag = self.evidence_status.strip().upper()
        return not (tag.startswith("RETIRED") or tag.startswith("DEFERRED"))


@dataclass(frozen=True)
class Catalogue:
    catalogue_version: str
    catalogue_status: str
    source_path: str
    skills: tuple[str, ...]
    templates: tuple[ItemTemplate, ...]

    def by_id(self, item_template_id: str) -> Optional[ItemTemplate]:
        for template in self.templates:
            if template.item_template_id == item_template_id:
                return template
        return None

    def eligible_for(self, grade: Grade, skill_id: Optional[str] = None) -> tuple[ItemTemplate, ...]:
        out = [
            t
            for t in self.templates
            if t.is_active() and t.is_eligible_for_grade(grade) and (skill_id is None or t.skill_id == skill_id)
        ]
        return tuple(sorted(out, key=lambda t: t.item_template_id))


# --------------------------------------------------------------------------------------
# Activation
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ActivationDecision:
    item_template_id: str
    recognized: bool
    implementation_supported: bool
    grade_eligible: bool
    curriculum_active: bool
    catalogue_status_ok: bool
    calibration_restricted: bool
    active: bool
    reason: str


# --------------------------------------------------------------------------------------
# Sequencing
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class SequencingCandidate:
    skill_id: str
    item_template_id: str
    difficulty_band: int


@dataclass(frozen=True)
class SequencingFeatures:
    mastery_gap: float
    prerequisite_readiness: float
    spacing_due: float


@dataclass(frozen=True)
class SequencingWeights:
    """The FROZEN 0.50/0.30/0.20 weights (BEplan §"sequencing uses the frozen weighted
    score"). Callers never supply a different set through this type; the adapter re-validates
    the pinned values against the package's own frozen config before scoring."""

    mastery_gap: float = 0.50
    prerequisite_readiness: float = 0.30
    spacing_due: float = 0.20


@dataclass(frozen=True)
class ScoredCandidate:
    candidate: SequencingCandidate
    features: SequencingFeatures
    score: float


@dataclass(frozen=True)
class SelectionReason:
    winning_item_template_id: str
    winning_skill_id: str
    score: float
    mastery_gap: float
    prerequisite_readiness: float
    spacing_due: float
    tie_broken: bool
    tie_break_basis: str


@dataclass(frozen=True)
class SelectionResult:
    candidate: SequencingCandidate
    selection_reason: SelectionReason


# --------------------------------------------------------------------------------------
# Deterministic task construction
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class TaskConstructionRequest:
    """Everything the adapter needs to build one deterministic task instance.

    ``global_seed`` is the session-pinned root seed (BE2 runtime pinning); the adapter derives
    the package's internal opportunity/instance seed lineage from it. Callers never construct a
    package ``SeedLineage`` themselves.
    """

    item_opportunity_id: str
    student_id: str
    grade: Grade
    scheduled_session_number: int
    b_session_index: int
    item_index: int
    event_order: int
    item_template_id: str
    skill_id: str
    curriculum_node_id: str
    selection_reason_internal: str
    global_seed: int


@dataclass(frozen=True)
class TaskInstance:
    item_instance_id: str
    item_opportunity_id: str
    item_template_id: str
    skill_id: str
    grade: Grade
    difficulty_level: str
    representation_type: str
    response_format: str
    generated_operands: Mapping[str, object]
    prompt: Mapping[str, object]
    correct_answer: str
    allowed_equivalent_answers: tuple[str, ...]
    distractor_candidates: tuple[str, ...]
    distractor_rule_ids: tuple[str, ...]
    generation_seed: int
    catalogue_version: str
    catalogue_checksum: str
    applied_guard_ids: tuple[str, ...]


# --------------------------------------------------------------------------------------
# Hints
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class HintReference:
    item_template_id: str
    hint_level: int
    content: str
    content_id: str
    catalogue_version: str
    catalogue_checksum: str


# --------------------------------------------------------------------------------------
# BKT
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class SkillBktParams:
    p_l0: float
    p_t: float
    p_g: float
    p_s: float


@dataclass(frozen=True)
class BktConfig:
    skill_params: Mapping[str, SkillBktParams]
    theta_b: float
    floor_quantile: float
    floor_min_obs: int
    config_version: str
    parameter_source_status: str


class GuessGuardStatus(str, Enum):
    NOT_TRIGGERED = "NOT_TRIGGERED"
    TRIGGERED = "TRIGGERED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


# --------------------------------------------------------------------------------------
# Session aggregation
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class OpportunityResponse:
    """Domain mirror of the reviewed subset of ``BOpportunityResponseSummary`` needed for
    session aggregation. No hidden truth, no ``population``/``dd_subtype``."""

    learner_id: str
    session_id: str
    scheduled_session_index: int
    item_opportunity_id: str
    task_instance_id: str
    item_template_id: str
    skill_id: str
    first_attempt_correct: bool
    first_attempt_error_pattern: str
    total_attempts: int
    hint_requested: bool
    hint_count: int
    final_item_completed: bool
    assisted_completion: bool
    unassisted_completion: bool
    total_response_time_ms: int
    first_attempt_response_time_ms: int


@dataclass(frozen=True)
class SkillMasteryUpdate:
    student_id: str
    skill_id: str
    b_session_index: int
    mastery_before: Optional[float]
    predicted_correct_probability: Optional[float]
    posterior_l: Optional[float]
    mastery_after: Optional[float]


@dataclass(frozen=True)
class SessionIdentity:
    student_id: str
    b_session_index: int
    scheduled_session_number: int
    status: str  # "attended" | "missed"


@dataclass(frozen=True)
class SkillSessionRollup:
    skill_id: str
    opportunities: int
    attempts: int
    first_attempt_correct: int
    first_attempt_accuracy: float
    estimated_mastery: Optional[float]
    certified: Optional[bool]


@dataclass(frozen=True)
class SessionAggregateStats:
    session_id: str
    first_attempt_accuracy: Optional[float]
    completion_count: int
    completion_rate: Optional[float]
    total_retries: int
    hint_bearing_opportunities: int
    response_time_mean_ms: Optional[float]
    response_time_median_ms: Optional[float]
    response_time_std_ms: Optional[float]
    error_class_distribution: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class SessionAggregate:
    session_id: str
    status: str
    opportunity_ids: tuple[str, ...]
    skill_ids_practiced: tuple[str, ...]
    stats: SessionAggregateStats
    skill_rollups: tuple[SkillSessionRollup, ...]
