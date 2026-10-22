"""Corrective replay, concurrency, and rollback evidence for authorized POSTs.

This batch supplies the governance-required identical-replay, body-mismatch,
concurrent-duplicate, and injected-failure rollback evidence for each of the three
authorized POST commands:

- POST /api/v1/teacher/profile
- POST /api/v1/learner/profile
- POST /api/v1/classrooms

Concurrency uses real PostgreSQL transactions. Failure is injected only through a
test-only in-process service instance; no production failure flag or debug endpoint
is added. No runtime endpoint, table, column, role, or scientific behavior is added.
"""

import asyncio
import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.routes.profile_classroom import service
from app.application.profile_classroom import ProfileClassroomService
from app.core.config import get_settings
from app.domain.principal import AuthenticatedPrincipal
from app.infrastructure.auth import get_authenticated_principal
from app.infrastructure.database import async_database_url
from app.infrastructure.persistence_models import (
    AppUser,
    AppUserLearnerLink,
    AuditEvent,
    Classroom,
    IdempotencyRecord,
    Learner,
    TeacherProfile,
)
from app.main import app


SECRET_BEARER = "corrective-secret-that-must-not-be-logged"


def upgrade() -> None:
    subprocess.run(["alembic", "upgrade", "head"], check=True)


def client_for(subject: str, injected_service: ProfileClassroomService | None = None) -> TestClient:
    app.dependency_overrides[get_authenticated_principal] = lambda: AuthenticatedPrincipal(
        user_id=subject, email="verified@example.test"
    )
    if injected_service is not None:
        app.dependency_overrides[service] = lambda: injected_service
    client = TestClient(app)
    client.__enter__()
    return client


def close_client(client: TestClient) -> None:
    client.__exit__(None, None, None)
    app.dependency_overrides.clear()


def headers(key: str, request_id: str | None = None) -> dict[str, str]:
    return {
        "Idempotency-Key": key,
        "X-Request-ID": request_id or f"req-{uuid4()}",
        "Authorization": f"Bearer {SECRET_BEARER}",
    }


async def counts(subject: str, operation: str, key: str, entity: type | None = None) -> dict[str, int]:
    engine = create_async_engine(async_database_url(get_settings().database_url), poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        user = await session.scalar(select(AppUser).where(AppUser.supabase_subject == subject))
        result = {
            "users": await session.scalar(select(func.count()).select_from(AppUser).where(AppUser.supabase_subject == subject)),
            "idempotency": 0,
            "audits": 0,
            "entities": 0,
            "links": 0,
        }
        if user is not None:
            result["idempotency"] = await session.scalar(
                select(func.count()).select_from(IdempotencyRecord).where(
                    IdempotencyRecord.actor_user_id == user.user_id,
                    IdempotencyRecord.operation_identifier == operation,
                    IdempotencyRecord.idempotency_key == key,
                )
            )
            result["audits"] = await session.scalar(
                select(func.count()).select_from(AuditEvent).where(
                    AuditEvent.actor_user_id == user.user_id,
                    AuditEvent.operation_or_event_type == operation.replace(".create", ".created"),
                )
            )
            result["links"] = await session.scalar(
                select(func.count()).select_from(AppUserLearnerLink).where(
                    AppUserLearnerLink.user_id == user.user_id
                )
            )
            if entity is TeacherProfile:
                result["entities"] = await session.scalar(
                    select(func.count()).select_from(TeacherProfile).where(TeacherProfile.user_id == user.user_id)
                )
            elif entity is Learner:
                result["entities"] = result["links"]
            elif entity is Classroom:
                teacher_id = await session.scalar(
                    select(TeacherProfile.teacher_profile_id).where(TeacherProfile.user_id == user.user_id)
                )
                result["entities"] = await session.scalar(
                    select(func.count()).select_from(Classroom).where(Classroom.teacher_profile_id == teacher_id)
                )
    await engine.dispose()
    return result


async def live_source_classes(subject: str) -> set[str]:
    """Every persisted live row for the subject must carry server-assigned REAL provenance."""
    engine = create_async_engine(async_database_url(get_settings().database_url), poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    classes: set[str] = set()
    async with factory() as session:
        user = await session.scalar(select(AppUser).where(AppUser.supabase_subject == subject))
        if user is not None:
            classes.add(user.source_class)
            for model, column in (
                (TeacherProfile, TeacherProfile.user_id),
                (AppUserLearnerLink, AppUserLearnerLink.user_id),
                (IdempotencyRecord, IdempotencyRecord.actor_user_id),
                (AuditEvent, AuditEvent.actor_user_id),
            ):
                rows = await session.scalars(select(model).where(column == user.user_id))
                classes.update(row.source_class for row in rows)
            link = await session.scalar(select(AppUserLearnerLink).where(AppUserLearnerLink.user_id == user.user_id))
            if link is not None:
                learner = await session.get(Learner, link.learner_id)
                if learner is not None:
                    classes.add(learner.source_class)
            teacher_id = await session.scalar(select(TeacherProfile.teacher_profile_id).where(TeacherProfile.user_id == user.user_id))
            if teacher_id is not None:
                classrooms = await session.scalars(select(Classroom).where(Classroom.teacher_profile_id == teacher_id))
                classes.update(row.source_class for row in classrooms)
    await engine.dispose()
    return classes


# ---------------------------------------------------------------------------
# Replay and body-mismatch evidence
# ---------------------------------------------------------------------------

PROFILE_CASES = (
    ("teacher", "/api/v1/teacher/profile", {"name": "Teacher Safe"}, {"name": "Teacher Changed"}, "teacher.profile.create", TeacherProfile, "teacher_profile_id"),
    ("learner", "/api/v1/learner/profile", {"name": "Learner Safe"}, {"name": "Learner Changed"}, "learner.profile.create", Learner, "learner_id"),
)


@pytest.mark.parametrize("label,path,payload,changed,operation,entity,identity", PROFILE_CASES)
def test_profile_replay_and_mismatch(label, path, payload, changed, operation, entity, identity) -> None:
    upgrade()
    subject, key = f"{label}-replay-{uuid4()}", str(uuid4())
    client = client_for(subject)
    try:
        first = client.post(path, json=payload, headers=headers(key))
        replay = client.post(path, json=payload, headers=headers(key))
        conflict = client.post(path, json=changed, headers=headers(key))
        assert first.status_code == replay.status_code == 201
        # Identical replay returns the original committed identity/result.
        assert replay.json()[identity] == first.json()[identity]
        assert replay.json() == first.json()
        # Same key with a different body fails with the authorized stable conflict.
        assert conflict.status_code == 409
        assert conflict.json()["error"]["code"] == "CONFLICT"
        assert conflict.json()["error"]["request_id"]
    finally:
        close_client(client)
    state = asyncio.run(counts(subject, operation, key, entity))
    assert state["users"] == state["entities"] == state["idempotency"] == state["audits"] == 1
    if entity is Learner:
        assert state["links"] == 1
    # REAL provenance is server-assigned; clients never submit source_class.
    assert asyncio.run(live_source_classes(subject)) == {"REAL"}


def test_classroom_replay_and_all_authorized_mismatches() -> None:
    upgrade()
    subject, key = f"classroom-replay-{uuid4()}", str(uuid4())
    client = client_for(subject)
    try:
        owner = client.post("/api/v1/teacher/profile", json={"name": "Owner"}, headers=headers(str(uuid4())))
        assert owner.status_code == 201
        teacher_profile_id = owner.json()["teacher_profile_id"]
        payload = {"name": "Class Safe", "grade": "GRADE_2"}
        first = client.post("/api/v1/classrooms", json=payload, headers=headers(key))
        replay = client.post("/api/v1/classrooms", json=payload, headers=headers(key))
        assert first.status_code == replay.status_code == 201
        # Identical replay returns the original classroom.
        assert replay.json()["classroom_id"] == first.json()["classroom_id"]
        assert replay.json() == first.json()
        # Ownership is server-derived, never client-supplied.
        assert first.json()["teacher_profile_id"] == teacher_profile_id
        # Same key with a different authorized field (name or grade) fails with the authorized conflict.
        for changed in ({"name": "Changed", "grade": "GRADE_2"}, {"name": "Class Safe", "grade": "GRADE_3"}):
            conflict = client.post("/api/v1/classrooms", json=changed, headers=headers(key))
            assert conflict.status_code == 409 and conflict.json()["error"]["code"] == "CONFLICT"
    finally:
        close_client(client)
    state = asyncio.run(counts(subject, "classroom.create", key, Classroom))
    assert state["entities"] == state["idempotency"] == state["audits"] == 1
    assert asyncio.run(live_source_classes(subject)) == {"REAL"}


def test_classroom_accepts_only_grade_2_and_grade_3_and_enforces_ownership() -> None:
    upgrade()
    subject = f"classroom-grade-{uuid4()}"
    client = client_for(subject)
    try:
        assert client.post("/api/v1/teacher/profile", json={"name": "Owner"}, headers=headers(str(uuid4()))).status_code == 201
        assert client.post("/api/v1/classrooms", json={"name": "Two", "grade": "GRADE_2"}, headers=headers(str(uuid4()))).status_code == 201
        assert client.post("/api/v1/classrooms", json={"name": "Three", "grade": "GRADE_3"}, headers=headers(str(uuid4()))).status_code == 201
        for bad in ("GRADE_1", "GRADE_4", "grade_2", "2"):
            assert client.post("/api/v1/classrooms", json={"name": bad, "grade": bad}, headers=headers(str(uuid4()))).status_code == 422
    finally:
        close_client(client)
    # A learner may never create a classroom (ownership/role boundary preserved).
    learner = client_for(f"classroom-grade-learner-{uuid4()}")
    try:
        assert learner.post("/api/v1/learner/profile", json={"name": "Learner"}, headers=headers(str(uuid4()))).status_code == 201
        assert learner.post("/api/v1/classrooms", json={"name": "No", "grade": "GRADE_2"}, headers=headers(str(uuid4()))).status_code == 403
    finally:
        close_client(learner)


# ---------------------------------------------------------------------------
# Concurrent duplicate submission evidence (real PostgreSQL transactions)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("label,path,payload,operation,entity,identity", (
    ("teacher", "/api/v1/teacher/profile", {"name": "Concurrent Teacher"}, "teacher.profile.create", TeacherProfile, "teacher_profile_id"),
    ("learner", "/api/v1/learner/profile", {"name": "Concurrent Learner"}, "learner.profile.create", Learner, "learner_id"),
))
def test_profile_concurrent_duplicate_is_one_atomic_result(label, path, payload, operation, entity, identity) -> None:
    upgrade()
    subject, key, barrier = f"{label}-concurrent-{uuid4()}", str(uuid4()), Barrier(2)
    client = client_for(subject)

    def submit():
        barrier.wait()
        return client.post(path, json=payload, headers=headers(key))

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _: submit(), range(2)))
        # One deterministic authorized outcome; the losing/replayed request also receives 201.
        assert [response.status_code for response in responses] == [201, 201]
        assert len({response.json()[identity] for response in responses}) == 1
        # Transaction state remains usable afterward.
        assert client.get(path).status_code == 200
    finally:
        close_client(client)
    state = asyncio.run(counts(subject, operation, key, entity))
    assert state["users"] == state["entities"] == state["idempotency"] == state["audits"] == 1
    if entity is Learner:
        assert state["links"] == 1


def test_classroom_concurrent_duplicate_is_one_atomic_result() -> None:
    upgrade()
    subject, key, barrier = f"classroom-concurrent-{uuid4()}", str(uuid4()), Barrier(2)
    client = client_for(subject)
    try:
        assert client.post("/api/v1/teacher/profile", json={"name": "Owner"}, headers=headers(str(uuid4()))).status_code == 201

        def submit():
            barrier.wait()
            return client.post("/api/v1/classrooms", json={"name": "Concurrent", "grade": "GRADE_3"}, headers=headers(key))

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _: submit(), range(2)))
        assert [response.status_code for response in responses] == [201, 201]
        assert len({response.json()["classroom_id"] for response in responses}) == 1
        # No duplicate audit/idempotency/classroom state, and the connection remains usable.
        assert client.get("/api/v1/classrooms").status_code == 200
        assert len(client.get("/api/v1/classrooms").json()["classrooms"]) == 1
    finally:
        close_client(client)
    state = asyncio.run(counts(subject, "classroom.create", key, Classroom))
    assert state["entities"] == state["idempotency"] == state["audits"] == 1


# ---------------------------------------------------------------------------
# Injected-failure rollback evidence
# ---------------------------------------------------------------------------

def _failing_audit(*_args):
    raise RuntimeError("controlled-test-failure")


@pytest.mark.parametrize("label,path,payload,operation,entity", (
    ("teacher", "/api/v1/teacher/profile", {"name": "Rollback Teacher"}, "teacher.profile.create", TeacherProfile),
    ("learner", "/api/v1/learner/profile", {"name": "Rollback Learner"}, "learner.profile.create", Learner),
))
def test_profile_injected_failure_rolls_back_and_retry_succeeds(monkeypatch, caplog, label, path, payload, operation, entity) -> None:
    upgrade()
    subject, key, request_id = f"{label}-rollback-{uuid4()}", str(uuid4()), f"rollback-{uuid4()}"
    # Inject failure after primary entity persistence and before audit/commit persistence.
    injected = ProfileClassroomService()
    monkeypatch.setattr(injected, "_audit", _failing_audit)
    caplog.set_level(logging.INFO)
    client = client_for(subject, injected)
    try:
        failed = client.post(path, json=payload, headers=headers(key, request_id))
        assert failed.status_code == 500
        assert failed.json()["error"]["code"] == "INTERNAL_ERROR"
        assert failed.json()["error"]["request_id"] == request_id
        # No answer key, secret, or exception internals leak in the error body.
        assert SECRET_BEARER not in failed.text
        assert "controlled-test-failure" not in failed.text
    finally:
        close_client(client)
    # Full rollback: entity, app-user mutation, owning link, idempotency, and audit are all absent.
    assert asyncio.run(counts(subject, operation, key, entity)) == {"users": 0, "idempotency": 0, "audits": 0, "entities": 0, "links": 0}
    log_text = caplog.text
    assert SECRET_BEARER not in log_text and "Authorization" not in log_text
    # A valid retry after rollback succeeds under the authorized behavior.
    retry = client_for(subject)
    try:
        assert retry.post(path, json=payload, headers=headers(key)).status_code == 201
    finally:
        close_client(retry)


def test_classroom_injected_failure_rolls_back_and_retry_succeeds(monkeypatch, caplog) -> None:
    upgrade()
    subject, key, request_id = f"classroom-rollback-{uuid4()}", str(uuid4()), f"rollback-{uuid4()}"
    setup = client_for(subject)
    try:
        assert setup.post("/api/v1/teacher/profile", json={"name": "Owner"}, headers=headers(str(uuid4()))).status_code == 201
    finally:
        close_client(setup)
    baseline = asyncio.run(counts(subject, "classroom.create", key, Classroom))
    # Inject failure after classroom persistence but before audit/commit.
    injected = ProfileClassroomService()
    monkeypatch.setattr(injected, "_audit", _failing_audit)
    caplog.set_level(logging.INFO)
    client = client_for(subject, injected)
    payload = {"name": "Rollback Class", "grade": "GRADE_2"}
    try:
        failed = client.post("/api/v1/classrooms", json=payload, headers=headers(key, request_id))
        assert failed.status_code == 500
        assert failed.json()["error"]["code"] == "INTERNAL_ERROR"
        assert failed.json()["error"]["request_id"] == request_id
        assert SECRET_BEARER not in failed.text
    finally:
        close_client(client)
    # Classroom, idempotency, and audit rollback leaves the pre-failure baseline untouched.
    after = asyncio.run(counts(subject, "classroom.create", key, Classroom))
    assert after == baseline == {"users": 1, "idempotency": 0, "audits": 0, "entities": 0, "links": 0}
    assert SECRET_BEARER not in caplog.text and "Authorization" not in caplog.text
    retry = client_for(subject)
    try:
        assert retry.post("/api/v1/classrooms", json=payload, headers=headers(key)).status_code == 201
    finally:
        close_client(retry)
