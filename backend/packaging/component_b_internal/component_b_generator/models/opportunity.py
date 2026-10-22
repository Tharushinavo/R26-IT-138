"""Internal canonical records (SPEC §6.11).

Four canonical streams are designed for: ``b_item_opportunities`` (emitted in Phase B1),
``b_attempt_events``, ``b_skill_mastery_updates``, ``b_session_summaries`` (Phase B2+ stubs).

Phase B1 emits ``GeneratedItemOpportunity`` records whose **attempt-derived** fields
(``first_attempt_correct``, ``final_item_completed``, ``total_attempts``,
``hint_requests_item``, ``first_attempt_error_class``, ``item_difficulty``) are explicit,
typed ``None`` placeholders — listed in ``pending_fields`` — never fabricated.

None of these internal records carry ``population`` / ``dd_subtype`` (audit-only; kept only
on ``LearnerAuditIdentity``). Later ``adapters/`` derive B->C / B->3 payloads from these.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from models.contracts import SKILLS

from .enums import Grade, SessionAttendanceStatus
from .session import SeedLineage

# item_opportunity_id: STU-0001-B003-I002  (learner - B-session index - item index)
ITEM_OPPORTUNITY_ID_RE = re.compile(r"^STU-[0-9]{4}-B[0-9]{3}-I[0-9]{3}$")

# Attempt-derived fields not produced in Phase B1 (declared pending, never fabricated).
PENDING_OPPORTUNITY_FIELDS: Tuple[str, ...] = (
    "item_difficulty",
    "first_attempt_correct",
    "final_item_completed",
    "total_attempts",
    "hint_requests_item",
    "first_attempt_error_class",
)


class GeneratedItemOpportunity(BaseModel):
    """One row of the ``b_item_opportunities`` canonical stream (SPEC §6.11).

    ``curriculum_node_id`` is internal-only and must never be exported to Component C.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # --- identity / lineage ---
    item_opportunity_id: str
    student_id: str
    grade: Grade
    scheduled_session_number: int
    b_session_index: int
    item_index: int  # 1-based, chronological within the B-session
    event_order: int  # monotonic within the B-session (== item_index in B1)

    # --- catalogue linkage ---
    item_template_id: str
    skill_id: str
    curriculum_node_id: str  # INTERNAL ONLY — never crosses B->C

    # --- selection provenance (Phase B1 uses a placeholder; adaptive sequencing is B2+) ---
    selection_reason_internal: str
    seed_lineage: SeedLineage

    # --- attempt-derived fields: PENDING placeholders in Phase B1 (typed, not fabricated) ---
    item_difficulty: Optional[float] = None
    first_attempt_correct: Optional[bool] = None
    final_item_completed: Optional[bool] = None
    total_attempts: Optional[int] = None
    hint_requests_item: Optional[int] = None
    first_attempt_error_class: Optional[str] = None

    generation_phase: str = "B1"
    pending_fields: Tuple[str, ...] = PENDING_OPPORTUNITY_FIELDS

    @field_validator("item_opportunity_id")
    @classmethod
    def _id_format(cls, v: str) -> str:
        if not ITEM_OPPORTUNITY_ID_RE.match(v):
            raise ValueError(f"item_opportunity_id must match {ITEM_OPPORTUNITY_ID_RE.pattern}, got {v!r}")
        return v

    @model_validator(mode="after")
    def _phase_b1_fields_are_pending(self) -> "GeneratedItemOpportunity":
        # In Phase B1 the attempt-derived fields must remain None (nothing fabricated).
        if self.generation_phase == "B1":
            for f in PENDING_OPPORTUNITY_FIELDS:
                if getattr(self, f) is not None:
                    raise ValueError(f"Phase B1 must not populate attempt-derived field {f!r}")
        return self


# --------------------------------------------------------------------------------------
# Phase B2+ canonical-record stubs (designed for; not emitted in Phase B1).
# --------------------------------------------------------------------------------------
#
# NOTE: the canonical ``b_attempt_events`` observable model is now
# :class:`component_b_generator.models.behaviour.BAttemptEvent` (Phase B2B.0). The former
# ``AttemptEvent`` placeholder was retired to avoid two competing canonical definitions.


SKILL_MASTERY_UPDATE_SCHEMA_VERSION = "b3-1.0.0"


class SkillMasteryUpdate(BaseModel):
    """``b_skill_mastery_updates`` — one BKT update per skill-practising opportunity
    (SPEC §6.10). Phase B3.0 — fields only (populated starting B3.2); no update math here.

    ``mastery_before`` / ``mastery_after`` are the pre- and post-update BKT posterior estimates
    ``p(L)`` (never the hidden simulation truth). ``predicted_correct_probability`` is the BKT
    prediction made *before* the observation; ``posterior_l`` is the Bayesian posterior
    ``p(L|obs)`` *before* the ``P(T)`` transition is applied (SPEC §F "pre-P(T) posterior
    direction"); ``mastery_after`` is ``posterior_l`` advanced through the transition. Adding
    these fields is an additive, report-first patch to the ``b3-1.0.0`` schema version — no prior
    field is removed or renamed.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    student_id: str
    skill_id: str
    b_session_index: int
    schema_version: str = SKILL_MASTERY_UPDATE_SCHEMA_VERSION
    generation_phase: str = "PENDING_B3"

    mastery_before: Optional[float] = None
    predicted_correct_probability: Optional[float] = None
    posterior_l: Optional[float] = None
    mastery_after: Optional[float] = None


SESSION_SUMMARY_SCHEMA_VERSION = "b5-1.0.0"

# session_id: STU-0001-B-003  (learner - B-session index), same shape as contracts.BSessionId.
SESSION_ID_RE = re.compile(r"^STU-[0-9]{4}-B-[0-9]{3}$")


class SessionSummary(BaseModel):
    """``b_session_summaries`` — per B-session aggregate (SPEC §6.11).

    Phase B5.0 — shape only: deterministic session identity, ordered opportunity references,
    and placeholders for the per-session totals / per-skill roll-ups the B5.1 aggregator will
    populate. No aggregation math is performed here. A ``missed`` session (SF-040) carries no
    opportunity references or totals — the row exists only to record that the scheduled slot
    was not attended; it is never expanded into per-item rows downstream.

    Carries no ``population``/``dd_subtype``, hidden truth, BKT internals, or
    ``plausibility_floor`` — this is a B-internal record, not a B->C/B->3 export.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # --- identity (deterministic, ordered) ---
    session_id: str
    student_id: str
    b_session_index: int
    scheduled_session_number: int
    status: SessionAttendanceStatus

    # --- ordered references into b_item_opportunities (empty when status == "missed") ---
    opportunity_ids: Tuple[str, ...] = ()

    # --- per-skill roll-up references, canonical SKILLS order, subset of skills practiced ---
    skill_ids_practiced: Tuple[str, ...] = ()

    # --- per-session totals/counts: PENDING placeholders, populated by the B5.1 aggregator ---
    total_opportunities: Optional[int] = None
    total_attempts: Optional[int] = None
    total_correct_first_attempt: Optional[int] = None
    total_hints_requested: Optional[int] = None
    total_response_time_ms: Optional[int] = None

    schema_version: str = SESSION_SUMMARY_SCHEMA_VERSION
    generation_phase: str = "PENDING_B5_1"

    @field_validator("session_id")
    @classmethod
    def _session_id_format(cls, v: str) -> str:
        if not SESSION_ID_RE.match(v):
            raise ValueError(f"session_id must match {SESSION_ID_RE.pattern}, got {v!r}")
        return v

    @field_validator("scheduled_session_number")
    @classmethod
    def _positive_scheduled_session_number(cls, v: int) -> int:
        if v < 1:
            raise ValueError("scheduled_session_number must be >= 1")
        return v

    @model_validator(mode="after")
    def _identity_consistency(self) -> "SessionSummary":
        expected_id = f"{self.student_id}-B-{self.b_session_index:03d}"
        if self.session_id != expected_id:
            raise ValueError(f"session_id {self.session_id!r} must equal {expected_id!r}")
        return self

    @model_validator(mode="after")
    def _opportunity_ids_ordered(self) -> "SessionSummary":
        if len(set(self.opportunity_ids)) != len(self.opportunity_ids):
            raise ValueError("opportunity_ids must not contain duplicates")
        for opp_id in self.opportunity_ids:
            if not ITEM_OPPORTUNITY_ID_RE.match(opp_id):
                raise ValueError(f"opportunity_id {opp_id!r} does not match {ITEM_OPPORTUNITY_ID_RE.pattern}")
        item_indices = [int(opp_id.rsplit("-I", 1)[1]) for opp_id in self.opportunity_ids]
        if item_indices != sorted(item_indices):
            raise ValueError("opportunity_ids must be strictly ordered by ascending item index")
        return self

    @model_validator(mode="after")
    def _skill_ids_practiced_canonical_order(self) -> "SessionSummary":
        if len(set(self.skill_ids_practiced)) != len(self.skill_ids_practiced):
            raise ValueError("skill_ids_practiced must not contain duplicates")
        for skill_id in self.skill_ids_practiced:
            if skill_id not in SKILLS:
                raise ValueError(f"skill_ids_practiced must be one of the seven frozen skills, got {skill_id!r}")
        canonical_order = [s for s in SKILLS if s in self.skill_ids_practiced]
        if list(self.skill_ids_practiced) != canonical_order:
            raise ValueError("skill_ids_practiced must follow the canonical SKILLS order")
        return self

    @model_validator(mode="after")
    def _missed_session_is_empty(self) -> "SessionSummary":
        # A missed scheduled session (SF-040) produces no opportunity/attempt/skill-update rows.
        if self.status == "missed":
            if self.opportunity_ids or self.skill_ids_practiced:
                raise ValueError("a missed session must not carry opportunity_ids or skill_ids_practiced")
            totals = (
                self.total_opportunities,
                self.total_attempts,
                self.total_correct_first_attempt,
                self.total_hints_requested,
                self.total_response_time_ms,
            )
            if any(t is not None for t in totals):
                raise ValueError("a missed session must not carry populated totals")
        return self
