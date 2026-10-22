"""BE4b (BEplan §9 BE4.2) adaptive-selection tests: migration cycle, grade gate, frozen
weights, selection determinism, fail-closed (missing bundle / deferred template), one-open-
per-session, and public-response privacy.

Every scientific assertion below goes through ``app.infrastructure.live_engine.adapter.
LiveEngineAdapter`` — no formula is reimplemented here, only exercised and inspected.
"""

import asyncio
import hashlib
import subprocess
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

from app.application.opportunity_selection import (
    _B_SESSION_INDEX,
    _ENGINEERING_BKT_CONFIG,
    _ENGINEERING_TEST_BUNDLES,
    OpportunitySelectionService,
    build_task,
    package_item_opportunity_id,
    select_candidate,
)
from app.core.config import get_settings
from app.core.errors import ConflictError
from app.domain.b_opportunity import OpportunityPresentationResponse
from app.domain.principal import AuthenticatedPrincipal
from app.infrastructure.database import async_database_url
from app.infrastructure.live_engine.adapter import LiveEngineAdapter
from app.infrastructure.persistence_models import AppUser, AppUserLearnerLink, Learner, RuntimeBundleRecord, SessionRecord
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


ENGINEERING_BUNDLE_VERSION = "be3b-test-fixture-1.0"
_MANIFEST_PATH, _CATALOGUE_PATH = _ENGINEERING_TEST_BUNDLES[ENGINEERING_BUNDLE_VERSION]
DEFERRED_TEMPLATE_ID = "B-CNT05-FORWARD-FROM-N"  # DEFERRED_CALIBRATION_PENDING in the fixture catalogue


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
        "system_actor": "be4b-isolated-test",
        "request_id": f"test-{uuid4()}",
        "operation_or_event_type": "test.be4b_adaptive_selection",
        "reason_code": "ISOLATED_SYNTHETIC_TEST",
        "resource_type": resource_type,
        "resource_id": resource_id,
        "source_class": "TEST",
        "source_system": "be4b-isolated-test-suite",
        "environment": "test",
        "schema_revision": "20260727_0002",
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
            manifest_checksum=hashlib.sha256(b"be4b-engineering-test-bundle-db-stub").hexdigest(),
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


async def _seed_learner_and_session(session: AsyncSession, *, grade: int | None) -> tuple[UUID, UUID, str]:
    """Insert an authenticated LEARNER AppUser -> Learner -> link -> active SessionRecord pinned
    to the ENGINEERING_BUNDLE_VERSION fixture bundle. Returns (session_id, learner_id, subject)."""
    bundle_id = await _ensure_engineering_test_bundle(session)

    subject = f"subject-{uuid4()}"
    user_id = uuid4()
    session.add(
        AppUser(
            user_id=user_id,
            supabase_subject=subject,
            status="active",
            profile_type="LEARNER",
            **provenance("app_user", user_id),
        )
    )
    learner_id = uuid4()
    session.add(Learner(learner_id=learner_id, grade=grade, status="active", **provenance("b_learner", learner_id)))
    await session.flush()

    link_id = uuid4()
    session.add(
        AppUserLearnerLink(
            link_id=link_id, user_id=user_id, learner_id=learner_id, **provenance("app_user_learner_link", link_id)
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


def test_migration_downgrade_reupgrade_cycle_and_schema() -> None:
    alembic("upgrade", "head")

    async def inspect_schema() -> None:
        database_engine, _ = isolated_database()
        async with database_engine.connect() as connection:
            def assertions(sync_connection) -> None:
                inspector = inspect(sync_connection)
                tables = set(inspector.get_table_names())
                assert "b_learner_skill_states" in tables
                unique_constraints = {uc["name"] for uc in inspector.get_unique_constraints("b_learner_skill_states")}
                assert "uq_b_learner_skill_states_pair" in unique_constraints

            await connection.run_sync(assertions)
        await database_engine.dispose()

    asyncio.run(inspect_schema())

    alembic("downgrade", "20260727_0001")

    async def assert_dropped() -> None:
        database_engine, _ = isolated_database()
        async with database_engine.connect() as connection:
            def assertions(sync_connection) -> None:
                inspector = inspect(sync_connection)
                assert "b_learner_skill_states" not in set(inspector.get_table_names())

            await connection.run_sync(assertions)
        await database_engine.dispose()

    asyncio.run(assert_dropped())
    alembic("upgrade", "head")


# ---------------------------------------------------------------------------
# Grade gate (direct adapter-level, matching the BEplan §9 BE4.2 hard-gate requirement)
# ---------------------------------------------------------------------------


def test_grade_2_never_activates_multiplication_or_division() -> None:
    adapter = LiveEngineAdapter()
    catalogue = adapter.load(_CATALOGUE_PATH)
    supported = adapter.supported_template_ids()
    for template in catalogue.templates:
        if template.skill_id in ("multiplication", "division"):
            decision = adapter.decide_activation(catalogue, template.item_template_id, supported, grade=2)
            assert not decision.active, template.item_template_id
            assert not decision.grade_eligible, template.item_template_id


def test_grade_3_exposes_all_seven_skills() -> None:
    adapter = LiveEngineAdapter()
    catalogue = adapter.load(_CATALOGUE_PATH)
    supported = adapter.supported_template_ids()
    active_skills: set[str] = set()
    for template in catalogue.templates:
        decision = adapter.decide_activation(catalogue, template.item_template_id, supported, grade=3)
        if decision.active:
            active_skills.add(template.skill_id)
    assert active_skills == set(catalogue.skills)


def test_deferred_template_never_activates_for_any_grade() -> None:
    adapter = LiveEngineAdapter()
    catalogue = adapter.load(_CATALOGUE_PATH)
    supported = adapter.supported_template_ids()
    for grade in (2, 3):
        decision = adapter.decide_activation(catalogue, DEFERRED_TEMPLATE_ID, supported, grade=grade)
        assert not decision.active, (DEFERRED_TEMPLATE_ID, grade)


def test_full_selection_for_grade_2_learner_never_returns_multiplication_or_division() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            session_id, learner_id, subject = await _seed_learner_and_session(session, grade=2)
            await session.commit()

        service = OpportunitySelectionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))
        principal = AuthenticatedPrincipal(user_id=subject, email="learner@example.test")
        response = await service.select_next_opportunity(principal, session_id, f"req-{uuid4()}")
        assert response.skill_id not in ("multiplication", "division")

        await database_engine.dispose()

    asyncio.run(exercise())


# ---------------------------------------------------------------------------
# Frozen weights + determinism (pure functions, no DB)
# ---------------------------------------------------------------------------


def test_selection_uses_the_frozen_0_50_0_30_0_20_weights() -> None:
    adapter = LiveEngineAdapter()
    catalogue = adapter.load(_CATALOGUE_PATH)
    mastery = {skill: 0.2 for skill in catalogue.skills}

    result = select_candidate(
        adapter=adapter, catalogue=catalogue, bkt_config=_ENGINEERING_BKT_CONFIG, grade=3, mastery=mastery
    )
    reason = result.selection_reason
    expected = 0.50 * reason.mastery_gap + 0.30 * reason.prerequisite_readiness + 0.20 * reason.spacing_due
    assert reason.score == pytest.approx(expected)


def test_selection_is_deterministic_under_fixed_identity() -> None:
    adapter = LiveEngineAdapter()
    catalogue = adapter.load(_CATALOGUE_PATH)
    catalogue_checksum = adapter.checksum(_CATALOGUE_PATH)
    mastery = {skill: 0.2 for skill in catalogue.skills}

    first_selection = select_candidate(
        adapter=adapter, catalogue=catalogue, bkt_config=_ENGINEERING_BKT_CONFIG, grade=3, mastery=mastery
    )
    second_selection = select_candidate(
        adapter=adapter, catalogue=catalogue, bkt_config=_ENGINEERING_BKT_CONFIG, grade=3, mastery=mastery
    )
    assert first_selection == second_selection

    kwargs = dict(
        adapter=adapter,
        catalogue=catalogue,
        catalogue_checksum=catalogue_checksum,
        selection=first_selection,
        student_id="STU-BE4B-DETERMINISM",
        grade=3,
        item_opportunity_id=package_item_opportunity_id(uuid4(), _B_SESSION_INDEX, 1),
        opportunity_index=1,
        global_seed=20260728,
    )
    first_task = build_task(**kwargs)
    second_task = build_task(**kwargs)
    assert first_task == second_task


# ---------------------------------------------------------------------------
# Fail-closed
# ---------------------------------------------------------------------------


def test_fails_closed_when_session_bundle_is_not_an_engineering_test_bundle() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            unresolved_bundle_id = uuid4()
            session.add(
                RuntimeBundleRecord(
                    runtime_bundle_record_id=unresolved_bundle_id,
                    bundle_version=f"unmapped-bundle-{unresolved_bundle_id}",
                    manifest_checksum=hashlib.sha256(str(unresolved_bundle_id).encode()).hexdigest(),
                    publication_state="PUBLISHED",
                    approval_status="APPROVED",
                    immutable_after_publication=True,
                    **provenance("b_runtime_bundle_record", unresolved_bundle_id),
                )
            )
            await session.flush()

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
            link_id = uuid4()
            session.add(
                AppUserLearnerLink(
                    link_id=link_id, user_id=user_id, learner_id=learner_id,
                    **provenance("app_user_learner_link", link_id),
                )
            )
            session_id = uuid4()
            session.add(
                SessionRecord(
                    session_id=session_id, learner_id=learner_id, runtime_bundle_record_id=unresolved_bundle_id,
                    state="active", expires_at_utc=None, row_version=0,
                    **provenance("b_session", session_id),
                )
            )
            await session.commit()

        service = OpportunitySelectionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))
        principal = AuthenticatedPrincipal(user_id=subject, email="learner@example.test")
        with pytest.raises(ConflictError):
            await service.select_next_opportunity(principal, session_id, f"req-{uuid4()}")

        await database_engine.dispose()

    asyncio.run(exercise())


def test_one_open_opportunity_per_session_resumes_the_same_opportunity_on_a_second_select() -> None:
    """BE4e (BEplan §9 BE4.6 step 6) changed this from a hard reject to a resumable re-fetch: a
    second select while one opportunity is still OPEN must recover app restart / a retried
    network call / a stale presentation token by returning the *same* opportunity (fresh token,
    no duplicate row) rather than raising ``ConflictError``. The DB-level one-open-per-session
    invariant (``uq_b_item_opportunities_one_open_per_session``) is still what makes this safe —
    see ``tests/test_be4e_session_completion.py`` for the dedicated recovery tests."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            session_id, learner_id, subject = await _seed_learner_and_session(session, grade=3)
            await session.commit()

        service = OpportunitySelectionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))
        principal = AuthenticatedPrincipal(user_id=subject, email="learner@example.test")
        first = await service.select_next_opportunity(principal, session_id, f"req-{uuid4()}")
        assert first.item_opportunity_id

        second = await service.select_next_opportunity(principal, session_id, f"req-{uuid4()}")
        assert second.item_opportunity_id == first.item_opportunity_id
        assert second.presentation_token != first.presentation_token

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
    "generated_operands",
    "generation_seed",
    "applied_guard_ids",
    "catalogue_version",
    "catalogue_checksum",
    "selection_provenance",
    "mastery_gap",
    "prerequisite_readiness",
    "spacing_due",
    "score",
    "tie_broken",
    "tie_break_basis",
    "p_l",
    "theta_b",
}


def test_public_selection_response_contains_no_private_fields() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            session_id, learner_id, subject = await _seed_learner_and_session(session, grade=3)
            await session.commit()

        service = OpportunitySelectionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))
        principal = AuthenticatedPrincipal(user_id=subject, email="learner@example.test")
        response = await service.select_next_opportunity(principal, session_id, f"req-{uuid4()}")

        assert isinstance(response, OpportunityPresentationResponse)
        public_dict = response.model_dump(mode="json")
        assert not (FORBIDDEN_PRIVATE_KEYS & set(public_dict))
        assert public_dict["presentation_token"]
        assert public_dict["server_timeout_deadline_utc"]

        await database_engine.dispose()

    asyncio.run(exercise())
