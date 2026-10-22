"""PostgreSQL migration, repository, provenance, idempotency, and audit tests."""

import asyncio
import subprocess
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.infrastructure.database import async_database_url
from app.infrastructure.persistence_models import (
    AppUser,
    AppUserLearnerLink,
    AuditEvent,
    IdempotencyRecord,
    Learner,
    RuntimeBundleRecord,
    SessionEvent,
    SessionRecord,
)
from app.infrastructure.repositories import (
    AppUserLearnerLinkRepository,
    AppUserRepository,
    AuditEventRepository,
    IdempotencyRecordRepository,
    LearnerRepository,
    RuntimeBundleRecordRepository,
    SessionEventRepository,
    SessionRecordRepository,
)


EXPECTED_TABLES = {
    "app_users", "b_learners", "app_user_learner_links", "b_runtime_bundle_records",
    "b_sessions", "b_session_events", "b_idempotency_records", "b_audit_events",
    "teacher_profiles", "classrooms", "classroom_invites", "classroom_memberships",
    "teacher_profiles", "classrooms", "classroom_invites", "classroom_memberships",
    # BE4a (BEplan §9 BE4.1) — private opportunity/task-instance/presentation-token tables.
    "b_item_opportunities", "b_task_instances", "b_presentation_tokens",
    # BE4b (BEplan §9 BE4.2) — private per-learner, per-skill BKT state.
    "b_learner_skill_states",
    # BE4c (BEplan §9 BE4.3 + BE4.4) — private attempt events + immutable BKT transitions.
    "b_attempts", "b_skill_state_transitions",
    # BE4d (BEplan §9 BE4.5) — private governed hint events, separate from attempts/transitions.
    "b_hint_events",
    # BE4e (BEplan §9 BE4.6) — private, immutable session-aggregate + skill-certification results.
    "b_session_aggregate_results", "b_skill_certification_results",
    # Component C Phase 2 — mirrors b_runtime_bundle_records for Component C's own wheel pin.
    "c_runtime_bundle_records",
    # Component C Phase 3a (v3.0 §11 Phase 3) — the ten tables.
    "c_sessions", "c_task_opportunities", "c_task_instances", "c_gameplay_events",
    "c_task_opportunity_summaries", "c_session_aggregate_results", "c_learner_local_state",
    "c_policy_decisions", "c_safety_events", "c_scaffold_events",
    # Component C backend remediation, batch 4 (Amendment A-1) — the durable exclusion-reason /
    # supersession-chain table, created by its own migration (20260816_0007).
    "c_task_opportunity_verdicts",
    # Component C batch 9c-1a (Master Build Plan v3.0 §11 Phase 9; 9b_9c plan Track 9c, "9c-1 —
    # the tables and the routing") — the two shared B/C outbox tables, deliberately unprefixed
    # (shared infrastructure, not shared ownership — owner condition 1), created by their own
    # migration (20260816_0008).
    "outbox_events", "contract_deliveries",
    # Component D (Component D authorization, owner decision D-011 A1, 2026-10-21) — the three
    # cognitive-profiling tables, created by their own migration (20261021_0010).
    #
    # NOTE FOR WHOEVER ADDS THE NEXT TABLE: this set is a SECOND COPY of the one in
    # test_be2_architecture_guards.py. The two are maintained by hand and drift silently —
    # adding a table to the guard file alone leaves THIS test red, with an error that says
    # nothing about which list is stale. That is the "second record of a property, capable of
    # drifting from the first" defect 9c1b-work-order-v2.md names. Not consolidated here because
    # doing so would rewrite a Component B test for a Component D change, which the integration
    # rules forbid; recorded instead so the next person pays five minutes rather than an hour.
    "d_learner_state", "d_interactions", "d_cognitive_profiles",
}
COMMON_COLUMNS = {
    "created_at_utc", "updated_at_utc", "actor_user_id", "system_actor", "request_id",
    "operation_or_event_type", "reason_code", "resource_type", "resource_id",
    "before_reference_or_version", "after_reference_or_version", "source_class",
    "source_system", "source_record_id", "environment", "schema_revision",
    "approval_evidence_reference",
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


def system_provenance(resource_type: str, resource_id: UUID, source_class: str = "TEST") -> dict[str, object]:
    return {
        "system_actor": "be2-isolated-test",
        "request_id": f"test-{uuid4()}",
        "operation_or_event_type": "test.persistence",
        "reason_code": "ISOLATED_SYNTHETIC_TEST",
        "resource_type": resource_type,
        "resource_id": resource_id,
        "source_class": source_class,
        "source_system": "be2-isolated-test-suite",
        "environment": "test",
        "schema_revision": "20260722_0002",
    }


def actor_provenance(resource_type: str, resource_id: UUID, actor_user_id: UUID) -> dict[str, object]:
    values = system_provenance(resource_type, resource_id)
    values.pop("system_actor")
    values["actor_user_id"] = actor_user_id
    return values


def test_migration_upgrade_schema_constraints_and_cycle() -> None:
    alembic("upgrade", "head")

    async def inspect_schema() -> None:
        database_engine, _ = isolated_database()
        async with database_engine.connect() as connection:
            def assertions(sync_connection) -> None:
                inspector = inspect(sync_connection)
                actual = set(inspector.get_table_names()) - {"alembic_version", "be1_persistence_check"}
                assert actual == EXPECTED_TABLES
                for table in EXPECTED_TABLES:
                    columns = {column["name"]: column for column in inspector.get_columns(table)}
                    assert COMMON_COLUMNS <= set(columns)
                    for required in COMMON_COLUMNS - {
                        "actor_user_id", "system_actor", "before_reference_or_version",
                        "after_reference_or_version", "source_record_id", "approval_evidence_reference",
                    }:
                        assert columns[required]["nullable"] is False
                foreign_keys = inspector.get_foreign_keys("app_user_learner_links")
                referred = {foreign_key["referred_table"] for foreign_key in foreign_keys}
                assert {"app_users", "b_learners"} <= referred
                session_indexes = {index["name"] for index in inspector.get_indexes("b_sessions")}
                assert "uq_b_sessions_one_starting_or_active_per_learner" in session_indexes
                idempotency_uniques = {
                    constraint["name"] for constraint in inspector.get_unique_constraints("b_idempotency_records")
                }
                assert "uq_b_idempotency_records_scope" in idempotency_uniques
                assert "profile_type" in {column["name"] for column in inspector.get_columns("app_users")}
                assert "name" in {column["name"] for column in inspector.get_columns("b_learners")}
                assert "learner_profiles" not in actual
                assert "profile_type" in {column["name"] for column in inspector.get_columns("app_users")}
                assert "name" in {column["name"] for column in inspector.get_columns("b_learners")}
                assert "learner_profiles" not in actual
            await connection.run_sync(assertions)
        await database_engine.dispose()

    asyncio.run(inspect_schema())
    alembic("downgrade", "20260722_0001")

    async def assert_empty() -> None:
        database_engine, _ = isolated_database()
        async with database_engine.connect() as connection:
            names = await connection.run_sync(lambda sync: set(inspect(sync).get_table_names()))
            assert not (names & EXPECTED_TABLES)
        await database_engine.dispose()

    asyncio.run(assert_empty())
    alembic("upgrade", "head")


def test_repository_add_get_exists_audit_and_rollback() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, session_factory = isolated_database()
        user_id = uuid4()
        learner_id = uuid4()
        link_id = uuid4()
        bundle_id = uuid4()
        session_id = uuid4()
        session_event_id = uuid4()
        audit_id = uuid4()
        async with session_factory() as session:
            users = AppUserRepository(session)
            learners = LearnerRepository(session)
            links = AppUserLearnerLinkRepository(session)
            bundles = RuntimeBundleRecordRepository(session)
            sessions = SessionRecordRepository(session)
            session_events = SessionEventRepository(session)
            audits = AuditEventRepository(session)
            user = AppUser(
                user_id=user_id,
                supabase_subject=f"synthetic-subject-{user_id}",
                status="test_only",
                **system_provenance("app_user", user_id),
            )
            await users.add(user)
            learner = Learner(
                learner_id=learner_id,
                grade=None,
                status="test_only",
                **actor_provenance("b_learner", learner_id, user_id),
            )
            await learners.add(learner)
            link = AppUserLearnerLink(
                link_id=link_id,
                user_id=user_id,
                learner_id=learner_id,
                **actor_provenance("app_user_learner_link", link_id, user_id),
            )
            await links.add(link)
            bundle = RuntimeBundleRecord(
                runtime_bundle_record_id=bundle_id,
                bundle_version=f"test-{bundle_id}",
                manifest_checksum=bundle_id.hex * 2,
                publication_state="DRAFT",
                approval_status="UNRESOLVED",
                immutable_after_publication=False,
                **actor_provenance("b_runtime_bundle_record", bundle_id, user_id),
            )
            await bundles.add(bundle)
            session_record = SessionRecord(
                session_id=session_id,
                learner_id=learner_id,
                runtime_bundle_record_id=None,
                state="technical_failed",
                expires_at_utc=None,
                row_version=0,
                **actor_provenance("b_session", session_id, user_id),
            )
            await sessions.add(session_record)
            session_event = SessionEvent(
                session_event_id=session_event_id,
                session_id=session_id,
                **actor_provenance("b_session_event", session_event_id, user_id),
            )
            await session_events.add(session_event)
            audit = AuditEvent(
                audit_event_id=audit_id,
                **actor_provenance("b_audit_event", audit_id, user_id),
            )
            await audits.add(audit)
            await session.commit()
            assert await users.get_by_id(user_id) is user
            assert await learners.exists(learner_id)
            assert await links.get_by_id(link_id) is link
            assert await bundles.exists(bundle_id)
            assert await sessions.get_by_id(session_id) is session_record
            assert await session_events.exists(session_event_id)
            assert await audits.get_by_id(audit_id) is audit

        rolled_back_id = uuid4()
        async with session_factory() as session:
            await LearnerRepository(session).add(
                Learner(
                    learner_id=rolled_back_id,
                    grade=2,
                    status="test_only",
                    **actor_provenance("b_learner", rolled_back_id, user_id),
                )
            )
            await session.rollback()
        async with session_factory() as session:
            assert not await LearnerRepository(session).exists(rolled_back_id)
        await database_engine.dispose()

    asyncio.run(exercise())


def test_provenance_and_idempotency_constraints_fail_closed() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, session_factory = isolated_database()
        user_id = uuid4()
        async with session_factory() as session:
            await AppUserRepository(session).add(
                AppUser(
                    user_id=user_id,
                    supabase_subject=f"synthetic-subject-{user_id}",
                    status="test_only",
                    **system_provenance("app_user", user_id),
                )
            )
            await session.commit()

        invalid_id = uuid4()
        async with session_factory() as session:
            session.add(
                Learner(
                    learner_id=invalid_id,
                    grade=2,
                    status="test_only",
                    **actor_provenance("b_learner", invalid_id, user_id),
                )
            )
            session.add(
                Learner(
                    learner_id=uuid4(),
                    grade=2,
                    status="test_only",
                    **{**actor_provenance("b_learner", uuid4(), user_id), "source_class": "UNKNOWN"},
                )
            )
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
            else:
                raise AssertionError("Unknown provenance must be rejected")

        now = datetime.now(UTC)
        scope = {
            "http_method": "POST",
            "operation_identifier": "future-neutral-operation",
            "idempotency_key": str(uuid4()),
            "request_fingerprint": "a" * 64,
            "processing_status": "in_progress",
            "expires_at_utc": now + timedelta(hours=1),
        }
        first_id = uuid4()
        async with session_factory() as session:
            repository = IdempotencyRecordRepository(session)
            first = IdempotencyRecord(
                idempotency_record_id=first_id,
                **scope,
                **actor_provenance("b_idempotency_record", first_id, user_id),
            )
            await repository.add(first)
            await session.commit()
            assert await repository.find_scoped(
                user_id, "POST", "future-neutral-operation", scope["idempotency_key"]
            ) is not None

        duplicate_id = uuid4()
        async with session_factory() as session:
            session.add(
                IdempotencyRecord(
                    idempotency_record_id=duplicate_id,
                    **scope,
                    **actor_provenance("b_idempotency_record", duplicate_id, user_id),
                )
            )
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
            else:
                raise AssertionError("Duplicate idempotency scope must be rejected")

        await database_engine.dispose()

    asyncio.run(exercise())
