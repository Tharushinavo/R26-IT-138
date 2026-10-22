"""BE4a (BEplan §9 BE4.1) persistence + presentation-token tests: migration cycle,
one-open-opportunity DB constraint, token issue/validate fail-closed paths, and safe-DTO
privacy (public projection must never carry any private task-instance field).
"""

import asyncio
import hashlib
import subprocess
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.application.opportunity_persistence import OpportunityPersistenceService
from app.core.config import get_settings
from app.core.errors import ConflictError
from app.domain.b_opportunity import (
    PresentationTokenExpiredError,
    PresentationTokenMismatchError,
    PresentationTokenNotFoundError,
    project_task_instance_to_presentation,
)
from app.infrastructure.database import async_database_url
from app.infrastructure.persistence_models import (
    AppUser,
    ItemOpportunityRecord,
    Learner,
    RuntimeBundleRecord,
    SessionRecord,
    TaskInstanceRecord,
)


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
        "system_actor": "be4a-isolated-test",
        "request_id": f"test-{uuid4()}",
        "operation_or_event_type": "test.be4a_persistence",
        "reason_code": "ISOLATED_SYNTHETIC_TEST",
        "resource_type": resource_type,
        "resource_id": resource_id,
        "source_class": "TEST",
        "source_system": "be4a-isolated-test-suite",
        "environment": "test",
        "schema_revision": "20260727_0001",
    }


async def _seed_session(session: AsyncSession) -> tuple[UUID, UUID, UUID]:
    """Insert one AppUser -> Learner -> RuntimeBundleRecord -> active SessionRecord chain,
    returning (session_id, learner_id, runtime_bundle_record_id)."""
    user_id = uuid4()
    session.add(AppUser(user_id=user_id, supabase_subject=f"subject-{user_id}", status="active", **provenance("app_user", user_id)))

    learner_id = uuid4()
    session.add(Learner(learner_id=learner_id, grade=2, status="active", **provenance("b_learner", learner_id)))

    bundle_id = uuid4()
    session.add(
        RuntimeBundleRecord(
            runtime_bundle_record_id=bundle_id,
            bundle_version=f"bundle-{bundle_id}",
            manifest_checksum=hashlib.sha256(str(bundle_id).encode()).hexdigest(),
            publication_state="PUBLISHED",
            approval_status="APPROVED",
            immutable_after_publication=True,
            **provenance("b_runtime_bundle_record", bundle_id),
        )
    )
    await session.flush()

    session_id = uuid4()
    session.add(
        SessionRecord(
            session_id=session_id,
            learner_id=learner_id,
            runtime_bundle_record_id=bundle_id,
            state="active",
            expires_at_utc=None,
            row_version=0,
            **provenance("b_session", session_id),
        )
    )
    await session.flush()
    return session_id, learner_id, bundle_id


def test_migration_downgrade_reupgrade_cycle_and_schema() -> None:
    alembic("upgrade", "head")

    async def inspect_schema() -> None:
        database_engine, _ = isolated_database()
        async with database_engine.connect() as connection:
            def assertions(sync_connection) -> None:
                inspector = inspect(sync_connection)
                tables = set(inspector.get_table_names())
                assert {"b_item_opportunities", "b_task_instances", "b_presentation_tokens"} <= tables
                opportunity_indexes = {ix["name"] for ix in inspector.get_indexes("b_item_opportunities")}
                assert "uq_b_item_opportunities_one_open_per_session" in opportunity_indexes

            await connection.run_sync(assertions)
        await database_engine.dispose()

    asyncio.run(inspect_schema())

    alembic("downgrade", "20260723_0001")

    async def assert_dropped() -> None:
        database_engine, _ = isolated_database()
        async with database_engine.connect() as connection:
            def assertions(sync_connection) -> None:
                inspector = inspect(sync_connection)
                tables = set(inspector.get_table_names())
                assert not ({"b_item_opportunities", "b_task_instances", "b_presentation_tokens"} & tables)

            await connection.run_sync(assertions)
        await database_engine.dispose()

    asyncio.run(assert_dropped())
    alembic("upgrade", "head")


def test_one_open_opportunity_per_session_enforced_at_db_level() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            session_id, learner_id, _bundle_id = await _seed_session(session)
            service = OpportunityPersistenceService(session)

            await service.open_opportunity(
                session_id=session_id,
                learner_id=learner_id,
                skill_id="skill.addition",
                item_template_id="template.addition.001",
                opportunity_index=1,
                selection_provenance={"winning_item_template_id": "template.addition.001"},
                timeout=timedelta(minutes=5),
                provenance=provenance("b_item_opportunity", uuid4()),
            )
            await session.commit()

        async with factory() as session:
            with pytest.raises(ConflictError):
                await OpportunityPersistenceService(session).open_opportunity(
                    session_id=session_id,
                    learner_id=learner_id,
                    skill_id="skill.subtraction",
                    item_template_id="template.subtraction.001",
                    opportunity_index=2,
                    selection_provenance={"winning_item_template_id": "template.subtraction.001"},
                    timeout=timedelta(minutes=5),
                    provenance=provenance("b_item_opportunity", uuid4()),
                )
            await session.rollback()

        async with factory() as session:
            count = await session.scalar(
                select(ItemOpportunityRecord).where(
                    ItemOpportunityRecord.session_id == session_id, ItemOpportunityRecord.state == "OPEN"
                )
            )
            assert count is not None

        await database_engine.dispose()

    asyncio.run(exercise())


def test_close_opportunity_allows_a_new_open_opportunity_for_the_same_session() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            session_id, learner_id, _bundle_id = await _seed_session(session)
            service = OpportunityPersistenceService(session)
            first = await service.open_opportunity(
                session_id=session_id,
                learner_id=learner_id,
                skill_id="skill.addition",
                item_template_id="template.addition.001",
                opportunity_index=1,
                selection_provenance={},
                timeout=timedelta(minutes=5),
                provenance=provenance("b_item_opportunity", uuid4()),
            )
            await session.commit()

        async with factory() as session:
            service = OpportunityPersistenceService(session)
            closed = await service.close_opportunity(first.item_opportunity_id)
            assert closed.state == "CLOSED"
            second = await service.open_opportunity(
                session_id=session_id,
                learner_id=learner_id,
                skill_id="skill.subtraction",
                item_template_id="template.subtraction.001",
                opportunity_index=2,
                selection_provenance={},
                timeout=timedelta(minutes=5),
                provenance=provenance("b_item_opportunity", uuid4()),
            )
            assert second.state == "OPEN"
            await session.commit()

        await database_engine.dispose()

    asyncio.run(exercise())


def test_presentation_token_issue_and_validate_happy_path() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            session_id, learner_id, bundle_id = await _seed_session(session)
            service = OpportunityPersistenceService(session)
            opportunity = await service.open_opportunity(
                session_id=session_id,
                learner_id=learner_id,
                skill_id="skill.addition",
                item_template_id="template.addition.001",
                opportunity_index=1,
                selection_provenance={},
                timeout=timedelta(minutes=5),
                provenance=provenance("b_item_opportunity", uuid4()),
            )
            raw_token, record = await service.issue_presentation_token(
                session_id=session_id,
                item_opportunity_id=opportunity.item_opportunity_id,
                learner_id=learner_id,
                runtime_bundle_record_id=bundle_id,
                ttl=timedelta(minutes=5),
                provenance=provenance("b_presentation_token", uuid4()),
            )
            await session.commit()
            assert raw_token not in record.token_hash

            validated = await service.validate_presentation_token(
                raw_token,
                session_id=session_id,
                item_opportunity_id=opportunity.item_opportunity_id,
                learner_id=learner_id,
            )
            assert validated.presentation_token_id == record.presentation_token_id

        await database_engine.dispose()

    asyncio.run(exercise())


def test_presentation_token_fails_closed_on_expiry_mismatch_and_unknown() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            session_id, learner_id, bundle_id = await _seed_session(session)
            service = OpportunityPersistenceService(session)
            opportunity = await service.open_opportunity(
                session_id=session_id,
                learner_id=learner_id,
                skill_id="skill.addition",
                item_template_id="template.addition.001",
                opportunity_index=1,
                selection_provenance={},
                timeout=timedelta(minutes=5),
                provenance=provenance("b_item_opportunity", uuid4()),
            )

            expired_token, _ = await service.issue_presentation_token(
                session_id=session_id,
                item_opportunity_id=opportunity.item_opportunity_id,
                learner_id=learner_id,
                runtime_bundle_record_id=bundle_id,
                ttl=timedelta(milliseconds=50),
                provenance=provenance("b_presentation_token", uuid4()),
            )
            await asyncio.sleep(0.2)
            live_token, _ = await service.issue_presentation_token(
                session_id=session_id,
                item_opportunity_id=opportunity.item_opportunity_id,
                learner_id=learner_id,
                runtime_bundle_record_id=bundle_id,
                ttl=timedelta(minutes=5),
                provenance=provenance("b_presentation_token", uuid4()),
            )
            await session.commit()

            with pytest.raises(PresentationTokenExpiredError):
                await service.validate_presentation_token(
                    expired_token, session_id=session_id, item_opportunity_id=opportunity.item_opportunity_id, learner_id=learner_id
                )

            with pytest.raises(PresentationTokenMismatchError):
                await service.validate_presentation_token(
                    live_token, session_id=uuid4(), item_opportunity_id=opportunity.item_opportunity_id, learner_id=learner_id
                )

            with pytest.raises(PresentationTokenMismatchError):
                await service.validate_presentation_token(
                    live_token, session_id=session_id, item_opportunity_id=uuid4(), learner_id=learner_id
                )

            with pytest.raises(PresentationTokenMismatchError):
                await service.validate_presentation_token(
                    live_token, session_id=session_id, item_opportunity_id=opportunity.item_opportunity_id, learner_id=uuid4()
                )

            with pytest.raises(PresentationTokenNotFoundError):
                await service.validate_presentation_token(
                    "not-a-real-token", session_id=session_id, item_opportunity_id=opportunity.item_opportunity_id, learner_id=learner_id
                )

        await database_engine.dispose()

    asyncio.run(exercise())


FORBIDDEN_PRIVATE_KEYS = {
    "correct_answer",
    "allowed_equivalent_answers",
    "distractor_candidates",
    "distractor_rule_ids",
    "generated_operands",
    "generation_seed",
    "applied_guard_ids",
    "catalogue_version",
    "catalogue_checksum",
    "selection_provenance",
}


def test_safe_presentation_dto_excludes_every_private_field() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            session_id, learner_id, bundle_id = await _seed_session(session)
            service = OpportunityPersistenceService(session)
            opportunity = await service.open_opportunity(
                session_id=session_id,
                learner_id=learner_id,
                skill_id="skill.addition",
                item_template_id="template.addition.001",
                opportunity_index=1,
                selection_provenance={"winning_item_template_id": "template.addition.001", "score": 0.91},
                timeout=timedelta(minutes=5),
                provenance=provenance("b_item_opportunity", uuid4()),
            )
            task_instance = await service.create_task_instance(
                item_opportunity_id=opportunity.item_opportunity_id,
                item_template_id="template.addition.001",
                skill_id="skill.addition",
                grade=2,
                difficulty_level="EASY",
                representation_type="NUMERIC",
                response_format="MULTIPLE_CHOICE",
                prompt={"text": "3 + 4 = ?"},
                correct_answer="7",
                allowed_equivalent_answers=("7", "7.0"),
                distractor_candidates=("6", "8"),
                distractor_rule_ids=("off_by_one_low", "off_by_one_high"),
                generated_operands={"a": 3, "b": 4},
                generation_seed=123456789,
                applied_guard_ids=("guard.grade_gate",),
                catalogue_version="catalogue-2026.1",
                catalogue_checksum="b" * 64,
                provenance=provenance("b_task_instance", uuid4()),
            )
            raw_token, _ = await service.issue_presentation_token(
                session_id=session_id,
                item_opportunity_id=opportunity.item_opportunity_id,
                learner_id=learner_id,
                runtime_bundle_record_id=bundle_id,
                ttl=timedelta(minutes=5),
                provenance=provenance("b_presentation_token", uuid4()),
            )
            await session.commit()

            presented = project_task_instance_to_presentation(
                task_instance,
                presentation_token=raw_token,
                server_timeout_deadline_utc=opportunity.timeout_deadline_utc,
            )
            public_dict = presented.to_public_dict()

            assert not (FORBIDDEN_PRIVATE_KEYS & set(public_dict))
            assert "7" in presented.presented_choices and "6" in presented.presented_choices
            assert public_dict["presentation_token"] == raw_token
            assert public_dict["skill_id"] == "skill.addition"

        await database_engine.dispose()

    asyncio.run(exercise())
