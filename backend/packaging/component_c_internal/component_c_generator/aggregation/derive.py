"""§18 session aggregation -- deterministic DERIVE-only rollup from the committed C3
``GameplayEvent``/``CTaskOpportunitySummary`` stream and the committed C4.1
``AdaptationDecision`` trajectory (SPEC §18; C Parameters §12, Catalogue §9.3).

Nothing here samples or resamples (SPEC §18: "C5 never samples or resamples them"). Every field
is a count, sum, ratio, or trajectory read of already-generated, committed telemetry.

--------------------------------------------------------------------------------------------
RESOLVED -- ``time_in_target_band_sec`` is a confirmed caller-supplied input (supervisor, C5.0
revision)
--------------------------------------------------------------------------------------------
SPEC §18/§19 and C Parameters §8.4/§9 treat ``time_in_target_band_sec`` as a genuine per-session
observable ("OBSERVED", "challenge-fit exposure"). Neither the committed ``GameplayEvent`` nor
the committed ``CTaskOpportunitySummary`` (models/gameplay.py) carries any target-band/
challenge-fit field to derive it from -- C3 emits no target-band signal at all. Supervisor
confirmed (Phase C5.0 revision): this stays an explicit caller-supplied value; C7's pilot
profile supplies it per C Parameters §313. This module does not derive it and does not invent a
proxy formula for it.

--------------------------------------------------------------------------------------------
RESOLVED -- ``safety_override_count`` is a confirmed caller-supplied input (supervisor, C5.0
revision)
--------------------------------------------------------------------------------------------
C Parameters §15's authoritative trigger ("a safety override fires when
``consecutive_error_max >= 5`` AT THE DIFFICULTY FLOOR, or ``difficulty_floor_hits >= 3`` within
the session") is intentionally distinct from the committed C4.1 safety controller's
``activate_recovery_flag`` (``safety.controller.apply_safety``), which fires on a different
condition (``recent_consecutive_error_max >= consecutive_error_trigger`` regardless of floor, or
``rolling_strain_score >= strain_trigger``) and serves a different purpose (an immediate,
per-decision policy override, not the exported session-level count). Supervisor confirmed
(Phase C5.0 revision): ``safety_override_count`` is authoritatively defined by C Parameters §15
alone and will be runtime-accumulated by C6 (which observes each decision's realized difficulty
against the floor across the session, per the Params §15 trigger). This module does not ship a
``derive_safety_override_count`` function; it stays an explicit, caller-supplied integer on
``derive_session_aggregate``.
"""

from __future__ import annotations

import statistics
from typing import Optional, Sequence

from ..models.adaptation import AdaptationDecision
from ..models.gameplay import CTaskOpportunitySummary, GameplayEvent
from .config import CAggregationConfig
from .models import CSessionAggregate, DifficultyTrend


def _clamp_null_ratio(numerator: int, denominator: int) -> Optional[float]:
    if denominator == 0:
        return None
    return numerator / denominator


def _decide_difficulty_trend(
    decisions: Sequence[AdaptationDecision],
    completed_task_count: int,
    config: CAggregationConfig,
) -> DifficultyTrend:
    """Params §14: insufficient evidence (< the configured minimum completed tasks) -> "stable".
    Otherwise, the sign of the net change across the session's ordered difficulty trajectory
    (first decision's ``difficulty_before`` vs. the last decision's ``difficulty_after``) -- no
    additional invented magnitude threshold is needed since only the sign is reported."""
    if completed_task_count < config.min_completed_tasks_for_difficulty_trend or not decisions:
        return "stable"
    net = decisions[-1].difficulty_after - decisions[0].difficulty_before
    if net > 0:
        return "increasing"
    if net < 0:
        return "decreasing"
    return "stable"


def derive_session_aggregate(
    events: Sequence[GameplayEvent],
    summaries: Sequence[CTaskOpportunitySummary],
    adaptation_decisions: Sequence[AdaptationDecision],
    *,
    time_in_target_band_sec: float,
    safety_override_count: int,
    inactive_time_available: bool,
    config: CAggregationConfig,
) -> CSessionAggregate:
    """Derive the §18 session aggregate from committed C3/C4.1 telemetry.

    ``time_in_target_band_sec`` (C7 pilot profile, C Parameters §313) and
    ``safety_override_count`` (accumulated by C6 per C Parameters §15) are confirmed
    caller-supplied inputs -- see the two RESOLVED notes in this module's docstring.
    ``inactive_time_available`` records whether ``inactive_time_sec`` (summed below from the
    committed per-task ``CTaskOpportunitySummary.inactive_time_sec`` field) is genuine session
    telemetry or a placeholder, for the composite fallback-periods decision (see
    ``composites.engagement_frustration``).
    """
    if not events:
        raise ValueError("derive_session_aggregate requires a non-empty chronological event stream")

    task_opportunity_count = len(summaries)
    completed_task_count = sum(1 for s in summaries if s.task_completed)
    correct_task_count = sum(1 for s in summaries if s.correct_task)
    total_attempt_count = sum(s.total_attempts for s in summaries)

    # SPEC §18 FROZEN identities (C→3 v3.0 §4.3).
    accuracy_rate = _clamp_null_ratio(correct_task_count, completed_task_count)
    avg_attempts_per_task = (
        total_attempt_count / completed_task_count if completed_task_count > 0 else None
    )
    task_completion_rate = (
        completed_task_count / task_opportunity_count if task_opportunity_count > 0 else 0.0
    )

    inactivity_periods = sum(s.inactivity_periods for s in summaries)
    inactive_time_sec = sum(s.inactive_time_sec for s in summaries)

    # FIX 1 (C5.0 revision): the committed C3 attempt-loop builds a FRESH per-task event clock
    # (``behaviour.attempt_loop``'s ``_EventBuilder`` starts each task at ``clock_ms=0``), so
    # ``event_timestamp_relative_ms`` is relative to EACH TASK's own start, not the session.
    # Taking a single global max-min across all events therefore collapses to ~the longest
    # single task's span, badly undercounting session duration. The correct derivation groups
    # events by task (``task_index``), takes each task-group's own max timestamp (that task's
    # terminal-event clock = that task's duration), and SUMS those per-task spans across the
    # session.
    per_task_span_ms: dict[int, int] = {}
    for e in events:
        per_task_span_ms[e.task_index] = max(per_task_span_ms.get(e.task_index, 0), e.event_timestamp_relative_ms)
    session_duration_sec = sum(per_task_span_ms.values()) / 1000.0
    if session_duration_sec <= 0.0:
        raise ValueError("session_duration_sec must be > 0 (derived from summed per-task event spans)")

    # C3 §15: consecutive_error_max_within_task is the per-task streak; the session-level value
    # is the max across all task opportunities (no cross-task streak concept exists on the
    # committed per-task summary model).
    consecutive_error_max = max((s.consecutive_error_max_within_task for s in summaries), default=0)

    # FIX 2 (C5.0 revision): C Parameters line 206 defines difficulty_floor_hits as driven by
    # "adaptation strain (§14)", not merely "any decision that happens to sit at level 1".
    # Counting every difficulty_after==1 decision wrongly maxes this out for cold-start/c_only
    # sessions pinned at level 1 by a BASELINE cap (familiarization cap 2, c_only cap 1) with
    # zero strain -- systematically inflating frustration_index and biasing C-LS rule 5 toward
    # "overloaded". A floor hit is therefore only counted when the decision lands at the floor
    # UNDER DOWNWARD ADAPTATION PRESSURE: difficulty_after == 1 AND a decrease was proposed
    # and/or applied on that decision (TEST_FIXTURE_ONLY interpretation of "adaptation strain",
    # Params §14; a baseline level-1 hold with no decrease proposed or applied is not a strain
    # event and is not counted).
    difficulty_floor_hits = sum(
        1
        for d in adaptation_decisions
        if d.difficulty_after == 1
        and (d.applied_action == "decrease_difficulty" or d.selected_action == "decrease_difficulty")
    )

    quit_after_error = any(s.quit_after_error for s in summaries)
    session_technical_issue_flag = any(s.technical_issue for s in summaries) or any(
        e.technical_flag for e in events
    )

    latencies = [s.task_latency_sec for s in summaries if s.task_latency_sec is not None]
    if completed_task_count == 0 or not latencies:
        c_mean_game_task_latency_sec = None
        c_median_game_task_latency_sec = None
    else:
        c_mean_game_task_latency_sec = statistics.mean(latencies)
        c_median_game_task_latency_sec = statistics.median(latencies)

    if adaptation_decisions:
        current_difficulty_level = adaptation_decisions[-1].difficulty_after
    else:
        current_difficulty_level = 1

    difficulty_trend = _decide_difficulty_trend(adaptation_decisions, completed_task_count, config)

    return CSessionAggregate(
        task_opportunity_count=task_opportunity_count,
        completed_task_count=completed_task_count,
        correct_task_count=correct_task_count,
        total_attempt_count=total_attempt_count,
        accuracy_rate=accuracy_rate,
        avg_attempts_per_task=avg_attempts_per_task,
        task_completion_rate=task_completion_rate,
        inactivity_periods=inactivity_periods,
        inactive_time_sec=inactive_time_sec,
        inactive_time_available=inactive_time_available,
        session_duration_sec=session_duration_sec,
        time_in_target_band_sec=time_in_target_band_sec,
        consecutive_error_max=consecutive_error_max,
        difficulty_floor_hits=difficulty_floor_hits,
        quit_after_error=quit_after_error,
        safety_override_count=safety_override_count,
        c_mean_game_task_latency_sec=c_mean_game_task_latency_sec,
        c_median_game_task_latency_sec=c_median_game_task_latency_sec,
        current_difficulty_level=current_difficulty_level,
        difficulty_trend=difficulty_trend,
        session_technical_issue_flag=session_technical_issue_flag,
    )
