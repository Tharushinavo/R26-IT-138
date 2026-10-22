"""Focused PostgreSQL enforcement tests for BE2 corrective revision 0003."""

import asyncio
import subprocess
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.infrastructure.database import async_database_url
from app.infrastructure.persistence_models import Learner, RuntimeBundleRecord, SessionRecord


def alembic_upgrade() -> None:
    subprocess.run(["alembic", "upgrade", "head"], check=True)


def isolated_database():
    database_engine = create_async_engine(
        async_database_url(get_settings().database_url),
        poolclass=NullPool,
    )
    return database_engine, async_sessionmaker(
        database_engine, expire_on_commit=False, class_=AsyncSession
    )


def provenance(resource_type: str, resource_id: UUID) -> dict[str, object]:
    return {
        "system_actor": "be2-corrective-test",
        "request_id": f"corrective-{uuid4()}",
        "operation_or_event_type": "test.bundle_integrity",
        "reason_code": "ISOLATED_SYNTHETIC_TEST",
        "resource_type": resource_type,
        "resource_id": resource_id,
        "source_class": "TEST",
        "source_system": "be2-corrective-test-suite",
        "environment": "test",
        "schema_revision": "20260722_0003",
    }


def bundle(
    bundle_id: UUID,
    publication_state: str,
    approval_status: str,
    immutable: bool,
    checksum_character: str,
) -> RuntimeBundleRecord:
    return RuntimeBundleRecord(
        runtime_bundle_record_id=bundle_id,
        bundle_version=f"corrective-{bundle_id}",
        manifest_checksum=checksum_character * 64,
        publication_state=publication_state,
        approval_status=approval_status,
        immutable_after_publication=immutable,
        **provenance("b_runtime_bundle_record", bundle_id),
    )


async def expect_integrity_error(operation) -> None:
    try:
        await operation()
    except IntegrityError:
        return
    raise AssertionError("Database integrity guard did not reject the write")


def test_active_session_requires_published_approved_immutable_bundle() -> None:
    alembic_upgrade()

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        learner_ids = [uuid4() for _ in range(4)]
        draft_id, unresolved_id, eligible_id = uuid4(), uuid4(), uuid4()

        async with factory() as session:
            session.add_all(
                [
                    Learner(
                        learner_id=learner_id,
                        grade=None,
                        status="test_only",
                        **provenance("b_learner", learner_id),
                    )
                    for learner_id in learner_ids
                ]
                + [
                    bundle(draft_id, "DRAFT", "UNRESOLVED", False, "a"),
                    bundle(unresolved_id, "PUBLISHED", "UNRESOLVED", True, "b"),
                    bundle(eligible_id, "PUBLISHED", "APPROVED", True, "c"),
                ]
            )
            await session.commit()

        non_active_id = uuid4()
        async with factory() as session:
            session.add(
                SessionRecord(
                    session_id=non_active_id,
                    learner_id=learner_ids[0],
                    runtime_bundle_record_id=draft_id,
                    state="technical_failed",
                    row_version=0,
                    **provenance("b_session", non_active_id),
                )
            )
            await session.commit()

        rejected_draft_id = uuid4()
        async with factory() as session:
            async def insert_draft_directly() -> None:
                await session.execute(
                    text(
                        """
                        INSERT INTO b_sessions (
                            session_id, learner_id, runtime_bundle_record_id, state,
                            system_actor, request_id, operation_or_event_type, reason_code,
                            resource_type, resource_id, source_class, source_system,
                            environment, schema_revision
                        ) VALUES (
                            :session_id, :learner_id, :bundle_id, 'active',
                            'be2-corrective-test', 'direct-sql-draft', 'test.bundle_integrity',
                            'ISOLATED_SYNTHETIC_TEST', 'b_session', :session_id,
                            'TEST', 'be2-corrective-test-suite', 'test', '20260722_0003'
                        )
                        """
                    ),
                    {
                        "session_id": rejected_draft_id,
                        "learner_id": learner_ids[1],
                        "bundle_id": draft_id,
                    },
                )
                await session.commit()

            await expect_integrity_error(insert_draft_directly)
            await session.rollback()

        async with factory() as session:
            assert await session.get(SessionRecord, rejected_draft_id) is None

        rejected_unresolved_id = uuid4()
        async with factory() as session:
            session.add(
                SessionRecord(
                    session_id=rejected_unresolved_id,
                    learner_id=learner_ids[2],
                    runtime_bundle_record_id=unresolved_id,
                    state="active",
                    row_version=0,
                    **provenance("b_session", rejected_unresolved_id),
                )
            )

            async def insert_unresolved() -> None:
                await session.commit()

            await expect_integrity_error(insert_unresolved)
            await session.rollback()

        eligible_session_id = uuid4()
        async with factory() as session:
            session.add(
                SessionRecord(
                    session_id=eligible_session_id,
                    learner_id=learner_ids[3],
                    runtime_bundle_record_id=eligible_id,
                    state="active",
                    row_version=0,
                    **provenance("b_session", eligible_session_id),
                )
            )
            await session.commit()

        async with factory() as session:
            non_active = await session.get(SessionRecord, non_active_id)
            assert non_active is not None
            non_active.state = "active"

            async def activate_with_draft() -> None:
                await session.commit()

            await expect_integrity_error(activate_with_draft)
            await session.rollback()

        async with factory() as session:
            active = await session.get(SessionRecord, eligible_session_id)
            assert active is not None
            active.runtime_bundle_record_id = draft_id

            async def repoint_to_draft() -> None:
                await session.commit()

            await expect_integrity_error(repoint_to_draft)
            await session.rollback()

        async with factory() as session:
            eligible = await session.get(RuntimeBundleRecord, eligible_id)
            assert eligible is not None
            eligible.approval_status = "UNRESOLVED"

            async def revoke_active_bundle_approval() -> None:
                await session.commit()

            await expect_integrity_error(revoke_active_bundle_approval)
            await session.rollback()

        async with factory() as session:
            active = await session.get(SessionRecord, eligible_session_id)
            eligible = await session.get(RuntimeBundleRecord, eligible_id)
            assert active is not None and active.runtime_bundle_record_id == eligible_id
            assert eligible is not None and eligible.approval_status == "APPROVED"

        await database_engine.dispose()

    asyncio.run(exercise())


def test_published_immutable_bundle_checksum_cannot_change() -> None:
    alembic_upgrade()

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        draft_id, published_id = uuid4(), uuid4()
        async with factory() as session:
            session.add_all(
                [
                    bundle(draft_id, "DRAFT", "UNRESOLVED", False, "d"),
                    bundle(published_id, "PUBLISHED", "APPROVED", True, "e"),
                ]
            )
            await session.commit()

        async with factory() as session:
            await session.execute(
                text(
                    "UPDATE b_runtime_bundle_records SET manifest_checksum = :checksum "
                    "WHERE runtime_bundle_record_id = :bundle_id"
                ),
                {"checksum": "f" * 64, "bundle_id": draft_id},
            )
            await session.commit()

        async with factory() as session:
            await session.execute(
                text(
                    "UPDATE b_runtime_bundle_records SET manifest_checksum = manifest_checksum "
                    "WHERE runtime_bundle_record_id = :bundle_id"
                ),
                {"bundle_id": published_id},
            )
            await session.commit()

        async with factory() as session:
            async def mutate_published_directly() -> None:
                await session.execute(
                    text(
                        "UPDATE b_runtime_bundle_records SET manifest_checksum = :checksum "
                        "WHERE runtime_bundle_record_id = :bundle_id"
                    ),
                    {"checksum": "0" * 64, "bundle_id": published_id},
                )
                await session.commit()

            await expect_integrity_error(mutate_published_directly)
            await session.rollback()

        async with factory() as session:
            draft_checksum = await session.scalar(
                select(RuntimeBundleRecord.manifest_checksum).where(
                    RuntimeBundleRecord.runtime_bundle_record_id == draft_id
                )
            )
            published_checksum = await session.scalar(
                select(RuntimeBundleRecord.manifest_checksum).where(
                    RuntimeBundleRecord.runtime_bundle_record_id == published_id
                )
            )
            assert draft_checksum == "f" * 64
            assert published_checksum == "e" * 64

        await database_engine.dispose()

    asyncio.run(exercise())
