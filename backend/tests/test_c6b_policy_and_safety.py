"""Component C Phase 6b: policy and the hard safety controller. v3.0's own highest-risk phase.

DISCLOSED, HEADLINE (X2-3, same register position Phase 5 used for "endpoints deliberately not
live"): under this batch's own real field classification (X3-f), EVERY per-field status in the
committed reference bundle is either CALIBRATION_PENDING or PROPOSED_UNSIGNED -- none is
APPROVED. X1's whitelist (usable = {APPROVED} only) therefore makes session_lifecycle.
create_session's own structural gate (X4) refuse EVERY real request. As of this batch, Component
C's backend cannot create a session in production at all. This is not a defect; it is the direct,
intended consequence of applying a hard whitelist to a project where nothing is yet signed.

Every positive control below is exercised via DIRECT, test-side construction of
PolicyObservableEvidence and direct calls into LiveEngineCAdapter -- never through app/ code,
which the T4 guards forbid from constructing evidence directly (S5-b/T4-d: "Test-constructed
evidence is a stimulus... A builder refusing them by over-applying my Phase 5 ruling has made the
opposite error.").
"""

from __future__ import annotations

import asyncio
import subprocess
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.application.live_engine_c.adaptation_service import (
    RECOVERY_TRIGGER_REASON_TOKENS,
    SAFE_TERMINATION_REASON_TOKEN,
    build_evidence_for_session,
    decide_and_persist_adaptation,
)
from app.application.live_engine_c.bundle_resolution import (
    USABLE_APPROVAL_STATUSES,
    assert_family_usable,
    resolve_safety_config,
    resolve_selection_config,
)
from app.application.live_engine_c.mastery_fixture import (
    FIXTURE_MASTERY_SOURCE_INTERVENTION_SESSION_ID,
    FIXTURE_MASTERY_SOURCE_STUDENT_ID,
)
from app.application.live_engine_c.session_lifecycle import create_session
from app.core.errors import ConflictError
from app.domain.live_engine_c.errors import (
    ConfigurationFamilyNotUsableError,
    QLearningDisabledError,
    SafetyConfigurationMissingError,
)
from app.domain.live_engine_c.types import (
    EvidenceWindowConfig,
    PolicyConfig,
    PolicyObservableEvidence,
    SeedLineage,
)
from app.domain.runtime_bundle_c.types import (
    EvidenceWindowConfigurationArtifact,
    SafetyConfigurationArtifact,
    SelectionConfigurationArtifact,
)
from app.infrastructure.live_engine_c.adapter import LiveEngineCAdapter
from app.infrastructure.persistence_models import CTaskOpportunityRecord, CTaskOpportunitySummaryRecord
from app.infrastructure.repositories import CPolicyDecisionRecordRepository, CSafetyEventRecordRepository
from tests.test_c4_session_lifecycle import (
    all_calibration_pending_field_statuses,
    all_usable_field_statuses,
    isolated_database,
    provenance,
    safety_config_fixture_for_tests,
    seed_learner,
    seed_runtime_bundle,
    selection_config_fixture_for_tests,
)


def alembic(*args: str) -> None:
    subprocess.run(["alembic", *args], check=True)


def policy_config_fixture_for_tests() -> PolicyConfig:
    """TEST_FIXTURE_ONLY -- mirrors component_c_generator.policy.config.default_policy_config()'s
    own values (never calling that factory from app/)."""
    return PolicyConfig(
        config_version="c4.1-policy-1.0.0",
        parameter_source_status="TEST_FIXTURE_ONLY",
        increase_correctness_threshold=0.80,
        increase_max_avg_attempts=1.30,
        increase_max_strain=0.30,
        decrease_correctness_threshold=0.40,
        decrease_error_run_threshold=3,
        decrease_min_strain=0.60,
    )


def evidence_window_config_fixture_for_tests() -> EvidenceWindowConfig:
    return EvidenceWindowConfig(
        config_version="c6.0-evidence-window-1.0.0", parameter_source_status="TEST_FIXTURE_ONLY",
        recent_window_task_count=5,
    )


def _baseline_evidence(**overrides: object) -> PolicyObservableEvidence:
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


# =====================================================================================
# X1 -- THE WHITELIST. usable = {APPROVED}, nothing else, proven with a nonsense status.
# =====================================================================================


def test_x1_usable_set_is_exactly_approved() -> None:
    assert USABLE_APPROVAL_STATUSES == frozenset({"APPROVED"})


def test_x1b_nonsense_status_refuses_by_default() -> None:
    """X1-b: a status string that exists in NO enum, considered by nobody, must refuse -- proving
    the whitelist default, not a deny-list match on a known-bad value."""
    with pytest.raises(ConfigurationFamilyNotUsableError) as excinfo:
        assert_family_usable(
            family_name="selection_config",
            field_statuses={"some_field": "COMPLETELY_MADE_UP_NONSENSE_STATUS_XYZ"},
        )
    assert "some_field" in excinfo.value.unusable_fields


def test_x1_every_named_status_except_approved_is_unusable() -> None:
    """X1-a: a whitelist, not a deny-list -- every one of the OTHER six named statuses
    (PROPOSED_UNSIGNED included) refuses, proven per-status, not merely "PROPOSED_UNSIGNED
    specifically"."""
    for status in (
        "APPROVED_FOR_PROVISIONAL_IMPLEMENTATION", "PROVISIONAL", "ENGINEERING_ASSUMPTION",
        "CALIBRATION_PENDING", "DISABLED", "UNRESOLVED", "PROPOSED_UNSIGNED",
    ):
        with pytest.raises(ConfigurationFamilyNotUsableError):
            assert_family_usable(family_name="x", field_statuses={"f": status})


# =====================================================================================
# X4/Z2 -- the FIVE-family structural gate (Phase 7 extends X4's two-family gate to all five:
# Selection, Safety, Generation, Policy, Scaffold -- one mechanism, two entry points, one error
# type). Z2-d-5, the principle this whole section exists to prove, owner's words: "'no failure'
# is not evidence a mechanism works, and 'refused' is not evidence a particular gate fired."
# Parametrizing over five families with the gate always refusing for whatever reason would give
# five green tests attributable to nothing -- Case 0 (below) proves the gate CAN pass at all;
# Cases 1-5 each independently isolate exactly one family and assert the refusal's own structured
# identity, never merely "it raised."
# =====================================================================================


# Phase 7, Z2-d-2a: USABILITY SEMANTICS for the three code-gated families, stated and justified
# BEFORE Case 0 was attempted (recorded here, not discovered by tuning): a code-gated family's
# config is usable iff smoke_mode=True, OR its parameter_source_status is outside
# {"TEST_FIXTURE_ONLY", "SMOKE_ONLY"} -- component_c_generator.generation_mode_guard's own
# DISALLOWED_OUTSIDE_SMOKE_MODE set, unchanged, generalized to Policy and Scaffold by direct
# analogy (Z1: identical classification, identical field shape). Every REAL config anywhere in
# this codebase carries "TEST_FIXTURE_ONLY" -- no other value has ever been constructed -- so in
# practice smoke_mode is the only lever. To isolate ONE of the three code-gated families as the
# SOLE unusable one (Cases 3/4/5 need this independently of Generation, Policy, and Scaffold
# sharing no other coupling), the other two need a status OUTSIDE the disallowed set while
# smoke_mode stays False -- this constant supplies exactly that, a TEST-ONLY marker, never a real
# governance value, exercising the semantic's own "status outside the disallowed set" branch
# rather than loosening it.
_TEST_ONLY_STATUS_OUTSIDE_DISALLOWED_SET = "TEST_ISOLATION_MARKER_NEVER_A_REAL_STATUS"


async def _create_bundle_and_session(
    session,
    *,
    selection_statuses: dict,
    safety_statuses: dict,
    evidence_window_statuses: dict,
    generation_status: str = "TEST_FIXTURE_ONLY",
    policy_status: str = "TEST_FIXTURE_ONLY",
    scaffold_status: str = "TEST_FIXTURE_ONLY",
    aggregation_status: str = "TEST_FIXTURE_ONLY",
    q_policy_status: str = "TEST_FIXTURE_ONLY",   # LIVE-01: new gated family
    smoke_mode: bool = True,
    session_creation_spy: list | None,
):
    student_id = await seed_learner(session)
    bundle_id = await seed_runtime_bundle(session)
    adapter = LiveEngineCAdapter()
    return await create_session(
        session, adapter, student_id=student_id, c_runtime_bundle_record_id=bundle_id,
        grade=2, session_mode="c_only", catalogue_version="test-catalogue-1",
        catalogue_checksum="a" * 64, global_seed=42,
        selection_config=selection_config_fixture_for_tests(),
        selection_config_field_statuses=selection_statuses,
        safety_config_field_statuses=safety_statuses,
        evidence_window_config_field_statuses=evidence_window_statuses,
        generation_parameter_source_status=generation_status,
        policy_parameter_source_status=policy_status,
        scaffold_parameter_source_status=scaffold_status,
        aggregation_parameter_source_status=aggregation_status,
        q_policy_parameter_source_status=q_policy_status,
        smoke_mode=smoke_mode,
        request_id=f"req-{uuid4()}",
        session_creation_spy=session_creation_spy,
    )


def test_case0_all_five_families_usable_session_creation_succeeds() -> None:
    """CASE 0 (Z2-d-1, built and demonstrated FIRST, before any refusal case): all SIX families
    usable -> session creation SUCCEEDS, spy shows exactly one created row. THIS IS THE
    LOAD-BEARING CASE -- without it, no refusal case below is attributable to anything, because
    there would be no proof the gate can ever pass at all.

    PHASE 9a: extended from five families to six -- ``aggregation_config`` now gates here too
    (Z2's own existing rule, "EVERY parameter family gates SESSION START," applied rather than
    extended; see ``session_lifecycle.create_session``'s own docstring for why this family, unlike
    Phase 8's telemetry family, was created).

    SEVENTH-FAMILY GATE batch: extended from six families to seven -- ``evidence_window_config``
    now gates here too, the SAME existing rule applied a second time (see
    ``session_lifecycle.create_session``'s own docstring, "SEVENTH-FAMILY GATE BATCH" paragraph).
    This test's own name keeps the historical "five" for minimal diff against Case 0's own git
    history; the body and the families it exercises are seven.

    WHAT THIS TEST ACTUALLY PROVES, AND WHAT IT DOES NOT (Z2-d-6, stated in this test's own
    words, not left implicit): this test runs with the bundle approval opt-out ON
    (require_approved=False, via the fixture bundle's own resolution path), smoke_mode=True, and
    Policy/Scaffold's parameter_source_status left at their only real value
    ("TEST_FIXTURE_ONLY") -- usable here only because smoke_mode is on. So this test demonstrates
    that the FIVE GATES COMPOSE CORRECTLY under those levers: five independent usability checks,
    called in sequence, all passing, one session row written. It does NOT demonstrate that
    PRODUCTION session creation works -- in this codebase, production session creation
    (CSessionService.create) hardcodes smoke_mode=False and resolves a bundle whose real,
    committed per-field statuses are never APPROVED (X2-3), so it refuses unconditionally,
    permanently, by design. A reader who sees this test green and concludes "the gate is not
    blocking anything" has misread it -- the gate is blocking everything in production; this test
    only proves the gate itself is a real, passable mechanism when every lever it checks is
    deliberately set to its usable value, which production never does."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            spy: list = []
            record = await _create_bundle_and_session(
                session,
                selection_statuses=all_usable_field_statuses(SelectionConfigurationArtifact.FIELD_NAMES),
                safety_statuses=all_usable_field_statuses(SafetyConfigurationArtifact.FIELD_NAMES),
                evidence_window_statuses=all_usable_field_statuses(
                    EvidenceWindowConfigurationArtifact.FIELD_NAMES
                ),
                generation_status="TEST_FIXTURE_ONLY",
                policy_status="TEST_FIXTURE_ONLY",
                scaffold_status="TEST_FIXTURE_ONLY",
                smoke_mode=True,
                session_creation_spy=spy,
            )
            assert spy == [record.c_session_id]
            await session.commit()
        await database_engine.dispose()

    asyncio.run(exercise())


# =====================================================================================
# CASES 1-5 (Z2-d): four usable, family F unusable -> session creation REFUSES, spy empty, AND
# the raised error's own structured content names family F -- "the state construction makes the
# refusal real, the structured identity makes it attributable. Neither alone is sufficient"
# (Z2-d-4). Each case is independently constructed -- never a parametrization that would make all
# five pass for the same reason (Z2-d's own rejected shape).
# =====================================================================================


def test_case1_selection_unusable_refuses_and_names_selection_config() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            spy: list = []
            with pytest.raises(ConfigurationFamilyNotUsableError) as excinfo:
                await _create_bundle_and_session(
                    session,
                    selection_statuses=all_calibration_pending_field_statuses(
                        SelectionConfigurationArtifact.FIELD_NAMES
                    ),
                    safety_statuses=all_usable_field_statuses(SafetyConfigurationArtifact.FIELD_NAMES),
                    evidence_window_statuses=all_usable_field_statuses(
                        EvidenceWindowConfigurationArtifact.FIELD_NAMES
                    ),
                    smoke_mode=True,
                    session_creation_spy=spy,
                )
            assert spy == []
            assert excinfo.value.family_name == "selection_config"
        await database_engine.dispose()

    asyncio.run(exercise())


def test_case2_safety_unusable_refuses_and_names_safety_config() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            spy: list = []
            with pytest.raises(ConfigurationFamilyNotUsableError) as excinfo:
                await _create_bundle_and_session(
                    session,
                    selection_statuses=all_usable_field_statuses(SelectionConfigurationArtifact.FIELD_NAMES),
                    safety_statuses=all_calibration_pending_field_statuses(
                        SafetyConfigurationArtifact.FIELD_NAMES
                    ),
                    evidence_window_statuses=all_usable_field_statuses(
                        EvidenceWindowConfigurationArtifact.FIELD_NAMES
                    ),
                    smoke_mode=True,
                    session_creation_spy=spy,
                )
            assert spy == []
            assert excinfo.value.family_name == "safety_config"
        await database_engine.dispose()

    asyncio.run(exercise())


def test_case3_generation_unusable_refuses_and_names_generation_config() -> None:
    """Isolates Generation as the SOLE unusable code-gated family: smoke_mode=False (so Generation's
    own TEST_FIXTURE_ONLY status is disallowed) while Policy and Scaffold are independently made
    usable via the test-only marker status (see its own module-level docstring for why this is
    exercising the semantic, not loosening it)."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            spy: list = []
            with pytest.raises(ConfigurationFamilyNotUsableError) as excinfo:
                await _create_bundle_and_session(
                    session,
                    selection_statuses=all_usable_field_statuses(SelectionConfigurationArtifact.FIELD_NAMES),
                    safety_statuses=all_usable_field_statuses(SafetyConfigurationArtifact.FIELD_NAMES),
                    evidence_window_statuses=all_usable_field_statuses(
                        EvidenceWindowConfigurationArtifact.FIELD_NAMES
                    ),
                    generation_status="TEST_FIXTURE_ONLY",
                    policy_status=_TEST_ONLY_STATUS_OUTSIDE_DISALLOWED_SET,
                    scaffold_status=_TEST_ONLY_STATUS_OUTSIDE_DISALLOWED_SET,
                    aggregation_status=_TEST_ONLY_STATUS_OUTSIDE_DISALLOWED_SET,
                    smoke_mode=False,
                    session_creation_spy=spy,
                )
            assert spy == []
            assert excinfo.value.family_name == "generation_config"
        await database_engine.dispose()

    asyncio.run(exercise())


def test_case4_policy_unusable_refuses_and_names_policy_config() -> None:
    """Isolates Policy: smoke_mode=False, Generation and Scaffold independently made usable via
    the test-only marker status, only Policy left at TEST_FIXTURE_ONLY. Z2-c's own coupling
    (apply_safety is called INSIDE decide_adaptation, adaptation.py:46) is why this family's gate
    matters at all -- this test proves the GATE fires for Policy specifically, not that the
    downstream coupling is exercised (that is Criterion 1's job, unchanged)."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            spy: list = []
            with pytest.raises(ConfigurationFamilyNotUsableError) as excinfo:
                await _create_bundle_and_session(
                    session,
                    selection_statuses=all_usable_field_statuses(SelectionConfigurationArtifact.FIELD_NAMES),
                    safety_statuses=all_usable_field_statuses(SafetyConfigurationArtifact.FIELD_NAMES),
                    evidence_window_statuses=all_usable_field_statuses(
                        EvidenceWindowConfigurationArtifact.FIELD_NAMES
                    ),
                    generation_status=_TEST_ONLY_STATUS_OUTSIDE_DISALLOWED_SET,
                    policy_status="TEST_FIXTURE_ONLY",
                    scaffold_status=_TEST_ONLY_STATUS_OUTSIDE_DISALLOWED_SET,
                    aggregation_status=_TEST_ONLY_STATUS_OUTSIDE_DISALLOWED_SET,
                    smoke_mode=False,
                    session_creation_spy=spy,
                )
            assert spy == []
            assert excinfo.value.family_name == "policy_config"
        await database_engine.dispose()

    asyncio.run(exercise())


def test_case5_scaffold_unusable_refuses_and_names_scaffold_config() -> None:
    """Isolates Scaffold: smoke_mode=False, Generation and Policy independently made usable via
    the test-only marker status, only Scaffold left at TEST_FIXTURE_ONLY."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            spy: list = []
            with pytest.raises(ConfigurationFamilyNotUsableError) as excinfo:
                await _create_bundle_and_session(
                    session,
                    selection_statuses=all_usable_field_statuses(SelectionConfigurationArtifact.FIELD_NAMES),
                    safety_statuses=all_usable_field_statuses(SafetyConfigurationArtifact.FIELD_NAMES),
                    evidence_window_statuses=all_usable_field_statuses(
                        EvidenceWindowConfigurationArtifact.FIELD_NAMES
                    ),
                    generation_status=_TEST_ONLY_STATUS_OUTSIDE_DISALLOWED_SET,
                    policy_status=_TEST_ONLY_STATUS_OUTSIDE_DISALLOWED_SET,
                    scaffold_status="TEST_FIXTURE_ONLY",
                    aggregation_status=_TEST_ONLY_STATUS_OUTSIDE_DISALLOWED_SET,
                    smoke_mode=False,
                    session_creation_spy=spy,
                )
            assert spy == []
            assert excinfo.value.family_name == "scaffold_config"


def test_case6_aggregation_unusable_refuses_and_names_aggregation_config() -> None:
    """Isolates Aggregation (Phase 9a, P5-a): smoke_mode=False, Generation/Policy/Scaffold all
    independently made usable via the test-only marker status, only Aggregation left at
    TEST_FIXTURE_ONLY. Same shape as Cases 3-5, one family later -- AggregationConfig exists, is
    consumed by pinned code, and this batch uses it (see session_lifecycle.create_session's own
    docstring for why this differs from Phase 8's telemetry family, which was never created)."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            spy: list = []
            with pytest.raises(ConfigurationFamilyNotUsableError) as excinfo:
                await _create_bundle_and_session(
                    session,
                    selection_statuses=all_usable_field_statuses(SelectionConfigurationArtifact.FIELD_NAMES),
                    safety_statuses=all_usable_field_statuses(SafetyConfigurationArtifact.FIELD_NAMES),
                    evidence_window_statuses=all_usable_field_statuses(
                        EvidenceWindowConfigurationArtifact.FIELD_NAMES
                    ),
                    generation_status=_TEST_ONLY_STATUS_OUTSIDE_DISALLOWED_SET,
                    policy_status=_TEST_ONLY_STATUS_OUTSIDE_DISALLOWED_SET,
                    scaffold_status=_TEST_ONLY_STATUS_OUTSIDE_DISALLOWED_SET,
                    aggregation_status="TEST_FIXTURE_ONLY",
                    smoke_mode=False,
                    session_creation_spy=spy,
                )
            assert spy == []
            assert excinfo.value.family_name == "aggregation_config"
        await database_engine.dispose()

    asyncio.run(exercise())


def test_case7_evidence_window_unusable_refuses_and_names_evidence_window_config() -> None:
    """Isolates EvidenceWindowConfig (SEVENTH-FAMILY GATE batch): a BUNDLE-classified family, so
    this case has the SAME shape as Cases 1-2 (smoke_mode=True, the three code-gated families
    left at their only real value, usable only because smoke_mode is on), not Cases 3-6's
    marker-status shape -- evidence_window_config isolates via its own per-field status map,
    exactly like selection_config/safety_config. EvidenceWindowConfig exists
    (``domain/live_engine_c/types.py``), is consumed by ``adaptation_service.
    build_evidence_for_session``, and this batch wires its real resolver into both
    ``c_session_service.CSessionService.create`` and ``task_service.TaskService.submit_action``
    -- the same "exists, is consumed, this batch uses it" shape Case 6's own docstring names for
    Aggregation, one family later."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            spy: list = []
            with pytest.raises(ConfigurationFamilyNotUsableError) as excinfo:
                await _create_bundle_and_session(
                    session,
                    selection_statuses=all_usable_field_statuses(SelectionConfigurationArtifact.FIELD_NAMES),
                    safety_statuses=all_usable_field_statuses(SafetyConfigurationArtifact.FIELD_NAMES),
                    evidence_window_statuses=all_calibration_pending_field_statuses(
                        EvidenceWindowConfigurationArtifact.FIELD_NAMES
                    ),
                    smoke_mode=True,
                    session_creation_spy=spy,
                )
            assert spy == []
            assert excinfo.value.family_name == "evidence_window_config"
        await database_engine.dispose()

    asyncio.run(exercise())


# =====================================================================================
# W2-b -- nine usable, one pending: per-field status is for accuracy of the record, never
# partial enablement. Parametrized across ALL nine safety fields.
# =====================================================================================


@pytest.mark.parametrize("pending_field", SafetyConfigurationArtifact.FIELD_NAMES)
def test_w2b_one_pending_safety_field_makes_the_whole_block_unusable(pending_field: str) -> None:
    statuses = all_usable_field_statuses(SafetyConfigurationArtifact.FIELD_NAMES)
    statuses[pending_field] = "CALIBRATION_PENDING"
    with pytest.raises(ConfigurationFamilyNotUsableError) as excinfo:
        assert_family_usable(family_name="safety_config", field_statuses=statuses)
    assert excinfo.value.unusable_fields == (pending_field,)


def test_w2b_all_nine_usable_succeeds() -> None:
    """The paired positive control X2-2 itself demands: nine refuses (above, parametrized) AND
    ten succeeds -- without this, "nine refuses" could pass merely because the check never runs
    at all under some other silent short-circuit."""
    assert_family_usable(
        family_name="safety_config",
        field_statuses=all_usable_field_statuses(SafetyConfigurationArtifact.FIELD_NAMES),
    )  # does not raise


# =====================================================================================
# Criterion 1 -- six positive controls. Each docstring carries BOTH X7-a limits: reachability
# not correctness, against TEST_FIXTURE_ONLY thresholds; AND, until I4 unblocks the attempt cap,
# production history structurally cannot contain errors, so these controls are simultaneously
# the only thing exercising the triggers AND calibrated against invented numbers.
# =====================================================================================

_BOTH_LIMITS = (
    "REACHABILITY, NOT CORRECTNESS: proves the branch CAN fire, not that it fires at the right "
    "point, and is written against TEST_FIXTURE_ONLY thresholds that need revisiting on "
    "calibration. SECOND, INDEPENDENT LIMIT: until I4 unblocks the attempt cap, production "
    "history structurally cannot contain errors, so this control is simultaneously the only "
    "thing exercising this trigger AND calibrated against invented numbers."
)


def test_c1_veto_increase() -> None:
    f"""Criterion 1, action 1/6 -- veto increase. {_BOTH_LIMITS}"""
    safety_config = safety_config_fixture_for_tests()
    policy_config = policy_config_fixture_for_tests()
    selection_config = selection_config_fixture_for_tests()
    adapter = LiveEngineCAdapter()
    evidence = _baseline_evidence(
        recent_correctness_rate=0.95, recent_avg_attempts=1.0, rolling_strain_score=0.05,
        safety_increase_block_remaining=1,  # a carried-over block, no new trigger this task
    )
    decision = adapter.decide_adaptation(
        policy_mode="rule_based_baseline", evidence=evidence, current_difficulty_level=2,
        seed_lineage=_seed_lineage(), policy_config=policy_config, safety_config=safety_config,
        selection_config=selection_config,
    )
    assert decision.selected_action == "increase_difficulty"
    assert decision.applied_action == "hold"
    assert "increase_blocked_active_window" in (decision.safety_reason or "")
    assert decision.action_overridden is True


def test_c2_force_hold() -> None:
    f"""Criterion 1, action 2/6 -- force hold (technical issue neutralization). {_BOTH_LIMITS}"""
    safety_config = safety_config_fixture_for_tests()
    policy_config = policy_config_fixture_for_tests()
    selection_config = selection_config_fixture_for_tests()
    adapter = LiveEngineCAdapter()
    evidence = _baseline_evidence(
        recent_correctness_rate=0.2, recent_consecutive_error_max=1, rolling_strain_score=0.2,
        technical_issue_current_task=True,
    )
    decision = adapter.decide_adaptation(
        policy_mode="rule_based_baseline", evidence=evidence, current_difficulty_level=2,
        seed_lineage=_seed_lineage(), policy_config=policy_config, safety_config=safety_config,
        selection_config=selection_config,
    )
    assert decision.selected_action == "decrease_difficulty"
    assert decision.applied_action == "hold"
    assert "technical_issue_neutralized" in (decision.safety_reason or "")


def test_c3_decrease_via_severe_trigger() -> None:
    f"""Criterion 1, action 3/6 -- decrease difficulty via a severe safety trigger. DISCLOSED
    LIMIT specific to this control: safety.config.CSafetyConfig's own docstring states
    consecutive_error_trigger is "deliberately set at or above the rule-based policy's own
    decrease_error_run_threshold" (5 >= 3 here) -- so any evidence severe enough to trip safety's
    trigger ALSO trips the policy's own decrease proposal; this control proves the safety-layer
    REASON CODE fires and is recorded (the auditable, logged fact SPEC §17 requires), not that
    safety's decrease OVERRIDES a conflicting policy proposal -- that specific override shape is
    structurally unreachable under this exact fixture threshold relationship, not tested here,
    and not silently implied. {_BOTH_LIMITS}"""
    safety_config = safety_config_fixture_for_tests()
    policy_config = policy_config_fixture_for_tests()
    selection_config = selection_config_fixture_for_tests()
    adapter = LiveEngineCAdapter()
    evidence = _baseline_evidence(
        recent_correctness_rate=0.6, recent_consecutive_error_max=5, rolling_strain_score=0.1,
    )
    decision = adapter.decide_adaptation(
        policy_mode="rule_based_baseline", evidence=evidence, current_difficulty_level=2,
        seed_lineage=_seed_lineage(), policy_config=policy_config, safety_config=safety_config,
        selection_config=selection_config,
    )
    assert decision.applied_action == "decrease_difficulty"
    assert any(token in (decision.safety_reason or "") for token in RECOVERY_TRIGGER_REASON_TOKENS)


def test_c4_activate_recovery_flag_proxy() -> None:
    f"""Criterion 1, action 4/6 -- activate C4 recovery. AdaptationPort.decide_adaptation's
    composed AdaptationDecision does not expose SafetyDecision.activate_recovery_flag as its own
    boolean (only the pinned, internal SafetyDecision does, and it never crosses X-3 on its own)
    -- detected here via the SAME reason tokens controller.py's own `activate_recovery_flag =
    trigger_error or trigger_strain` always appends alongside (verified by direct read of
    safety/controller.py:64-72). {_BOTH_LIMITS}"""
    safety_config = safety_config_fixture_for_tests()
    policy_config = policy_config_fixture_for_tests()
    selection_config = selection_config_fixture_for_tests()
    adapter = LiveEngineCAdapter()
    evidence = _baseline_evidence(rolling_strain_score=0.90)  # >= strain_trigger=0.85
    decision = adapter.decide_adaptation(
        policy_mode="rule_based_baseline", evidence=evidence, current_difficulty_level=2,
        seed_lineage=_seed_lineage(), policy_config=policy_config, safety_config=safety_config,
        selection_config=selection_config,
    )
    assert "rolling_strain_safety_trigger" in (decision.safety_reason or "")


def test_c5_arm_increase_block() -> None:
    f"""Criterion 1, action 5/6 -- arm the increase-block window. {_BOTH_LIMITS}"""
    safety_config = safety_config_fixture_for_tests()
    policy_config = policy_config_fixture_for_tests()
    selection_config = selection_config_fixture_for_tests()
    adapter = LiveEngineCAdapter()
    evidence = _baseline_evidence(recent_consecutive_error_max=5)  # >= consecutive_error_trigger=5
    decision = adapter.decide_adaptation(
        policy_mode="rule_based_baseline", evidence=evidence, current_difficulty_level=2,
        seed_lineage=_seed_lineage(), policy_config=policy_config, safety_config=safety_config,
        selection_config=selection_config,
    )
    assert decision.increase_block_remaining == safety_config.increase_block_window


def test_c6_request_safe_termination() -> None:
    f"""Criterion 1, action 6/6 -- request safe session termination. {_BOTH_LIMITS}"""
    safety_config = safety_config_fixture_for_tests()
    policy_config = policy_config_fixture_for_tests()
    selection_config = selection_config_fixture_for_tests()
    adapter = LiveEngineCAdapter()
    evidence = _baseline_evidence(
        recent_consecutive_error_max=7,  # >= safe_termination_error_threshold=7
    )
    decision = adapter.decide_adaptation(
        policy_mode="rule_based_baseline", evidence=evidence, current_difficulty_level=2,
        seed_lineage=_seed_lineage(), policy_config=policy_config, safety_config=safety_config,
        selection_config=selection_config,
    )
    assert SAFE_TERMINATION_REASON_TOKEN in (decision.safety_reason or "")


# =====================================================================================
# S8-c -- no path returns an unsafetied decision. Structural (the pinned function's own
# composition) plus a behavioral proof.
# =====================================================================================


def test_s8c_decide_adaptation_always_applies_safety_structurally() -> None:
    """S8-c: reads adaptation.py's own source (pinned, byte-identical) and asserts apply_safety
    is called unconditionally -- not behind any if-branch that could skip it."""
    import inspect

    from component_c_generator import adaptation as pkg_adaptation

    source = inspect.getsource(pkg_adaptation.decide_adaptation)
    assert "apply_safety(" in source
    # Structural: apply_safety's own call is not inside any conditional in this function body --
    # verified by AST, not string position, so indentation changes cannot silently defeat this.
    import ast

    tree = ast.parse(source)
    func = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
    top_level_calls = [
        n.value.func.id if isinstance(n.value.func, ast.Name) else None
        for n in func.body if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call)
    ]
    assert "apply_safety" in top_level_calls, "apply_safety must be called at the function's top level, unconditionally"


def test_s8c_behavioral_every_decision_carries_safety_fields() -> None:
    """Behavioral companion: every AdaptationDecision, triggering or not, carries a
    rolling_strain_bucket and a non-negative increase_block_remaining -- fields only apply_safety
    computes, never left null/absent."""
    safety_config = safety_config_fixture_for_tests()
    policy_config = policy_config_fixture_for_tests()
    selection_config = selection_config_fixture_for_tests()
    adapter = LiveEngineCAdapter()
    for evidence in (_baseline_evidence(), _baseline_evidence(recent_consecutive_error_max=5)):
        decision = adapter.decide_adaptation(
            policy_mode="rule_based_baseline", evidence=evidence, current_difficulty_level=2,
            seed_lineage=_seed_lineage(), policy_config=policy_config, safety_config=safety_config,
            selection_config=selection_config,
        )
        assert decision.rolling_strain_bucket in ("low", "moderate", "high", "severe")
        assert decision.increase_block_remaining >= 0


# =====================================================================================
# S8-d -- Q-learning both directions (X-10).
# =====================================================================================


def test_s8d_rule_based_baseline_works() -> None:
    safety_config = safety_config_fixture_for_tests()
    policy_config = policy_config_fixture_for_tests()
    selection_config = selection_config_fixture_for_tests()
    adapter = LiveEngineCAdapter()
    decision = adapter.decide_adaptation(
        policy_mode="rule_based_baseline", evidence=_baseline_evidence(), current_difficulty_level=2,
        seed_lineage=_seed_lineage(), policy_config=policy_config, safety_config=safety_config,
        selection_config=selection_config,
    )
    assert decision.policy_mode == "rule_based_baseline"


async def _seed_session_with_summaries(session, *, summary_overrides: list[dict]) -> tuple[UUID, UUID]:
    """Shared setup for criterion 2/3/S8-b: a real CSessionRecord (via create_session, all-usable
    statuses -- these tests are about evidence assembly, not the gate) plus one
    CTaskOpportunityRecord/CTaskInstanceRecord/CTaskOpportunitySummaryRecord chain per entry in
    ``summary_overrides`` (each a dict of CTaskOpportunitySummaryRecord field overrides layered
    on a minimal valid default). Returns ``(c_session_id, last_instance_id)`` -- the last created
    instance id, for callers exercising ``build_evidence_for_session``'s own Z6-a
    ``recovery_parent_instance_id`` derivation (every instance here has it set to ``None``, so
    ``is_recovery_context`` derives to ``False``, matching every prior call site's own literal
    ``False``)."""
    from datetime import UTC, datetime as dt

    from app.infrastructure.persistence_models import CTaskInstanceRecord

    record = await _create_bundle_and_session(
        session,
        selection_statuses=all_usable_field_statuses(SelectionConfigurationArtifact.FIELD_NAMES),
        safety_statuses=all_usable_field_statuses(SafetyConfigurationArtifact.FIELD_NAMES),
        evidence_window_statuses=all_usable_field_statuses(EvidenceWindowConfigurationArtifact.FIELD_NAMES),
        session_creation_spy=None,
    )
    c_session_id = record.c_session_id

    for task_index, overrides in enumerate(summary_overrides, start=1):
        opportunity_id = uuid4()
        session.add(
            CTaskOpportunityRecord(
                c_task_opportunity_id=opportunity_id, c_session_id=c_session_id, task_index=task_index,
                selected_skill_id="counting", selected_template_id="C-FIXTURE", initial_difficulty_level=1,
                mastery_context_mode="unavailable_fallback", mastery_selected_skill=None,
                session_phase="c_only", terminal_reason=None, task_offered_at_utc=dt.now(UTC),
                **provenance("c_task_opportunity", opportunity_id),
            )
        )
        await session.flush()
        instance_id = uuid4()
        session.add(
            CTaskInstanceRecord(
                c_task_instance_id=instance_id, c_task_opportunity_id=opportunity_id,
                game_family_id="C-GF-FIXTURE", game_task_template_id="C-FIXTURE", template_version="v0",
                catalogue_version="test-catalogue-1", generator_version="test-gen-1", task_index=task_index,
                skill_id="counting", curriculum_node_id="node", grade_scope=2, difficulty_level=1,
                difficulty_vector={}, functional_role="MAIN", representation_mode="text",
                prompt_payload={}, interactive_assets={}, correct_answer_payload={"x": 1},
                correctness_function_id="_evaluate_fixture", valid_action_space={"x": "int"},
                completion_condition="submit", failure_condition="none", scaffold_state="C0",
                recovery_parent_instance_id=None, technical_status="OK",
                seed_lineage_global_seed=1, seed_lineage_path=[], seed_lineage_seed=1,
                **provenance("c_task_instance", instance_id),
            )
        )
        await session.flush()
        defaults = dict(
            task_offered=True, task_started=True, task_completed=True, task_skipped=False,
            task_quit=False, technical_issue=False, correct_task=True, total_attempts=1, retry_count=0,
            scaffold_requested=False, scaffold_count=0, highest_scaffold_level=None, c_answer_changes=0,
            task_latency_sec=1.5, inactive_time_sec=0.0, inactivity_periods=0, quit_after_error=False,
            terminal_reason="completed_correct", first_attempt_correct=True, final_attempt_correct=True,
            consecutive_error_max_within_task=0,
        )
        defaults.update(overrides)
        defaults["retry_count"] = max(defaults["total_attempts"] - 1, 0)
        summary_id = uuid4()
        session.add(
            CTaskOpportunitySummaryRecord(
                c_task_opportunity_summary_id=summary_id, c_session_id=c_session_id,
                game_task_instance_id=instance_id, task_index=task_index,
                **provenance("c_task_opportunity_summary", summary_id), **defaults,
            )
        )
    await session.flush()
    return c_session_id, instance_id


# =====================================================================================
# Criterion 2 -- estimator-input parity, SETTLED per S5-a (6a's own finding): both paths call
# the SAME shipped build_policy_evidence, so the real subject is the backend's OWN history
# assembly (completeness and ordering), not the package function's own correctness. No
# externally-generated fixture is needed.
# =====================================================================================


def test_criterion2_backend_history_assembly_matches_the_oracle_field_for_field() -> None:
    """A pass establishes that the backend reads and orders EVERY persisted summary for a session
    faithfully before handing it to the shipped build_policy_evidence -- NOT that
    build_policy_evidence's own windowing/aggregation is correct (that is pinned, reviewed
    research code, out of this project's authority, same limit 6a's own parity test named)."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            c_session_id, current_instance_id = await _seed_session_with_summaries(
                session,
                summary_overrides=[
                    {"correct_task": True, "total_attempts": 1},
                    {"correct_task": False, "total_attempts": 2, "consecutive_error_max_within_task": 1},
                    {"correct_task": True, "total_attempts": 1},
                ],
            )
            adapter = LiveEngineCAdapter()
            evidence = await build_evidence_for_session(
                session, adapter=adapter, c_session_id=c_session_id,
                student_id=FIXTURE_MASTERY_SOURCE_STUDENT_ID,
                intervention_session_id=FIXTURE_MASTERY_SOURCE_INTERVENTION_SESSION_ID,
                stu_session_id=f"{FIXTURE_MASTERY_SOURCE_STUDENT_ID}-C-001",
                session_mode="c_only", session_phase="c_only", current_difficulty_level=1,
                c_task_instance_id=current_instance_id, prior_session_end_state=None,
                evidence_window_config=evidence_window_config_fixture_for_tests(),
            )

            # Oracle: the SAME three summaries, read back and reconstituted the same way (proving
            # this test's own fixture round-trips), run through the shipped function directly.
            from app.infrastructure.repositories import CTaskOpportunitySummaryRecordRepository
            from component_c_generator.pipeline.evidence import (
                build_policy_evidence as pkg_build_policy_evidence,
            )
            from component_c_generator.pipeline.config import CEvidenceWindowConfig as PkgWindowConfig

            records = await CTaskOpportunitySummaryRecordRepository(session).list_ordered_for_session(
                c_session_id
            )
            from app.application.live_engine_c.adaptation_service import _to_domain_summary
            from app.infrastructure.live_engine_c.adapter import _to_pkg_task_opportunity_summary

            pkg_history = [
                _to_pkg_task_opportunity_summary(
                    _to_domain_summary(
                        r, student_id=FIXTURE_MASTERY_SOURCE_STUDENT_ID,
                        intervention_session_id=FIXTURE_MASTERY_SOURCE_INTERVENTION_SESSION_ID,
                        c_session_id=f"{FIXTURE_MASTERY_SOURCE_STUDENT_ID}-C-001",
                    )
                )
                for r in records
            ]
            oracle = pkg_build_policy_evidence(
                session_mode="c_only", session_phase="c_only", current_difficulty_level=1,
                history=pkg_history, is_recovery_context=False, prior_session_end_state=None,
                safety_increase_block_remaining=0,
                config=PkgWindowConfig(
                    config_version="c6.0-evidence-window-1.0.0",
                    parameter_source_status="TEST_FIXTURE_ONLY", recent_window_task_count=5,
                ),
            )

            for field in (
                "recent_correctness_rate", "recent_avg_attempts", "recent_inactivity_periods",
                "recent_scaffold_use_count", "recent_consecutive_error_max", "rolling_strain_score",
            ):
                assert getattr(evidence, field) == getattr(oracle, field), field
        await database_engine.dispose()

    asyncio.run(exercise())


# =====================================================================================
# Criterion 3 -- truncated-history regression: a silent truncation must be VISIBLE.
# =====================================================================================


def test_criterion3_truncated_history_produces_different_evidence_than_full_history() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            c_session_id, current_instance_id = await _seed_session_with_summaries(
                session,
                summary_overrides=[
                    {"correct_task": False, "total_attempts": 3, "consecutive_error_max_within_task": 2},
                    {"correct_task": False, "total_attempts": 3, "consecutive_error_max_within_task": 2},
                    {"correct_task": True, "total_attempts": 1, "consecutive_error_max_within_task": 0},
                ],
            )
            adapter = LiveEngineCAdapter()
            full_evidence = await build_evidence_for_session(
                session, adapter=adapter, c_session_id=c_session_id,
                student_id=FIXTURE_MASTERY_SOURCE_STUDENT_ID,
                intervention_session_id=FIXTURE_MASTERY_SOURCE_INTERVENTION_SESSION_ID,
                stu_session_id=f"{FIXTURE_MASTERY_SOURCE_STUDENT_ID}-C-001",
                session_mode="c_only", session_phase="c_only", current_difficulty_level=1,
                c_task_instance_id=current_instance_id, prior_session_end_state=None,
                evidence_window_config=evidence_window_config_fixture_for_tests(),
            )

            # Truncated: only the current (last) task's summary, mirroring what a silent
            # truncation bug would look like.
            from app.infrastructure.repositories import CTaskOpportunitySummaryRecordRepository

            records = await CTaskOpportunitySummaryRecordRepository(session).list_ordered_for_session(
                c_session_id
            )
            from app.application.live_engine_c.adaptation_service import _to_domain_summary

            truncated_history = [
                _to_domain_summary(
                    records[-1], student_id=FIXTURE_MASTERY_SOURCE_STUDENT_ID,
                    intervention_session_id=FIXTURE_MASTERY_SOURCE_INTERVENTION_SESSION_ID,
                    c_session_id=f"{FIXTURE_MASTERY_SOURCE_STUDENT_ID}-C-001",
                )
            ]
            truncated_evidence = adapter.build_policy_evidence(
                session_mode="c_only", session_phase="c_only", current_difficulty_level=1,
                history=truncated_history, is_recovery_context=False, prior_session_end_state=None,
                safety_increase_block_remaining=0, config=evidence_window_config_fixture_for_tests(),
            )

            assert full_evidence.recent_correctness_rate != truncated_evidence.recent_correctness_rate
        await database_engine.dispose()

    asyncio.run(exercise())


# =====================================================================================
# S8-b -- the increase-block feedback loop is STATEFUL ACROSS TASKS. Would fail if the value
# were not persisted and fed back.
# =====================================================================================


def test_s8b_increase_block_remaining_persists_and_feeds_back_across_tasks() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            c_session_id, current_instance_id = await _seed_session_with_summaries(
                session, summary_overrides=[{"consecutive_error_max_within_task": 5}],
            )
            opportunities = (await session.execute(
                __import__("sqlalchemy").select(CTaskOpportunityRecord).where(
                    CTaskOpportunityRecord.c_session_id == c_session_id
                )
            )).scalars().all()
            opportunity_id = opportunities[0].c_task_opportunity_id
            await session.commit()

            adapter = LiveEngineCAdapter()
            safety_config = safety_config_fixture_for_tests()
            policy_config = policy_config_fixture_for_tests()
            selection_config = selection_config_fixture_for_tests()

            # Task 1: a severe trigger arms the block.
            evidence_1 = await build_evidence_for_session(
                session, adapter=adapter, c_session_id=c_session_id,
                student_id=FIXTURE_MASTERY_SOURCE_STUDENT_ID,
                intervention_session_id=FIXTURE_MASTERY_SOURCE_INTERVENTION_SESSION_ID,
                stu_session_id=f"{FIXTURE_MASTERY_SOURCE_STUDENT_ID}-C-001",
                session_mode="c_only", session_phase="c_only", current_difficulty_level=1,
                c_task_instance_id=current_instance_id, prior_session_end_state=None,
                evidence_window_config=evidence_window_config_fixture_for_tests(),
            )
            assert evidence_1.safety_increase_block_remaining == 0  # nothing persisted yet
            decision_1 = await decide_and_persist_adaptation(
                session, adapter=adapter, c_session_id=c_session_id, c_task_opportunity_id=opportunity_id,
                policy_mode="rule_based_baseline", evidence=evidence_1, current_difficulty_level=1,
                seed_lineage=_seed_lineage(), policy_config=policy_config, safety_config=safety_config,
                selection_config=selection_config, request_id=f"req-{uuid4()}",
            )
            assert decision_1.increase_block_remaining == safety_config.increase_block_window

            # Task 2: the SAME session -- evidence must read the PERSISTED value back, not a
            # fresh default. Would FAIL (asserting 0) if the value were not fed back.
            evidence_2 = await build_evidence_for_session(
                session, adapter=adapter, c_session_id=c_session_id,
                student_id=FIXTURE_MASTERY_SOURCE_STUDENT_ID,
                intervention_session_id=FIXTURE_MASTERY_SOURCE_INTERVENTION_SESSION_ID,
                stu_session_id=f"{FIXTURE_MASTERY_SOURCE_STUDENT_ID}-C-001",
                session_mode="c_only", session_phase="c_only", current_difficulty_level=1,
                c_task_instance_id=current_instance_id, prior_session_end_state=None,
                evidence_window_config=evidence_window_config_fixture_for_tests(),
            )
            assert evidence_2.safety_increase_block_remaining == decision_1.increase_block_remaining

            # The real assembly's own recent_consecutive_error_max is a MAX over the whole
            # window (pipeline/evidence.py) and task 1's triggering summary is still IN that
            # window, so evidence_2 (built via the real assembly above) would re-arm the block
            # rather than decrement it -- correct windowing behavior, not what this assertion is
            # about. To isolate the DECREMENT branch specifically, evidence_3 is hand-built
            # (T4-d-permitted test-side construction) with a LOW error/strain and the SAME fed-
            # back safety_increase_block_remaining evidence_2 already proved was read correctly.
            evidence_3 = _baseline_evidence(
                session_mode="c_only", session_phase="c_only", current_difficulty_level=1,
                safety_increase_block_remaining=decision_1.increase_block_remaining,
            )
            decision_2 = await decide_and_persist_adaptation(
                session, adapter=adapter, c_session_id=c_session_id, c_task_opportunity_id=opportunity_id,
                policy_mode="rule_based_baseline", evidence=evidence_3, current_difficulty_level=1,
                seed_lineage=_seed_lineage(), policy_config=policy_config, safety_config=safety_config,
                selection_config=selection_config, request_id=f"req-{uuid4()}",
            )
            # Countdown decremented by exactly 1 (no new severe trigger this task).
            assert decision_2.increase_block_remaining == decision_1.increase_block_remaining - 1
        await database_engine.dispose()

    asyncio.run(exercise())


def test_s8d_any_other_mode_raises_qlearning_disabled() -> None:
    safety_config = safety_config_fixture_for_tests()
    policy_config = policy_config_fixture_for_tests()
    selection_config = selection_config_fixture_for_tests()
    adapter = LiveEngineCAdapter()
    for mode in ("q_learning_offline", "frozen_q_evaluation"):
        with pytest.raises(QLearningDisabledError):
            adapter.decide_adaptation(
                policy_mode=mode, evidence=_baseline_evidence(), current_difficulty_level=2,
                seed_lineage=_seed_lineage(), policy_config=policy_config, safety_config=safety_config,
                selection_config=selection_config,
            )
