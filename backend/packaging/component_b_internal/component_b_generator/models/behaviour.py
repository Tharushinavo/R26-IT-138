"""Observable opportunity-response summary schema (subset of Phase B2B.0 interaction models).

PACKAGING NOTE (upadya-component-b-live-engine): this file is a reviewed live-safe subset of
the pinned Yass source file ``component_b_generator/models/behaviour.py``. ``ERROR_PATTERNS``,
``ErrorPattern``, ``HINT_LEVELS``, ``_require_skill``, and :class:`BOpportunityResponseSummary`
are byte-identical to the pinned commit and are the only symbols required by the reviewed
live-safe closure (``behaviour.hints`` and ``aggregation.session``; see
``backend/provenance/component-b-live-engine-reuse-map.json``).

Removed, and therefore unreachable from this package, are the audit-only hidden-truth and
synthetic-behaviour-generation models from the pinned source: ``AuditOnlyModel``,
``BLearnerSkillTruth`` (hidden mastery / behavioural trait truth), ``BAttemptEvent``,
``BoundedBetaSpec`` / ``BoundedNormalSpec`` / ``BTruthInitializationConfig`` /
``BInitialLearnerSkillTruth`` (synthetic trait initialization), ``LognormalLatencySpec`` /
``BFirstAttemptBehaviourConfig`` (simulated latency / first-attempt generation), and
``BAttemptLoopConfig`` / ``BOpportunityAttemptResult`` (synthetic attempt-loop generation).
These are explicitly prohibited from the application per
``backend/provenance/component-b-live-engine-reuse-map.json``
(``explicitly_prohibited_from_application``: hidden learner truth, synthetic learner traits,
``behaviour.first_attempt``, ``behaviour.latency``, ``behaviour.attempt_loop``). Neither
retained symbol references any of the removed classes.
"""

from __future__ import annotations

from typing import Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from models.contracts import SKILLS  # single source of truth: the seven frozen skills

# Frozen Component B error-evidence vocabulary (spec §17). Validates only; never infers or
# generates them.
ERROR_PATTERNS: Tuple[str, ...] = (
    "correct",
    "off_by_one",
    "place_value",
    "operator_confusion",
    "transposition",
    "fact_retrieval",
    "timeout_no_response",
    "random",
)
ErrorPattern = Literal[
    "correct",
    "off_by_one",
    "place_value",
    "operator_confusion",
    "transposition",
    "fact_retrieval",
    "timeout_no_response",
    "random",
]

HINT_LEVELS: Tuple[int, ...] = (1, 2, 3)  # template-controlled L1/L2/L3

_SEVEN_SKILLS = frozenset(SKILLS)


def _require_skill(v: str) -> str:
    if v not in _SEVEN_SKILLS:
        raise ValueError(f"skill_id must be one of the seven frozen skills {tuple(SKILLS)}, got {v!r}")
    return v


class BOpportunityResponseSummary(BaseModel):
    """Opportunity-level record derived from ``b_attempt_events`` (spec §24).

    This is NOT a session summary; it is local opportunity-level derivation only. It never
    carries hidden truth, ``population``/``dd_subtype``, BKT, certification, sequencing, or
    downstream data.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    learner_id: str
    session_id: str
    scheduled_session_index: int = Field(ge=1)
    item_opportunity_id: str
    task_instance_id: str
    item_template_id: str
    skill_id: str

    first_attempt_correct: bool
    first_attempt_error_pattern: ErrorPattern
    total_attempts: int = Field(ge=1)
    retry_count: int = Field(ge=0)
    hint_requested: bool
    hint_count: int = Field(ge=0)
    final_item_completed: bool
    assisted_completion: bool
    unassisted_completion: bool
    total_response_time_ms: int = Field(ge=0)
    first_attempt_response_time_ms: int = Field(ge=0)
    final_submitted_answer: Optional[str] = None

    derivation_version: str
    source_event_schema_version: str

    _skill = field_validator("skill_id")(_require_skill)

    @model_validator(mode="after")
    def _summary_invariants(self) -> "BOpportunityResponseSummary":
        if self.retry_count != self.total_attempts - 1:
            raise ValueError("retry_count must equal total_attempts - 1")
        if self.hint_count > self.total_attempts:
            raise ValueError("hint_count cannot exceed total_attempts (one hint per attempt max)")
        if self.total_response_time_ms < self.first_attempt_response_time_ms:
            raise ValueError("total_response_time_ms cannot be less than first_attempt_response_time_ms")
        if self.first_attempt_correct != (self.first_attempt_error_pattern == "correct"):
            raise ValueError("first_attempt_correct must agree with first_attempt_error_pattern")
        if self.assisted_completion and self.unassisted_completion:
            raise ValueError("assisted_completion and unassisted_completion cannot both be true")
        if self.final_item_completed:
            if not (self.assisted_completion ^ self.unassisted_completion):
                raise ValueError("a completed item must be exactly one of assisted / unassisted")
            if self.assisted_completion and self.hint_count < 1:
                raise ValueError("assisted_completion requires hint_count >= 1")
            if self.unassisted_completion and self.hint_count != 0:
                raise ValueError("unassisted_completion requires hint_count == 0")
        else:
            if self.assisted_completion or self.unassisted_completion:
                raise ValueError("an incomplete item cannot be assisted or unassisted completed")
        return self
