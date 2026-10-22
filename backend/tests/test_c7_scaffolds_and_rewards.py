"""Component C Phase 7: the C0-C4 ladder and safe child-facing reward events.

Y0/Z7 -- ACCEPTANCE CRITERIA: v3.0 states NONE for Phase 7 (every other phase has them). The six
below are PROPOSED BY THIS BATCH, derived one-for-one from Phase 7's own hard constraints, and
ratified as this batch's own criteria -- never presented as v3.0's own text.
  1. Scaffold level is decided server-side only; the request DTO accepts no level/preference/hint.
  2. A missing/ungoverned scaffold content source fails closed (ConflictError shape), never a
     generic fallback.
  3. No C scaffold code path imports, reads, or mirrors B's hint machinery.
  4. C4 is reachable both by ordinary escalation and by a safety-forced path; time pressure
     removal is visible in what is served/persisted.
  5. Each of the six reward prohibitions is structurally impossible (verified) or covered by a
     provocation test.
  6. No reward code path writes learner state or touches any B-owned table/model.
"""

from __future__ import annotations

import asyncio
import subprocess
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.application.live_engine_c.adaptation_service import build_evidence_for_session
from app.application.live_engine_c.reward_service import decide_child_facing_reward
from app.application.live_engine_c.scaffold_service import decide_and_persist_scaffold_level
from app.application.live_engine_c.session_lifecycle import create_session
from app.application.live_engine_c.task_service import (
    PRODUCTION_GENERATION_CONFIG,
    PRODUCTION_SCAFFOLD_CONFIG,
    TaskService,
)
from app.domain.live_engine_c.types import RewardOutcomeContext, ScaffoldDecisionContext
from app.domain.runtime_bundle_c.types import (
    EvidenceWindowConfigurationArtifact,
    SafetyConfigurationArtifact,
    SelectionConfigurationArtifact,
)
from app.infrastructure.live_engine_c.adapter import LiveEngineCAdapter
from app.infrastructure.persistence_models import CScaffoldEventRecord, CTaskInstanceRecord, CTaskOpportunityRecord
from app.infrastructure.repositories import CGameplayEventRecordRepository, CScaffoldEventRecordRepository
from tests.test_c4_session_lifecycle import (
    all_usable_field_statuses,
    isolated_database,
    provenance,
    safety_config_fixture_for_tests,
    seed_learner,
    seed_runtime_bundle,
    selection_config_fixture_for_tests,
)
from tests.test_c5_task_serve_and_evaluate import (
    _create_real_instance_via_smoke_mode,
    generation_config_fixture_for_tests,
    seed_active_session,
)
from tests.test_c6b_policy_and_safety import evidence_window_config_fixture_for_tests


def alembic(*args: str) -> None:
    subprocess.run(["alembic", *args], check=True)


# =====================================================================================
# Z5-a -- SERVER DECIDES. The request DTO carries no level/preference/hint; a client-supplied
# level is REJECTED (422, extra_forbidden), not silently ignored.
# =====================================================================================


def test_z5a_submit_action_request_carries_no_scaffold_field() -> None:
    from app.api.routes.c_task import CSubmitActionRequest

    assert set(CSubmitActionRequest.model_fields.keys()) == {"action_payload"}


def test_z5a_client_supplied_scaffold_level_is_rejected_not_ignored() -> None:
    """R-5's own precedent: a rejected extra is provable, a silently-ignored one is not."""
    from fastapi.testclient import TestClient

    from app.domain.principal import AuthenticatedPrincipal
    from app.infrastructure.auth import get_authenticated_principal
    from app.main import app

    subject = f"c7-z5a-{uuid4()}"
    app.dependency_overrides[get_authenticated_principal] = lambda: AuthenticatedPrincipal(
        user_id=subject, email="verified@example.test"
    )
    client = TestClient(app)
    client.__enter__()
    try:
        response = client.post(
            f"/api/v1/c/sessions/{uuid4()}/tasks/{uuid4()}/actions",
            json={"action_payload": {}, "scaffold_level": "C4"},
            headers={"X-Request-ID": f"req-{uuid4()}", "Authorization": "Bearer x"},
        )
        assert response.status_code == 422, response.text
        body = response.json()
        assert body["error"]["code"] == "REQUEST_VALIDATION_FAILED"
        assert any(entry["type"] == "extra_forbidden" for entry in body["error"]["details"])
    finally:
        client.__exit__(None, None, None)
        app.dependency_overrides.clear()


# =====================================================================================
# Z5-c -- CSubmitActionResult carries the decided scaffold level, allow-list constructed.
# =====================================================================================


def test_z5c_submit_action_result_exact_key_set_includes_scaffold_level() -> None:
    from app.domain.c_task import CSubmitActionResult

    assert set(CSubmitActionResult.model_fields.keys()) == {
        "c_task_instance_id", "response_matched", "scaffold_level", "request_id",
    }


# =====================================================================================
# Z5-d -- C4 reachable BOTH ways: ordinary escalation (wired, real data) and safety-forced
# (proven directly against decide_scaffold_level, test-side construction, T4-d's own discipline).
# Time pressure removal asserted where it is actually visible: recovery.py's own frozen constant
# and the difficulty_vector marker it sets -- verified by direct read, not re-implemented.
# =====================================================================================


def test_z5d_ordinary_escalation_reaches_c4_wired_through_submit_action() -> None:
    """Four consecutive incorrect submissions on the SAME task instance escalate C0 -> C1 -> C2
    -> C3 -> C4, decided from the real persisted event stream each time -- never a caller-
    asserted count."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            _, c_session_id, instance_id, subject = await _create_real_instance_via_smoke_mode(session)
            instance = await session.get(CTaskInstanceRecord, instance_id)

            def wrong_value(declared_type: str):
                if "|" in declared_type:
                    options = declared_type.split("|")
                    return options[-1] if len(options) > 1 else options[0] + "_wrong"
                if declared_type in ("int", "number"):
                    return -999999
                if declared_type == "bool":
                    return True
                if declared_type.startswith("list["):
                    return []
                raise AssertionError(declared_type)

            payload = {key: wrong_value(t) for key, t in instance.valid_action_space.items()}
            if payload == dict(instance.correct_answer_payload):
                await database_engine.dispose()
                return

            levels: list[str] = []
            for _ in range(5):
                result = await TaskService().submit_action(
                    session, principal_user_id=subject, request_id=f"req-{uuid4()}",
                    c_session_id=c_session_id, c_task_instance_id=instance_id,
                    action_payload=payload, generation_config=PRODUCTION_GENERATION_CONFIG,
                    scaffold_config=PRODUCTION_SCAFFOLD_CONFIG,
                )
                assert result.response_matched is False
                levels.append(result.scaffold_level)

            assert levels == ["C1", "C2", "C3", "C4", "C4"]

            events = await CScaffoldEventRecordRepository(session).session.execute(
                __import__("sqlalchemy").select(CScaffoldEventRecord).where(
                    CScaffoldEventRecord.c_session_id == c_session_id
                )
            )
            rows = events.scalars().all()
            assert len(rows) == 5
            assert [r.scaffold_level for r in rows] == ["C1", "C2", "C3", "C4", "C4"]
        await database_engine.dispose()

    asyncio.run(exercise())


# =====================================================================================
# CONNECT Step 5 (Family 3, ESCALATIONS.md §2, CLOSED): attempt_number, made real. Placed in
# THIS file, not test_c5_task_serve_and_evaluate.py or test_c6a_summary_derivation.py, because
# this is the file that already has a working repeated-wrong-answer-on-one-instance fixture
# (test_z5d_ordinary_escalation_reaches_c4_wired_through_submit_action, immediately above) --
# picked by which fixture already exists and works, not by which file's name best matches the
# feature under test (supervisor ruling: "pick by fixture, not taxonomy").
# =====================================================================================


def test_z6_attempt_number_increments_across_repeated_wrong_answers_on_one_instance() -> None:
    """Positive control for CONNECT Step 5. Three wrong-answer submissions on the SAME task
    instance -- same fixture and wrong-value construction as
    test_z5d_ordinary_escalation_reaches_c4_wired_through_submit_action above -- persist
    attempt_number 1, 2, 3 on their answer_submitted events, in event_index order. Additionally
    (supervisor's own addition to this control): for each submission, its answer_submitted and
    answer_evaluated events carry the SAME attempt_number as each other, and consecutive
    event_index values -- proving the shared-value derivation stayed synchronized with the
    event_index derivation the c_gameplay_events triggers themselves own, not just that the
    attempt_number sequence looks right in isolation."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            _, c_session_id, instance_id, subject = await _create_real_instance_via_smoke_mode(session)
            instance = await session.get(CTaskInstanceRecord, instance_id)

            def wrong_value(declared_type: str):
                if "|" in declared_type:
                    options = declared_type.split("|")
                    return options[-1] if len(options) > 1 else options[0] + "_wrong"
                if declared_type in ("int", "number"):
                    return -999999
                if declared_type == "bool":
                    return True
                if declared_type.startswith("list["):
                    return []
                raise AssertionError(declared_type)

            payload = {key: wrong_value(t) for key, t in instance.valid_action_space.items()}
            if payload == dict(instance.correct_answer_payload):
                await database_engine.dispose()
                return

            for _ in range(3):
                result = await TaskService().submit_action(
                    session, principal_user_id=subject, request_id=f"req-{uuid4()}",
                    c_session_id=c_session_id, c_task_instance_id=instance_id,
                    action_payload=payload, generation_config=PRODUCTION_GENERATION_CONFIG,
                    scaffold_config=PRODUCTION_SCAFFOLD_CONFIG,
                )
                assert result.response_matched is False

            events = await CGameplayEventRecordRepository(session).list_ordered_for_instance(instance_id)
            submitted = [e for e in events if e.event_type == "answer_submitted"]
            evaluated = [e for e in events if e.event_type == "answer_evaluated"]
            assert [e.attempt_number for e in submitted] == [1, 2, 3]

            # Each submission's own pair shares one attempt_number and has consecutive event_index
            # -- the shared-derivation proof, not just the sequence-looks-right proof above.
            assert len(evaluated) == 3
            for submitted_event, evaluated_event in zip(submitted, evaluated):
                assert submitted_event.attempt_number == evaluated_event.attempt_number
                assert evaluated_event.event_index == submitted_event.event_index + 1
        await database_engine.dispose()

    asyncio.run(exercise())


def test_z5d_safety_forced_c4_reachable_directly() -> None:
    """The safety-forced path, proven directly against decide_scaffold_level (test-side
    construction, T4-d's own discipline) -- unconditionally C4 regardless of the escalation
    count, per SPEC §15 "safety may force C4"."""
    adapter = LiveEngineCAdapter()
    context = ScaffoldDecisionContext(consecutive_incorrect_current_task=0, safety_forces_recovery=True)
    level = adapter.decide_scaffold_level(context, PRODUCTION_SCAFFOLD_CONFIG)
    assert level == "C4"


def test_z5d_recovery_removes_time_pressure_verified_from_source() -> None:
    """recovery.py's own frozen constants (SPEC §10/§15, hardcoded, never reimplemented here --
    Z6-d): RECOVERY_DIFFICULTY_LEVEL == 1, RECOVERY_SCAFFOLD_STATE == "C4", and the
    difficulty_vector["time_pressure"] = "removed" marker it sets, verified by reading the
    package source directly."""
    import inspect

    from component_c_generator.scaffolds import recovery as pkg_recovery

    assert pkg_recovery.RECOVERY_DIFFICULTY_LEVEL == 1
    assert pkg_recovery.RECOVERY_SCAFFOLD_STATE == "C4"
    source = inspect.getsource(pkg_recovery.build_recovery_task)
    assert 'recovery_difficulty_vector["time_pressure"] = "removed"' in source


# =====================================================================================
# Z6 -- recovery wiring: is_recovery_context DERIVED from real persisted data
# (recovery_parent_instance_id), never hardcoded False.
# =====================================================================================


async def _seed_session_and_instance(
    session, *, recovery_parent_instance_id, c_session_id: UUID | None = None, task_index: int = 1
) -> tuple[UUID, UUID]:
    from datetime import UTC, datetime as dt

    from app.infrastructure.persistence_models import CTaskOpportunitySummaryRecord

    if c_session_id is None:
        student_id = await seed_learner(session)
        bundle_id = await seed_runtime_bundle(session)
        adapter = LiveEngineCAdapter()
        record = await create_session(
            session, adapter, student_id=student_id, c_runtime_bundle_record_id=bundle_id,
            grade=2, session_mode="c_only", catalogue_version="test-catalogue-1",
            catalogue_checksum="a" * 64, global_seed=42,
            selection_config=selection_config_fixture_for_tests(),
            selection_config_field_statuses=all_usable_field_statuses(SelectionConfigurationArtifact.FIELD_NAMES),
            safety_config_field_statuses=all_usable_field_statuses(SafetyConfigurationArtifact.FIELD_NAMES),
            evidence_window_config_field_statuses=all_usable_field_statuses(
                EvidenceWindowConfigurationArtifact.FIELD_NAMES
            ),
            generation_parameter_source_status="TEST_FIXTURE_ONLY",
            policy_parameter_source_status="TEST_FIXTURE_ONLY",
            scaffold_parameter_source_status="TEST_FIXTURE_ONLY",
            aggregation_parameter_source_status="TEST_FIXTURE_ONLY",
            q_policy_parameter_source_status="TEST_FIXTURE_ONLY",   # LIVE-01: new gated family
            smoke_mode=True,
            request_id=f"req-{uuid4()}",
        )
        c_session_id = record.c_session_id
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
            recovery_parent_instance_id=recovery_parent_instance_id, technical_status="OK",
            seed_lineage_global_seed=1, seed_lineage_path=[], seed_lineage_seed=1,
            **provenance("c_task_instance", instance_id),
        )
    )
    await session.flush()
    # build_policy_evidence requires a non-empty history (the just-finished task) -- one minimal
    # completed summary for THIS instance.
    summary_id = uuid4()
    session.add(
        CTaskOpportunitySummaryRecord(
            c_task_opportunity_summary_id=summary_id, c_session_id=c_session_id,
            game_task_instance_id=instance_id, task_index=task_index,
            task_offered=True, task_started=True, task_completed=True, task_skipped=False,
            task_quit=False, technical_issue=False, correct_task=True, total_attempts=1, retry_count=0,
            scaffold_requested=False, scaffold_count=0, highest_scaffold_level=None, c_answer_changes=0,
            task_latency_sec=1.5, inactive_time_sec=0.0, inactivity_periods=0, quit_after_error=False,
            terminal_reason="completed_correct", first_attempt_correct=True, final_attempt_correct=True,
            consecutive_error_max_within_task=0,
            **provenance("c_task_opportunity_summary", summary_id),
        )
    )
    await session.flush()
    return c_session_id, instance_id


def test_z6a_is_recovery_context_derives_false_when_no_parent() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            c_session_id, instance_id = await _seed_session_and_instance(
                session, recovery_parent_instance_id=None
            )
            adapter = LiveEngineCAdapter()
            evidence = await build_evidence_for_session(
                session, adapter=adapter, c_session_id=c_session_id, c_task_instance_id=instance_id,
                student_id="STU-0001", intervention_session_id="STU-0001-I-001",
                stu_session_id="STU-0001-C-001", session_mode="c_only", session_phase="c_only",
                current_difficulty_level=1, prior_session_end_state=None,
                evidence_window_config=evidence_window_config_fixture_for_tests(),
            )
        await database_engine.dispose()
        return evidence

    evidence = asyncio.run(exercise())
    assert evidence.is_recovery_context is False


def test_z6a_is_recovery_context_derives_true_from_real_recovery_parent_instance_id() -> None:
    """THE MECHANISM, proven real and non-hardcoded (Z6-b, first half): a genuine
    recovery_parent_instance_id on the persisted row makes is_recovery_context True, derived,
    never a caller-asserted boolean."""
    alembic("upgrade", "head")

    async def exercise():
        database_engine, factory = isolated_database()
        async with factory() as session:
            c_session_id, instance_id = await _seed_session_and_instance(
                session, recovery_parent_instance_id=None
            )
            # A second instance, chained to the first as its recovery task, in the SAME session.
            _, recovery_instance_id = await _seed_session_and_instance(
                session, recovery_parent_instance_id=instance_id, c_session_id=c_session_id, task_index=2,
            )
            adapter = LiveEngineCAdapter()
            evidence = await build_evidence_for_session(
                session, adapter=adapter, c_session_id=c_session_id, c_task_instance_id=recovery_instance_id,
                student_id="STU-0001", intervention_session_id="STU-0001-I-001",
                stu_session_id="STU-0001-C-001", session_mode="c_only", session_phase="c_only",
                current_difficulty_level=1, prior_session_end_state=None,
                evidence_window_config=evidence_window_config_fixture_for_tests(),
            )
        await database_engine.dispose()
        return evidence

    evidence = asyncio.run(exercise())
    assert evidence.is_recovery_context is True


def test_z6b_recovery_task_creation_itself_is_smoke_gated() -> None:
    """THE PRODUCTION GUARANTEE, proven it CANNOT close (Z6-b, second half): build_recovery_task
    builds THROUGH generation.build_task_instance (recovery.py:153-163), which the generation
    smoke gate refuses outside smoke_mode=True -- verified structurally, by source inspection,
    not merely asserted."""
    import inspect

    from component_c_generator.scaffolds import recovery as pkg_recovery

    source = inspect.getsource(pkg_recovery.build_recovery_task)
    assert "build_task_instance(" in source
    # And the generation smoke gate itself is real and unconditional for TEST_FIXTURE_ONLY.
    from app.domain.live_engine_c.generation_mode_guard import (
        GenerationConfigNotPermittedError,
        assert_generation_config_permitted,
    )
    from app.domain.live_engine_c.types import GenerationConfig

    always_unsigned = GenerationConfig(
        config_version="v", parameter_source_status="TEST_FIXTURE_ONLY", per_template={}
    )
    with pytest.raises(GenerationConfigNotPermittedError):
        assert_generation_config_permitted(always_unsigned, smoke_mode=False)


# =====================================================================================
# Z4 -- REWARDS. Ephemeral (verified, not assumed -- see reward_service.py's own module
# docstring for the C->3/telemetry search result). Computed and returned, never persisted.
# =====================================================================================


def test_z4_correct_completion_reward_reachable() -> None:
    adapter = LiveEngineCAdapter()
    context = RewardOutcomeContext(
        task_completed_correctly=True, is_recovery_task=False,
        retried_after_incorrect_then_continued=False,
        continued_after_safety_event_without_quitting=False,
    )
    reward = decide_child_facing_reward(adapter, context)
    assert reward is not None
    assert reward.reward_reason == "correct_completion"


def test_z4_recovery_reward_reachable() -> None:
    adapter = LiveEngineCAdapter()
    context = RewardOutcomeContext(
        task_completed_correctly=False, is_recovery_task=True,
        retried_after_incorrect_then_continued=False,
        continued_after_safety_event_without_quitting=False,
    )
    reward = decide_child_facing_reward(adapter, context)
    assert reward is not None
    assert reward.reward_reason == "recovery"


def test_z4_persistence_reward_reachable() -> None:
    adapter = LiveEngineCAdapter()
    context = RewardOutcomeContext(
        task_completed_correctly=False, is_recovery_task=False,
        retried_after_incorrect_then_continued=True,
        continued_after_safety_event_without_quitting=False,
    )
    reward = decide_child_facing_reward(adapter, context)
    assert reward is not None
    assert reward.reward_reason == "persistence"


def test_z4_safe_continuation_reward_reachable() -> None:
    adapter = LiveEngineCAdapter()
    context = RewardOutcomeContext(
        task_completed_correctly=False, is_recovery_task=False,
        retried_after_incorrect_then_continued=False,
        continued_after_safety_event_without_quitting=True,
    )
    reward = decide_child_facing_reward(adapter, context)
    assert reward is not None
    assert reward.reward_reason == "safe_continuation"


def test_z4_no_reward_is_silence_never_a_negative_signal() -> None:
    adapter = LiveEngineCAdapter()
    context = RewardOutcomeContext(
        task_completed_correctly=False, is_recovery_task=False,
        retried_after_incorrect_then_continued=False,
        continued_after_safety_event_without_quitting=False,
    )
    reward = decide_child_facing_reward(adapter, context)
    assert reward is None


def test_z4b_no_reward_table_exists_ten_table_guard_makes_it_a_design() -> None:
    """Z4-b: the EXPECTED_TABLES/AUTHORIZED_TABLES guard in test_be2_architecture_guards.py
    asserts the C table set by EXACT equality -- no c_reward_events (or equivalent) is among
    them, and that guard would fail the moment one was added without updating the record. This
    test names the absence directly, rather than relying on the reader to infer it."""
    from app.infrastructure.persistence_models import AUTHORIZED_TABLES

    reward_tables = {name for name in AUTHORIZED_TABLES if "reward" in name}
    assert reward_tables == set()
