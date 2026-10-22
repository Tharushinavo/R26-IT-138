"""Component D Phase 1 (Component D authorization, owner decision D-011): the three profiling
tables.

Covers the migration cycle, the constraints that carry meaning rather than typing, and -- most
importantly -- the two naming facts the authorization turns on. The guard tests themselves
(``test_be2_architecture_guards.py``) already assert the table set by exact equality; what they
cannot say is WHY these column names are what they are, which is what the last two tests here pin.
"""

import asyncio
import subprocess
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.infrastructure.database import async_database_url
from app.infrastructure.persistence_models import (
    AppUser,
    Base,
    DCognitiveProfileRecord,
    DInteractionRecord,
    DLearnerStateRecord,
    Learner,
)


D_TABLES = {"d_learner_state", "d_interactions", "d_cognitive_profiles"}


def alembic(*args: str) -> None:
    subprocess.run(["alembic", *args], check=True)


def isolated_database():
    engine = create_async_engine(async_database_url(get_settings().database_url), poolclass=NullPool)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def _seed_learner(session) -> tuple:
    """A learner and its app_user, the minimum every D row needs. Provenance values mirror the
    ones B's own tests use; `source_class="TEST"` is deliberate -- these rows are test fixtures
    and must never be mistaken for REAL ones in an audit."""
    user = AppUser(
        user_id=uuid4(),
        supabase_subject=f"d-test-{uuid4()}",
        status="ACTIVE",
        profile_type="LEARNER",
        request_id="req-d-test",
        operation_or_event_type="test.seed",
        reason_code="TEST_FIXTURE",
        resource_type="app_user",
        resource_id=uuid4(),
        source_class="TEST",
        source_system="pytest",
        environment="test",
        schema_revision="20261021_0010",
        system_actor="pytest",
    )
    session.add(user)
    await session.flush()
    learner = Learner(
        learner_id=uuid4(),
        status="ACTIVE",
        name="D Test Learner",
        request_id="req-d-test",
        operation_or_event_type="test.seed",
        reason_code="TEST_FIXTURE",
        resource_type="b_learner",
        resource_id=uuid4(),
        source_class="TEST",
        source_system="pytest",
        environment="test",
        schema_revision="20261021_0010",
        system_actor="pytest",
    )
    session.add(learner)
    await session.flush()
    return user, learner


def _provenance(resource_type: str) -> dict:
    return {
        "request_id": "req-d-test",
        "operation_or_event_type": "test.seed",
        "reason_code": "TEST_FIXTURE",
        "resource_type": resource_type,
        "resource_id": uuid4(),
        "source_class": "TEST",
        "source_system": "pytest",
        "environment": "test",
        "schema_revision": "20261021_0010",
        "system_actor": "pytest",
    }


def _interaction(learner_id, session_id, question_id: str) -> DInteractionRecord:
    return DInteractionRecord(
        learner_id=learner_id,
        session_id=session_id,
        question_id=question_id,
        topic="Counting",
        difficulty="Easy",
        response_time_sec=3.5,
        attempts=1,
        response_matched=True,
        assist_used=False,
        click_count=2,
        session_time_sec=30.0,
        time_between_actions=1.25,
        error_type="none",
        **_provenance("d_interaction"),
    )


def _profile(learner_id, session_id) -> DCognitiveProfileRecord:
    return DCognitiveProfileRecord(
        learner_id=learner_id,
        session_id=session_id,
        memory_level="medium",
        attention_level="high",
        number_sense_level="low",
        processing_speed_level="Moderate",
        confidence_score=0.72,
        model_version="rule-based-v1",
        features={"accuracy": 0.8, "total_questions": 10, "mean_clicks_per_question": 0.2},
        generated_at=datetime.now(UTC),
        **_provenance("d_cognitive_profile"),
    )


def test_migration_downgrade_reupgrade_cycle_and_schema() -> None:
    """The host's standard migration proof, applied to D: upgrade creates the three tables with
    their index, downgrade removes all three, and re-upgrade restores them. A migration that
    cannot be reversed is one nobody can roll back under pressure."""
    alembic("upgrade", "head")

    async def inspect_schema() -> None:
        database_engine, _ = isolated_database()
        async with database_engine.connect() as connection:
            def assertions(sync_connection) -> None:
                inspector = inspect(sync_connection)
                tables = set(inspector.get_table_names())
                assert D_TABLES <= tables
                profile_indexes = {ix["name"] for ix in inspector.get_indexes("d_cognitive_profiles")}
                assert "ix_d_cognitive_profiles_learner_generated_at" in profile_indexes
                interaction_uniques = {
                    uq["name"] for uq in inspector.get_unique_constraints("d_interactions")
                }
                assert "uq_d_interactions_session_question" in interaction_uniques

            await connection.run_sync(assertions)
        await database_engine.dispose()

    asyncio.run(inspect_schema())

    alembic("downgrade", "20260914_0009")

    async def assert_dropped() -> None:
        database_engine, _ = isolated_database()
        async with database_engine.connect() as connection:
            def assertions(sync_connection) -> None:
                inspector = inspect(sync_connection)
                assert not (D_TABLES & set(inspector.get_table_names()))

            await connection.run_sync(assertions)
        await database_engine.dispose()

    asyncio.run(assert_dropped())
    alembic("upgrade", "head")


def test_one_profile_per_session_and_one_interaction_per_question() -> None:
    """The two uniqueness rules the profile POST's idempotency rests on. Without them a retried
    submission (N-FE-003 re-sends the identical body) would write a second profile for the same
    run, and `GET /d/sessions/{session_id}/profile` would have two rows to choose between."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            _user, learner = await _seed_learner(session)
            session_id = uuid4()
            session.add(_interaction(learner.learner_id, session_id, "Q1"))
            session.add(_profile(learner.learner_id, session_id))
            await session.commit()

        async with factory() as session:
            session.add(_interaction(learner.learner_id, session_id, "Q1"))
            with pytest.raises(IntegrityError):
                await session.commit()

        async with factory() as session:
            # A DIFFERENT learner reusing the same session id must also fail: the profile's
            # uniqueness is GLOBAL, which is what lets a foreign session id be refused as a 404
            # instead of silently creating a second profile under someone else's name.
            _user2, learner2 = await _seed_learner(session)
            session.add(_profile(learner2.learner_id, session_id))
            with pytest.raises(IntegrityError):
                await session.commit()

        await database_engine.dispose()

    asyncio.run(exercise())


def test_check_constraints_refuse_out_of_domain_values() -> None:
    """Spot-checks that the CHECKs are real rather than decorative: a level outside its enum, a
    confidence score outside [0, 1], and a negative duration are each refused by the database,
    not merely by Pydantic. The API validates too; this is the backstop for anything that reaches
    the table by another route."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            _user, learner = await _seed_learner(session)
            await session.commit()
            learner_id = learner.learner_id

        async def refuses(mutate) -> None:
            async with factory() as session:
                record = _profile(learner_id, uuid4())
                mutate(record)
                session.add(record)
                with pytest.raises(IntegrityError):
                    await session.commit()

        # Both bad values are SHORT ENOUGH to reach the CHECK. An over-length value is rejected
        # by the column width first, which looks like a pass while testing nothing -- this test
        # did exactly that until the length was the thing that failed.
        await refuses(lambda r: setattr(r, "memory_level", "mid"))
        await refuses(lambda r: setattr(r, "processing_speed_level", "fast"))  # wrong case
        await refuses(lambda r: setattr(r, "confidence_score", 1.5))
        await refuses(lambda r: setattr(r, "model_version", ""))

        async with factory() as session:
            interaction = _interaction(learner_id, uuid4(), "Q-neg")
            interaction.response_time_sec = -1.0
            session.add(interaction)
            with pytest.raises(IntegrityError):
                await session.commit()

        async with factory() as session:
            interaction = _interaction(learner_id, uuid4(), "Q-zero-attempts")
            interaction.attempts = 0
            session.add(interaction)
            with pytest.raises(IntegrityError):
                await session.commit()

        await database_engine.dispose()

    asyncio.run(exercise())


def test_learner_state_language_is_constrained_and_intro_is_a_timestamp() -> None:
    """`intro_completed_at` is a timestamp, not a boolean: the public DTO derives
    `intro_completed` from IS NOT NULL. A boolean would answer "whether" and throw away "when"
    for no saving."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            _user, learner = await _seed_learner(session)
            state = DLearnerStateRecord(
                learner_id=learner.learner_id,
                intro_completed_at=None,
                language="si",
                **_provenance("d_learner_state"),
            )
            session.add(state)
            await session.commit()
            assert state.intro_completed_at is None
            learner_id = learner.learner_id

        async with factory() as session:
            bad = DLearnerStateRecord(
                learner_id=learner_id,
                intro_completed_at=datetime.now(UTC),
                language="fr",
                **_provenance("d_learner_state"),
            )
            session.add(bad)
            with pytest.raises(IntegrityError):
                await session.commit()

        await database_engine.dispose()

    asyncio.run(exercise())


# --- the authorization's naming decisions, pinned ------------------------------------------------


def test_no_d_column_carries_a_prohibited_term_and_no_exemption_exists() -> None:
    """THE AUTHORIZATION'S CENTRAL CLAIM, asserted rather than trusted.

    D-011 A5 states that no column exemption is granted, because the host already had names for
    both colliding concepts. That only holds if D's columns really are clean, so this checks every
    one of them against the live `PROHIBITED_COLUMN_TERMS` and requires the exemption sets to be
    untouched by D.

    If a future change reintroduces `is_correct` or `hint_used`, this fails HERE, with a message
    about the authorization -- rather than in the architecture guard, where the tempting fix is to
    add an exemption the owner never granted.
    """
    from tests.test_be2_architecture_guards import (
        AUTHORIZED_ANSWER_BEARING_COLUMNS,
        AUTHORIZED_C_COLUMN_EXCEPTIONS,
        PROHIBITED_COLUMN_TERMS,
    )

    offenders = {
        (table.name, column.name)
        for table in Base.metadata.tables.values()
        if table.name in D_TABLES
        for column in table.columns
        if any(term in column.name.lower() for term in PROHIBITED_COLUMN_TERMS)
    }
    assert not offenders, (
        "Component D columns must carry no prohibited term. D-011 A5 granted NO exemption, "
        f"so there is nothing to allow-list these: {offenders}"
    )

    exemptions = AUTHORIZED_ANSWER_BEARING_COLUMNS | AUTHORIZED_C_COLUMN_EXCEPTIONS
    assert not {pair for pair in exemptions if pair[0] in D_TABLES}, (
        "No Component D table may appear in an exemption set: the authorization granted none."
    )


def test_d_uses_the_hosts_own_names_for_correctness_and_assistance() -> None:
    """The positive half of the test above: D does not merely avoid the banned words, it uses the
    SAME names the host already uses for the same two concepts (`b_attempts.response_matched`,
    `b_hint_events.assist_*`). That is what makes the renames consistency rather than evasion --
    the distinction D-011 A4 rests on. If B ever renames its own column, this fails and the two
    are reconciled deliberately instead of drifting apart."""
    d_interactions = Base.metadata.tables["d_interactions"]
    b_attempts = Base.metadata.tables["b_attempts"]
    b_hint_events = Base.metadata.tables["b_hint_events"]

    assert "response_matched" in d_interactions.columns
    assert "response_matched" in b_attempts.columns, (
        "D took this name from b_attempts; if B renamed it, D's justification needs revisiting."
    )
    assert "assist_used" in d_interactions.columns
    assert any(name.startswith("assist_") for name in b_hint_events.columns.keys()), (
        "D's assist_used follows b_hint_events' assist_* convention; if that changed, revisit."
    )
    for banned in ("is_correct", "hint_used"):
        assert banned not in d_interactions.columns
