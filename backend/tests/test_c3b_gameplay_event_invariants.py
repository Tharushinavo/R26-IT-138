"""Component C Phase 3b acceptance tests (Phase 3b work order, rulings R-J through R-O).

Covers: I1's AT MOST ONE terminal-event-per-task partial unique index (never "exactly one" --
R-N); I2's event_index-consecutive-from-1 trigger; I3's event_timestamp_relative_ms-non-decreasing
trigger; I4's structural attempt_number/event_type CHECK (NOT "attempt counts bounded" -- I4's
numeric bound is BLOCKED, ESCALATED TO THE OWNER per R-L, and is not built or tested here in any
form); and the migration-content guard (R-O).

Every provocation test here is SEQUENTIAL. Per R-M: this proves the rule FIRES. It does not prove
either trigger survives concurrent writers -- this suite has no precedent for driving two real
concurrent database connections from pytest, and none is introduced here. The row-lock mechanism
(SELECT ... FOR UPDATE on the parent c_task_instances row) mirrors Component B's own
enforce_b_session_active_bundle_eligibility trigger, used there for the same concurrency reason;
that similarity is the basis for the design, not a substitute for a concurrent-writer test.
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
    CGameplayEventRecord,
    CRuntimeBundleRecord,
    CSessionRecord,
    CTaskInstanceRecord,
    CTaskOpportunityRecord,
    Learner,
)

MIGRATION_PATH = Path("migrations/versions/20260816_0003_c3b_gameplay_event_invariants.py")


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
        "system_actor": "c3b-isolated-test",
        "request_id": f"test-{uuid4()}",
        "operation_or_event_type": "test.persistence",
        "reason_code": "ISOLATED_SYNTHETIC_TEST",
        "resource_type": resource_type,
        "resource_id": resource_id,
        "source_class": "TEST",
        "source_system": "c3b-isolated-test-suite",
        "environment": "test",
        "schema_revision": "20260816_0003",
    }


async def seed_learner(session: AsyncSession) -> UUID:
    learner_id = uuid4()
    session.add(
        Learner(learner_id=learner_id, grade=2, status="test_only", **provenance("b_learner", learner_id))
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


async def seed_session(session: AsyncSession, *, student_id: UUID, bundle_id: UUID) -> UUID:
    session_id = uuid4()
    session.add(
        CSessionRecord(
            c_session_id=session_id,
            student_id=student_id,
            intervention_session_id=f"intervention-{session_id}",
            session_mode="c_only",
            session_phase="c_only",
            mastery_context_mode="unavailable_fallback",
            catalogue_version="test-catalogue-1",
            catalogue_checksum="a" * 64,
            c_runtime_bundle_record_id=bundle_id,
            grade=2,
            state="active",
            global_seed=42,
            started_at_utc=datetime.now(UTC),
            completed_at_utc=None,
            row_version=0,
            **provenance("c_session", session_id),
        )
    )
    await session.flush()
    return session_id


async def seed_opportunity(session: AsyncSession, *, session_id: UUID) -> UUID:
    opportunity_id = uuid4()
    session.add(
        CTaskOpportunityRecord(
            c_task_opportunity_id=opportunity_id,
            c_session_id=session_id,
            task_index=0,
            selected_skill_id="skill.count_to_10",
            selected_template_id="template.count_and_collect.v1",
            initial_difficulty_level=2,
            mastery_context_mode="unavailable_fallback",
            mastery_selected_skill=None,
            session_phase="c_only",
            terminal_reason=None,
            task_offered_at_utc=datetime.now(UTC),
            **provenance("c_task_opportunity", opportunity_id),
        )
    )
    await session.flush()
    return opportunity_id


async def seed_instance(session: AsyncSession, *, opportunity_id: UUID) -> UUID:
    instance_id = uuid4()
    session.add(
        CTaskInstanceRecord(
            c_task_instance_id=instance_id,
            c_task_opportunity_id=opportunity_id,
            game_family_id="count_and_collect",
            game_task_template_id="template.count_and_collect.v1",
            template_version="1.0.0",
            catalogue_version="test-catalogue-1",
            generator_version="0.1.0+c1.09267ab",
            task_index=0,
            skill_id="skill.count_to_10",
            curriculum_node_id="node.counting.grade2",
            grade_scope=2,
            difficulty_level=2,
            difficulty_vector={"magnitude": 2, "support": 1},
            functional_role="primary",
            representation_mode="concrete",
            prompt_payload={"text": "Count the apples."},
            interactive_assets={"assets": []},
            correct_answer_payload={"value": 4},
            correctness_function_id="exact_match_v1",
            valid_action_space={"actions": ["tap"]},
            completion_condition="answer_submitted",
            failure_condition="attempt_cap_exhausted",
            scaffold_state="C0",
            recovery_parent_instance_id=None,
            technical_status="OK",
            seed_lineage_global_seed=42,
            seed_lineage_path=["global", "session", "task"],
            seed_lineage_seed=4242,
            **provenance("c_task_instance", instance_id),
        )
    )
    await session.flush()
    return instance_id


async def seed_full_graph(session: AsyncSession) -> dict[str, UUID]:
    student_id = await seed_learner(session)
    bundle_id = await seed_runtime_bundle(session)
    session_id = await seed_session(session, student_id=student_id, bundle_id=bundle_id)
    opportunity_id = await seed_opportunity(session, session_id=session_id)
    instance_id = await seed_instance(session, opportunity_id=opportunity_id)
    return {
        "student_id": student_id,
        "bundle_id": bundle_id,
        "session_id": session_id,
        "opportunity_id": opportunity_id,
        "instance_id": instance_id,
    }


def event_kwargs(
    *,
    session_id: UUID,
    instance_id: UUID,
    event_index: int,
    event_timestamp_relative_ms: int,
    event_type: str = "action_performed",
    attempt_number: int | None = None,
    terminal_reason: str | None = None,
    **overrides: object,
) -> dict[str, object]:
    event_id = uuid4()
    values: dict[str, object] = {
        "c_gameplay_event_id": event_id,
        "c_session_id": session_id,
        "game_task_instance_id": instance_id,
        "task_index": 0,
        "event_type": event_type,
        "event_index": event_index,
        "attempt_number": attempt_number,
        "event_timestamp_relative_ms": event_timestamp_relative_ms,
        "action_payload": None,
        "evaluation_payload": None,
        "scaffold_code": None,
        "technical_flag": False,
        "terminal_reason": terminal_reason,
        "seed_lineage_global_seed": 42,
        "seed_lineage_path": ["global", "session", "task"],
        "seed_lineage_seed": 4242,
        "generator_version": "0.1.0+c1.09267ab",
        "config_checksum": "b" * 64,
        **provenance("c_gameplay_event", event_id),
    }
    values.update(overrides)
    return values


# =====================================================================================
# I1 -- AT MOST ONE terminal event per task (never "exactly one" -- R-N).
# =====================================================================================


def test_c3b_at_most_one_terminal_event_positive_control_single_terminal_event_succeeds() -> None:
    """SIGNAL: a single terminal event for a task is accepted -- proves the index does not
    over-reject the ordinary case before the rejection test below is trusted."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            graph = await seed_full_graph(session)
            session.add(
                CGameplayEventRecord(
                    **event_kwargs(
                        session_id=graph["session_id"],
                        instance_id=graph["instance_id"],
                        event_index=1,
                        event_timestamp_relative_ms=0,
                        event_type="game_task_completed",
                        terminal_reason="completed_correct",
                    )
                )
            )
            await session.commit()
        await database_engine.dispose()

    asyncio.run(exercise())


def test_c3b_at_most_one_terminal_event_rejects_second_terminal_row() -> None:
    """SIGNAL: a second terminal-type event (different row, same task) is rejected by the
    partial unique index -- would FAIL (no IntegrityError) if the index's WHERE clause or column
    were wrong, or if the index were dropped."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            graph = await seed_full_graph(session)
            session.add(
                CGameplayEventRecord(
                    **event_kwargs(
                        session_id=graph["session_id"],
                        instance_id=graph["instance_id"],
                        event_index=1,
                        event_timestamp_relative_ms=0,
                        event_type="game_task_completed",
                        terminal_reason="completed_correct",
                    )
                )
            )
            await session.commit()
        async with factory() as session:
            session.add(
                CGameplayEventRecord(
                    **event_kwargs(
                        session_id=graph["session_id"],
                        instance_id=graph["instance_id"],
                        event_index=2,
                        event_timestamp_relative_ms=100,
                        event_type="game_task_quit",
                        terminal_reason="quit_without_recent_error",
                    )
                )
            )
            with pytest.raises(IntegrityError) as excinfo:
                await session.commit()
            assert "uq_c_gameplay_events_at_most_one_terminal_per_instance" in str(excinfo.value)
            await session.rollback()
        await database_engine.dispose()

    asyncio.run(exercise())


# =====================================================================================
# I2 -- event_index consecutive from 1 within a task (trigger, R-J).
# =====================================================================================


def test_c3b_event_index_positive_control_consecutive_sequence_succeeds() -> None:
    """SIGNAL: 1, 2, 3 for the same task all succeed -- proves the trigger does not over-reject
    the ordinary append sequence before the rejection tests below are trusted."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            graph = await seed_full_graph(session)
            for index, ts in ((1, 0), (2, 100), (3, 200)):
                session.add(
                    CGameplayEventRecord(
                        **event_kwargs(
                            session_id=graph["session_id"],
                            instance_id=graph["instance_id"],
                            event_index=index,
                            event_timestamp_relative_ms=ts,
                        )
                    )
                )
                await session.commit()
        await database_engine.dispose()

    asyncio.run(exercise())


def test_c3b_event_index_rejects_non_one_first_event() -> None:
    """SIGNAL: the first event for a task with event_index != 1 is rejected -- would FAIL if the
    trigger only checked the gap case and never the "no prior rows" base case."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            graph = await seed_full_graph(session)
            session.add(
                CGameplayEventRecord(
                    **event_kwargs(
                        session_id=graph["session_id"],
                        instance_id=graph["instance_id"],
                        event_index=2,
                        event_timestamp_relative_ms=0,
                    )
                )
            )
            with pytest.raises(IntegrityError) as excinfo:
                await session.commit()
            assert excinfo.value.orig.__cause__.constraint_name == "ck_c_gameplay_events_index_consecutive"
            await session.rollback()
        await database_engine.dispose()

    asyncio.run(exercise())


def test_c3b_event_index_rejects_gap_after_valid_first_event() -> None:
    """SIGNAL: event_index jumping from 1 to 3 (skipping 2) is rejected -- would FAIL if the
    trigger only checked exact duplicates (a UNIQUE constraint would catch that) rather than
    true consecutiveness."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            graph = await seed_full_graph(session)
            session.add(
                CGameplayEventRecord(
                    **event_kwargs(
                        session_id=graph["session_id"],
                        instance_id=graph["instance_id"],
                        event_index=1,
                        event_timestamp_relative_ms=0,
                    )
                )
            )
            await session.commit()
        async with factory() as session:
            session.add(
                CGameplayEventRecord(
                    **event_kwargs(
                        session_id=graph["session_id"],
                        instance_id=graph["instance_id"],
                        event_index=3,
                        event_timestamp_relative_ms=100,
                    )
                )
            )
            with pytest.raises(IntegrityError) as excinfo:
                await session.commit()
            assert excinfo.value.orig.__cause__.constraint_name == "ck_c_gameplay_events_index_consecutive"
            await session.rollback()
        await database_engine.dispose()

    asyncio.run(exercise())


# =====================================================================================
# I3 -- event_timestamp_relative_ms non-decreasing within a task (trigger, R-J).
# =====================================================================================


def test_c3b_event_timestamp_positive_control_equal_and_increasing_succeed() -> None:
    """SIGNAL: an equal timestamp (non-decreasing allows ties) followed by an increasing one
    both succeed -- proves the trigger's boundary (< vs <=) is the intended one."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            graph = await seed_full_graph(session)
            for index, ts in ((1, 100), (2, 100), (3, 250)):
                session.add(
                    CGameplayEventRecord(
                        **event_kwargs(
                            session_id=graph["session_id"],
                            instance_id=graph["instance_id"],
                            event_index=index,
                            event_timestamp_relative_ms=ts,
                        )
                    )
                )
                await session.commit()
        await database_engine.dispose()

    asyncio.run(exercise())


def test_c3b_event_timestamp_rejects_decrease_within_task() -> None:
    """SIGNAL: a later-inserted event with an earlier timestamp than the task's current max is
    rejected -- would FAIL if the trigger compared only to the immediately-preceding row's
    event_index rather than the true max timestamp for the task."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            graph = await seed_full_graph(session)
            session.add(
                CGameplayEventRecord(
                    **event_kwargs(
                        session_id=graph["session_id"],
                        instance_id=graph["instance_id"],
                        event_index=1,
                        event_timestamp_relative_ms=500,
                    )
                )
            )
            await session.commit()
        async with factory() as session:
            session.add(
                CGameplayEventRecord(
                    **event_kwargs(
                        session_id=graph["session_id"],
                        instance_id=graph["instance_id"],
                        event_index=2,
                        event_timestamp_relative_ms=100,
                    )
                )
            )
            with pytest.raises(IntegrityError) as excinfo:
                await session.commit()
            assert excinfo.value.orig.__cause__.constraint_name == "ck_c_gameplay_events_timestamp_non_decreasing"
            await session.rollback()
        await database_engine.dispose()

    asyncio.run(exercise())


# =====================================================================================
# I4's structural sub-rule -- attempt_number only on ATTEMPT_SCOPED_EVENT_TYPES (R-L). This is
# NOT "attempt counts bounded"; no numeric bound is asserted anywhere in this file.
# =====================================================================================


def test_c3b_attempt_number_positive_control_on_attempt_scoped_event_type_succeeds() -> None:
    """SIGNAL: attempt_number set on answer_submitted (an ATTEMPT_SCOPED_EVENT_TYPES member)
    succeeds -- proves the CHECK does not over-reject the ordinary case."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            graph = await seed_full_graph(session)
            session.add(
                CGameplayEventRecord(
                    **event_kwargs(
                        session_id=graph["session_id"],
                        instance_id=graph["instance_id"],
                        event_index=1,
                        event_timestamp_relative_ms=0,
                        event_type="answer_submitted",
                        attempt_number=1,
                        action_payload={"value": 4},
                    )
                )
            )
            await session.commit()
        await database_engine.dispose()

    asyncio.run(exercise())


def test_c3b_attempt_number_rejects_on_non_attempt_scoped_event_type() -> None:
    """SIGNAL: attempt_number set on game_task_offered (not in ATTEMPT_SCOPED_EVENT_TYPES) is
    rejected -- would FAIL if the CHECK's event_type list drifted from the package's own
    ATTEMPT_SCOPED_EVENT_TYPES."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            graph = await seed_full_graph(session)
            session.add(
                CGameplayEventRecord(
                    **event_kwargs(
                        session_id=graph["session_id"],
                        instance_id=graph["instance_id"],
                        event_index=1,
                        event_timestamp_relative_ms=0,
                        event_type="game_task_offered",
                        attempt_number=1,
                    )
                )
            )
            with pytest.raises(IntegrityError) as excinfo:
                await session.commit()
            assert "ck_c_gameplay_events_attempt_number_scope" in str(excinfo.value)
            await session.rollback()
        await database_engine.dispose()

    asyncio.run(exercise())


# =====================================================================================
# R-O -- migration-content guard: no table creation; every named object present; no
# component_c_generator/yass reference.
# =====================================================================================


def test_c3b_migration_creates_no_table_and_adds_only_the_named_objects() -> None:
    migration = MIGRATION_PATH.read_text(encoding="utf-8")
    assert not re.findall(r'op\.create_table\(\s*"([^"]+)"', migration)
    assert "uq_c_gameplay_events_at_most_one_terminal_per_instance" in migration
    assert "ck_c_gameplay_events_attempt_number_scope" in migration
    assert "enforce_c_gameplay_event_index_consecutive" in migration
    assert "trg_c_gameplay_events_index_consecutive" in migration
    assert "enforce_c_gameplay_event_timestamp_non_decreasing" in migration
    assert "trg_c_gameplay_events_timestamp_non_decreasing" in migration
    lowered = migration.lower()
    assert "component_c_generator" not in lowered
    assert "yass" not in lowered
