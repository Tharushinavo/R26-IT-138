"""BE4c (BEplan §9 BE4.3 + BE4.4) tests: migration cycle, server-side correctness evaluation,
first-attempt-only atomic BKT, replay/idempotency, concurrency, timeout, infra-failure handling,
and public-response privacy.

Every correctness/BKT assertion goes through
``app.infrastructure.live_engine.adapter.LiveEngineAdapter`` — no formula is reimplemented here.
Opportunities/task-instances are built directly through BE4a's
``OpportunityPersistenceService`` (as ``test_be4a_opportunity_persistence.py`` does), bypassing
BE4b's full adaptive-selection pipeline so these tests can pin a known ``correct_answer`` and
skill without depending on selection scoring.
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
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.application.attempt_submission import AttemptSubmissionService
from app.application.opportunity_persistence import OpportunityPersistenceService
from app.application.opportunity_selection import _ENGINEERING_BKT_CONFIG
from app.core.config import get_settings
from app.core.errors import ConflictError, TechnicalFailureError
from app.domain.b_attempt import AttemptResponse, SubmitResponseRequest
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
    SessionRecord,
    SkillStateTransitionRecord,
)
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


SKILL_ID = "addition"


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
        "system_actor": "be4c-isolated-test",
        "request_id": f"test-{uuid4()}",
        "operation_or_event_type": "test.be4c_attempt_submission",
        "reason_code": "ISOLATED_SYNTHETIC_TEST",
        "resource_type": resource_type,
        "resource_id": resource_id,
        "source_class": "TEST",
        "source_system": "be4c-isolated-test-suite",
        "environment": "test",
        "schema_revision": "20260728_0001",
    }


async def _seed_learner_session_and_skill_state(session: AsyncSession) -> tuple[UUID, UUID, UUID, str]:
    """Insert AppUser -> Learner -> link -> RuntimeBundleRecord -> active SessionRecord ->
    LearnerSkillStateRecord(skill=SKILL_ID). Returns (session_id, learner_id, bundle_id, subject)."""
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

    p_l0 = _ENGINEERING_BKT_CONFIG.skill_params[SKILL_ID].p_l0
    session.add(
        LearnerSkillStateRecord(
            learner_skill_state_id=uuid4(),
            learner_id=learner_id,
            skill_id=SKILL_ID,
            p_l=p_l0,
            observation_count=0,
            **provenance("b_learner_skill_state", uuid4()),
        )
    )
    await session.flush()
    return session_id, learner_id, bundle_id, subject


async def _open_opportunity(
    session: AsyncSession,
    *,
    session_id: UUID,
    learner_id: UUID,
    timeout: timedelta = timedelta(minutes=5),
    presented: bool = True,
) -> UUID:
    """Directly persists one OPEN opportunity + task instance with a known correct_answer
    ("7"), mirroring test_be4a_opportunity_persistence.py rather than exercising BE4b's
    full adaptive-selection pipeline.

    ``presented`` defaults to True because that is the ordinary state of a question a child is
    answering: the screen acknowledged presentation and the deadline was anchored to it. A timeout
    MEANS "was shown the question and did not answer in time", so a fixture that never marked
    presentation was not modelling a timeout at all -- it was modelling the failed-acknowledgement
    anomaly, which since 2026-10-10 is deliberately not treated as a timeout (see
    ``attempt_submission.py``'s own note). Pass ``presented=False`` to exercise THAT case."""
    persistence = OpportunityPersistenceService(session)
    opportunity = await persistence.open_opportunity(
        session_id=session_id,
        learner_id=learner_id,
        skill_id=SKILL_ID,
        item_template_id="B-ADD04-2D-NO-REGROUP",
        opportunity_index=1,
        selection_provenance={"winning_item_template_id": "B-ADD04-2D-NO-REGROUP", "score": 0.5},
        timeout=timeout,
        provenance=provenance("b_item_opportunity", uuid4()),
    )
    await persistence.create_task_instance(
        item_opportunity_id=opportunity.item_opportunity_id,
        item_template_id="B-ADD04-2D-NO-REGROUP",
        skill_id=SKILL_ID,
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
    if presented:
        # Anchored to the SAME instant the deadline was computed from, so a `timeout=0` fixture is
        # still immediately past its deadline and a five-minute one still has five minutes. This
        # marks the question as shown without moving the clock the fixture asked for.
        opportunity.presented_at_utc = opportunity.timeout_deadline_utc - timeout
        await session.flush()
    return opportunity.item_opportunity_id


async def _submit(
    service: AttemptSubmissionService,
    *,
    subject: str,
    session_id: UUID,
    item_opportunity_id: UUID,
    submitted_value: str,
    idempotency_key: str | None = None,
) -> AttemptResponse:
    principal = AuthenticatedPrincipal(user_id=subject, email="learner@example.test")
    return await service.submit_response(
        principal,
        session_id,
        item_opportunity_id,
        idempotency_key or f"key-{uuid4()}",
        f"req-{uuid4()}",
        SubmitResponseRequest(submitted_value=submitted_value, client_elapsed_ms=1500),
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
                assert {"b_attempts", "b_skill_state_transitions"} <= tables
                attempt_uniques = {uc["name"] for uc in inspector.get_unique_constraints("b_attempts")}
                assert "uq_b_attempts_opportunity_index" in attempt_uniques
                transition_uniques = {uc["name"] for uc in inspector.get_unique_constraints("b_skill_state_transitions")}
                assert "uq_b_skill_state_transitions_opportunity" in transition_uniques

            await connection.run_sync(assertions)
        await database_engine.dispose()

    asyncio.run(inspect_schema())

    alembic("downgrade", "20260727_0002")

    async def assert_dropped() -> None:
        database_engine, _ = isolated_database()
        async with database_engine.connect() as connection:
            def assertions(sync_connection) -> None:
                inspector = inspect(sync_connection)
                tables = set(inspector.get_table_names())
                assert not ({"b_attempts", "b_skill_state_transitions"} & tables)

            await connection.run_sync(assertions)
        await database_engine.dispose()

    asyncio.run(assert_dropped())
    alembic("upgrade", "head")


# ---------------------------------------------------------------------------
# Correctness (server-side, via adapter) + first-attempt-only atomic BKT
# ---------------------------------------------------------------------------


def test_correct_first_attempt_creates_exactly_one_transition_and_updates_skill_state() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            session_id, learner_id, _bundle_id, subject = await _seed_learner_session_and_skill_state(session)
            item_opportunity_id = await _open_opportunity(session, session_id=session_id, learner_id=learner_id)
            await session.commit()

        service = AttemptSubmissionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))
        response = await _submit(
            service, subject=subject, session_id=session_id, item_opportunity_id=item_opportunity_id, submitted_value="7"
        )
        assert response.attempt_index == 1
        assert response.event_kind == "RESPONSE"
        assert response.response_matched is True

        async with factory() as session:
            transitions = (
                await session.scalars(
                    select(SkillStateTransitionRecord).where(
                        SkillStateTransitionRecord.item_opportunity_id == item_opportunity_id
                    )
                )
            ).all()
            assert len(transitions) == 1
            transition = transitions[0]
            assert transition.response_matched is True
            assert transition.p_l_after > transition.p_l_before

            skill_state = await session.scalar(
                select(LearnerSkillStateRecord).where(
                    LearnerSkillStateRecord.learner_id == learner_id, LearnerSkillStateRecord.skill_id == SKILL_ID
                )
            )
            assert skill_state.observation_count == 1
            assert skill_state.p_l == pytest.approx(transition.p_l_after)

        await database_engine.dispose()

    asyncio.run(exercise())


def test_retry_after_wrong_first_attempt_creates_no_second_transition() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            session_id, learner_id, _bundle_id, subject = await _seed_learner_session_and_skill_state(session)
            item_opportunity_id = await _open_opportunity(session, session_id=session_id, learner_id=learner_id)
            await session.commit()

        service = AttemptSubmissionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))

        first = await _submit(
            service, subject=subject, session_id=session_id, item_opportunity_id=item_opportunity_id, submitted_value="6"
        )
        assert first.attempt_index == 1
        assert first.response_matched is False

        second = await _submit(
            service, subject=subject, session_id=session_id, item_opportunity_id=item_opportunity_id, submitted_value="7"
        )
        assert second.attempt_index == 2
        assert second.response_matched is True

        async with factory() as session:
            transitions = (
                await session.scalars(
                    select(SkillStateTransitionRecord).where(
                        SkillStateTransitionRecord.item_opportunity_id == item_opportunity_id
                    )
                )
            ).all()
            assert len(transitions) == 1
            assert transitions[0].response_matched is False  # from attempt 1, not attempt 2

            skill_state = await session.scalar(
                select(LearnerSkillStateRecord).where(
                    LearnerSkillStateRecord.learner_id == learner_id, LearnerSkillStateRecord.skill_id == SKILL_ID
                )
            )
            assert skill_state.observation_count == 1  # attempt 2 never incremented it

            attempts = (
                await session.scalars(
                    select(AttemptRecord).where(AttemptRecord.item_opportunity_id == item_opportunity_id)
                )
            ).all()
            assert len(attempts) == 2

        await database_engine.dispose()

    asyncio.run(exercise())


# ---------------------------------------------------------------------------
# Replay / idempotency
# ---------------------------------------------------------------------------


def test_replay_with_same_idempotency_key_returns_original_result_and_no_second_bkt_update() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            session_id, learner_id, _bundle_id, subject = await _seed_learner_session_and_skill_state(session)
            item_opportunity_id = await _open_opportunity(session, session_id=session_id, learner_id=learner_id)
            await session.commit()

        service = AttemptSubmissionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))
        key = f"replay-key-{uuid4()}"

        first = await _submit(
            service,
            subject=subject, session_id=session_id, item_opportunity_id=item_opportunity_id,
            submitted_value="7", idempotency_key=key,
        )
        second = await _submit(
            service,
            subject=subject, session_id=session_id, item_opportunity_id=item_opportunity_id,
            submitted_value="7", idempotency_key=key,
        )
        assert first == second

        async with factory() as session:
            attempts = (
                await session.scalars(
                    select(AttemptRecord).where(AttemptRecord.item_opportunity_id == item_opportunity_id)
                )
            ).all()
            assert len(attempts) == 1
            transitions = (
                await session.scalars(
                    select(SkillStateTransitionRecord).where(
                        SkillStateTransitionRecord.item_opportunity_id == item_opportunity_id
                    )
                )
            ).all()
            assert len(transitions) == 1

        await database_engine.dispose()

    asyncio.run(exercise())


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------


def test_concurrent_first_attempts_produce_exactly_one_transition() -> None:
    """The opportunity row is locked FOR UPDATE before attempt-index derivation, so two
    concurrent submissions serialize rather than truly race — one lands as attempt 1 (claims the
    unique first-attempt transition), the other as attempt 2 (never touches BKT state). Either
    ordering is acceptable; what must hold is exactly one transition and no lost/duplicated
    attempt index."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            session_id, learner_id, _bundle_id, subject = await _seed_learner_session_and_skill_state(session)
            item_opportunity_id = await _open_opportunity(session, session_id=session_id, learner_id=learner_id)
            await session.commit()

        service = AttemptSubmissionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))
        principal = AuthenticatedPrincipal(user_id=subject, email="learner@example.test")

        async def one_submission() -> AttemptResponse | Exception:
            try:
                return await service.submit_response(
                    principal, session_id, item_opportunity_id, f"concurrent-{uuid4()}", f"req-{uuid4()}",
                    SubmitResponseRequest(submitted_value="7"),
                )
            except Exception as exc:  # noqa: BLE001 - either racer may legitimately fail closed
                return exc

        results = await asyncio.gather(one_submission(), one_submission())
        successes = [r for r in results if isinstance(r, AttemptResponse)]
        failures = [r for r in results if isinstance(r, Exception)]
        for failure in failures:
            assert isinstance(failure, ConflictError)
        assert len(successes) + len(failures) == 2
        assert len(successes) >= 1
        assert len({r.attempt_index for r in successes}) == len(successes)  # no duplicate index

        async with factory() as session:
            transitions = (
                await session.scalars(
                    select(SkillStateTransitionRecord).where(
                        SkillStateTransitionRecord.item_opportunity_id == item_opportunity_id
                    )
                )
            ).all()
            assert len(transitions) == 1

        await database_engine.dispose()

    asyncio.run(exercise())


# ---------------------------------------------------------------------------
# Timeout
# ---------------------------------------------------------------------------


def test_expired_deadline_records_timeout_and_creates_no_bkt_observation() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            session_id, learner_id, _bundle_id, subject = await _seed_learner_session_and_skill_state(session)
            item_opportunity_id = await _open_opportunity(
                session, session_id=session_id, learner_id=learner_id, timeout=timedelta(seconds=0)
            )
            await session.commit()

        await asyncio.sleep(0.05)  # ensure now() >= the (effectively immediate) deadline

        service = AttemptSubmissionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))
        response = await _submit(
            service, subject=subject, session_id=session_id, item_opportunity_id=item_opportunity_id, submitted_value="7"
        )
        assert response.event_kind == "TIMEOUT"
        assert response.response_matched is None

        async with factory() as session:
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
            assert skill_state.observation_count == 0

            # BF-2: the learner's answer must be persisted even though it arrived after the
            # deadline — not compared (response_matched stays None, asserted above), but no longer
            # silently discarded. AttemptResponse itself never exposes submitted_value (it is not
            # part of the safe public DTO), so this is checked against the persisted row directly.
            attempt = await session.scalar(
                select(AttemptRecord).where(AttemptRecord.item_opportunity_id == item_opportunity_id)
            )
            assert attempt.submitted_value == "7"
            assert attempt.event_kind == "TIMEOUT"

        await database_engine.dispose()

    asyncio.run(exercise())


def test_an_unacknowledged_opportunity_is_never_judged_late() -> None:
    """OWNER REPORT, 2026-10-10: a child opened a Number Sense question, answered in about one
    second, and was shown "Time's up".

    The cause, from the live row: `presented_at_utc = NULL` -- no presentation acknowledgement ever
    landed -- so the deadline still in force was the FAIL-SAFE written at SELECTION. Home warms
    Component B on mount, so the opportunity had been minted minutes before the child entered, and
    on a degraded network all four acknowledgement attempts failed. The child was therefore judged
    against a clock that had been measuring prefetch and network time, on a question the system has
    no record of ever having shown them.

    This fixture is that exact shape: a long-expired deadline AND no acknowledgement. It must grade
    normally. `component-b-closure-decisions.json`'s timeout-policy ruling -- "infrastructure
    failure is never learner failure" -- is the authority, and `anchor_presentation` already quotes
    it for the sibling case.

    The negative control is the test above: an expired deadline WITH a confirmed presentation is
    still a TIMEOUT. Together they pin the distinction rather than just the new behaviour."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            session_id, learner_id, _bundle_id, subject = await _seed_learner_session_and_skill_state(session)
            item_opportunity_id = await _open_opportunity(
                session,
                session_id=session_id,
                learner_id=learner_id,
                timeout=timedelta(seconds=0),
                presented=False,
            )
            await session.commit()

        await asyncio.sleep(0.05)  # the deadline is now comfortably in the past

        service = AttemptSubmissionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))
        response = await _submit(
            service, subject=subject, session_id=session_id, item_opportunity_id=item_opportunity_id, submitted_value="7"
        )
        assert response.event_kind == "RESPONSE", "a question never shown cannot have been answered late"
        assert response.response_matched is True, "and a correct answer must actually be graded"

        async with factory() as session:
            attempt = await session.scalar(
                select(AttemptRecord).where(AttemptRecord.item_opportunity_id == item_opportunity_id)
            )
            assert attempt.event_kind == "RESPONSE"
            assert attempt.submitted_value == "7"

            # The null acknowledgement is LEFT null: it is the audit trail of why this submission
            # was not treated as late. Nothing here invents a presentation time.
            opportunity = await session.scalar(
                select(ItemOpportunityRecord).where(
                    ItemOpportunityRecord.item_opportunity_id == item_opportunity_id
                )
            )
            assert opportunity.presented_at_utc is None

            # GATE B CONSEQUENCE, asserted rather than described: this attempt now observes, where
            # as a TIMEOUT it would have contributed nothing. If the owner rules the other way,
            # this is the assertion that has to change.
            skill_state = await session.scalar(
                select(LearnerSkillStateRecord).where(
                    LearnerSkillStateRecord.learner_id == learner_id, LearnerSkillStateRecord.skill_id == SKILL_ID
                )
            )
            assert skill_state.observation_count == 1

        await database_engine.dispose()

    asyncio.run(exercise())


def test_timeout_submitted_value_matches_what_was_sent_not_the_correct_answer() -> None:
    """BF-2 regression guard, independent of the happy-path test above: the persisted value must
    be the learner's own submission, not silently coerced to the correct answer or left blank.
    Submits a value that does NOT match the correct answer ("7") to prove this isn't a passing
    accident of the fixture using the same string for both."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            session_id, learner_id, _bundle_id, subject = await _seed_learner_session_and_skill_state(session)
            item_opportunity_id = await _open_opportunity(
                session, session_id=session_id, learner_id=learner_id, timeout=timedelta(seconds=0)
            )
            await session.commit()

        await asyncio.sleep(0.05)

        service = AttemptSubmissionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))
        response = await _submit(
            service,
            subject=subject,
            session_id=session_id,
            item_opportunity_id=item_opportunity_id,
            submitted_value="banana",
        )
        assert response.event_kind == "TIMEOUT"
        assert response.response_matched is None

        async with factory() as session:
            attempt = await session.scalar(
                select(AttemptRecord).where(AttemptRecord.item_opportunity_id == item_opportunity_id)
            )
            assert attempt.submitted_value == "banana"

        await database_engine.dispose()

    asyncio.run(exercise())


# ---------------------------------------------------------------------------
# Infra failure != learner failure
# ---------------------------------------------------------------------------


class _FailAtCommitUnitOfWork(SqlAlchemyUnitOfWork):
    """Simulates a DB failure AFTER the BKT compute (attempt + transition + skill-state are
    already flushed in-transaction) but BEFORE commit — the whole transaction must roll back."""

    async def commit(self) -> None:
        raise SQLAlchemyError("simulated infra failure at commit")


def test_failure_after_bkt_compute_before_commit_rolls_back_everything() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            session_id, learner_id, _bundle_id, subject = await _seed_learner_session_and_skill_state(session)
            item_opportunity_id = await _open_opportunity(session, session_id=session_id, learner_id=learner_id)
            await session.commit()

        service = AttemptSubmissionService(uow_factory=partial(_FailAtCommitUnitOfWork, factory=factory))
        with pytest.raises(TechnicalFailureError):
            await _submit(
                service, subject=subject, session_id=session_id, item_opportunity_id=item_opportunity_id,
                submitted_value="7",
            )

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
            assert skill_state.observation_count == 0
            assert skill_state.p_l == pytest.approx(_ENGINEERING_BKT_CONFIG.skill_params[SKILL_ID].p_l0)

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


def test_public_attempt_response_contains_no_private_fields() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            session_id, learner_id, _bundle_id, subject = await _seed_learner_session_and_skill_state(session)
            item_opportunity_id = await _open_opportunity(session, session_id=session_id, learner_id=learner_id)
            await session.commit()

        service = AttemptSubmissionService(uow_factory=partial(SqlAlchemyUnitOfWork, factory=factory))
        response = await _submit(
            service, subject=subject, session_id=session_id, item_opportunity_id=item_opportunity_id, submitted_value="6"
        )
        public_dict = response.model_dump(mode="json")
        assert not (FORBIDDEN_PRIVATE_KEYS & set(public_dict))
        assert set(public_dict) == {
            "item_opportunity_id", "attempt_index", "event_kind", "response_matched",
            "server_submitted_at_utc", "request_id",
        }

        await database_engine.dispose()

    asyncio.run(exercise())
