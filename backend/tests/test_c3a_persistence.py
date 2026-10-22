"""Component C Phase 3a acceptance tests (Phase 3a work order, ACCEPTANCE A3-A6): a real-database
round-trip per table, provocation tests for every domain CHECK constraint added this batch, the
R-E-named UNIQUE, A5's mastery_context_mode rejection, the allow-list mechanism firing against the
real ten tables (not synthetic metadata, A4), and a migration-content guard (A3).

Table-shape only: no cross-row invariant is exercised or asserted here (Phase 3b's job, per the
Phase 3a work order's own scope split -- see persistence_models.py's Phase 3a block header).
"""

from __future__ import annotations

import asyncio
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.infrastructure.database import async_database_url
from app.infrastructure.persistence_models import (
    Base,
    CGameplayEventRecord,
    CLearnerLocalStateRecord,
    CPolicyDecisionRecord,
    CRuntimeBundleRecord,
    CSafetyEventRecord,
    CScaffoldEventRecord,
    CSessionAggregateResultRecord,
    CSessionRecord,
    CTaskInstanceRecord,
    CTaskOpportunityRecord,
    CTaskOpportunitySummaryRecord,
    Learner,
)
from tests.test_be2_architecture_guards import AUTHORIZED_C_COLUMN_EXCEPTIONS, PROHIBITED_COLUMN_TERMS

MIGRATION_PATH = Path("migrations/versions/20260816_0002_c3a_ten_tables.py")
C3A_TABLES = {
    "c_sessions", "c_task_opportunities", "c_task_instances", "c_gameplay_events",
    "c_task_opportunity_summaries", "c_session_aggregate_results", "c_learner_local_state",
    "c_policy_decisions", "c_safety_events", "c_scaffold_events",
}


def alembic(*args: str) -> None:
    subprocess.run(["alembic", *args], check=True)


def isolated_database():
    database_engine = create_async_engine(
        async_database_url(get_settings().database_url),
        poolclass=NullPool,
    )
    factory = async_sessionmaker(database_engine, expire_on_commit=False, class_=AsyncSession)
    return database_engine, factory


def provenance(resource_type: str, resource_id: UUID) -> dict[str, object]:
    return {
        "system_actor": "c3a-isolated-test",
        "request_id": f"test-{uuid4()}",
        "operation_or_event_type": "test.persistence",
        "reason_code": "ISOLATED_SYNTHETIC_TEST",
        "resource_type": resource_type,
        "resource_id": resource_id,
        "source_class": "TEST",
        "source_system": "c3a-isolated-test-suite",
        "environment": "test",
        "schema_revision": "20260816_0002",
    }


async def seed_learner(session: AsyncSession) -> UUID:
    learner_id = uuid4()
    session.add(
        Learner(
            learner_id=learner_id,
            grade=2,
            status="test_only",
            **provenance("b_learner", learner_id),
        )
    )
    await session.flush()
    return learner_id


async def seed_runtime_bundle(session: AsyncSession) -> UUID:
    bundle_id = uuid4()
    session.add(
        CRuntimeBundleRecord(
            c_runtime_bundle_record_id=bundle_id,
            bundle_version=f"test-{bundle_id}",
            manifest_checksum=bundle_id.hex * 2,
            publication_state="DRAFT",
            approval_status="UNRESOLVED",
            immutable_after_publication=False,
            **provenance("c_runtime_bundle_record", bundle_id),
        )
    )
    await session.flush()
    return bundle_id


def session_kwargs(*, student_id: UUID, bundle_id: UUID, **overrides: object) -> dict[str, object]:
    session_id = uuid4()
    values: dict[str, object] = {
        "c_session_id": session_id,
        "student_id": student_id,
        "intervention_session_id": f"intervention-{session_id}",
        "session_mode": "c_only",
        "session_phase": "c_only",
        "mastery_context_mode": "unavailable_fallback",
        "catalogue_version": "test-catalogue-1",
        "catalogue_checksum": "a" * 64,
        "c_runtime_bundle_record_id": bundle_id,
        "grade": 2,
        "state": "active",
        "global_seed": 42,
        "started_at_utc": datetime.now(UTC),
        "completed_at_utc": None,
        "row_version": 0,
        **provenance("c_session", session_id),
    }
    values.update(overrides)
    return values


async def seed_session(session: AsyncSession, *, student_id: UUID, bundle_id: UUID) -> UUID:
    kwargs = session_kwargs(student_id=student_id, bundle_id=bundle_id)
    session.add(CSessionRecord(**kwargs))
    await session.flush()
    return kwargs["c_session_id"]


def opportunity_kwargs(*, session_id: UUID, **overrides: object) -> dict[str, object]:
    opportunity_id = uuid4()
    values: dict[str, object] = {
        "c_task_opportunity_id": opportunity_id,
        "c_session_id": session_id,
        "task_index": 0,
        "selected_skill_id": "skill.count_to_10",
        "selected_template_id": "template.count_and_collect.v1",
        "initial_difficulty_level": 2,
        "mastery_context_mode": "unavailable_fallback",
        "mastery_selected_skill": None,
        "session_phase": "c_only",
        "terminal_reason": None,
        "task_offered_at_utc": datetime.now(UTC),
        **provenance("c_task_opportunity", opportunity_id),
    }
    values.update(overrides)
    return values


async def seed_opportunity(session: AsyncSession, *, session_id: UUID) -> UUID:
    kwargs = opportunity_kwargs(session_id=session_id)
    session.add(CTaskOpportunityRecord(**kwargs))
    await session.flush()
    return kwargs["c_task_opportunity_id"]


def instance_kwargs(*, opportunity_id: UUID, **overrides: object) -> dict[str, object]:
    instance_id = uuid4()
    values: dict[str, object] = {
        "c_task_instance_id": instance_id,
        "c_task_opportunity_id": opportunity_id,
        "game_family_id": "count_and_collect",
        "game_task_template_id": "template.count_and_collect.v1",
        "template_version": "1.0.0",
        "catalogue_version": "test-catalogue-1",
        "generator_version": "0.1.0+c1.09267ab",
        "task_index": 0,
        "skill_id": "skill.count_to_10",
        "curriculum_node_id": "node.counting.grade2",
        "grade_scope": 2,
        "difficulty_level": 2,
        "difficulty_vector": {"magnitude": 2, "support": 1},
        "functional_role": "primary",
        "representation_mode": "concrete",
        "prompt_payload": {"text": "Count the apples."},
        "interactive_assets": {"assets": []},
        "correct_answer_payload": {"value": 4},
        "correctness_function_id": "exact_match_v1",
        "valid_action_space": {"actions": ["tap"]},
        "completion_condition": "answer_submitted",
        "failure_condition": "attempt_cap_exhausted",
        "scaffold_state": "C0",
        "recovery_parent_instance_id": None,
        "technical_status": "OK",
        "seed_lineage_global_seed": 42,
        "seed_lineage_path": ["global", "session", "task"],
        "seed_lineage_seed": 4242,
        **provenance("c_task_instance", instance_id),
    }
    values.update(overrides)
    return values


async def seed_instance(session: AsyncSession, *, opportunity_id: UUID) -> UUID:
    kwargs = instance_kwargs(opportunity_id=opportunity_id)
    session.add(CTaskInstanceRecord(**kwargs))
    await session.flush()
    return kwargs["c_task_instance_id"]


async def seed_up_to_opportunity(session: AsyncSession) -> dict[str, UUID]:
    """No instance -- c_task_instances has UNIQUE(c_task_opportunity_id) (B's 1:1 minimal-FK
    style), so any test that inserts its OWN instance row must start from an opportunity that
    does not already have one. Callers that only need to reference an existing instance's id
    (gameplay_events, summaries, policy_decisions, safety_events, scaffold_events,
    aggregate_results) should use seed_full_graph instead."""
    student_id = await seed_learner(session)
    bundle_id = await seed_runtime_bundle(session)
    session_id = await seed_session(session, student_id=student_id, bundle_id=bundle_id)
    opportunity_id = await seed_opportunity(session, session_id=session_id)
    return {
        "student_id": student_id,
        "bundle_id": bundle_id,
        "session_id": session_id,
        "opportunity_id": opportunity_id,
    }


async def seed_full_graph(session: AsyncSession) -> dict[str, UUID]:
    graph = await seed_up_to_opportunity(session)
    graph["instance_id"] = await seed_instance(session, opportunity_id=graph["opportunity_id"])
    return graph


# =====================================================================================
# A7 -- one round-trip insert/read test per table.
# =====================================================================================


def test_c3a_c_sessions_round_trip() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            student_id = await seed_learner(session)
            bundle_id = await seed_runtime_bundle(session)
            kwargs = session_kwargs(student_id=student_id, bundle_id=bundle_id)
            row = CSessionRecord(**kwargs)
            session.add(row)
            await session.commit()
        async with factory() as session:
            fetched = await session.get(CSessionRecord, kwargs["c_session_id"])
            assert fetched is not None
            assert fetched.student_id == student_id
            assert fetched.session_mode == "c_only"
            assert fetched.mastery_context_mode == "unavailable_fallback"
            assert fetched.grade == 2
        await database_engine.dispose()

    asyncio.run(exercise())


def test_c3a_c_task_opportunities_round_trip() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            graph = await seed_full_graph(session)
            kwargs = opportunity_kwargs(session_id=graph["session_id"])
            session.add(CTaskOpportunityRecord(**kwargs))
            await session.commit()
        async with factory() as session:
            fetched = await session.get(CTaskOpportunityRecord, kwargs["c_task_opportunity_id"])
            assert fetched is not None
            assert fetched.c_session_id == graph["session_id"]
            assert fetched.selected_skill_id == "skill.count_to_10"
            assert fetched.mastery_selected_skill is None
        await database_engine.dispose()

    asyncio.run(exercise())


def test_c3a_c_task_instances_round_trip() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            graph = await seed_up_to_opportunity(session)
            kwargs = instance_kwargs(opportunity_id=graph["opportunity_id"])
            session.add(CTaskInstanceRecord(**kwargs))
            await session.commit()
        async with factory() as session:
            fetched = await session.get(CTaskInstanceRecord, kwargs["c_task_instance_id"])
            assert fetched is not None
            assert fetched.c_task_opportunity_id == graph["opportunity_id"]
            assert fetched.correct_answer_payload == {"value": 4}
            assert fetched.correctness_function_id == "exact_match_v1"
            assert fetched.difficulty_vector == {"magnitude": 2, "support": 1}
        await database_engine.dispose()

    asyncio.run(exercise())


def test_c3a_c_gameplay_events_round_trip() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            graph = await seed_full_graph(session)
            event_id = uuid4()
            row = CGameplayEventRecord(
                c_gameplay_event_id=event_id,
                c_session_id=graph["session_id"],
                game_task_instance_id=graph["instance_id"],
                task_index=0,
                event_type="game_task_offered",
                event_index=1,
                attempt_number=None,
                event_timestamp_relative_ms=0,
                action_payload=None,
                evaluation_payload=None,
                scaffold_code=None,
                technical_flag=False,
                terminal_reason=None,
                seed_lineage_global_seed=42,
                seed_lineage_path=["global", "session", "task"],
                seed_lineage_seed=4242,
                generator_version="0.1.0+c1.09267ab",
                config_checksum="b" * 64,
                **provenance("c_gameplay_event", event_id),
            )
            session.add(row)
            await session.commit()
        async with factory() as session:
            fetched = await session.get(CGameplayEventRecord, event_id)
            assert fetched is not None
            assert fetched.event_type == "game_task_offered"
            assert fetched.event_timestamp_relative_ms == 0
        await database_engine.dispose()

    asyncio.run(exercise())


def test_c3a_c_task_opportunity_summaries_round_trip() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            graph = await seed_full_graph(session)
            summary_id = uuid4()
            row = CTaskOpportunitySummaryRecord(
                c_task_opportunity_summary_id=summary_id,
                c_session_id=graph["session_id"],
                game_task_instance_id=graph["instance_id"],
                task_index=0,
                task_offered=True,
                task_started=True,
                task_completed=True,
                task_skipped=False,
                task_quit=False,
                technical_issue=False,
                correct_task=True,
                total_attempts=1,
                retry_count=0,
                scaffold_requested=False,
                scaffold_count=0,
                highest_scaffold_level=None,
                c_answer_changes=0,
                task_latency_sec=3.5,
                inactive_time_sec=0.0,
                inactivity_periods=0,
                quit_after_error=False,
                terminal_reason="completed_correct",
                first_attempt_correct=True,
                final_attempt_correct=True,
                consecutive_error_max_within_task=0,
                **provenance("c_task_opportunity_summary", summary_id),
            )
            session.add(row)
            await session.commit()
        async with factory() as session:
            fetched = await session.get(CTaskOpportunitySummaryRecord, summary_id)
            assert fetched is not None
            assert fetched.correct_task is True
            assert fetched.terminal_reason == "completed_correct"
        await database_engine.dispose()

    asyncio.run(exercise())


def test_c3a_c_session_aggregate_results_round_trip() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            graph = await seed_full_graph(session)
            result_id = uuid4()
            row = CSessionAggregateResultRecord(
                c_session_aggregate_result_id=result_id,
                c_session_id=graph["session_id"],
                task_opportunity_count=1,
                completed_task_count=1,
                correct_task_count=1,
                total_attempt_count=1,
                accuracy_rate=1.0,
                avg_attempts_per_task=1.0,
                task_completion_rate=1.0,
                inactivity_periods=0,
                inactive_time_sec=0.0,
                inactive_time_available=True,
                session_duration_sec=60.0,
                time_in_target_band_sec=30.0,
                consecutive_error_max=0,
                difficulty_floor_hits=0,
                quit_after_error=False,
                safety_override_count=0,
                c_mean_game_task_latency_sec=3.5,
                c_median_game_task_latency_sec=3.5,
                current_difficulty_level=2,
                difficulty_trend="stable",
                session_technical_issue_flag=False,
                engagement_score=None,
                engagement_completion_component=None,
                engagement_activity_component=None,
                engagement_target_band_component=None,
                engagement_accuracy_component=None,
                frustration_index=None,
                frustration_error_run_component=None,
                frustration_excess_attempt_component=None,
                frustration_inactivity_burden_component=None,
                frustration_floor_hit_component=None,
                frustration_quit_after_error_component=None,
                frustration_safety_override_component=None,
                telemetry_quality_status="complete",
                learner_state="engaged",
                state_reason="high_engagement_low_friction",
                **provenance("c_session_aggregate_result", result_id),
            )
            session.add(row)
            await session.commit()
        async with factory() as session:
            fetched = await session.get(CSessionAggregateResultRecord, result_id)
            assert fetched is not None
            assert fetched.correct_task_count == 1
            assert fetched.difficulty_trend == "stable"
            assert fetched.learner_state == "engaged"
        await database_engine.dispose()

    asyncio.run(exercise())


def test_c3a_c_learner_local_state_round_trip() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            student_id = await seed_learner(session)
            state_id = uuid4()
            row = CLearnerLocalStateRecord(
                c_learner_local_state_id=state_id,
                student_id=student_id,
                eligible_combined_handoffs_completed=0,
                sessions_since_last_practice={"skill.count_to_10": 0},
                prior_session_end_state="engaged",
                **provenance("c_learner_local_state", state_id),
            )
            session.add(row)
            await session.commit()
        async with factory() as session:
            fetched = await session.get(CLearnerLocalStateRecord, state_id)
            assert fetched is not None
            assert fetched.student_id == student_id
            assert fetched.sessions_since_last_practice == {"skill.count_to_10": 0}
        await database_engine.dispose()

    asyncio.run(exercise())


def test_c3a_c_policy_decisions_round_trip() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            graph = await seed_full_graph(session)
            decision_id = uuid4()
            row = CPolicyDecisionRecord(
                c_policy_decision_id=decision_id,
                c_session_id=graph["session_id"],
                c_task_opportunity_id=graph["opportunity_id"],
                policy_mode="rule_based_baseline",
                policy_version="1.0.0",
                rl_state=None,
                selected_action="hold",
                applied_action="hold",
                action_overridden=False,
                safety_reason=None,
                difficulty_before=2,
                difficulty_after=2,
                rolling_strain_bucket="low",
                session_start_state_bucket=None,
                increase_block_remaining=0,
                internal_reward=None,
                seed_lineage_global_seed=42,
                seed_lineage_path=["global", "session", "task"],
                seed_lineage_seed=4242,
                evidence_snapshot={"recent_correctness_rate": 1.0},
                # Batch 3 (F-2): mirrors c_scaffold_events' own sibling column round-trip below
                # exactly -- Boolean, NOT NULL, no invented vocabulary.
                safety_forces_recovery=True,
                **provenance("c_policy_decision", decision_id),
            )
            session.add(row)
            await session.commit()
        async with factory() as session:
            fetched = await session.get(CPolicyDecisionRecord, decision_id)
            assert fetched is not None
            assert fetched.selected_action == "hold"
            assert fetched.evidence_snapshot == {"recent_correctness_rate": 1.0}
            assert fetched.safety_forces_recovery is True
        await database_engine.dispose()

    asyncio.run(exercise())


def test_c3a_c_safety_events_round_trip() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            graph = await seed_full_graph(session)
            event_id = uuid4()
            row = CSafetyEventRecord(
                c_safety_event_id=event_id,
                c_session_id=graph["session_id"],
                c_policy_decision_id=None,
                trigger_reason="consecutive_incorrect_threshold",
                action_taken="force_difficulty_decrease",
                difficulty_before=2,
                difficulty_after=1,
                **provenance("c_safety_event", event_id),
            )
            session.add(row)
            await session.commit()
        async with factory() as session:
            fetched = await session.get(CSafetyEventRecord, event_id)
            assert fetched is not None
            assert fetched.trigger_reason == "consecutive_incorrect_threshold"
            assert fetched.difficulty_after == 1
        await database_engine.dispose()

    asyncio.run(exercise())


def test_c3a_c_scaffold_events_round_trip() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            graph = await seed_full_graph(session)
            event_id = uuid4()
            row = CScaffoldEventRecord(
                c_scaffold_event_id=event_id,
                c_session_id=graph["session_id"],
                c_task_opportunity_id=graph["opportunity_id"],
                event_type="requested",
                scaffold_level="C1",
                consecutive_incorrect_current_task=2,
                safety_forces_recovery=False,
                **provenance("c_scaffold_event", event_id),
            )
            session.add(row)
            await session.commit()
        async with factory() as session:
            fetched = await session.get(CScaffoldEventRecord, event_id)
            assert fetched is not None
            assert fetched.scaffold_level == "C1"
            assert fetched.consecutive_incorrect_current_task == 2
        await database_engine.dispose()

    asyncio.run(exercise())


# =====================================================================================
# A5/A6 -- CHECK constraint provocation tests. Each case overrides exactly one field of an
# otherwise-valid row with a value outside its CHECK's domain and asserts IntegrityError. A5
# (mastery_context_mode on c_sessions) is included as one case among these, not special-cased.
# =====================================================================================

SESSION_CHECK_CASES = [
    ("session_mode", "not_a_real_mode"),
    ("session_phase", "not_a_real_phase"),
    ("mastery_context_mode", "not_a_real_mastery_mode"),  # A5
    ("grade", 5),
]

OPPORTUNITY_CHECK_CASES = [
    ("session_phase", "not_a_real_phase"),
    ("mastery_context_mode", "not_a_real_mastery_mode"),
]

INSTANCE_CHECK_CASES = [
    ("grade_scope", 5),
    ("scaffold_state", "C9"),
    ("technical_status", "MAYBE"),
]

GAMEPLAY_EVENT_CHECK_CASES = [
    ("event_type", "not_a_real_event_type"),
    ("event_timestamp_relative_ms", -1),
    ("scaffold_code", "C9"),
    ("terminal_reason", "not_a_real_terminal_reason"),
]

# c_gameplay_events' timestamp CHECK is named after its purpose (R-E), not its column -- every
# other case below follows the ck_{table}_{field} convention.
GAMEPLAY_EVENT_CONSTRAINT_NAMES = {
    "event_type": "ck_c_gameplay_events_event_type",
    "event_timestamp_relative_ms": "ck_c_gameplay_events_timestamp_non_negative",
    "scaffold_code": "ck_c_gameplay_events_scaffold_code",
    "terminal_reason": "ck_c_gameplay_events_terminal_reason",
}

SUMMARY_CHECK_CASES = [
    ("terminal_reason", "not_a_real_terminal_reason"),
    ("highest_scaffold_level", "C9"),
]

AGGREGATE_CHECK_CASES = [
    ("difficulty_trend", "sideways"),
    ("telemetry_quality_status", "not_a_real_status"),
    ("learner_state", "not_a_real_state"),
    ("state_reason", "not_a_real_reason"),
]

LEARNER_LOCAL_STATE_CHECK_CASES = [
    ("prior_session_end_state", "not_a_real_state"),
]

POLICY_DECISION_CHECK_CASES = [
    ("policy_mode", "not_a_real_mode"),
    ("selected_action", "not_a_real_action"),
    ("applied_action", "not_a_real_action"),
    ("rolling_strain_bucket", "extreme"),
    ("session_start_state_bucket", "not_a_real_state"),
]

SCAFFOLD_EVENT_CHECK_CASES = [
    ("scaffold_level", "C9"),
]


@pytest.mark.parametrize("field,invalid_value", SESSION_CHECK_CASES)
def test_c3a_c_sessions_check_constraints_reject(field: str, invalid_value: object) -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            student_id = await seed_learner(session)
            bundle_id = await seed_runtime_bundle(session)
            kwargs = session_kwargs(student_id=student_id, bundle_id=bundle_id, **{field: invalid_value})
            session.add(CSessionRecord(**kwargs))
            with pytest.raises(IntegrityError) as excinfo:
                await session.commit()
            assert f"ck_c_sessions_{field}" in str(excinfo.value)
            await session.rollback()
        await database_engine.dispose()

    asyncio.run(exercise())


@pytest.mark.parametrize("field,invalid_value", OPPORTUNITY_CHECK_CASES)
def test_c3a_c_task_opportunities_check_constraints_reject(field: str, invalid_value: object) -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            graph = await seed_full_graph(session)
            kwargs = opportunity_kwargs(session_id=graph["session_id"], **{field: invalid_value})
            session.add(CTaskOpportunityRecord(**kwargs))
            with pytest.raises(IntegrityError) as excinfo:
                await session.commit()
            assert f"ck_c_task_opportunities_{field}" in str(excinfo.value)
            await session.rollback()
        await database_engine.dispose()

    asyncio.run(exercise())


@pytest.mark.parametrize("field,invalid_value", INSTANCE_CHECK_CASES)
def test_c3a_c_task_instances_check_constraints_reject(field: str, invalid_value: object) -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            graph = await seed_up_to_opportunity(session)
            kwargs = instance_kwargs(opportunity_id=graph["opportunity_id"], **{field: invalid_value})
            session.add(CTaskInstanceRecord(**kwargs))
            with pytest.raises(IntegrityError) as excinfo:
                await session.commit()
            assert f"ck_c_task_instances_{field}" in str(excinfo.value)
            await session.rollback()
        await database_engine.dispose()

    asyncio.run(exercise())


@pytest.mark.parametrize("field,invalid_value", GAMEPLAY_EVENT_CHECK_CASES)
def test_c3a_c_gameplay_events_check_constraints_reject(field: str, invalid_value: object) -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            graph = await seed_full_graph(session)
            event_id = uuid4()
            values: dict[str, object] = {
                "c_gameplay_event_id": event_id,
                "c_session_id": graph["session_id"],
                "game_task_instance_id": graph["instance_id"],
                "task_index": 0,
                "event_type": "game_task_offered",
                "event_index": 1,
                "attempt_number": None,
                "event_timestamp_relative_ms": 0,
                "action_payload": None,
                "evaluation_payload": None,
                "scaffold_code": None,
                "technical_flag": False,
                "terminal_reason": None,
                "seed_lineage_global_seed": 42,
                "seed_lineage_path": ["global", "session", "task"],
                "seed_lineage_seed": 4242,
                "generator_version": "0.1.0+c1.09267ab",
                "config_checksum": "b" * 64,
                **provenance("c_gameplay_event", event_id),
            }
            values[field] = invalid_value
            session.add(CGameplayEventRecord(**values))
            with pytest.raises(IntegrityError) as excinfo:
                await session.commit()
            expected_constraint = GAMEPLAY_EVENT_CONSTRAINT_NAMES[field]
            assert expected_constraint in str(excinfo.value)
            await session.rollback()
        await database_engine.dispose()

    asyncio.run(exercise())


@pytest.mark.parametrize("field,invalid_value", SUMMARY_CHECK_CASES)
def test_c3a_c_task_opportunity_summaries_check_constraints_reject(field: str, invalid_value: object) -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            graph = await seed_full_graph(session)
            summary_id = uuid4()
            values: dict[str, object] = {
                "c_task_opportunity_summary_id": summary_id,
                "c_session_id": graph["session_id"],
                "game_task_instance_id": graph["instance_id"],
                "task_index": 0,
                "task_offered": True,
                "task_started": True,
                "task_completed": True,
                "task_skipped": False,
                "task_quit": False,
                "technical_issue": False,
                "correct_task": True,
                "total_attempts": 1,
                "retry_count": 0,
                "scaffold_requested": False,
                "scaffold_count": 0,
                "highest_scaffold_level": None,
                "c_answer_changes": 0,
                "task_latency_sec": 3.5,
                "inactive_time_sec": 0.0,
                "inactivity_periods": 0,
                "quit_after_error": False,
                "terminal_reason": "completed_correct",
                "first_attempt_correct": True,
                "final_attempt_correct": True,
                "consecutive_error_max_within_task": 0,
                **provenance("c_task_opportunity_summary", summary_id),
            }
            values[field] = invalid_value
            session.add(CTaskOpportunitySummaryRecord(**values))
            with pytest.raises(IntegrityError) as excinfo:
                await session.commit()
            assert f"ck_c_task_opportunity_summaries_{field}" in str(excinfo.value)
            await session.rollback()
        await database_engine.dispose()

    asyncio.run(exercise())


@pytest.mark.parametrize("field,invalid_value", AGGREGATE_CHECK_CASES)
def test_c3a_c_session_aggregate_results_check_constraints_reject(field: str, invalid_value: object) -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            graph = await seed_full_graph(session)
            result_id = uuid4()
            values: dict[str, object] = {
                "c_session_aggregate_result_id": result_id,
                "c_session_id": graph["session_id"],
                "task_opportunity_count": 1,
                "completed_task_count": 1,
                "correct_task_count": 1,
                "total_attempt_count": 1,
                "accuracy_rate": 1.0,
                "avg_attempts_per_task": 1.0,
                "task_completion_rate": 1.0,
                "inactivity_periods": 0,
                "inactive_time_sec": 0.0,
                "inactive_time_available": True,
                "session_duration_sec": 60.0,
                "time_in_target_band_sec": 30.0,
                "consecutive_error_max": 0,
                "difficulty_floor_hits": 0,
                "quit_after_error": False,
                "safety_override_count": 0,
                "c_mean_game_task_latency_sec": 3.5,
                "c_median_game_task_latency_sec": 3.5,
                "current_difficulty_level": 2,
                "difficulty_trend": "stable",
                "session_technical_issue_flag": False,
                "engagement_score": None,
                "engagement_completion_component": None,
                "engagement_activity_component": None,
                "engagement_target_band_component": None,
                "engagement_accuracy_component": None,
                "frustration_index": None,
                "frustration_error_run_component": None,
                "frustration_excess_attempt_component": None,
                "frustration_inactivity_burden_component": None,
                "frustration_floor_hit_component": None,
                "frustration_quit_after_error_component": None,
                "frustration_safety_override_component": None,
                "telemetry_quality_status": "complete",
                "learner_state": "engaged",
                "state_reason": "high_engagement_low_friction",
                **provenance("c_session_aggregate_result", result_id),
            }
            values[field] = invalid_value
            session.add(CSessionAggregateResultRecord(**values))
            with pytest.raises(IntegrityError) as excinfo:
                await session.commit()
            assert f"ck_c_session_aggregate_results_{field}" in str(excinfo.value)
            await session.rollback()
        await database_engine.dispose()

    asyncio.run(exercise())


@pytest.mark.parametrize("field,invalid_value", LEARNER_LOCAL_STATE_CHECK_CASES)
def test_c3a_c_learner_local_state_check_constraints_reject(field: str, invalid_value: object) -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            student_id = await seed_learner(session)
            state_id = uuid4()
            values: dict[str, object] = {
                "c_learner_local_state_id": state_id,
                "student_id": student_id,
                "eligible_combined_handoffs_completed": 0,
                "sessions_since_last_practice": {},
                "prior_session_end_state": "engaged",
                **provenance("c_learner_local_state", state_id),
            }
            values[field] = invalid_value
            session.add(CLearnerLocalStateRecord(**values))
            with pytest.raises(IntegrityError) as excinfo:
                await session.commit()
            assert f"ck_c_learner_local_state_{field}" in str(excinfo.value)
            await session.rollback()
        await database_engine.dispose()

    asyncio.run(exercise())


@pytest.mark.parametrize("field,invalid_value", POLICY_DECISION_CHECK_CASES)
def test_c3a_c_policy_decisions_check_constraints_reject(field: str, invalid_value: object) -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            graph = await seed_full_graph(session)
            decision_id = uuid4()
            values: dict[str, object] = {
                "c_policy_decision_id": decision_id,
                "c_session_id": graph["session_id"],
                "c_task_opportunity_id": graph["opportunity_id"],
                "policy_mode": "rule_based_baseline",
                "policy_version": "1.0.0",
                "rl_state": None,
                "selected_action": "hold",
                "applied_action": "hold",
                "action_overridden": False,
                "safety_reason": None,
                "difficulty_before": 2,
                "difficulty_after": 2,
                "rolling_strain_bucket": "low",
                "session_start_state_bucket": None,
                "increase_block_remaining": 0,
                "internal_reward": None,
                "seed_lineage_global_seed": 42,
                "seed_lineage_path": ["global", "session", "task"],
                "seed_lineage_seed": 4242,
                "evidence_snapshot": {},
                "safety_forces_recovery": False,
                **provenance("c_policy_decision", decision_id),
            }
            values[field] = invalid_value
            session.add(CPolicyDecisionRecord(**values))
            with pytest.raises(IntegrityError) as excinfo:
                await session.commit()
            assert f"ck_c_policy_decisions_{field}" in str(excinfo.value)
            await session.rollback()
        await database_engine.dispose()

    asyncio.run(exercise())


@pytest.mark.parametrize("field,invalid_value", SCAFFOLD_EVENT_CHECK_CASES)
def test_c3a_c_scaffold_events_check_constraints_reject(field: str, invalid_value: object) -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            graph = await seed_full_graph(session)
            event_id = uuid4()
            values: dict[str, object] = {
                "c_scaffold_event_id": event_id,
                "c_session_id": graph["session_id"],
                "c_task_opportunity_id": graph["opportunity_id"],
                "event_type": "requested",
                "scaffold_level": "C1",
                "consecutive_incorrect_current_task": 2,
                "safety_forces_recovery": False,
                **provenance("c_scaffold_event", event_id),
            }
            values[field] = invalid_value
            session.add(CScaffoldEventRecord(**values))
            with pytest.raises(IntegrityError) as excinfo:
                await session.commit()
            assert f"ck_c_scaffold_events_{field}" in str(excinfo.value)
            await session.rollback()
        await database_engine.dispose()

    asyncio.run(exercise())


# =====================================================================================
# R-E's UNIQUE(student_id, intervention_session_id) on c_sessions -- the one non-CHECK invariant
# authorized to land in 3a. Provoked directly: a second row with the same pair must be rejected.
# =====================================================================================


def test_c3a_c_sessions_unique_student_intervention_session_rejects_duplicate() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            student_id = await seed_learner(session)
            bundle_id = await seed_runtime_bundle(session)
            shared_intervention_id = f"shared-{uuid4()}"
            first_kwargs = session_kwargs(
                student_id=student_id, bundle_id=bundle_id, intervention_session_id=shared_intervention_id
            )
            session.add(CSessionRecord(**first_kwargs))
            await session.commit()
        async with factory() as session:
            second_kwargs = session_kwargs(
                student_id=student_id, bundle_id=bundle_id, intervention_session_id=shared_intervention_id
            )
            session.add(CSessionRecord(**second_kwargs))
            with pytest.raises(IntegrityError) as excinfo:
                await session.commit()
            assert "uq_c_sessions_student_intervention_session" in str(excinfo.value)
            await session.rollback()
        await database_engine.dispose()

    asyncio.run(exercise())


# =====================================================================================
# A4 -- the allow-list mechanism fires for REAL against the real ten tables (not just the
# synthetic-metadata check in test_be2_architecture_guards.py). Recomputes the collision set
# independently in this file, against the same live Base.metadata, and cross-checks it equals
# AUTHORIZED_C_COLUMN_EXCEPTIONS -- a second, independent witness of the same real-metadata fact
# the guard file's own test asserts, not a re-import of that test's result.
# =====================================================================================


def test_c3a_allow_list_mechanism_fires_against_real_ten_tables() -> None:
    c3a_tables = {name: Base.metadata.tables[name] for name in C3A_TABLES}
    computed_collisions_on_c3a_tables = {
        (table.name, column.name)
        for table in c3a_tables.values()
        for column in table.columns
        if any(term in column.name.lower() for term in PROHIBITED_COLUMN_TERMS)
    }
    assert computed_collisions_on_c3a_tables == AUTHORIZED_C_COLUMN_EXCEPTIONS
    assert len(computed_collisions_on_c3a_tables) == 14


# =====================================================================================
# A3 -- migration content: creates exactly the ten authorized tables, nothing else; no trigger;
# no import of the generator or Yass by name. Mirrors Phase 2's
# test_c2_migration_creates_only_the_runtime_bundle_table pattern exactly.
# =====================================================================================


def test_c3a_migration_creates_only_the_ten_authorized_tables() -> None:
    migration = MIGRATION_PATH.read_text(encoding="utf-8")
    created = set(re.findall(r'op\.create_table\(\s*"([^"]+)"', migration))
    assert created == C3A_TABLES
    lowered = migration.lower()
    assert "create_trigger" not in lowered
    assert "create trigger" not in lowered
    assert "bulk_insert" not in lowered
    assert "component_c_generator" not in lowered
    assert "yass" not in lowered
