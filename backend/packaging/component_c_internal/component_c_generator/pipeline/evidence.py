"""Builds the committed ``CPolicyObservableEvidence`` from the session's running
``CTaskOpportunitySummary`` history (Phase C6.0). Pure functions of already-derived C3 telemetry
-- no sampling, no RNG, no new correctness/latency/attempt model.

``compute_rolling_strain`` transcribes C Parameters §14's ``c_rolling_strain`` formula
VERBATIM: ``clamp01(0.5*(recent_consecutive_errors/5) + 0.3*(recent_excess_attempts/3) +
0.2*recent_quit)`` over the last **w=3** completed tasks (also Params §14, hardcoded here to
match the citation exactly -- not a tunable value). This is the same rolling-strain concept
``CPolicyObservableEvidence.rolling_strain_score`` and ``AdaptationDecision.rolling_strain_bucket``
already consume; C6.0 is the first phase that must actually produce it from history.
"""

from __future__ import annotations

from typing import Optional, Sequence

from models.contracts import BToCMasteryPayload

from ..models.adaptation import CPolicyObservableEvidence
from ..models.enums import LearnerState, SessionMode, SessionPhase
from ..models.gameplay import CTaskOpportunitySummary
from .config import CEvidenceWindowConfig

# C Parameters §14: c_rolling_strain's own frozen window + weights -- cited, not invented.
_ROLLING_STRAIN_WINDOW = 3
_ROLLING_STRAIN_ERROR_WEIGHT = 0.5
_ROLLING_STRAIN_ATTEMPT_WEIGHT = 0.3
_ROLLING_STRAIN_QUIT_WEIGHT = 0.2
_ROLLING_STRAIN_ERROR_DIVISOR = 5.0
_ROLLING_STRAIN_ATTEMPT_DIVISOR = 3.0

_MASTERY_FIELD_BY_SKILL = {
    "counting": "mastery_counting",
    "number_sense": "mastery_number_sense",
    "place_value": "mastery_place_value",
    "addition": "mastery_addition",
    "subtraction": "mastery_subtraction",
    "multiplication": "mastery_multiplication",
    "division": "mastery_division",
}


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def mastery_value_for_skill(mastery_payload: BToCMasteryPayload, skill_id: str) -> float:
    """The B->C v2.1 scalar for one skill (a field lookup, not a new computation) -- used to
    supply C3's ``generate_task_gameplay(selected_skill_mastery=...)`` for a combined-mode task
    regardless of session_phase. ``selection.selector.SelectionResult.mastery_selected_skill`` is
    intentionally ``None`` during familiarization (a SELECTION-purity requirement, cold-start
    assessment §5.4: "never rank by mastery") -- that says nothing about whether B's mastery
    value for the rotated-to skill is available for C3's separate gameplay outcome model. B ran
    and produced all seven scalars for every combined session (assessment §5.3), so the
    familiarization-selected skill's own scalar is genuinely available here."""
    return getattr(mastery_payload, _MASTERY_FIELD_BY_SKILL[skill_id])


def compute_rolling_strain(recent_summaries: Sequence[CTaskOpportunitySummary]) -> float:
    """C Parameters §14 ``c_rolling_strain`` over the last w=3 completed tasks (verbatim
    formula/weights/window). ``recent_summaries`` should already be the full running history in
    chronological order; only the trailing 3 COMPLETED tasks are used."""
    completed = [s for s in recent_summaries if s.task_completed]
    window = completed[-_ROLLING_STRAIN_WINDOW:]
    if not window:
        return 0.0
    recent_consecutive_errors = max(s.consecutive_error_max_within_task for s in window)
    recent_excess_attempts = max(0.0, (sum(s.total_attempts for s in window) / len(window)) - 1.0)
    recent_quit = 1.0 if any(s.task_quit for s in recent_summaries[-_ROLLING_STRAIN_WINDOW:]) else 0.0
    return _clamp01(
        _ROLLING_STRAIN_ERROR_WEIGHT * (recent_consecutive_errors / _ROLLING_STRAIN_ERROR_DIVISOR)
        + _ROLLING_STRAIN_ATTEMPT_WEIGHT * (recent_excess_attempts / _ROLLING_STRAIN_ATTEMPT_DIVISOR)
        + _ROLLING_STRAIN_QUIT_WEIGHT * recent_quit
    )


def build_policy_evidence(
    *,
    session_mode: SessionMode,
    session_phase: SessionPhase,
    current_difficulty_level: int,
    history: Sequence[CTaskOpportunitySummary],
    is_recovery_context: bool,
    prior_session_end_state: Optional[LearnerState],
    safety_increase_block_remaining: int,
    config: CEvidenceWindowConfig,
) -> CPolicyObservableEvidence:
    """Assemble the current-session observable evidence window (SPEC §14.2) from the running
    ``history`` of already-derived ``CTaskOpportunitySummary`` rows (most recent last).
    ``history`` must include the just-finished task (evidence is always built AFTER a task
    completes, per SPEC §14's "current-session observable evidence" -- never a future task)."""
    if not history:
        raise ValueError("build_policy_evidence requires at least one summary (the just-finished task)")

    window = history[-config.recent_window_task_count:]
    completed_in_window = [s for s in window if s.task_completed]

    if completed_in_window:
        recent_correctness_rate = sum(1.0 for s in completed_in_window if s.correct_task) / len(completed_in_window)
    else:
        # No completed-task evidence yet in the window -- a neutral, non-biasing default
        # (ENGINEERING_ASSUMPTION; not specified by any committed source).
        recent_correctness_rate = 0.5

    attempted_in_window = [s for s in window if s.total_attempts > 0]
    if attempted_in_window:
        recent_avg_attempts = sum(s.total_attempts for s in attempted_in_window) / len(attempted_in_window)
    else:
        recent_avg_attempts = 1.0

    recent_inactivity_periods = sum(s.inactivity_periods for s in window)
    recent_scaffold_use_count = sum(s.scaffold_count for s in window)
    recent_consecutive_error_max = max((s.consecutive_error_max_within_task for s in window), default=0)

    rolling_strain_score = compute_rolling_strain(history)

    current = history[-1]

    return CPolicyObservableEvidence(
        session_mode=session_mode,
        session_phase=session_phase,
        current_difficulty_level=current_difficulty_level,
        recent_correctness_rate=recent_correctness_rate,
        recent_avg_attempts=recent_avg_attempts,
        recent_inactivity_periods=recent_inactivity_periods,
        recent_scaffold_use_count=recent_scaffold_use_count,
        recent_consecutive_error_max=recent_consecutive_error_max,
        rolling_strain_score=rolling_strain_score,
        prior_session_end_state=prior_session_end_state,
        is_recovery_context=is_recovery_context,
        technical_issue_current_task=current.technical_issue,
        safety_increase_block_remaining=safety_increase_block_remaining,
    )
