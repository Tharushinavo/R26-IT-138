"""BE4e (BEplan §9 BE4.6) tests: migration cycle, next-or-complete atomicity, reuse-determinism
of session aggregation/Guess-Guard/certification via the adapter, SAFE-standing privacy, no
extra BKT observation on completion, replay/idempotency, and recovery (resumable re-fetch of an
OPEN opportunity; stale-token fail-closed).

Every attempt/BKT step below goes through the real BE4c/BE4b services (``AttemptSubmissionService``
/``OpportunitySelectionService``) rather than hand-inserted rows, so the session-aggregation input
this module builds is the same shape production would produce. Aggregation/Guess-Guard/
certification themselves are asserted only through
``app.infrastructure.live_engine.adapter.LiveEngineAdapter`` — no formula is reimplemented here.
"""

import asyncio
import hashlib
import subprocess
from datetime import UTC, datetime, timedelta
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

import app.application.session_completion as session_completion_module
from app.application.attempt_submission import AttemptSubmissionService
from app.application.opportunity_selection import _ENGINEERING_TEST_BUNDLES, OpportunitySelectionService
from app.application.opportunity_persistence import OpportunityPersistenceService
from app.application.session_completion import SessionCompletionService
from app.core.config import get_settings
from app.core.errors import ConflictError
from app.domain.b_completion import OpportunityAdvanceResponse, SessionStandingResponse
from app.domain.b_opportunity import PresentationTokenNotFoundError
from app.domain.principal import AuthenticatedPrincipal
from app.infrastructure.database import async_database_url
from app.infrastructure.persistence_models import (
    AppUser,
    AppUserLearnerLink,
    AttemptRecord,
    ItemOpportunityRecord,
    Learner,
    LearnerSkillStateRecord,
    RuntimeBundleRecord,
    SessionAggregateResultRecord,
    SessionRecord,
    SkillCertificationResultRecord,
    SkillStateTransitionRecord,
    TaskInstanceRecord,
)
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


ENGINEERING_BUNDLE_VERSION = "be3b-test-fixture-1.0"
_MANIFEST_PATH, _CATALOGUE_PATH = _ENGINEERING_TEST_BUNDLES[ENGINEERING_BUNDLE_VERSION]


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
        "system_actor": "be4e-isolated-test",
        "request_id": f"test-{uuid4()}",
        "operation_or_event_type": "test.be4e_session_completion",
        "reason_code": "ISOLATED_SYNTHETIC_TEST",
        "resource_type": resource_type,
        "resource_id": resource_id,
        "source_class": "TEST",
        "source_system": "be4e-isolated-test-suite",
        "environment": "test",
        "schema_revision": "20260728_0003",
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
            manifest_checksum=hashlib.sha256(b"be4e-engineering-test-bundle-db-stub").hexdigest(),
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


def _principal(subject: str) -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(user_id=subject, email="learner@example.test")


async def _select_opportunity(service: OpportunitySelectionService, *, subject: str, session_id: UUID):
    return await service.select_next_opportunity(_principal(subject), session_id, f"req-{uuid4()}")


async def _submit_correct_first_attempt(
    factory, service: AttemptSubmissionService, *, subject: str, session_id: UUID, item_opportunity_id: UUID
):
    async with factory() as session:
        task_instance = await session.scalar(
            select(TaskInstanceRecord).where(TaskInstanceRecord.item_opportunity_id == item_opportunity_id)
        )
        correct_answer = task_instance.correct_answer

    from app.domain.b_attempt import SubmitResponseRequest

    return await service.submit_response(
        _principal(subject),
        session_id,
        item_opportunity_id,
        f"key-{uuid4()}",
        f"req-{uuid4()}",
        SubmitResponseRequest(submitted_value=correct_answer, client_elapsed_ms=1200),
    )


async def _complete_and_advance(
    service: SessionCompletionService,
    *,
    subject: str,
    session_id: UUID,
    item_opportunity_id: UUID,
    idempotency_key: str | None = None,
) -> OpportunityAdvanceResponse:
    return await service.complete_and_advance(
        _principal(subject), session_id, item_opportunity_id, idempotency_key or f"key-{uuid4()}", f"req-{uuid4()}"
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
                assert {"b_session_aggregate_results", "b_skill_certification_results"} <= tables
                aggregate_uniques = {uc["name"] for uc in inspector.get_unique_constraints("b_session_aggregate_results")}
                assert "uq_b_session_aggregate_results_session" in aggregate_uniques
                certification_uniques = {
                    uc["name"] for uc in inspector.get_unique_constraints("b_skill_certification_results")
                }
                assert "uq_b_skill_certification_results_session_skill" in certification_uniques

            await connection.run_sync(assertions)
        await database_engine.dispose()

    asyncio.run(inspect_schema())

    alembic("downgrade", "20260728_0002")

    async def assert_dropped() -> None:
        database_engine, _ = isolated_database()
        async with database_engine.connect() as connection:
            def assertions(sync_connection) -> None:
                inspector = inspect(sync_connection)
                tables = set(inspector.get_table_names())
                assert not ({"b_session_aggregate_results", "b_skill_certification_results"} & tables)

            await connection.run_sync(assertions)
        await database_engine.dispose()

    asyncio.run(assert_dropped())
    alembic("upgrade", "head")


# ---------------------------------------------------------------------------
# Next-or-complete, atomic
# ---------------------------------------------------------------------------


def test_complete_below_bound_closes_current_and_opens_exactly_one_next_opportunity() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            session_id, learner_id, subject = await _seed_learner_and_session(session)
            await session.commit()

        selection_service = OpportunitySelectionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))
        attempt_service = AttemptSubmissionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))
        completion_service = SessionCompletionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))

        first = await _select_opportunity(selection_service, subject=subject, session_id=session_id)
        first_opportunity_id = UUID(first.item_opportunity_id)
        await _submit_correct_first_attempt(
            factory, attempt_service, subject=subject, session_id=session_id, item_opportunity_id=first_opportunity_id
        )

        response = await _complete_and_advance(
            completion_service, subject=subject, session_id=session_id, item_opportunity_id=first_opportunity_id
        )
        assert response.session_state == "active"
        assert response.opportunities_completed == 1
        assert response.next_opportunity is not None
        assert UUID(response.next_opportunity.item_opportunity_id) != first_opportunity_id

        async with factory() as session:
            rows = (
                await session.scalars(select(ItemOpportunityRecord).where(ItemOpportunityRecord.session_id == session_id))
            ).all()
            assert len(rows) == 2
            states = {row.item_opportunity_id: row.state for row in rows}
            assert states[first_opportunity_id] == "CLOSED"
            open_rows = [row for row in rows if row.state == "OPEN"]
            assert len(open_rows) == 1

            session_row = await session.get(SessionRecord, session_id)
            assert session_row.state == "active"

        await database_engine.dispose()

    asyncio.run(exercise())


def test_complete_at_bound_completes_session_and_persists_aggregate_and_certification_privately() -> None:
    alembic("upgrade", "head")
    original_bound = session_completion_module.MAX_OPPORTUNITIES_PER_SESSION
    session_completion_module.MAX_OPPORTUNITIES_PER_SESSION = 1
    try:

        async def exercise() -> None:
            database_engine, factory = isolated_database()
            async with factory() as session:
                session_id, learner_id, subject = await _seed_learner_and_session(session)
                await session.commit()

            selection_service = OpportunitySelectionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))
            attempt_service = AttemptSubmissionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))
            completion_service = SessionCompletionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))

            first = await _select_opportunity(selection_service, subject=subject, session_id=session_id)
            first_opportunity_id = UUID(first.item_opportunity_id)
            attempt = await _submit_correct_first_attempt(
                factory, attempt_service, subject=subject, session_id=session_id, item_opportunity_id=first_opportunity_id
            )
            assert attempt.response_matched is True

            async with factory() as session:
                transition = await session.scalar(
                    select(SkillStateTransitionRecord).where(
                        SkillStateTransitionRecord.item_opportunity_id == first_opportunity_id
                    )
                )
                assert transition is not None
                skill_id = transition.skill_id

            response = await _complete_and_advance(
                completion_service, subject=subject, session_id=session_id, item_opportunity_id=first_opportunity_id
            )
            assert response.session_state == "completed"
            assert response.next_opportunity is None
            assert response.opportunities_completed == 1
            assert response.opportunities_total_bound == 1

            async with factory() as session:
                session_row = await session.get(SessionRecord, session_id)
                assert session_row.state == "completed"

                aggregate = await session.scalar(
                    select(SessionAggregateResultRecord).where(SessionAggregateResultRecord.session_id == session_id)
                )
                assert aggregate is not None
                assert aggregate.opportunity_count == 1
                assert aggregate.first_attempt_match_rate == 1.0
                assert aggregate.completion_count == 1
                assert aggregate.completion_rate == 1.0
                assert aggregate.total_retry_count == 0
                assert aggregate.completion_policy_version == session_completion_module.COMPLETION_POLICY_VERSION

                certification = await session.scalar(
                    select(SkillCertificationResultRecord).where(
                        SkillCertificationResultRecord.session_id == session_id,
                        SkillCertificationResultRecord.skill_id == skill_id,
                    )
                )
                assert certification is not None
                assert certification.opportunity_count == 1
                assert certification.attempt_count == 1
                assert certification.first_attempt_match_count == 1
                assert certification.skill_estimate is not None
                # Guess-Guard needs >= floor_min_obs (5) valid RTs (the TEST_FIXTURE_ONLY BKT
                # config); a single opportunity's one RT sample is below that, so the frozen
                # 3-valued rule reports INSUFFICIENT_EVIDENCE (never fabricated NOT_TRIGGERED),
                # and certify_skill's frozen rule (both TRIGGERED and INSUFFICIENT_EVIDENCE block)
                # withholds certification.
                assert certification.plausibility_status == "INSUFFICIENT_EVIDENCE"
                assert certification.threshold_met_flag is False

            await database_engine.dispose()

        asyncio.run(exercise())
    finally:
        session_completion_module.MAX_OPPORTUNITIES_PER_SESSION = original_bound


def test_advance_requires_at_least_one_attempt() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            session_id, learner_id, subject = await _seed_learner_and_session(session)
            await session.commit()

        selection_service = OpportunitySelectionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))
        completion_service = SessionCompletionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))

        first = await _select_opportunity(selection_service, subject=subject, session_id=session_id)
        first_opportunity_id = UUID(first.item_opportunity_id)

        with pytest.raises(ConflictError):
            await _complete_and_advance(
                completion_service, subject=subject, session_id=session_id, item_opportunity_id=first_opportunity_id
            )

        await database_engine.dispose()

    asyncio.run(exercise())


def test_completion_creates_no_additional_bkt_transition_or_observation() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            session_id, learner_id, subject = await _seed_learner_and_session(session)
            await session.commit()

        selection_service = OpportunitySelectionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))
        attempt_service = AttemptSubmissionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))
        completion_service = SessionCompletionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))

        first = await _select_opportunity(selection_service, subject=subject, session_id=session_id)
        first_opportunity_id = UUID(first.item_opportunity_id)
        await _submit_correct_first_attempt(
            factory, attempt_service, subject=subject, session_id=session_id, item_opportunity_id=first_opportunity_id
        )

        async with factory() as session:
            before_count = len(
                (await session.scalars(select(SkillStateTransitionRecord))).all()
            )

        await _complete_and_advance(
            completion_service, subject=subject, session_id=session_id, item_opportunity_id=first_opportunity_id
        )

        async with factory() as session:
            after_count = len(
                (await session.scalars(select(SkillStateTransitionRecord))).all()
            )
        assert after_count == before_count

        await database_engine.dispose()

    asyncio.run(exercise())


# ---------------------------------------------------------------------------
# Replay / idempotency
# ---------------------------------------------------------------------------


def test_replay_with_same_idempotency_key_returns_same_response_without_second_effect() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            session_id, learner_id, subject = await _seed_learner_and_session(session)
            await session.commit()

        selection_service = OpportunitySelectionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))
        attempt_service = AttemptSubmissionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))
        completion_service = SessionCompletionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))

        first = await _select_opportunity(selection_service, subject=subject, session_id=session_id)
        first_opportunity_id = UUID(first.item_opportunity_id)
        await _submit_correct_first_attempt(
            factory, attempt_service, subject=subject, session_id=session_id, item_opportunity_id=first_opportunity_id
        )

        key = f"replay-key-{uuid4()}"
        one = await _complete_and_advance(
            completion_service,
            subject=subject, session_id=session_id, item_opportunity_id=first_opportunity_id, idempotency_key=key,
        )
        two = await _complete_and_advance(
            completion_service,
            subject=subject, session_id=session_id, item_opportunity_id=first_opportunity_id, idempotency_key=key,
        )
        assert one == two

        async with factory() as session:
            rows = (
                await session.scalars(select(ItemOpportunityRecord).where(ItemOpportunityRecord.session_id == session_id))
            ).all()
            assert len(rows) == 2  # replay opened no second "next" opportunity

        await database_engine.dispose()

    asyncio.run(exercise())


# ---------------------------------------------------------------------------
# Recovery: resumable re-fetch of an OPEN opportunity; stale-token fail-closed
# ---------------------------------------------------------------------------


def test_reselecting_with_an_open_opportunity_returns_the_same_opportunity_not_a_duplicate() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            session_id, learner_id, subject = await _seed_learner_and_session(session)
            await session.commit()

        selection_service = OpportunitySelectionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))

        first = await _select_opportunity(selection_service, subject=subject, session_id=session_id)
        # Simulate app restart / retried network call: select again with no attempt in between.
        second = await _select_opportunity(selection_service, subject=subject, session_id=session_id)

        assert first.item_opportunity_id == second.item_opportunity_id
        assert first.presentation_token != second.presentation_token  # fresh token, same opportunity

        async with factory() as session:
            rows = (
                await session.scalars(select(ItemOpportunityRecord).where(ItemOpportunityRecord.session_id == session_id))
            ).all()
            assert len(rows) == 1  # no duplicate opportunity was created

        await database_engine.dispose()

    asyncio.run(exercise())


def test_stale_presentation_token_fails_closed_and_clean_reselect_succeeds() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            session_id, learner_id, subject = await _seed_learner_and_session(session)
            await session.commit()

        selection_service = OpportunitySelectionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))
        first = await _select_opportunity(selection_service, subject=subject, session_id=session_id)
        item_opportunity_id = UUID(first.item_opportunity_id)

        async with factory() as session:
            with pytest.raises(PresentationTokenNotFoundError):
                await OpportunityPersistenceService(session).validate_presentation_token(
                    "not-a-real-token",
                    session_id=session_id,
                    item_opportunity_id=item_opportunity_id,
                    learner_id=learner_id,
                )

        # A stale/unknown token fails closed; a clean re-select still recovers the same,
        # still-OPEN opportunity rather than duplicating it.
        second = await _select_opportunity(selection_service, subject=subject, session_id=session_id)
        assert second.item_opportunity_id == first.item_opportunity_id

        async with factory() as session:
            rows = (
                await session.scalars(select(ItemOpportunityRecord).where(ItemOpportunityRecord.session_id == session_id))
            ).all()
            assert len(rows) == 1

        await database_engine.dispose()

    asyncio.run(exercise())


# ---------------------------------------------------------------------------
# SAFE-progress privacy
# ---------------------------------------------------------------------------

FORBIDDEN_PRIVATE_KEYS = {
    "p_l", "p_l_before", "p_l_after", "predicted_probability", "posterior_p_l",
    "skill_estimate", "certified", "threshold_met_flag", "plausibility_status",
    "correct_answer", "allowed_equivalent_answers", "selection_provenance",
    "theta_b", "guard_status",
}


def test_public_advance_and_standing_responses_contain_no_private_fields() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            session_id, learner_id, subject = await _seed_learner_and_session(session)
            await session.commit()

        selection_service = OpportunitySelectionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))
        attempt_service = AttemptSubmissionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))
        completion_service = SessionCompletionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))

        first = await _select_opportunity(selection_service, subject=subject, session_id=session_id)
        first_opportunity_id = UUID(first.item_opportunity_id)
        await _submit_correct_first_attempt(
            factory, attempt_service, subject=subject, session_id=session_id, item_opportunity_id=first_opportunity_id
        )
        advance = await _complete_and_advance(
            completion_service, subject=subject, session_id=session_id, item_opportunity_id=first_opportunity_id
        )
        advance_dict = advance.model_dump(mode="json")
        assert not (FORBIDDEN_PRIVATE_KEYS & set(advance_dict))
        assert set(advance_dict) == {
            "item_opportunity_id", "session_state", "opportunities_completed",
            "opportunities_total_bound", "next_opportunity", "request_id",
        }
        if advance_dict["next_opportunity"] is not None:
            assert not (FORBIDDEN_PRIVATE_KEYS & set(advance_dict["next_opportunity"]))

        standing = await completion_service.get_session_standing(_principal(subject), session_id, f"req-{uuid4()}")
        assert isinstance(standing, SessionStandingResponse)
        standing_dict = standing.model_dump(mode="json")
        assert not (FORBIDDEN_PRIVATE_KEYS & set(standing_dict))
        assert set(standing_dict) == {
            "session_id", "session_state", "opportunities_completed", "opportunities_total_bound", "request_id",
        }

        await database_engine.dispose()

    asyncio.run(exercise())


# ---------------------------------------------------------------------------
# BF-1: Guess-Guard wiring - the floor must come from PRIOR sessions, never this session's own
# sample. Before this fix, TRIGGERED was mathematically unreachable for any input: the floor
# (q=0.1) and the current session's own median (q=0.5) were computed from the identical
# current-session-only sample, and a quantile function is monotonically non-decreasing in q, so
# median < floor could never hold. See session_completion.py's BF-1 docstring at the call site
# and repositories.py's prior_session_first_attempt_rts docstring for the full reasoning.
# ---------------------------------------------------------------------------

_GUARD_SKILL_ID = "addition"
_GUARD_TEMPLATE_ID = "B-ADD04-2D-NO-REGROUP"


async def _seed_skill_state(session: AsyncSession, learner_id: UUID, *, p_l: float) -> None:
    session.add(
        LearnerSkillStateRecord(
            learner_skill_state_id=uuid4(),
            learner_id=learner_id,
            skill_id=_GUARD_SKILL_ID,
            p_l=p_l,
            observation_count=0,
            **provenance("b_learner_skill_state", uuid4()),
        )
    )
    await session.flush()


async def _open_pinned_opportunity(session: AsyncSession, *, session_id: UUID, learner_id: UUID) -> UUID:
    """Direct construction via BE4a OpportunityPersistenceService, bypassing BE4b adaptive
    selection - mirrors test_be4c_attempt_submission.py _open_opportunity so these Guess-Guard
    fixtures can pin a known skill/template without depending on selection scoring."""
    persistence = OpportunityPersistenceService(session)
    opportunity = await persistence.open_opportunity(
        session_id=session_id,
        learner_id=learner_id,
        skill_id=_GUARD_SKILL_ID,
        item_template_id=_GUARD_TEMPLATE_ID,
        opportunity_index=1,
        selection_provenance={"winning_item_template_id": _GUARD_TEMPLATE_ID, "score": 0.5},
        timeout=timedelta(minutes=5),
        provenance=provenance("b_item_opportunity", uuid4()),
    )
    await persistence.create_task_instance(
        item_opportunity_id=opportunity.item_opportunity_id,
        item_template_id=_GUARD_TEMPLATE_ID,
        skill_id=_GUARD_SKILL_ID,
        grade=3,
        difficulty_level="L1",
        representation_type="NUMERIC",
        response_format="MULTIPLE_CHOICE",
        prompt={"text": "3 + 4 = ?"},
        correct_answer="7",
        allowed_equivalent_answers=("7", "+7"),
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


async def _seed_prior_session_response(
    session: AsyncSession, bundle_id: UUID, learner_id: UUID, *, created_at_utc: datetime, client_elapsed_ms: int
) -> None:
    """A CLOSED prior session with one first-attempt RESPONSE for _GUARD_SKILL_ID, at an explicit
    past created_at_utc. Direct construction only - prior_session_first_attempt_rts reads
    Attempt/Opportunity/Session rows alone, never skill-state or BKT, so these fixtures do not
    need real adaptive selection or a real submission-service call to be faithful."""
    prior_session_id = uuid4()
    session.add(
        SessionRecord(
            session_id=prior_session_id,
            learner_id=learner_id,
            runtime_bundle_record_id=bundle_id,
            state="completed",
            expires_at_utc=None,
            row_version=0,
            created_at_utc=created_at_utc,
            **provenance("b_session", prior_session_id),
        )
    )
    await session.flush()

    item_opportunity_id = await _open_pinned_opportunity(session, session_id=prior_session_id, learner_id=learner_id)

    attempt_id = uuid4()
    session.add(
        AttemptRecord(
            attempt_id=attempt_id,
            item_opportunity_id=item_opportunity_id,
            learner_id=learner_id,
            attempt_index=1,
            event_kind="RESPONSE",
            submitted_value="7",
            response_matched=True,
            client_elapsed_ms=client_elapsed_ms,
            server_submitted_at_utc=created_at_utc,
            **provenance("b_attempt", attempt_id),
        )
    )
    await session.flush()


async def _seed_guard_learner(session: AsyncSession, *, p_l: float) -> tuple[UUID, UUID, UUID, str]:
    """Learner + skill-state (pinned p_l, bypassing real BKT convergence - this fixture tests the
    Guess-Guard wiring, not BKT convergence, which is covered elsewhere) + a fresh active session
    for the caller to attach a real, current-session attempt to."""
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
    await _seed_skill_state(session, learner_id, p_l=p_l)

    current_session_id = uuid4()
    session.add(
        SessionRecord(
            session_id=current_session_id,
            learner_id=learner_id,
            runtime_bundle_record_id=bundle_id,
            state="active",
            expires_at_utc=None,
            row_version=0,
            **provenance("b_session", current_session_id),
        )
    )
    await session.flush()
    return bundle_id, learner_id, current_session_id, subject


def test_guess_guard_triggers_with_sufficient_prior_history_and_fast_current_median() -> None:
    """The single most important assertion in BF-1. Before the fix this was mathematically
    impossible for any input whatsoever, not merely rare. p_l0=0.2, p_t=0.15, p_g=0.2, p_s=0.1
    (the TEST_FIXTURE_ONLY config): starting p_l=0.6 with one correct response yields
    p_l_after approximately 0.89, comfortably above theta_b=0.8."""
    alembic("upgrade", "head")
    original_bound = session_completion_module.MAX_OPPORTUNITIES_PER_SESSION
    session_completion_module.MAX_OPPORTUNITIES_PER_SESSION = 1
    try:

        async def exercise() -> None:
            database_engine, factory = isolated_database()
            async with factory() as session:
                bundle_id, learner_id, current_session_id, subject = await _seed_guard_learner(session, p_l=0.6)
                now = datetime.now(UTC)
                for i in range(5):
                    await _seed_prior_session_response(
                        session, bundle_id, learner_id,
                        created_at_utc=now - timedelta(days=5 - i),
                        client_elapsed_ms=3000,  # normal speed: 3s, comfortably above any plausible floor
                    )
                current_opportunity_id = await _open_pinned_opportunity(
                    session, session_id=current_session_id, learner_id=learner_id
                )
                await session.commit()

            attempt_service = AttemptSubmissionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))
            completion_service = SessionCompletionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))

            from app.domain.b_attempt import SubmitResponseRequest

            attempt = await attempt_service.submit_response(
                _principal(subject), current_session_id, current_opportunity_id,
                f"key-{uuid4()}", f"req-{uuid4()}",
                SubmitResponseRequest(submitted_value="7", client_elapsed_ms=50),  # 0.05s: implausibly fast
            )
            assert attempt.response_matched is True

            response = await _complete_and_advance(
                completion_service, subject=subject, session_id=current_session_id,
                item_opportunity_id=current_opportunity_id,
            )
            assert response.session_state == "completed"

            async with factory() as session:
                certification = await session.scalar(
                    select(SkillCertificationResultRecord).where(
                        SkillCertificationResultRecord.session_id == current_session_id,
                        SkillCertificationResultRecord.skill_id == _GUARD_SKILL_ID,
                    )
                )
                assert certification is not None
                assert certification.skill_estimate > 0.8, "precondition: mastery must exceed theta_b"
                assert certification.plausibility_status == "TRIGGERED"
                # certify_skill's frozen rule: TRIGGERED blocks certification even with p_l > theta_b.
                assert certification.threshold_met_flag is False

            await database_engine.dispose()

        asyncio.run(exercise())
    finally:
        session_completion_module.MAX_OPPORTUNITIES_PER_SESSION = original_bound


def test_guess_guard_insufficient_evidence_without_prior_session_history() -> None:
    """No prior sessions at all (a first-time learner) must yield INSUFFICIENT_EVIDENCE, never a
    fabricated floor and never TRIGGERED, even with mastery above theta_b and an implausibly fast
    current-session response. This is also the cleanest proof that the current session's own fast
    RT cannot leak into being used as its own floor: if it could, this exact setup (fast current
    response, nothing else) would produce a false TRIGGERED instead of the honest
    INSUFFICIENT_EVIDENCE."""
    alembic("upgrade", "head")
    original_bound = session_completion_module.MAX_OPPORTUNITIES_PER_SESSION
    session_completion_module.MAX_OPPORTUNITIES_PER_SESSION = 1
    try:

        async def exercise() -> None:
            database_engine, factory = isolated_database()
            async with factory() as session:
                _bundle_id, learner_id, current_session_id, subject = await _seed_guard_learner(session, p_l=0.6)
                current_opportunity_id = await _open_pinned_opportunity(
                    session, session_id=current_session_id, learner_id=learner_id
                )
                await session.commit()

            attempt_service = AttemptSubmissionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))
            completion_service = SessionCompletionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))

            from app.domain.b_attempt import SubmitResponseRequest

            await attempt_service.submit_response(
                _principal(subject), current_session_id, current_opportunity_id,
                f"key-{uuid4()}", f"req-{uuid4()}",
                SubmitResponseRequest(submitted_value="7", client_elapsed_ms=50),
            )
            await _complete_and_advance(
                completion_service, subject=subject, session_id=current_session_id,
                item_opportunity_id=current_opportunity_id,
            )

            async with factory() as session:
                certification = await session.scalar(
                    select(SkillCertificationResultRecord).where(
                        SkillCertificationResultRecord.session_id == current_session_id,
                        SkillCertificationResultRecord.skill_id == _GUARD_SKILL_ID,
                    )
                )
                assert certification is not None
                assert certification.skill_estimate > 0.8
                assert certification.plausibility_status == "INSUFFICIENT_EVIDENCE"
                assert certification.threshold_met_flag is False

            await database_engine.dispose()

        asyncio.run(exercise())
    finally:
        session_completion_module.MAX_OPPORTUNITIES_PER_SESSION = original_bound


def test_guess_guard_not_triggered_with_normal_speed_response_and_sufficient_prior_history() -> None:
    """Sufficient prior history and mastery above theta_b, but a NORMAL-speed current response
    (not implausibly fast) must be NOT_TRIGGERED. Isolates "fast response" as the necessary
    condition, distinct from merely having enough history."""
    alembic("upgrade", "head")
    original_bound = session_completion_module.MAX_OPPORTUNITIES_PER_SESSION
    session_completion_module.MAX_OPPORTUNITIES_PER_SESSION = 1
    try:

        async def exercise() -> None:
            database_engine, factory = isolated_database()
            async with factory() as session:
                bundle_id, learner_id, current_session_id, subject = await _seed_guard_learner(session, p_l=0.6)
                now = datetime.now(UTC)
                for i in range(5):
                    await _seed_prior_session_response(
                        session, bundle_id, learner_id,
                        created_at_utc=now - timedelta(days=5 - i),
                        client_elapsed_ms=3000,
                    )
                current_opportunity_id = await _open_pinned_opportunity(
                    session, session_id=current_session_id, learner_id=learner_id
                )
                await session.commit()

            attempt_service = AttemptSubmissionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))
            completion_service = SessionCompletionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))

            from app.domain.b_attempt import SubmitResponseRequest

            await attempt_service.submit_response(
                _principal(subject), current_session_id, current_opportunity_id,
                f"key-{uuid4()}", f"req-{uuid4()}",
                SubmitResponseRequest(submitted_value="7", client_elapsed_ms=3200),  # normal speed
            )
            await _complete_and_advance(
                completion_service, subject=subject, session_id=current_session_id,
                item_opportunity_id=current_opportunity_id,
            )

            async with factory() as session:
                certification = await session.scalar(
                    select(SkillCertificationResultRecord).where(
                        SkillCertificationResultRecord.session_id == current_session_id,
                        SkillCertificationResultRecord.skill_id == _GUARD_SKILL_ID,
                    )
                )
                assert certification is not None
                assert certification.skill_estimate > 0.8
                assert certification.plausibility_status == "NOT_TRIGGERED"
                # certify_skill's frozen rule: p_l > theta_b AND NOT_TRIGGERED certifies.
                assert certification.threshold_met_flag is True

            await database_engine.dispose()

        asyncio.run(exercise())
    finally:
        session_completion_module.MAX_OPPORTUNITIES_PER_SESSION = original_bound
