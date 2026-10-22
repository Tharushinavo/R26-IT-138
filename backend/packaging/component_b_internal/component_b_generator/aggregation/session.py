"""Phase B5.1 — fold one B-session's opportunity/skill-update rows into aggregates.

``aggregate_session`` is a pure function: no seed/RNG, no mutation of its inputs, and no read
of ``population``/``dd_subtype``/hidden truth. It reuses the B2B ``BOpportunityResponseSummary``
(first-attempt correctness, response time, hints, error class), the B3 ``SkillMasteryUpdate``
(BKT posterior *estimate*, never truth) plus ``certify_skill``/``GuessGuardStatus`` (B3.4/B3.3),
and the B5.0 ``SessionSummary`` shape. It builds no B->C / B->3 adapter and serializes nothing.

Design choices (documented per SPEC §G):

- **Response-time statistics** are computed only over *non-timeout* first-attempt response
  times. A ``timeout_no_response`` observation has no genuine response latency to measure (the
  learner never answered), so including it would distort the RT distribution even though the
  timeout correctly counts as an incorrect first attempt everywhere else (totals, accuracy,
  error-class distribution). This is the "timeout => incorrect" semantics applied to
  *correctness*, deliberately not extended to *timing*.
- **Standard deviation** is the *population* std (``ddof=0``): a session's opportunities are the
  complete set of observations for that session, not a sample drawn from a larger population of
  sessions, so there is no unbiasing correction to apply. Computed deterministically with no
  floating-point-order sensitivity (single pass over a fixed, pre-sorted sequence).
- **Median** reuses ``bkt.guess_guard._quantile`` (type-7 / ``numpy.quantile`` default) at
  ``q=0.5`` rather than re-implementing quantile interpolation.
- **Error-class distribution** is a fraction over *error-bearing* observations only (
  ``first_attempt_error_pattern != "correct"``), summing to ``1.0`` when at least one exists.
  With zero error-bearing observations the distribution is the empty mapping ``{}`` — not a
  fabricated uniform distribution over the taxonomy — signalling "no error evidence this
  session" rather than asserting a shape for evidence that does not exist.
- **Per-skill estimated mastery** is the *last* ``SkillMasteryUpdate.mastery_after`` for that
  skill in session order (the most recent BKT posterior estimate produced during the session).
  Certification is computed via the frozen, non-sticky ``certify_skill`` rule from that estimate
  plus an externally-supplied Guess-Guard status; both are ``None`` when the caller does not
  supply the guard status / threshold for a skill, never fabricated.
- **Missed sessions** (SF-040): a session with ``status="missed"`` yields a ``SessionSummary``
  with no opportunity/skill references and no populated totals (enforced by the B5.0 validators)
  and no ``SkillSessionRollup`` rows; ``opportunities`` / ``skill_mastery_updates`` must be empty.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Sequence, Tuple

from pydantic import BaseModel, ConfigDict, Field

from ..bkt.certification import certify_skill
from ..bkt.guess_guard import GuessGuardStatus, _quantile
from ..models.behaviour import ERROR_PATTERNS, BOpportunityResponseSummary
from ..models.enums import SessionAttendanceStatus
from ..models.opportunity import (
    SESSION_SUMMARY_SCHEMA_VERSION,
    SessionSummary,
    SkillMasteryUpdate,
)
from models.contracts import SKILLS

B5_1_GENERATION_PHASE = "B5.1"

# Error-bearing classes: the frozen taxonomy minus "correct" (SPEC §17).
_ERROR_BEARING_CLASSES: Tuple[str, ...] = tuple(p for p in ERROR_PATTERNS if p != "correct")


@dataclass(frozen=True)
class SessionIdentity:
    """The deterministic session-identity inputs ``aggregate_session`` needs (SPEC §6.11)."""

    student_id: str
    b_session_index: int
    scheduled_session_number: int
    status: SessionAttendanceStatus


class SkillSessionRollup(BaseModel):
    """Per-skill roll-up for one session: observed counts/accuracy plus the *estimated* BKT
    mastery and certification decision (never hidden truth — SPEC §G)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    skill_id: str
    opportunities: int = Field(ge=0)
    attempts: int = Field(ge=0)
    first_attempt_correct: int = Field(ge=0)
    first_attempt_accuracy: float = Field(ge=0.0, le=1.0)
    estimated_mastery: Optional[float] = None
    certified: Optional[bool] = None


class SessionAggregateStats(BaseModel):
    """Session-level derived statistics not carried directly on ``SessionSummary`` (SPEC §G)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    session_id: str
    first_attempt_accuracy: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    completion_count: int = Field(ge=0)
    completion_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    total_retries: int = Field(ge=0)
    # Count of OPPORTUNITIES that received >=1 hint (bounded by total_opportunities) -- distinct
    # from the raw hint-EVENT total on SessionSummary.total_hints_requested, which can exceed
    # total_opportunities when a single opportunity accumulates hints across multiple retry
    # attempts. Added to feed the B->3 adapter's `hint_requests` field, whose contract invariant
    # (DF-02: hint_requests <= total_questions) counts questions-with-a-hint, not hint events.
    hint_bearing_opportunities: int = Field(ge=0)
    response_time_mean_ms: Optional[float] = None
    response_time_median_ms: Optional[float] = None
    response_time_std_ms: Optional[float] = None
    error_class_distribution: Mapping[str, float] = Field(default_factory=dict)


@dataclass(frozen=True)
class SessionAggregationResult:
    summary: SessionSummary
    stats: SessionAggregateStats
    skill_rollups: Tuple[SkillSessionRollup, ...]


def _session_id(student_id: str, b_session_index: int) -> str:
    return f"{student_id}-B-{b_session_index:03d}"


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


def _population_std(values: Sequence[float], mean: float) -> float:
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return variance**0.5


def _response_time_stats(
    opportunities: Sequence[BOpportunityResponseSummary],
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    rts = [
        float(opp.first_attempt_response_time_ms)
        for opp in opportunities
        if opp.first_attempt_error_pattern != "timeout_no_response"
    ]
    if not rts:
        return None, None, None
    mean = _mean(rts)
    median = _quantile(sorted(rts), 0.5)
    # Std is undefined for <2 timed responses and 0.0 for zero variance; contracts.py's
    # b_item_response_time_std_sec is PositiveTiming | None (gt=0.0), so export None rather
    # than a rejected 0.0 — same "no usable evidence" precedent as the all-timeout None case.
    std = _population_std(rts, mean) if len(rts) >= 2 else None
    if std == 0.0:
        std = None
    return mean, median, std


def _error_class_distribution(
    opportunities: Sequence[BOpportunityResponseSummary],
) -> Mapping[str, float]:
    error_bearing = [
        opp.first_attempt_error_pattern
        for opp in opportunities
        if opp.first_attempt_error_pattern != "correct"
    ]
    if not error_bearing:
        return {}
    total = len(error_bearing)
    counts: dict[str, int] = {cls: 0 for cls in _ERROR_BEARING_CLASSES}
    for cls in error_bearing:
        counts[cls] += 1
    return {cls: count / total for cls, count in counts.items() if count > 0}


def _skill_rollups(
    opportunities: Sequence[BOpportunityResponseSummary],
    skill_mastery_updates: Sequence[SkillMasteryUpdate],
    guard_statuses: Optional[Mapping[str, GuessGuardStatus]],
    theta_B: Optional[float],
) -> Tuple[SkillSessionRollup, ...]:
    by_skill: dict[str, list[BOpportunityResponseSummary]] = {}
    for opp in opportunities:
        by_skill.setdefault(opp.skill_id, []).append(opp)

    latest_mastery: dict[str, float] = {}
    for update in skill_mastery_updates:
        if update.mastery_after is not None:
            latest_mastery[update.skill_id] = update.mastery_after

    rollups: list[SkillSessionRollup] = []
    for skill_id in SKILLS:
        skill_opps = by_skill.get(skill_id)
        if not skill_opps:
            continue
        opportunities_count = len(skill_opps)
        attempts_count = sum(o.total_attempts for o in skill_opps)
        correct_count = sum(1 for o in skill_opps if o.first_attempt_correct)
        estimated_mastery = latest_mastery.get(skill_id)

        certified: Optional[bool] = None
        if estimated_mastery is not None and theta_B is not None and guard_statuses is not None:
            guard_status = guard_statuses.get(skill_id)
            if guard_status is not None:
                certified = certify_skill(estimated_mastery, guard_status, theta_B)

        rollups.append(
            SkillSessionRollup(
                skill_id=skill_id,
                opportunities=opportunities_count,
                attempts=attempts_count,
                first_attempt_correct=correct_count,
                first_attempt_accuracy=correct_count / opportunities_count,
                estimated_mastery=estimated_mastery,
                certified=certified,
            )
        )
    return tuple(rollups)


def aggregate_session(
    session_identity: SessionIdentity,
    opportunities: Sequence[BOpportunityResponseSummary],
    skill_mastery_updates: Sequence[SkillMasteryUpdate],
    *,
    guard_statuses: Optional[Mapping[str, GuessGuardStatus]] = None,
    theta_B: Optional[float] = None,
) -> SessionAggregationResult:
    """Fold one session's opportunity/skill-update rows into a ``SessionSummary`` plus derived
    stats and per-skill roll-ups. Pure: no seed, no mutation of ``opportunities`` /
    ``skill_mastery_updates``, no ``population``/``dd_subtype``/hidden-truth read.

    ``guard_statuses`` / ``theta_B`` are optional externally-supplied Guess-Guard inputs (B3.3);
    without them, ``SkillSessionRollup.certified`` stays ``None`` rather than being fabricated.
    """
    session_id = _session_id(session_identity.student_id, session_identity.b_session_index)

    if session_identity.status == "missed":
        if opportunities or skill_mastery_updates:
            raise ValueError("a missed session must not receive opportunities or skill_mastery_updates")
        summary = SessionSummary(
            session_id=session_id,
            student_id=session_identity.student_id,
            b_session_index=session_identity.b_session_index,
            scheduled_session_number=session_identity.scheduled_session_number,
            status="missed",
            schema_version=SESSION_SUMMARY_SCHEMA_VERSION,
            generation_phase=B5_1_GENERATION_PHASE,
        )
        stats = SessionAggregateStats(
            session_id=session_id,
            completion_count=0,
            total_retries=0,
            hint_bearing_opportunities=0,
        )
        return SessionAggregationResult(summary=summary, stats=stats, skill_rollups=())

    ordered = tuple(sorted(opportunities, key=lambda o: o.item_opportunity_id))

    total_opportunities = len(ordered)
    total_attempts = sum(o.total_attempts for o in ordered)
    total_correct_first_attempt = sum(1 for o in ordered if o.first_attempt_correct)
    total_hints_requested = sum(o.hint_count for o in ordered)
    hint_bearing_opportunities = sum(1 for o in ordered if o.hint_requested)
    total_response_time_ms = sum(o.total_response_time_ms for o in ordered)
    completion_count = sum(1 for o in ordered if o.final_item_completed)
    total_retries = total_attempts - total_opportunities

    first_attempt_accuracy = (
        total_correct_first_attempt / total_opportunities if total_opportunities else None
    )
    completion_rate = completion_count / total_opportunities if total_opportunities else None

    rt_mean, rt_median, rt_std = _response_time_stats(ordered)
    error_dist = _error_class_distribution(ordered)

    skills_practiced = tuple(
        skill_id for skill_id in SKILLS if any(o.skill_id == skill_id for o in ordered)
    )

    summary = SessionSummary(
        session_id=session_id,
        student_id=session_identity.student_id,
        b_session_index=session_identity.b_session_index,
        scheduled_session_number=session_identity.scheduled_session_number,
        status="attended",
        opportunity_ids=tuple(o.item_opportunity_id for o in ordered),
        skill_ids_practiced=skills_practiced,
        total_opportunities=total_opportunities,
        total_attempts=total_attempts,
        total_correct_first_attempt=total_correct_first_attempt,
        total_hints_requested=total_hints_requested,
        total_response_time_ms=total_response_time_ms,
        schema_version=SESSION_SUMMARY_SCHEMA_VERSION,
        generation_phase=B5_1_GENERATION_PHASE,
    )
    stats = SessionAggregateStats(
        session_id=session_id,
        first_attempt_accuracy=first_attempt_accuracy,
        completion_count=completion_count,
        completion_rate=completion_rate,
        total_retries=total_retries,
        hint_bearing_opportunities=hint_bearing_opportunities,
        response_time_mean_ms=rt_mean,
        response_time_median_ms=rt_median,
        response_time_std_ms=rt_std,
        error_class_distribution=error_dist,
    )
    skill_rollups = _skill_rollups(ordered, skill_mastery_updates, guard_statuses, theta_B)

    return SessionAggregationResult(summary=summary, stats=stats, skill_rollups=skill_rollups)
