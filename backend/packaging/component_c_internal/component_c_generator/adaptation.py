"""Top-level Phase C4.1 orchestrator: policy proposal + hard safety layer -> ``AdaptationDecision``.

``decide_adaptation`` composes (never reimplements) ``policy.rule_based.propose_action`` and
``safety.controller.apply_safety``, then assembles the full internal-only ``AdaptationDecision``
record (SPEC §6.5). Both composed functions are pure and deterministic (no RNG is used anywhere
in this module -- the seed lineage is carried only for traceability/decision-id derivation,
never for a random draw), so the whole pipeline is deterministic for the same
``(policy_mode, evidence, current_difficulty_level, config)``.

This module produces the adaptation DECISION only -- it does not realize a scaffold/recovery
task (C4.2), aggregate a session (C5), or orchestrate a pipeline (C6).
"""

from __future__ import annotations

from .models.adaptation import AdaptationDecision, CPolicyObservableEvidence
from .models.enums import PolicyMode
from .policy.config import CPolicyConfig
from .policy.rule_based import RULE_BASED_POLICY_VERSION, propose_action
from .safety.config import CSafetyConfig
from .safety.controller import SAFETY_CONTROLLER_VERSION, apply_safety
from .selection.config import CSelectionConfig
from .seeds import CSeedLineage


def _decision_id(seed_lineage: CSeedLineage) -> str:
    return f"AD-{seed_lineage.seed:016x}"


def decide_adaptation(
    *,
    policy_mode: PolicyMode,
    evidence: CPolicyObservableEvidence,
    current_difficulty_level: int,
    seed_lineage: CSeedLineage,
    policy_config: CPolicyConfig,
    safety_config: CSafetyConfig,
    selection_config: CSelectionConfig,
) -> AdaptationDecision:
    """Propose a difficulty action via the active policy, apply the hard safety layer, and
    assemble the full ``AdaptationDecision`` record. Raises
    ``policy.rule_based.QLearningDisabledError`` for any non-``rule_based_baseline``
    ``policy_mode`` -- Q-learning is not implemented (SPEC §14)."""
    selected_action = propose_action(policy_mode, evidence, policy_config)

    safety_decision = apply_safety(
        selected_action=selected_action,
        evidence=evidence,
        current_difficulty_level=current_difficulty_level,
        selection_config=selection_config,
        safety_config=safety_config,
    )

    policy_version = f"{RULE_BASED_POLICY_VERSION}+{SAFETY_CONTROLLER_VERSION}"

    return AdaptationDecision(
        decision_id=_decision_id(seed_lineage),
        policy_mode=policy_mode,
        policy_version=policy_version,
        rl_state=None,  # RL is disabled in v1 (SPEC §14) -- never populated
        selected_action=selected_action,
        applied_action=safety_decision.applied_action,
        action_overridden=safety_decision.action_overridden,
        safety_reason=safety_decision.safety_reason,
        difficulty_before=current_difficulty_level,
        difficulty_after=safety_decision.difficulty_after,
        rolling_strain_bucket=safety_decision.rolling_strain_bucket,
        session_start_state_bucket=evidence.prior_session_end_state,
        increase_block_remaining=safety_decision.increase_block_remaining_after,
        internal_reward=None,  # RL is disabled in v1 (SPEC §14) -- never populated
        seed_lineage=seed_lineage,
    )
