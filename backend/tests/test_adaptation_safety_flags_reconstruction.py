"""Component C backend remediation, batch 1: reconstructing ``decide_adaptation``'s two dropped
safety fields.

``component_c_generator.adaptation.decide_adaptation`` (mirrored, byte-identical, at
``backend/packaging/component_c_internal/component_c_generator/adaptation.py``) computes a
``safety.controller.SafetyDecision`` internally and drops two of its fields --
``activate_recovery_flag`` and ``request_safe_termination`` -- when composing the
``AdaptationDecision`` it returns. ``AdaptationDecision`` is ``frozen=True``/``extra="forbid"``,
so neither field can be passed in or attached after construction. ``propose_action``
(``policy/rule_based.py``) and ``apply_safety`` (``safety/controller.py``) are both pure and
RNG-free, so ``LiveEngineCAdapter.decide_adaptation_with_safety_flags`` recovers the two dropped
fields by calling that exact same two-function sequence a second time, on an evidence object
translated from the domain type EXACTLY ONCE and reused by identity across all three pinned
calls (``propose_action``, ``apply_safety``, ``decide_adaptation``).

THIS WORKS ONLY BECAUSE OF AN UNPUBLISHED IMPLEMENTATION DETAIL OF A PINNED FUNCTION, NEVER A
PUBLISHED CONTRACT: ``decide_adaptation`` happens to compose ``propose_action`` then
``apply_safety`` with those exact arguments (verified by direct read of ``adaptation.py``, and
structurally by
``tests/test_c6b_policy_and_safety.py::test_s8c_decide_adaptation_always_applies_safety_structurally``).
If a future re-pin changes that composition -- a different argument, a different order, or
dropping the composition entirely -- this reconstruction silently stops matching, and THIS test
module is what catches it.

WORKAROUND -- REMOVAL TRIGGER: this test module, the adapter method it exercises
(``LiveEngineCAdapter.decide_adaptation_with_safety_flags``), its port declaration
(``AdaptationPort.decide_adaptation_with_safety_flags``), its domain return type
(``AdaptationDecisionWithSafetyFlags``), and the manifest's forward-looking verification
requirement are all removed TOGETHER, the moment the wheel is re-pinned to a Yass commit carrying
the owner-authorized ``AdaptationDecision`` interface change (``task_index``,
``activate_recovery_flag``, ``request_safe_termination`` as real fields on the package's own
``AdaptationDecision``).
"""

from __future__ import annotations

import pytest

from app.domain.live_engine_c.types import PolicyObservableEvidence, SeedLineage
from app.infrastructure.live_engine_c import adapter as adapter_module
from app.infrastructure.live_engine_c.adapter import LiveEngineCAdapter
from tests.test_c4_session_lifecycle import (
    safety_config_fixture_for_tests,
    selection_config_fixture_for_tests,
)
from tests.test_c6b_policy_and_safety import policy_config_fixture_for_tests


def _baseline_evidence(**overrides: object) -> PolicyObservableEvidence:
    """Mirrors ``tests/test_c6b_policy_and_safety.py::_baseline_evidence``'s own shape exactly
    (reused, not re-invented) -- a private per-module helper, so restated here rather than
    imported across test modules."""
    base: dict = dict(
        session_mode="c_only", session_phase="c_only", current_difficulty_level=2,
        recent_correctness_rate=0.6, recent_avg_attempts=1.2, recent_inactivity_periods=0,
        recent_scaffold_use_count=0, recent_consecutive_error_max=0, rolling_strain_score=0.1,
        prior_session_end_state=None, is_recovery_context=False, technical_issue_current_task=False,
        safety_increase_block_remaining=0,
    )
    base.update(overrides)
    return PolicyObservableEvidence(**base)


def _seed_lineage() -> SeedLineage:
    return SeedLineage(global_seed=1, path=(("task_index", "1"),), seed=1)


def _oracle_safety_decision(
    evidence: PolicyObservableEvidence,
    *,
    policy_mode: str,
    policy_config,
    safety_config,
    selection_config,
):
    """T4-d-permitted test-side construction: calls the package's own ``propose_action`` +
    ``apply_safety`` directly (never through the adapter's reconstruction method), so this is a
    genuinely INDEPENDENT computation of the SafetyDecision the parity test below checks against
    -- not merely the adapter re-checking its own arithmetic."""
    from component_c_generator.policy.rule_based import propose_action as pkg_propose_action
    from component_c_generator.safety.controller import apply_safety as pkg_apply_safety

    from app.infrastructure.live_engine_c.adapter import (
        _to_pkg_policy_config,
        _to_pkg_policy_observable_evidence,
        _to_pkg_safety_config,
        _to_pkg_selection_config,
    )

    pkg_evidence = _to_pkg_policy_observable_evidence(evidence)
    pkg_policy_config = _to_pkg_policy_config(policy_config)
    pkg_safety_config = _to_pkg_safety_config(safety_config)
    pkg_selection_config = _to_pkg_selection_config(selection_config)

    selected_action = pkg_propose_action(policy_mode, pkg_evidence, pkg_policy_config)
    return pkg_apply_safety(
        selected_action=selected_action,
        evidence=pkg_evidence,
        current_difficulty_level=evidence.current_difficulty_level,
        selection_config=pkg_selection_config,
        safety_config=pkg_safety_config,
    )


# =====================================================================================
# THE IDENTITY GUARANTEE -- both assertions required (neither alone suffices):
# (a) the evidence translation happens EXACTLY ONCE per call -- survives a future refactor
#     re-translating a second time; (b) the SAME package-side evidence object (by `is`, not
#     equality) reaches both the direct apply_safety call and the direct decide_adaptation call
#     -- proves the one translated object is actually what is reused, not merely that translation
#     was cheap to call once.
# =====================================================================================


def test_evidence_translated_once_and_reaches_both_pinned_call_sites_by_identity(monkeypatch) -> None:
    """(a) counts calls to ``_to_pkg_policy_observable_evidence`` -- must be exactly 1 per
    invocation of ``decide_adaptation_with_safety_flags``. (b) spies on the ``evidence=`` kwarg
    as it reaches the adapter's own direct ``apply_safety`` call and its own direct
    ``decide_adaptation`` call, and asserts both spies captured the SAME object by identity
    (`is`), never merely equal values. (a) alone survives a refactor that adds a
    ``.model_copy()`` before one of the two pinned calls -- identity would silently break while
    the call count stayed 1. (b) alone does not prove only one translation occurred -- two
    separately-translated-but-equal objects would also satisfy an equality check. Both together
    are required."""
    translation_call_count = {"n": 0}
    real_translate = adapter_module._to_pkg_policy_observable_evidence

    def counting_translate(evidence):
        translation_call_count["n"] += 1
        return real_translate(evidence)

    monkeypatch.setattr(adapter_module, "_to_pkg_policy_observable_evidence", counting_translate)

    captured_evidence_objects: dict = {}
    real_apply_safety = adapter_module._pkg_apply_safety
    real_decide_adaptation = adapter_module._pkg_decide_adaptation

    def spy_apply_safety(*, selected_action, evidence, current_difficulty_level, selection_config, safety_config):
        captured_evidence_objects["apply_safety"] = evidence
        return real_apply_safety(
            selected_action=selected_action, evidence=evidence,
            current_difficulty_level=current_difficulty_level,
            selection_config=selection_config, safety_config=safety_config,
        )

    def spy_decide_adaptation(
        *, policy_mode, evidence, current_difficulty_level, seed_lineage, policy_config, safety_config,
        selection_config,
    ):
        captured_evidence_objects["decide_adaptation"] = evidence
        return real_decide_adaptation(
            policy_mode=policy_mode, evidence=evidence, current_difficulty_level=current_difficulty_level,
            seed_lineage=seed_lineage, policy_config=policy_config, safety_config=safety_config,
            selection_config=selection_config,
        )

    monkeypatch.setattr(adapter_module, "_pkg_apply_safety", spy_apply_safety)
    monkeypatch.setattr(adapter_module, "_pkg_decide_adaptation", spy_decide_adaptation)

    adapter = LiveEngineCAdapter()
    adapter.decide_adaptation_with_safety_flags(
        policy_mode="rule_based_baseline",
        evidence=_baseline_evidence(),
        current_difficulty_level=2,
        seed_lineage=_seed_lineage(),
        policy_config=policy_config_fixture_for_tests(),
        safety_config=safety_config_fixture_for_tests(),
        selection_config=selection_config_fixture_for_tests(),
    )

    # (a) exactly one translation.
    assert translation_call_count["n"] == 1

    # (b) the SAME object, by identity, reached both pinned call sites.
    assert "apply_safety" in captured_evidence_objects
    assert "decide_adaptation" in captured_evidence_objects
    assert captured_evidence_objects["apply_safety"] is captured_evidence_objects["decide_adaptation"]


# =====================================================================================
# THE PARITY TEST -- four branches minimum, parametrized. Compares the reconstructed
# SafetyDecision's six fields (as independently computed by _oracle_safety_decision above)
# against the six corresponding fields the package composes onto AdaptationDecision, accounting
# for the one rename (SafetyDecision.increase_block_remaining_after ->
# AdaptationDecision.increase_block_remaining). Trigger values are read from the config
# fixtures, never invented.
# =====================================================================================


def _policy_config():
    return policy_config_fixture_for_tests()


def _safety_config():
    return safety_config_fixture_for_tests()


def _selection_config():
    return selection_config_fixture_for_tests()


def _case_no_override_hold():
    """Branch 1: no override -- proposes hold, safety applies unchanged, activate_recovery_flag
    False. Baseline evidence never crosses any policy or safety threshold."""
    return {}


def _case_increase_veto():
    """Branch 2: increase veto -- high correctness proposes increase, an active carried-over
    increase block vetoes it, action_overridden True."""
    policy_config = _policy_config()
    return dict(
        recent_correctness_rate=policy_config.increase_correctness_threshold,
        recent_avg_attempts=policy_config.increase_max_avg_attempts,
        rolling_strain_score=policy_config.increase_max_strain,
        safety_increase_block_remaining=1,  # a carried-over block, no new trigger this task
    )


def _case_severe_trigger_error_arm():
    """Branch 3: severe-trigger decrease via the ERROR arm -- consecutive errors at/above the
    configured trigger, strain low. Exercises `trigger_error` specifically, not `trigger_strain`."""
    safety_config = _safety_config()
    return dict(
        recent_correctness_rate=0.6,
        recent_consecutive_error_max=safety_config.consecutive_error_trigger,
        rolling_strain_score=0.1,  # well below strain_trigger -- the STRAIN arm must stay unfired
    )


def _case_recovery_flag_strain_arm():
    """Branch 4: recovery flag via the STRAIN arm -- consecutive errors zero, rolling strain
    at/above the configured strain trigger. Exercises `trigger_strain` specifically, not
    `trigger_error` -- the other disjunct of the same condition branch 3 exercised."""
    safety_config = _safety_config()
    return dict(
        recent_consecutive_error_max=0,
        rolling_strain_score=safety_config.strain_trigger,
    )


@pytest.mark.parametrize(
    "case_name, overrides_factory",
    [
        ("no_override_hold", _case_no_override_hold),
        ("increase_veto", _case_increase_veto),
        ("severe_trigger_error_arm", _case_severe_trigger_error_arm),
        ("recovery_flag_strain_arm", _case_recovery_flag_strain_arm),
    ],
)
def test_reconstructed_safety_fields_match_the_composed_adaptation_decision(case_name, overrides_factory) -> None:
    policy_config = _policy_config()
    safety_config = _safety_config()
    selection_config = _selection_config()
    evidence = _baseline_evidence(**overrides_factory())

    adapter = LiveEngineCAdapter()
    result = adapter.decide_adaptation_with_safety_flags(
        policy_mode="rule_based_baseline",
        evidence=evidence,
        current_difficulty_level=2,
        seed_lineage=_seed_lineage(),
        policy_config=policy_config,
        safety_config=safety_config,
        selection_config=selection_config,
    )

    oracle = _oracle_safety_decision(
        evidence,
        policy_mode="rule_based_baseline",
        policy_config=policy_config,
        safety_config=safety_config,
        selection_config=selection_config,
    )

    # The six fields adaptation.py's own composition sources from the internal SafetyDecision --
    # five name-matched, one renamed (increase_block_remaining_after -> increase_block_remaining).
    assert result.decision.applied_action == oracle.applied_action, case_name
    assert result.decision.action_overridden == oracle.action_overridden, case_name
    assert result.decision.safety_reason == oracle.safety_reason, case_name
    assert result.decision.difficulty_after == oracle.difficulty_after, case_name
    assert result.decision.rolling_strain_bucket == oracle.rolling_strain_bucket, case_name
    assert result.decision.increase_block_remaining == oracle.increase_block_remaining_after, case_name

    # The two otherwise-dropped fields this reconstruction exists to recover.
    assert result.activate_recovery_flag == oracle.activate_recovery_flag, case_name
    assert result.request_safe_termination == oracle.request_safe_termination, case_name

    # Branch-specific semantics -- proves each case actually exercises the disjunct it claims to,
    # not merely that parity holds trivially regardless of which branch fired.
    if case_name == "no_override_hold":
        assert result.decision.selected_action == "hold"
        assert result.decision.applied_action == "hold"
        assert result.activate_recovery_flag is False
    elif case_name == "increase_veto":
        assert result.decision.selected_action == "increase_difficulty"
        assert result.decision.applied_action == "hold"
        assert result.decision.action_overridden is True
        assert "increase_blocked_active_window" in (result.decision.safety_reason or "")
        assert result.activate_recovery_flag is False
    elif case_name == "severe_trigger_error_arm":
        assert result.activate_recovery_flag is True
        assert "consecutive_error_safety_trigger" in (result.decision.safety_reason or "")
        assert "rolling_strain_safety_trigger" not in (result.decision.safety_reason or "")
    elif case_name == "recovery_flag_strain_arm":
        assert result.activate_recovery_flag is True
        assert "rolling_strain_safety_trigger" in (result.decision.safety_reason or "")
        assert "consecutive_error_safety_trigger" not in (result.decision.safety_reason or "")
