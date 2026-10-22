"""BE4d (BEplan §9 BE4.5) tests: migration cycle, governed L1/L2/L3 hint escalation, fail-closed
catalogue lookup, replay/idempotency, hint-never-a-BKT-observation, and public-response privacy.

Every hint-content assertion goes through
``app.infrastructure.live_engine.adapter.LiveEngineAdapter.get_hint`` — no content is synthesized
here. Opportunities/task-instances are built directly through BE4a's
``OpportunityPersistenceService`` (as ``test_be4c_attempt_submission.py`` does), pinned to the
same BE3b TEST-provenance DRAFT fixture bundle BE4b's tests use so the hint route can resolve a
real catalogue.
"""

import asyncio
import hashlib
import subprocess
from datetime import timedelta
from functools import partial
from uuid import UUID, uuid4

import pytest

pytest.importorskip(
    "component_b_generator",
    reason="upadya-component-b-live-engine is not installed; see backend/requirements.in",
)

from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.application.hint_request import HintRequestService
from app.application.opportunity_persistence import OpportunityPersistenceService
from app.application.opportunity_selection import _ENGINEERING_TEST_BUNDLES
from app.core.config import get_settings
from app.core.errors import ConflictError
from app.domain.b_hint import HintRequestResponse
from app.domain.principal import AuthenticatedPrincipal
from app.infrastructure.database import async_database_url
from app.infrastructure.persistence_models import (
    AppUser,
    AppUserLearnerLink,
    AttemptRecord,
    HintEventRecord,
    Learner,
    LearnerSkillStateRecord,
    RuntimeBundleRecord,
    SessionRecord,
    SkillStateTransitionRecord,
)
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


ENGINEERING_BUNDLE_VERSION = "be3b-test-fixture-1.0"
_MANIFEST_PATH, _CATALOGUE_PATH = _ENGINEERING_TEST_BUNDLES[ENGINEERING_BUNDLE_VERSION]
SKILL_ID = "addition"
HINT_BEARING_TEMPLATE_ID = "B-ADD04-2D-NO-REGROUP"  # carries hint_level_1/2/3 in the fixture catalogue
# Every one of the fixture catalogue's 36 templates now carries governed L1/L2/L3 text, so there is
# no longer a real template that exercises the missing-content path. Absence is constructed
# explicitly with an id the catalogue does not contain, which `behaviour/hints.py` documents as a
# fail-closed path ("unknown item_template_id"). The guarantee under test is unchanged: content
# that cannot be produced raises, and is never synthesized or approximated.
NO_HINT_TEMPLATE_ID = "B-NOT-A-REAL-TEMPLATE"


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
        "system_actor": "be4d-isolated-test",
        "request_id": f"test-{uuid4()}",
        "operation_or_event_type": "test.be4d_hint_events",
        "reason_code": "ISOLATED_SYNTHETIC_TEST",
        "resource_type": resource_type,
        "resource_id": resource_id,
        "source_class": "TEST",
        "source_system": "be4d-isolated-test-suite",
        "environment": "test",
        "schema_revision": "20260728_0002",
    }


async def _ensure_engineering_test_bundle(session: AsyncSession) -> UUID:
    existing = await session.scalar(
        select(RuntimeBundleRecord).where(RuntimeBundleRecord.bundle_version == ENGINEERING_BUNDLE_VERSION)
    )
    if existing is not None:
        return existing.runtime_bundle_record_id
    bundle_id = uuid4()
    session.add(
        RuntimeBundleRecord(
            runtime_bundle_record_id=bundle_id,
            bundle_version=ENGINEERING_BUNDLE_VERSION,
            manifest_checksum=hashlib.sha256(b"be4d-engineering-test-bundle-db-stub").hexdigest(),
            publication_state="PUBLISHED",
            approval_status="APPROVED",
            immutable_after_publication=True,
            **provenance("b_runtime_bundle_record", bundle_id),
        )
    )
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        existing = await session.scalar(
            select(RuntimeBundleRecord).where(RuntimeBundleRecord.bundle_version == ENGINEERING_BUNDLE_VERSION)
        )
        assert existing is not None
        return existing.runtime_bundle_record_id
    return bundle_id


async def _seed_learner_and_session(session: AsyncSession) -> tuple[UUID, UUID, str]:
    bundle_id = await _ensure_engineering_test_bundle(session)

    subject = f"subject-{uuid4()}"
    user_id = uuid4()
    session.add(
        AppUser(
            user_id=user_id, supabase_subject=subject, status="active", profile_type="LEARNER",
            **provenance("app_user", user_id),
        )
    )
    learner_id = uuid4()
    session.add(Learner(learner_id=learner_id, grade=3, status="active", **provenance("b_learner", learner_id)))
    await session.flush()

    session.add(
        AppUserLearnerLink(
            link_id=uuid4(), user_id=user_id, learner_id=learner_id, **provenance("app_user_learner_link", uuid4())
        )
    )

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
    return session_id, learner_id, subject


async def _open_opportunity(
    session: AsyncSession, *, session_id: UUID, learner_id: UUID, item_template_id: str, skill_id: str = SKILL_ID
) -> UUID:
    persistence = OpportunityPersistenceService(session)
    opportunity = await persistence.open_opportunity(
        session_id=session_id,
        learner_id=learner_id,
        skill_id=skill_id,
        item_template_id=item_template_id,
        opportunity_index=1,
        selection_provenance={"winning_item_template_id": item_template_id, "score": 0.5},
        timeout=timedelta(minutes=5),
        provenance=provenance("b_item_opportunity", uuid4()),
    )
    await persistence.create_task_instance(
        item_opportunity_id=opportunity.item_opportunity_id,
        item_template_id=item_template_id,
        skill_id=skill_id,
        grade=3,
        difficulty_level="L1",
        representation_type="NUMERIC",
        response_format="MULTIPLE_CHOICE",
        prompt={"text": "3 + 4 = ?"},
        correct_answer="7",
        allowed_equivalent_answers=("7",),
        distractor_candidates=("6", "8"),
        distractor_rule_ids=("off_by_one_low", "off_by_one_high"),
        generated_operands={"a": 3, "b": 4},
        generation_seed=123456789,
        applied_guard_ids=(),
        catalogue_version="catalogue-2026.1",
        catalogue_checksum="b" * 64,
        provenance=provenance("b_task_instance", uuid4()),
    )
    return opportunity.item_opportunity_id


async def _request_hint(
    service: HintRequestService,
    *,
    subject: str,
    session_id: UUID,
    item_opportunity_id: UUID,
    idempotency_key: str | None = None,
) -> HintRequestResponse:
    principal = AuthenticatedPrincipal(user_id=subject, email="learner@example.test")
    return await service.request_hint(
        principal, session_id, item_opportunity_id, idempotency_key or f"key-{uuid4()}", f"req-{uuid4()}"
    )


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------


def test_migration_downgrade_reupgrade_cycle_and_schema() -> None:
    alembic("upgrade", "head")

    async def inspect_schema() -> None:
        database_engine, _ = isolated_database()
        async with database_engine.connect() as connection:
            def assertions(sync_connection) -> None:
                inspector = inspect(sync_connection)
                tables = set(inspector.get_table_names())
                assert "b_hint_events" in tables
                uniques = {uc["name"] for uc in inspector.get_unique_constraints("b_hint_events")}
                assert "uq_b_hint_events_opportunity_level" in uniques

            await connection.run_sync(assertions)
        await database_engine.dispose()

    asyncio.run(inspect_schema())

    alembic("downgrade", "20260728_0001")

    async def assert_dropped() -> None:
        database_engine, _ = isolated_database()
        async with database_engine.connect() as connection:
            def assertions(sync_connection) -> None:
                inspector = inspect(sync_connection)
                assert "b_hint_events" not in set(inspector.get_table_names())

            await connection.run_sync(assertions)
        await database_engine.dispose()

    asyncio.run(assert_dropped())
    alembic("upgrade", "head")


# ---------------------------------------------------------------------------
# Governed L1 -> L2 -> L3 escalation
# ---------------------------------------------------------------------------


def test_first_hint_request_returns_l1_and_persists_one_event() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            session_id, learner_id, subject = await _seed_learner_and_session(session)
            item_opportunity_id = await _open_opportunity(
                session, session_id=session_id, learner_id=learner_id, item_template_id=HINT_BEARING_TEMPLATE_ID
            )
            await session.commit()

        service = HintRequestService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))
        response = await _request_hint(
            service, subject=subject, session_id=session_id, item_opportunity_id=item_opportunity_id
        )
        assert response.hint_level == 1
        # Verbatim from R26-IT-138 §11 (the fixture previously carried fixture-authored text).
        assert response.content == "Add ones with ones and tens with tens."

        async with factory() as session:
            events = (
                await session.scalars(
                    select(HintEventRecord).where(HintEventRecord.item_opportunity_id == item_opportunity_id)
                )
            ).all()
            assert len(events) == 1
            assert events[0].assist_level == 1
            assert events[0].content_id == f"{HINT_BEARING_TEMPLATE_ID}::hint_l1"

        await database_engine.dispose()

    asyncio.run(exercise())


def test_sequential_requests_escalate_l1_l2_l3_then_refuse() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            session_id, learner_id, subject = await _seed_learner_and_session(session)
            item_opportunity_id = await _open_opportunity(
                session, session_id=session_id, learner_id=learner_id, item_template_id=HINT_BEARING_TEMPLATE_ID
            )
            await session.commit()

        service = HintRequestService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))

        first = await _request_hint(service, subject=subject, session_id=session_id, item_opportunity_id=item_opportunity_id)
        second = await _request_hint(service, subject=subject, session_id=session_id, item_opportunity_id=item_opportunity_id)
        third = await _request_hint(service, subject=subject, session_id=session_id, item_opportunity_id=item_opportunity_id)
        assert [first.hint_level, second.hint_level, third.hint_level] == [1, 2, 3]
        assert third.content == "Add each place separately, then combine tens and ones."

        with pytest.raises(ConflictError):
            await _request_hint(service, subject=subject, session_id=session_id, item_opportunity_id=item_opportunity_id)

        async with factory() as session:
            events = (
                await session.scalars(
                    select(HintEventRecord).where(HintEventRecord.item_opportunity_id == item_opportunity_id)
                )
            ).all()
            assert len(events) == 3
            assert sorted(event.assist_level for event in events) == [1, 2, 3]

        await database_engine.dispose()

    asyncio.run(exercise())


# ---------------------------------------------------------------------------
# Replay / idempotency
# ---------------------------------------------------------------------------


def test_replay_with_same_idempotency_key_returns_same_level_without_escalating() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            session_id, learner_id, subject = await _seed_learner_and_session(session)
            item_opportunity_id = await _open_opportunity(
                session, session_id=session_id, learner_id=learner_id, item_template_id=HINT_BEARING_TEMPLATE_ID
            )
            await session.commit()

        service = HintRequestService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))
        key = f"replay-key-{uuid4()}"

        first = await _request_hint(
            service, subject=subject, session_id=session_id, item_opportunity_id=item_opportunity_id, idempotency_key=key
        )
        second = await _request_hint(
            service, subject=subject, session_id=session_id, item_opportunity_id=item_opportunity_id, idempotency_key=key
        )
        assert first == second
        assert first.hint_level == 1

        async with factory() as session:
            events = (
                await session.scalars(
                    select(HintEventRecord).where(HintEventRecord.item_opportunity_id == item_opportunity_id)
                )
            ).all()
            assert len(events) == 1  # replay created no second event, no escalation

        await database_engine.dispose()

    asyncio.run(exercise())


# ---------------------------------------------------------------------------
# Fail-closed catalogue lookup — never synthesized, never leaks the answer
# ---------------------------------------------------------------------------


def test_absent_catalogue_hint_content_fails_closed() -> None:
    """Fail-closed coverage for absent hint content, via the real service path.

    NOTE: no catalogue template exercises the missing-content path any more — all 36 now carry
    governed L1/L2/L3 text. ``NO_HINT_TEMPLATE_ID`` is therefore an id the catalogue does not
    contain, rather than a real template that happens to lack hints. Coverage of the guarantee is
    unchanged and deliberately retained: the lookup raises a neutral ConflictError, leaks nothing,
    and persists no hint event.
    """
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            session_id, learner_id, subject = await _seed_learner_and_session(session)
            item_opportunity_id = await _open_opportunity(
                session,
                session_id=session_id,
                learner_id=learner_id,
                item_template_id=NO_HINT_TEMPLATE_ID,
                skill_id="counting",
            )
            await session.commit()

        service = HintRequestService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))
        with pytest.raises(ConflictError) as exc_info:
            await _request_hint(service, subject=subject, session_id=session_id, item_opportunity_id=item_opportunity_id)
        # Fail-closed and neutral: no answer/hint content leaked via the error itself.
        assert "7" not in str(exc_info.value)

        async with factory() as session:
            events = (
                await session.scalars(
                    select(HintEventRecord).where(HintEventRecord.item_opportunity_id == item_opportunity_id)
                )
            ).all()
            assert events == []  # the failed lookup persisted nothing

        await database_engine.dispose()

    asyncio.run(exercise())


# ---------------------------------------------------------------------------
# A hint request is never a mastery/BKT observation
# ---------------------------------------------------------------------------


def test_hint_request_creates_no_attempt_or_bkt_transition_and_no_skill_state() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            session_id, learner_id, subject = await _seed_learner_and_session(session)
            item_opportunity_id = await _open_opportunity(
                session, session_id=session_id, learner_id=learner_id, item_template_id=HINT_BEARING_TEMPLATE_ID
            )
            await session.commit()

        service = HintRequestService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))
        await _request_hint(service, subject=subject, session_id=session_id, item_opportunity_id=item_opportunity_id)
        await _request_hint(service, subject=subject, session_id=session_id, item_opportunity_id=item_opportunity_id)

        async with factory() as session:
            attempts = (
                await session.scalars(
                    select(AttemptRecord).where(AttemptRecord.item_opportunity_id == item_opportunity_id)
                )
            ).all()
            assert attempts == []
            transitions = (
                await session.scalars(
                    select(SkillStateTransitionRecord).where(
                        SkillStateTransitionRecord.item_opportunity_id == item_opportunity_id
                    )
                )
            ).all()
            assert transitions == []
            skill_state = await session.scalar(
                select(LearnerSkillStateRecord).where(
                    LearnerSkillStateRecord.learner_id == learner_id, LearnerSkillStateRecord.skill_id == SKILL_ID
                )
            )
            assert skill_state is None  # BE4d never initializes or touches learner skill state

        await database_engine.dispose()

    asyncio.run(exercise())


# ---------------------------------------------------------------------------
# Privacy
# ---------------------------------------------------------------------------

FORBIDDEN_PRIVATE_KEYS = {
    "correct_answer",
    "allowed_equivalent_answers",
    "distractor_candidates",
    "distractor_rule_ids",
    "p_l",
    "p_l_before",
    "p_l_after",
    "predicted_probability",
    "posterior_p_l",
    "theta_b",
}


def test_public_hint_response_contains_no_private_fields() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            session_id, learner_id, subject = await _seed_learner_and_session(session)
            item_opportunity_id = await _open_opportunity(
                session, session_id=session_id, learner_id=learner_id, item_template_id=HINT_BEARING_TEMPLATE_ID
            )
            await session.commit()

        service = HintRequestService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))
        response = await _request_hint(
            service, subject=subject, session_id=session_id, item_opportunity_id=item_opportunity_id
        )
        public_dict = response.model_dump(mode="json")
        assert not (FORBIDDEN_PRIVATE_KEYS & set(public_dict))
        assert set(public_dict) == {
            "item_opportunity_id", "hint_level", "content", "content_id",
            "catalogue_version", "catalogue_checksum", "request_id",
        }

        await database_engine.dispose()

    asyncio.run(exercise())
