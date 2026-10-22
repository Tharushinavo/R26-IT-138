"""Isolated endpoint tests for the limited profile and classroom batch."""

import asyncio
import subprocess
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.domain.principal import AuthenticatedPrincipal
from app.infrastructure.auth import get_authenticated_principal
from app.infrastructure.database import async_database_url
from app.infrastructure.persistence_models import AppUser, AuditEvent, Classroom, Learner
from app.main import app


def upgrade() -> None:
    subprocess.run(["alembic", "upgrade", "head"], check=True)


def client_for(subject: str, email: str = "verified@example.test") -> TestClient:
    app.dependency_overrides[get_authenticated_principal] = lambda: AuthenticatedPrincipal(user_id=subject, email=email)
    client = TestClient(app)
    client.__enter__()
    return client


def close_client(client: TestClient) -> None:
    client.__exit__(None, None, None)
    app.dependency_overrides.clear()


def post_headers(key: str) -> dict[str, str]:
    return {"Idempotency-Key": key, "X-Request-ID": f"req-{uuid4()}"}


def test_teacher_profile_create_retrieve_idempotency_and_role_boundary() -> None:
    upgrade()
    client = client_for(f"teacher-{uuid4()}")
    key = str(uuid4())
    try:
        created = client.post("/api/v1/teacher/profile", json={"name": "  Teacher One  "}, headers=post_headers(key))
        assert created.status_code == 201
        assert set(created.json()) == {"teacher_profile_id", "user_id", "profile_type", "name", "email", "created_at_utc", "request_id"}
        assert created.json()["profile_type"] == "TEACHER" and created.json()["name"] == "Teacher One"
        replay = client.post("/api/v1/teacher/profile", json={"name": "Teacher One"}, headers=post_headers(key))
        assert replay.status_code == 201 and replay.json()["teacher_profile_id"] == created.json()["teacher_profile_id"]
        assert client.post("/api/v1/teacher/profile", json={"name": "Different"}, headers=post_headers(key)).status_code == 409
        assert client.get("/api/v1/teacher/profile").status_code == 200
        assert client.get("/api/v1/learner/profile").status_code == 403
        assert client.post("/api/v1/learner/profile", json={"name": "No"}, headers=post_headers(str(uuid4()))).status_code == 409
    finally:
        close_client(client)


def test_learner_profile_reuses_b_learners_and_rejects_extra_grade() -> None:
    upgrade()
    subject = f"learner-{uuid4()}"
    client = client_for(subject)
    try:
        assert client.post("/api/v1/learner/profile", json={"name": "Learner", "grade": "GRADE_2"}, headers=post_headers(str(uuid4()))).status_code == 422
        created = client.post("/api/v1/learner/profile", json={"name": "Learner One"}, headers=post_headers(str(uuid4())))
        assert created.status_code == 201
        assert set(created.json()) == {"learner_id", "user_id", "profile_type", "name", "email", "created_at_utc", "request_id"}
        assert client.get("/api/v1/learner/profile").status_code == 200
        assert client.get("/api/v1/teacher/profile").status_code == 403

        async def inspect_row() -> None:
            engine = create_async_engine(async_database_url(get_settings().database_url), poolclass=NullPool)
            factory = async_sessionmaker(engine, expire_on_commit=False)
            async with factory() as session:
                user = await session.scalar(select(AppUser).where(AppUser.supabase_subject == subject))
                learner = await session.get(Learner, UUID(created.json()["learner_id"]))
                assert user is not None and user.profile_type == "LEARNER"
                assert learner is not None and learner.name == "Learner One" and learner.grade is None and learner.source_class == "REAL"
            await engine.dispose()
        asyncio.run(inspect_row())
    finally:
        close_client(client)


def test_classroom_grade_ownership_listing_and_audit() -> None:
    upgrade()
    client = client_for(f"teacher-a-{uuid4()}")
    try:
        assert client.post("/api/v1/teacher/profile", json={"name": "Owner"}, headers=post_headers(str(uuid4()))).status_code == 201
        grade_2 = client.post("/api/v1/classrooms", json={"name": "Grade 2A", "grade": "GRADE_2"}, headers=post_headers(str(uuid4())))
        grade_3 = client.post("/api/v1/classrooms", json={"name": "Grade 3A", "grade": "GRADE_3"}, headers=post_headers(str(uuid4())))
        assert grade_2.status_code == grade_3.status_code == 201
        assert client.post("/api/v1/classrooms", json={"name": "Grade 4", "grade": "GRADE_4"}, headers=post_headers(str(uuid4()))).status_code == 422
        assert len(client.get("/api/v1/classrooms").json()["classrooms"]) == 2
        classroom_id = grade_2.json()["classroom_id"]
        assert client.get(f"/api/v1/classrooms/{classroom_id}").status_code == 200
    finally:
        close_client(client)
    other = client_for(f"teacher-b-{uuid4()}")
    try:
        assert other.post("/api/v1/teacher/profile", json={"name": "Other"}, headers=post_headers(str(uuid4()))).status_code == 201
        assert other.get(f"/api/v1/classrooms/{classroom_id}").status_code == 404
        assert other.get("/api/v1/classrooms").json()["classrooms"] == []
    finally:
        close_client(other)
    learner = client_for(f"learner-classroom-{uuid4()}")
    try:
        assert learner.post("/api/v1/learner/profile", json={"name": "Learner"}, headers=post_headers(str(uuid4()))).status_code == 201
        assert learner.post("/api/v1/classrooms", json={"name": "No", "grade": "GRADE_2"}, headers=post_headers(str(uuid4()))).status_code == 403
    finally:
        close_client(learner)

    async def inspect_audit() -> None:
        engine = create_async_engine(async_database_url(get_settings().database_url), poolclass=NullPool)
        async with engine.connect() as connection:
            classrooms = await connection.scalar(select(func.count()).select_from(Classroom).where(Classroom.source_class == "REAL"))
            audits = await connection.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.operation_or_event_type == "classroom.created", AuditEvent.source_class == "REAL"))
            assert classrooms >= 2 and audits >= 2
        await engine.dispose()
    asyncio.run(inspect_audit())
