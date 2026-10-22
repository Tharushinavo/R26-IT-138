"""GET /api/v1/b/learner/skill-states -- the learner's own per-skill BKT state, read-only.

Admitted by the 2026-09-21 product-owner ruling (app/domain/b_skill_state.py, buildLog2.md).
These prove the read is exactly as narrow as that ruling: the caller's own rows and nothing
else, never a write, and the same role boundary every other learner-facing B endpoint has.
"""

import asyncio
import subprocess
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.domain.principal import AuthenticatedPrincipal
from app.infrastructure.auth import get_authenticated_principal
from app.infrastructure.database import async_database_url
from app.infrastructure.persistence_models import AppUser, AppUserLearnerLink, Learner, LearnerSkillStateRecord
from app.main import app


SEVEN_SKILLS = ("counting", "number_sense", "place_value", "addition", "subtraction", "multiplication", "division")


def upgrade() -> None:
    subprocess.run(["alembic", "upgrade", "head"], check=True)


def isolated_database():
    database_engine = create_async_engine(async_database_url(get_settings().database_url), poolclass=NullPool)
    factory = async_sessionmaker(database_engine, expire_on_commit=False, class_=AsyncSession)
    return database_engine, factory


def provenance(resource_type: str, resource_id: UUID) -> dict[str, object]:
    return {
        "system_actor": "learner-skill-states-isolated-test",
        "request_id": f"test-{uuid4()}",
        "operation_or_event_type": "test.learner_skill_states",
        "reason_code": "ISOLATED_SYNTHETIC_TEST",
        "resource_type": resource_type,
        "resource_id": resource_id,
        "source_class": "TEST",
        "source_system": "learner-skill-states-isolated-test-suite",
        "environment": "test",
        "schema_revision": "20260914_0009",
    }


def client_for(subject: str) -> TestClient:
    app.dependency_overrides[get_authenticated_principal] = lambda: AuthenticatedPrincipal(
        user_id=subject, email="verified@example.test"
    )
    client = TestClient(app)
    client.__enter__()
    return client


def close_client(client: TestClient) -> None:
    client.__exit__(None, None, None)
    app.dependency_overrides.clear()


async def _seed_user(session: AsyncSession, profile_type: str) -> tuple[str, UUID]:
    subject = f"subject-{uuid4()}"
    user_id = uuid4()
    session.add(
        AppUser(user_id=user_id, supabase_subject=subject, status="active", profile_type=profile_type, **provenance("app_user", user_id))
    )
    await session.flush()
    return subject, user_id


async def _seed_learner(session: AsyncSession) -> tuple[str, UUID]:
    """LEARNER AppUser -> Learner -> link. Returns (subject, learner_id)."""
    subject, user_id = await _seed_user(session, "LEARNER")
    learner_id = uuid4()
    session.add(Learner(learner_id=learner_id, grade=2, status="active", **provenance("b_learner", learner_id)))
    await session.flush()
    link_id = uuid4()
    session.add(AppUserLearnerLink(link_id=link_id, user_id=user_id, learner_id=learner_id, **provenance("app_user_learner_link", link_id)))
    await session.flush()
    return subject, learner_id


async def _seed_skill_states(session: AsyncSession, learner_id: UUID, states: dict[str, tuple[float, int]]) -> None:
    for skill_id, (p_l, observation_count) in states.items():
        record_id = uuid4()
        session.add(
            LearnerSkillStateRecord(
                learner_skill_state_id=record_id,
                learner_id=learner_id,
                skill_id=skill_id,
                p_l=p_l,
                observation_count=observation_count,
                **provenance("b_learner_skill_state", record_id),
            )
        )
    await session.flush()


async def _skill_state_row_count(learner_id: UUID) -> int:
    engine, factory = isolated_database()
    async with factory() as session:
        count = await session.scalar(
            select(func.count()).select_from(LearnerSkillStateRecord).where(LearnerSkillStateRecord.learner_id == learner_id)
        )
    await engine.dispose()
    return count


def test_learner_sees_own_states_only_sorted_and_bounded() -> None:
    upgrade()

    async def seed() -> tuple[str, UUID, str]:
        engine, factory = isolated_database()
        async with factory() as session:
            subject, learner_id = await _seed_learner(session)
            other_subject, other_learner_id = await _seed_learner(session)
            await _seed_skill_states(
                session,
                learner_id,
                {"counting": (0.73, 12), "addition": (0.41, 3), "division": (0.2, 0)},
            )
            # A second learner's rows must never leak into the first's read.
            await _seed_skill_states(session, other_learner_id, {"counting": (0.99, 40)})
            await session.commit()
        await engine.dispose()
        return subject, learner_id, other_subject

    subject, learner_id, other_subject = asyncio.run(seed())

    client = client_for(subject)
    try:
        response = client.get("/api/v1/b/learner/skill-states")
        assert response.status_code == 200
        body = response.json()
        assert body["request_id"] == response.headers["X-Request-ID"]
        # Sorted by skill_id, nothing but the caller's rows, and exactly the three fields.
        assert [row["skill_id"] for row in body["skill_states"]] == ["addition", "counting", "division"]
        by_skill = {row["skill_id"]: row for row in body["skill_states"]}
        assert by_skill["counting"] == {"skill_id": "counting", "p_l": 0.73, "observation_count": 12}
        assert by_skill["division"] == {"skill_id": "division", "p_l": 0.2, "observation_count": 0}
        for row in body["skill_states"]:
            assert set(row) == {"skill_id", "p_l", "observation_count"}
            assert 0.0 <= row["p_l"] <= 1.0
    finally:
        close_client(client)

    other = client_for(other_subject)
    try:
        body = other.get("/api/v1/b/learner/skill-states").json()
        assert [row["skill_id"] for row in body["skill_states"]] == ["counting"]
        assert body["skill_states"][0]["p_l"] == 0.99
    finally:
        close_client(other)


def test_learner_with_no_history_gets_empty_list_and_the_read_never_writes() -> None:
    """A learner who has never started a Component B session has no rows: the response is an
    empty list, and -- unlike opportunity_selection.load_or_init_skill_states, which seeds the
    P(L0) priors as a side effect of session start -- this read must not create any."""
    upgrade()

    async def seed() -> tuple[str, UUID]:
        engine, factory = isolated_database()
        async with factory() as session:
            subject, learner_id = await _seed_learner(session)
            await session.commit()
        await engine.dispose()
        return subject, learner_id

    subject, learner_id = asyncio.run(seed())
    assert asyncio.run(_skill_state_row_count(learner_id)) == 0

    client = client_for(subject)
    try:
        for _ in range(2):
            response = client.get("/api/v1/b/learner/skill-states")
            assert response.status_code == 200
            assert response.json()["skill_states"] == []
    finally:
        close_client(client)

    assert asyncio.run(_skill_state_row_count(learner_id)) == 0


def test_role_boundary_teacher_forbidden_unknown_and_unlinked_not_found() -> None:
    upgrade()

    async def seed() -> tuple[str, str]:
        engine, factory = isolated_database()
        async with factory() as session:
            teacher_subject, _ = await _seed_user(session, "TEACHER")
            # A LEARNER-typed user with no learner link is the "profile not yet created" shape.
            unlinked_subject, _ = await _seed_user(session, "LEARNER")
            await session.commit()
        await engine.dispose()
        return teacher_subject, unlinked_subject

    teacher_subject, unlinked_subject = asyncio.run(seed())

    for subject, expected_status, expected_code in (
        (teacher_subject, 403, "FORBIDDEN"),
        (unlinked_subject, 404, "RESOURCE_NOT_FOUND"),
        (f"never-registered-{uuid4()}", 404, "RESOURCE_NOT_FOUND"),
    ):
        client = client_for(subject)
        try:
            response = client.get("/api/v1/b/learner/skill-states")
            assert response.status_code == expected_status, subject
            assert response.json()["error"]["code"] == expected_code
        finally:
            close_client(client)


def test_unauthenticated_is_401() -> None:
    upgrade()
    client = TestClient(app)
    response = client.get("/api/v1/b/learner/skill-states")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"
