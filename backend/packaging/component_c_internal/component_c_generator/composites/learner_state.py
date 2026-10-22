"""``C-LS-v1`` deterministic telemetry-quality status + learner state (SPEC §20; C Parameters
§11-§13 -- rule chain, thresholds, and precedence transcribed verbatim, not redefined). Every
threshold below is a direct, cited transcription of the committed oracle's own hardcoded
validator literals (``models.contracts.CToComponent3Payload.validate_deterministic_invariants``)
-- they are NOT exposed as tunable config fields, for the same reason the composite weights
aren't (see ``composites.config`` docstring): the oracle model is frozen and uneditable, so any
independent "configurability" here would risk silently drifting from the one true frozen
identity it re-derives and rejects deviations from.

**LS-02** (a technical failure must never become ``disengaged``): structurally guaranteed --
``decide_learner_state`` returns ``None`` immediately for both ``technical_issue`` and
``insufficient_evidence`` quality statuses, before any of the ``overloaded``/``disengaged``
branches are ever reached.

**LS-04** (slow-but-accurate safeguard, C Parameters §13): holds by construction, not by an
extra rule -- ``decide_learner_state`` has no latency parameter at all (mirroring
``models.contracts``, which likewise excludes latency from every learner-state branch), so high
C latency has no code path through which it could independently push a session toward
``overloaded``/``disengaged``.
"""

from __future__ import annotations

from typing import Literal, Optional, Tuple

from ..models.enums import LearnerState

TelemetryQualityStatus = Literal["complete", "insufficient_evidence", "technical_issue"]

StateReason = Literal[
    "technical_issue",
    "insufficient_session_evidence",
    "safety_override_with_error_burst",
    "quit_after_error",
    "repeated_floor_hits_with_low_completion",
    "high_behavioral_friction",
    "low_engagement_score",
    "inactivity_with_low_completion",
    "high_engagement_low_friction",
    "sustained_participation_under_challenge",
    "insufficient_sustained_participation",
]

# C Parameters §12 sufficient-evidence gate.
_MIN_TASK_OPPORTUNITY_COUNT = 5
_MIN_COMPLETED_TASK_COUNT = 3
_MIN_SESSION_DURATION_SEC = 120.0

# C Parameters §11 rule-chain thresholds (v1 approved defaults; CALIBRATION_PENDING).
_SAFETY_OVERRIDE_ERROR_BURST_MIN_ERRORS = 4
_FLOOR_HITS_OVERLOAD_MIN = 2
_FLOOR_HITS_OVERLOAD_MAX_COMPLETION = 0.60
_FRUSTRATION_OVERLOAD_MIN = 0.70
_ENGAGEMENT_DISENGAGED_MAX = 0.45
_INACTIVITY_DISENGAGED_MIN_PERIODS = 3
_INACTIVITY_DISENGAGED_MAX_COMPLETION = 0.60
_ENGAGED_MIN_ENGAGEMENT = 0.70
_ENGAGED_MAX_FRUSTRATION = 0.40
_ENGAGED_MIN_COMPLETION = 0.75
_PRODUCTIVE_STRUGGLE_MIN_ENGAGEMENT = 0.50
_PRODUCTIVE_STRUGGLE_MIN_COMPLETION = 0.60


def decide_telemetry_quality_status(
    session_technical_issue_flag: bool,
    task_opportunity_count: int,
    completed_task_count: int,
    session_duration_sec: float,
    accuracy_rate: Optional[float],
    task_completion_rate: Optional[float],
) -> TelemetryQualityStatus:
    """C Parameters §12 sufficient-evidence gate (all must hold for "complete")."""
    if session_technical_issue_flag:
        return "technical_issue"
    sufficient_evidence = (
        task_opportunity_count >= _MIN_TASK_OPPORTUNITY_COUNT
        and completed_task_count >= _MIN_COMPLETED_TASK_COUNT
        and session_duration_sec >= _MIN_SESSION_DURATION_SEC
        and accuracy_rate is not None
        and task_completion_rate is not None
    )
    return "complete" if sufficient_evidence else "insufficient_evidence"


def decide_learner_state(
    telemetry_quality_status: TelemetryQualityStatus,
    safety_override_count: int,
    consecutive_error_max: int,
    quit_after_error: bool,
    difficulty_floor_hits: int,
    task_completion_rate: float,
    inactivity_periods: int,
    engagement_score: Optional[float],
    frustration_index: Optional[float],
) -> Tuple[Optional[LearnerState], StateReason]:
    """SPEC §20 / C Parameters §11 rule chain -- ``state_reason`` is the FIRST triggered rule.

    ``engagement_score``/``frustration_index`` are required (non-null) whenever
    ``telemetry_quality_status == "complete"``; the two early-return branches below never read
    them, so callers may safely pass ``None`` in the insufficient-evidence/technical-issue
    cases.
    """
    if telemetry_quality_status == "technical_issue":
        return None, "technical_issue"
    if telemetry_quality_status == "insufficient_evidence":
        return None, "insufficient_session_evidence"

    if engagement_score is None or frustration_index is None:
        raise ValueError("engagement_score/frustration_index must be non-null when telemetry_quality_status=='complete'")

    if safety_override_count >= 1 and consecutive_error_max >= _SAFETY_OVERRIDE_ERROR_BURST_MIN_ERRORS:
        return "overloaded", "safety_override_with_error_burst"
    if quit_after_error:
        return "overloaded", "quit_after_error"
    if difficulty_floor_hits >= _FLOOR_HITS_OVERLOAD_MIN and task_completion_rate < _FLOOR_HITS_OVERLOAD_MAX_COMPLETION:
        return "overloaded", "repeated_floor_hits_with_low_completion"
    if frustration_index >= _FRUSTRATION_OVERLOAD_MIN:
        return "overloaded", "high_behavioral_friction"
    if engagement_score < _ENGAGEMENT_DISENGAGED_MAX:
        return "disengaged", "low_engagement_score"
    if inactivity_periods >= _INACTIVITY_DISENGAGED_MIN_PERIODS and task_completion_rate < _INACTIVITY_DISENGAGED_MAX_COMPLETION:
        return "disengaged", "inactivity_with_low_completion"
    if (
        engagement_score >= _ENGAGED_MIN_ENGAGEMENT
        and frustration_index < _ENGAGED_MAX_FRUSTRATION
        and task_completion_rate >= _ENGAGED_MIN_COMPLETION
    ):
        return "engaged", "high_engagement_low_friction"
    if engagement_score >= _PRODUCTIVE_STRUGGLE_MIN_ENGAGEMENT and task_completion_rate >= _PRODUCTIVE_STRUGGLE_MIN_COMPLETION:
        return "productive_struggle", "sustained_participation_under_challenge"
    return "disengaged", "insufficient_sustained_participation"
