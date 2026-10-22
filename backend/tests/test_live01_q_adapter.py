"""LIVE-01: ``LiveEngineCAdapter.decide_with_proposed_action`` / ``preview_allowed_actions``.

The pinned ``decide_adaptation`` raises ``QLearningDisabledError`` for every non-rule mode, so the frozen Q
policy's decision is composed in the adapter from the pinned ``apply_safety``. These tests prove (1) the composed
decision equals what the pinned rule path produces for the same applied action, field-for-field, except
``policy_mode`` / ``policy_version`` / ``rl_state``; (2) safety still wins whatever Q proposes; (3) the allowed set
is exactly the actions safety would not override. The package-level ``QLearningDisabledError`` behaviour is unchanged
and stays tested in ``test_c6b_policy_and_safety.py``.
"""

from __future__ import annotations

import dataclasses

import pytest

from app.application.live_engine_c.q_policy import ACTIONS, load_q_policy, state_of
from app.domain.live_engine_c.errors import QLearningDisabledError, UnknownPolicyModeError
from app.domain.live_engine_c.types import PolicyObservableEvidence, SeedLineage
from app.infrastructure.live_engine_c.adapter import LiveEngineCAdapter
from tests.test_c4_session_lifecycle import safety_config_fixture_for_tests, selection_config_fixture_for_tests
from tests.test_c6b_policy_and_safety import policy_config_fixture_for_tests

ADAPTER = LiveEngineCAdapter()
SAFETY, SELECTION, POLICY = safety_config_fixture_for_tests(), selection_config_fixture_for_tests(), policy_config_fixture_for_tests()


def _evidence(**overrides: object) -> PolicyObservableEvidence:
    base: dict = dict(
        session_mode="c_only", session_phase="c_only", current_difficulty_level=2,
        recent_correctness_rate=0.6, recent_avg_attempts=1.2, recent_inactivity_periods=0,
        recent_scaffold_use_count=0, recent_consecutive_error_max=0, rolling_strain_score=0.1,
        prior_session_end_state=None, is_recovery_context=False, technical_issue_current_task=False,
        safety_increase_block_remaining=0,
    )
    base.update(overrides)
    return PolicyObservableEvidence(**base)


def _lineage(seed: int = 7) -> SeedLineage:
    return SeedLineage(global_seed=1, path=(("task_index", "1"),), seed=seed)


CASES = [
    _evidence(),
    _evidence(recent_correctness_rate=0.95, recent_avg_attempts=1.0, rolling_strain_score=0.05),     # rule: increase
    _evidence(recent_correctness_rate=0.1, recent_consecutive_error_max=2),                            # rule: decrease
    _evidence(recent_consecutive_error_max=5, rolling_strain_score=0.9),                                # forced recovery
    _evidence(rolling_strain_score=0.95),
    _evidence(safety_increase_block_remaining=2, recent_correctness_rate=0.95, recent_avg_attempts=1.0),
    _evidence(technical_issue_current_task=True),
    _evidence(current_difficulty_level=1, recent_correctness_rate=0.1),
    _evidence(current_difficulty_level=5, recent_correctness_rate=0.95, recent_avg_attempts=1.0),
    _evidence(is_recovery_context=True),
    _evidence(prior_session_end_state="overloaded"),
]


def _rule(evidence):
    return ADAPTER.decide_adaptation_with_safety_flags(
        policy_mode="rule_based_baseline", evidence=evidence, current_difficulty_level=evidence.current_difficulty_level,
        seed_lineage=_lineage(), policy_config=POLICY, safety_config=SAFETY, selection_config=SELECTION,
    )


def _composed(evidence, action, **kw):
    args = dict(
        selected_action=action, policy_mode="rule_based_baseline", policy_version="v", rl_state=None, evidence=evidence,
        current_difficulty_level=evidence.current_difficulty_level, seed_lineage=_lineage(), safety_config=SAFETY,
        selection_config=SELECTION,
    )
    args.update(kw)
    return ADAPTER.decide_with_proposed_action(**args)


@pytest.mark.parametrize("evidence", CASES)
def test_composed_decision_equals_the_pinned_rule_path_field_for_field(evidence) -> None:
    rule = _rule(evidence)
    composed = _composed(
        evidence, rule.decision.selected_action, policy_mode="rule_based_baseline",
        policy_version=rule.decision.policy_version, rl_state=None,
    )
    assert composed.decision == rule.decision                      # every field, incl. seed lineage and decision_id
    assert composed.activate_recovery_flag == rule.activate_recovery_flag
    assert composed.request_safe_termination == rule.request_safe_termination


@pytest.mark.parametrize("evidence", CASES)
def test_only_mode_version_and_rl_state_differ_for_a_q_decision(evidence) -> None:
    rule = _rule(evidence)
    rl_state = {"state": "x", "q_values": [0.0, 1.0, 2.0], "allowed": ["hold"], "artifact_file": "f", "artifact_sha256": "h"}
    q = _composed(
        evidence, rule.decision.selected_action, policy_mode="frozen_q_evaluation", policy_version="c-rl-q-v1+S", rl_state=rl_state,
    )
    assert q.decision.policy_mode == "frozen_q_evaluation" and q.decision.policy_version == "c-rl-q-v1+S"
    assert q.decision.rl_state == rl_state and q.decision.internal_reward is None
    assert dataclasses.replace(q.decision, policy_mode=rule.decision.policy_mode, policy_version=rule.decision.policy_version,
                               rl_state=None) == rule.decision
    assert (q.activate_recovery_flag, q.request_safe_termination) == (rule.activate_recovery_flag, rule.request_safe_termination)


@pytest.mark.parametrize("evidence", CASES)
def test_safety_wins_whatever_q_proposes(evidence) -> None:
    for action in ACTIONS:
        result = _composed(evidence, action, policy_mode="frozen_q_evaluation", policy_version="c-rl-q-v1+S", rl_state={})
        # the applied action / reason / flags are exactly what the pinned safety layer returns for that proposal
        from component_c_generator.safety.controller import apply_safety as pkg_apply_safety
        from app.infrastructure.live_engine_c.adapter import (
            _to_pkg_policy_observable_evidence, _to_pkg_safety_config, _to_pkg_selection_config)

        oracle = pkg_apply_safety(
            selected_action=action, evidence=_to_pkg_policy_observable_evidence(evidence),
            current_difficulty_level=evidence.current_difficulty_level, selection_config=_to_pkg_selection_config(SELECTION),
            safety_config=_to_pkg_safety_config(SAFETY))
        assert result.decision.selected_action == action
        assert result.decision.applied_action == oracle.applied_action
        assert result.decision.action_overridden == oracle.action_overridden
        assert result.decision.difficulty_after == oracle.difficulty_after
        assert result.activate_recovery_flag == oracle.activate_recovery_flag


def test_forced_recovery_overrides_an_increase_proposal() -> None:
    evidence = _evidence(recent_consecutive_error_max=5, rolling_strain_score=0.9)
    results = {a: _composed(evidence, a, policy_mode="frozen_q_evaluation", policy_version="v", rl_state={}) for a in ACTIONS}
    assert results["increase_difficulty"].activate_recovery_flag is True, "premise: this evidence must trigger forced recovery"
    assert results["increase_difficulty"].decision.applied_action != "increase_difficulty"
    assert results["increase_difficulty"].decision.action_overridden is True
    assert len({r.decision.applied_action for r in results.values()}) == 1       # same applied action whatever Q proposed


@pytest.mark.parametrize("evidence", CASES)
@pytest.mark.parametrize("mode", ["c_only", "combined"])
def test_allowed_set_is_what_safety_would_not_override_and_q_stays_inside_it(evidence, mode) -> None:
    allowed = ADAPTER.preview_allowed_actions(
        evidence=evidence, current_difficulty_level=evidence.current_difficulty_level, safety_config=SAFETY, selection_config=SELECTION)
    assert allowed and list(allowed) == [a for a in ACTIONS if a in allowed]        # canonical order, never empty
    for action in ACTIONS:
        overridden = _composed(evidence, action, policy_mode="frozen_q_evaluation", policy_version="v", rl_state={}).decision.action_overridden
        if len(allowed) == 1 and allowed == ("hold",) and overridden:
            continue                                                                  # all three overridden -> ("hold",) fallback
        assert (action in allowed) == (not overridden), (action, allowed)
    policy = load_q_policy(mode)
    mastery = None if mode == "c_only" else 0.5
    for tasks_done in (3, 6):
        action, _ = policy.propose(state_of(evidence.current_difficulty_level, 0.5, evidence.rolling_strain_score, mastery), allowed, tasks_done)
        assert action in allowed


def test_unknown_action_or_mode_is_refused() -> None:
    with pytest.raises(UnknownPolicyModeError):
        _composed(_evidence(), "go_wild")
    with pytest.raises(UnknownPolicyModeError):
        _composed(_evidence(), "hold", policy_mode="made_up_mode")


def test_the_pinned_decide_adaptation_still_refuses_q_modes() -> None:
    for mode in ("q_learning_offline", "frozen_q_evaluation"):
        with pytest.raises(QLearningDisabledError):
            ADAPTER.decide_adaptation(
                policy_mode=mode, evidence=_evidence(), current_difficulty_level=2, seed_lineage=_lineage(),
                policy_config=POLICY, safety_config=SAFETY, selection_config=SELECTION)


def test_safety_controller_version_is_exposed_for_the_policy_version() -> None:
    assert ADAPTER.safety_controller_version() == _rule(_evidence()).decision.policy_version.split("+", 1)[1]
