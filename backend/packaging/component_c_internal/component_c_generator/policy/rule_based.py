"""Pure rule-based difficulty policy (SPEC §14.1) -- the only active policy in v1.

``propose_difficulty_action`` reads ONLY ``CPolicyObservableEvidence`` (current-session
observable C evidence) and ``CPolicyConfig`` (explicit thresholds) -- no future information, no
population/dd_subtype, no Component 3 risk, no prohibited B field, no RNG, no I/O. Deterministic:
the same ``(evidence, config)`` always yields the same proposal.

Q-learning is EXPERIMENTAL_ONLY and NOT implemented here (SPEC §14): ``propose_action`` raises
``QLearningDisabledError`` for any ``policy_mode`` other than ``"rule_based_baseline"`` -- there
is no unrestricted online exploration anywhere in this module.
"""

from __future__ import annotations

from ..models.adaptation import CPolicyObservableEvidence, DifficultyAction
from ..models.enums import PolicyMode
from .config import CPolicyConfig

RULE_BASED_POLICY_VERSION = "c4.1-rule-based-1.0.0"

# SPEC §14: Q-learning is EXPERIMENTAL_ONLY until the rule baseline passes, state/action/reward
# are versioned, offline evaluation passes, the safety controller demonstrably overrides
# policy, and no unrestricted online exploration ever runs on children -- none of that has
# happened, so these modes stay hard-disabled.
DISABLED_POLICY_MODES = ("q_learning_offline", "frozen_q_evaluation")
ACTIVE_POLICY_MODES = ("rule_based_baseline",)


class QLearningDisabledError(NotImplementedError):
    """Raised for any non-baseline ``policy_mode`` -- Q-learning is EXPERIMENTAL_ONLY and not
    implemented in Phase C4.1 (SPEC §14)."""


class UnknownPolicyModeError(ValueError):
    """Raised for a ``policy_mode`` that is neither active nor a recognized disabled mode."""


def propose_difficulty_action(evidence: CPolicyObservableEvidence, config: CPolicyConfig) -> DifficultyAction:
    """SPEC §14.1 rule-based baseline: propose ``increase_difficulty`` only when recent
    correctness is high, average attempts are low, and strain is not elevated; propose
    ``decrease_difficulty`` when correctness is low, a real consecutive-error run exists, or
    strain is elevated; otherwise ``hold``. Bounded to the three allowed actions -- this
    function never returns a raw difficulty level (bounding to 1-5 and every session cap is the
    safety controller's job, SPEC §17)."""
    can_increase = (
        evidence.recent_correctness_rate >= config.increase_correctness_threshold
        and evidence.recent_avg_attempts <= config.increase_max_avg_attempts
        and evidence.rolling_strain_score <= config.increase_max_strain
    )
    must_decrease = (
        evidence.recent_correctness_rate <= config.decrease_correctness_threshold
        or evidence.recent_consecutive_error_max >= config.decrease_error_run_threshold
        or evidence.rolling_strain_score >= config.decrease_min_strain
    )

    if must_decrease:
        return "decrease_difficulty"
    if can_increase:
        return "increase_difficulty"
    return "hold"


def propose_action(policy_mode: PolicyMode, evidence: CPolicyObservableEvidence, config: CPolicyConfig) -> DifficultyAction:
    """Dispatch by ``policy_mode``. Only ``"rule_based_baseline"`` is active; the two RL modes
    raise ``QLearningDisabledError`` (SPEC §14) -- calling this with either never runs any
    exploration/learning code, because none exists."""
    if policy_mode in DISABLED_POLICY_MODES:
        raise QLearningDisabledError(
            f"policy_mode={policy_mode!r} is EXPERIMENTAL_ONLY and not implemented in Phase "
            f"C4.1; only {ACTIVE_POLICY_MODES!r} is active (SPEC §14)."
        )
    if policy_mode not in ACTIVE_POLICY_MODES:
        raise UnknownPolicyModeError(f"unrecognized policy_mode {policy_mode!r}")
    return propose_difficulty_action(evidence, config)
