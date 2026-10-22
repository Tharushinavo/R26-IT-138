"""The hard safety controller (SPEC §17) -- applied AFTER every policy proposal.

``apply_safety`` is a pure function of ``(selected_action, evidence, current_difficulty_level,
selection_config, safety_config)``: deterministic for the same state/config, versioned
(``SAFETY_CONTROLLER_VERSION``), and every input/output is recorded on the returned
``SafetyDecision`` (fully logged, per SPEC §17). It is never invoked with, and never reads, any
RL/Q-learning state -- Q-learning is not implemented (``policy/rule_based.py``), so there is no
code path by which RL could ever override this layer (SPEC §17: "never overridden by RL").

The FINAL applied action is always derived from the actual numeric ``difficulty_after`` versus
``difficulty_before`` (never a separately-tracked label that could drift out of sync with the
real bound-clamped outcome) -- this is what guarantees ``action_overridden`` is always accurate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from ..models.adaptation import CPolicyObservableEvidence, DifficultyAction, StrainBucket
from ..selection.config import CSelectionConfig
from .config import CSafetyConfig

SAFETY_CONTROLLER_VERSION = "c4.1-safety-controller-1.0.0"

_MIN_DIFFICULTY = 1
_MAX_DIFFICULTY = 5


@dataclass(frozen=True)
class SafetyDecision:
    applied_action: DifficultyAction
    difficulty_after: int
    action_overridden: bool
    safety_reason: Optional[str]
    activate_recovery_flag: bool
    increase_block_remaining_after: int
    request_safe_termination: bool
    rolling_strain_bucket: StrainBucket


def apply_safety(
    selected_action: DifficultyAction,
    evidence: CPolicyObservableEvidence,
    current_difficulty_level: int,
    selection_config: CSelectionConfig,
    safety_config: CSafetyConfig,
) -> SafetyDecision:
    """Apply the hard safety layer to a policy proposal (SPEC §17)."""
    if not (_MIN_DIFFICULTY <= current_difficulty_level <= _MAX_DIFFICULTY):
        raise ValueError(f"current_difficulty_level must be in 1..5, got {current_difficulty_level}")

    reasons: list[str] = []
    working_action: DifficultyAction = selected_action

    # (1) Technical issue neutralization: a technical-contaminated task must never register as
    # a punitive decrease (SPEC §17 "technical issues never become learner failure").
    if evidence.technical_issue_current_task and working_action == "decrease_difficulty":
        working_action = "hold"
        reasons.append("technical_issue_neutralized")

    # (2) Severe safety triggers: force at least a decrease, flag recovery, (re)arm the
    # increase-block window.
    trigger_error = evidence.recent_consecutive_error_max >= safety_config.consecutive_error_trigger
    trigger_strain = evidence.rolling_strain_score >= safety_config.strain_trigger
    activate_recovery_flag = trigger_error or trigger_strain
    if trigger_error:
        reasons.append("consecutive_error_safety_trigger")
    if trigger_strain:
        reasons.append("rolling_strain_safety_trigger")
    if activate_recovery_flag and working_action != "decrease_difficulty":
        working_action = "decrease_difficulty"

    if activate_recovery_flag:
        increase_block_remaining_after = safety_config.increase_block_window
    else:
        increase_block_remaining_after = max(0, evidence.safety_increase_block_remaining - 1)

    # (3) Increase-block veto: no increase while a block (fresh or carried over) is active.
    block_active = activate_recovery_flag or evidence.safety_increase_block_remaining > 0
    if working_action == "increase_difficulty" and block_active:
        working_action = "hold"
        reasons.append("increase_blocked_active_window")

    # (4) Ceiling/floor for this decision (SPEC §10.2 + the committed C4.0 session caps).
    ceiling, floor = _MAX_DIFFICULTY, _MIN_DIFFICULTY
    if evidence.is_recovery_context:
        ceiling, floor = 1, 1
        reasons.append("recovery_cap")
    else:
        if evidence.session_phase == "familiarization" and selection_config.familiarization_session_difficulty_cap < ceiling:
            ceiling = selection_config.familiarization_session_difficulty_cap
            reasons.append("familiarization_session_cap")
        if evidence.session_mode == "c_only" and selection_config.fallback_difficulty_cap < ceiling:
            ceiling = selection_config.fallback_difficulty_cap
            reasons.append("fallback_session_cap")
        if evidence.prior_session_end_state in ("overloaded", "disengaged") and safety_config.prior_overloaded_disengaged_cap < ceiling:
            ceiling = safety_config.prior_overloaded_disengaged_cap
            reasons.append("prior_state_cap")

    # (5) Numeric outcome -- the single source of truth for the final applied-action label.
    if working_action == "increase_difficulty":
        target = current_difficulty_level + 1
    elif working_action == "decrease_difficulty":
        target = current_difficulty_level - 1
    else:
        target = current_difficulty_level
    difficulty_after = max(floor, min(ceiling, target))

    if difficulty_after > current_difficulty_level:
        applied_action: DifficultyAction = "increase_difficulty"
    elif difficulty_after < current_difficulty_level:
        applied_action = "decrease_difficulty"
    else:
        applied_action = "hold"

    if applied_action != working_action and not reasons:
        # A cap silently absorbed the change without an explicit reason above (defensive; in
        # practice every ceiling/floor branch already appends a reason).
        reasons.append("difficulty_bound_clamped")

    # (6) Safe-session-termination request -- independent of, and can co-occur with, the above.
    request_safe_termination = evidence.recent_consecutive_error_max >= safety_config.safe_termination_error_threshold
    if request_safe_termination:
        reasons.append("safe_session_termination_requested")

    action_overridden = applied_action != selected_action

    return SafetyDecision(
        applied_action=applied_action,
        difficulty_after=difficulty_after,
        action_overridden=action_overridden,
        safety_reason="; ".join(reasons) if reasons else None,
        activate_recovery_flag=activate_recovery_flag,
        increase_block_remaining_after=increase_block_remaining_after,
        request_safe_termination=request_safe_termination,
        rolling_strain_bucket=safety_config.bucket_strain(evidence.rolling_strain_score),  # type: ignore[arg-type]
    )
