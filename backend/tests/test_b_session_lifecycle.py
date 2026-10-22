"""Comprehensive tests for the authorized BE2.3-BE2.4 neutral session-lifecycle
skeleton: start (fail-closed on no approved bundle, replay, concurrent dedup),
get-active (isolation), complete/abandon (transition, replay, path-mismatch conflict,
ownership, rollback), and bundle-pinning-survives-a-newer-bundle behavior.
"""

import asyncio
import hashlib
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import UUID, uuid4

from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.routes.b_session import service as b_session_service
from app.application.b_session_lifecycle import BSessionLifecycleService
from app.core.config import get_settings
from app.domain.principal import AuthenticatedPrincipal
from app.infrastructure.auth import get_authenticated_principal
from app.infrastructure.database import async_database_url
from app.infrastructure.persistence_models import AppUser, AuditEvent, IdempotencyRecord, RuntimeBundleRecord, SessionRecord
from app.main import app


def upgrade() -> None:
    subprocess.run(["alembic", "upgrade", "head"], check=True)


def client_for(subject: str, injected_service: BSessionLifecycleService | None = None) -> TestClient:
    app.dependency_overrides[get_authenticated_principal] = lambda: AuthenticatedPrincipal(
        user_id=subject, email="verified@example.test"
    )
    if injected_service is not None:
        app.dependency_overrides[b_session_service] = lambda: injected_service
    client = TestClient(app)
    client.__enter__()
    return client


def close_client(client: TestClient) -> None:
    client.__exit__(None, None, None)
    app.dependency_overrides.clear()


def multi_principal_client() -> TestClient:
    def resolve_principal(request: Request) -> AuthenticatedPrincipal:
        subject = request.headers.get("X-Test-Subject", "unresolved-test-subject")
        return AuthenticatedPrincipal(user_id=subject, email="verified@example.test")

    app.dependency_overrides[get_authenticated_principal] = resolve_principal
    client = TestClient(app)
    client.__enter__()
    return client


def headers(key: str | None = None, request_id: str | None = None, subject: str | None = None) -> dict[str, str]:
    result = {
        "X-Request-ID": request_id or f"req-{uuid4()}",
        "Authorization": "Bearer b-session-lifecycle-secret-that-must-not-be-logged",
    }
    if key is not None:
        result["Idempotency-Key"] = key
    if subject is not None:
        result["X-Test-Subject"] = subject
    return result


async def _engine():
    return create_async_engine(async_database_url(get_settings().database_url), poolclass=NullPool)


def setup_teacher(subject: str, name: str = "Owner") -> None:
    client = client_for(subject)
    try:
        assert client.post("/api/v1/teacher/profile", json={"name": name}, headers=headers(str(uuid4()))).status_code == 201
    finally:
        close_client(client)


def setup_learner(subject: str, name: str = "Learner") -> None:
    client = client_for(subject)
    try:
        assert client.post("/api/v1/learner/profile", json={"name": name}, headers=headers(str(uuid4()))).status_code == 201
    finally:
        close_client(client)


def insert_approved_bundle(bundle_version: str | None = None) -> UUID:
    async def _insert() -> UUID:
        engine = await _engine()
        factory = async_sessionmaker(engine, expire_on_commit=False)
        bundle_id = uuid4()
        version = bundle_version or f"bundle-{bundle_id}"
        async with factory() as session:
            session.add(
                RuntimeBundleRecord(
                    runtime_bundle_record_id=bundle_id,
                    bundle_version=version,
                    manifest_checksum=hashlib.sha256(version.encode()).hexdigest(),
                    publication_state="PUBLISHED",
                    approval_status="APPROVED",
                    immutable_after_publication=True,
                    system_actor="b-session-lifecycle-test",
                    request_id=f"bundle-setup-{bundle_id}",
                    operation_or_event_type="test.bundle_setup",
                    reason_code="ISOLATED_SYNTHETIC_TEST",
                    resource_type="b_runtime_bundle_record",
                    resource_id=bundle_id,
                    source_class="TEST",
                    source_system="b-session-lifecycle-test-suite",
                    environment="test",
                    schema_revision="20260723_0001",
                )
            )
            await session.commit()
        await engine.dispose()
        return bundle_id

    return asyncio.run(_insert())


async def _learner_id_for_subject(subject: str) -> UUID:
    engine = await _engine()
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        user = await session.scalar(select(AppUser).where(AppUser.supabase_subject == subject))
        row = await session.execute(text("SELECT learner_id FROM app_user_learner_links WHERE user_id = :uid"), {"uid": user.user_id})
        learner_id = row.scalar_one()
    await engine.dispose()
    return learner_id


async def idempotency_row(actor_subject: str, operation: str, key: str) -> IdempotencyRecord | None:
    engine = await _engine()
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        user = await session.scalar(select(AppUser).where(AppUser.supabase_subject == actor_subject))
        if user is None:
            return None
        row = await session.scalar(
            select(IdempotencyRecord).where(
                IdempotencyRecord.actor_user_id == user.user_id,
                IdempotencyRecord.operation_identifier == operation,
                IdempotencyRecord.idempotency_key == key,
            )
        )
    await engine.dispose()
    return row


async def audit_count(operation: str, resource_id: UUID | None = None) -> int:
    engine = await _engine()
    async with engine.connect() as connection:
        from sqlalchemy import func

        conditions = [AuditEvent.operation_or_event_type == operation]
        if resource_id is not None:
            conditions.append(AuditEvent.resource_id == resource_id)
        count = await connection.scalar(select(func.count()).select_from(AuditEvent).where(*conditions))
    await engine.dispose()
    return count


async def fetch_session(session_id: UUID) -> SessionRecord | None:
    engine = await _engine()
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        row = await session.get(SessionRecord, session_id)
    await engine.dispose()
    return row


async def active_or_starting_count(learner_id: UUID) -> int:
    engine = await _engine()
    async with engine.connect() as connection:
        from sqlalchemy import func

        count = await connection.scalar(
            select(func.count()).select_from(SessionRecord).where(
                SessionRecord.learner_id == learner_id, SessionRecord.state.in_(("starting", "active"))
            )
        )
    await engine.dispose()
    return count


def start_session(subject: str, key: str | None = None) -> "Response":  # noqa: F821
    client = client_for(subject)
    try:
        return client.post("/api/v1/b/sessions", json=None, headers=headers(key or str(uuid4())))
    finally:
        close_client(client)


def _failing_audit(*_args, **_kwargs):
    raise RuntimeError("controlled-test-failure")


async def _no_bundle_available(*_args, **_kwargs):
    return None


# ---------------------------------------------------------------------------
# Start
# ---------------------------------------------------------------------------


def test_start_creates_active_session_pinned_to_approved_bundle() -> None:
    upgrade()
    learner = f"learner-start-{uuid4()}"
    setup_learner(learner)
    bundle_id = insert_approved_bundle()
    client = client_for(learner)
    try:
        response = client.post("/api/v1/b/sessions", json=None, headers=headers(str(uuid4())))
        assert response.status_code == 201
        body = response.json()
        assert body["state"] == "active"
        assert set(body) == {"session_id", "state", "runtime_bundle_version", "created_at_utc", "row_version", "request_id"}
    finally:
        close_client(client)

    async def check() -> None:
        row = await fetch_session(UUID(body["session_id"]))
        assert row.state == "active"
        assert row.runtime_bundle_record_id == bundle_id
        assert row.expires_at_utc is None

    asyncio.run(check())


def test_start_fails_closed_when_no_approved_bundle_exists() -> None:
    upgrade()
    learner = f"learner-start-nobundle-{uuid4()}"
    setup_learner(learner)
    insert_approved_bundle()  # ensure at least one exists globally elsewhere
    injected = BSessionLifecycleService()
    injected._resolve_pinnable_bundle = _no_bundle_available
    client = client_for(learner, injected)
    try:
        response = client.post("/api/v1/b/sessions", json=None, headers=headers(str(uuid4())))
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "CONFLICT"
    finally:
        close_client(client)

    async def check_no_session() -> None:
        learner_id = await _learner_id_for_subject(learner)
        assert await active_or_starting_count(learner_id) == 0

    asyncio.run(check_no_session())


def test_start_replay_returns_same_session() -> None:
    upgrade()
    learner = f"learner-start-replay-{uuid4()}"
    setup_learner(learner)
    insert_approved_bundle()
    key = str(uuid4())
    client = client_for(learner)
    try:
        first = client.post("/api/v1/b/sessions", json=None, headers=headers(key))
        replay = client.post("/api/v1/b/sessions", json=None, headers=headers(key))
        assert first.status_code == replay.status_code == 201
        assert first.json() == replay.json()
    finally:
        close_client(client)


def test_start_role_and_profile_boundary() -> None:
    upgrade()
    teacher, no_profile = f"teacher-start-{uuid4()}", f"no-profile-start-{uuid4()}"
    setup_teacher(teacher)
    insert_approved_bundle()
    teacher_client = client_for(teacher)
    try:
        assert teacher_client.post("/api/v1/b/sessions", json=None, headers=headers(str(uuid4()))).status_code == 403
    finally:
        close_client(teacher_client)
    unknown_client = client_for(no_profile)
    try:
        assert unknown_client.post("/api/v1/b/sessions", json=None, headers=headers(str(uuid4()))).status_code == 404
    finally:
        close_client(unknown_client)


def test_start_concurrent_duplicate_produces_exactly_one_active_session() -> None:
    upgrade()
    learner = f"learner-start-concurrent-{uuid4()}"
    setup_learner(learner)
    insert_approved_bundle()
    client = client_for(learner)
    barrier = Barrier(2)

    def submit():
        barrier.wait()
        return client.post("/api/v1/b/sessions", json=None, headers=headers(str(uuid4())))

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _: submit(), range(2)))
        assert [response.status_code for response in responses] == [201, 201]
        assert len({response.json()["session_id"] for response in responses}) == 1
    finally:
        close_client(client)

    learner_id = asyncio.run(_learner_id_for_subject(learner))
    assert asyncio.run(active_or_starting_count(learner_id)) == 1


def test_start_rollback_on_injected_failure_leaves_no_session_audit_or_idempotency_row() -> None:
    upgrade()
    learner = f"learner-start-rollback-{uuid4()}"
    setup_learner(learner)
    insert_approved_bundle()
    injected = BSessionLifecycleService()
    injected._audit = _failing_audit
    key, request_id = str(uuid4()), f"start-rollback-{uuid4()}"
    client = client_for(learner, injected)
    try:
        failed = client.post("/api/v1/b/sessions", json=None, headers=headers(key, request_id))
        assert failed.status_code == 500
        assert failed.json()["error"]["request_id"] == request_id
    finally:
        close_client(client)

    learner_id = asyncio.run(_learner_id_for_subject(learner))
    assert asyncio.run(active_or_starting_count(learner_id)) == 0
    assert asyncio.run(idempotency_row(learner, "b_session.start", key)) is None

    retry = client_for(learner)
    try:
        assert retry.post("/api/v1/b/sessions", json=None, headers=headers(key)).status_code == 201
    finally:
        close_client(retry)


def test_runtime_bundle_pinning_survives_a_newer_bundle() -> None:
    upgrade()
    learner = f"learner-pin-{uuid4()}"
    setup_learner(learner)
    original_version = f"pin-original-{uuid4()}"
    insert_approved_bundle(original_version)
    client = client_for(learner)
    try:
        started = client.post("/api/v1/b/sessions", json=None, headers=headers(str(uuid4())))
        assert started.status_code == 201
        assert started.json()["runtime_bundle_version"] == original_version
    finally:
        close_client(client)

    newer_version = f"pin-newer-{uuid4()}"
    insert_approved_bundle(newer_version)

    active_client = client_for(learner)
    try:
        active = active_client.get("/api/v1/b/sessions/active")
        assert active.status_code == 200
        assert active.json()["session"]["runtime_bundle_version"] == original_version
    finally:
        close_client(active_client)


# ---------------------------------------------------------------------------
# Get active
# ---------------------------------------------------------------------------


def test_get_active_isolates_across_learners_and_returns_null_when_absent() -> None:
    upgrade()
    learner_a, learner_b = f"learner-active-a-{uuid4()}", f"learner-active-b-{uuid4()}"
    setup_learner(learner_a)
    setup_learner(learner_b)
    insert_approved_bundle()

    client_a = client_for(learner_a)
    try:
        empty = client_a.get("/api/v1/b/sessions/active")
        assert empty.status_code == 200
        assert empty.json()["session"] is None
        started = client_a.post("/api/v1/b/sessions", json=None, headers=headers(str(uuid4())))
        assert started.status_code == 201
        active = client_a.get("/api/v1/b/sessions/active")
        assert active.status_code == 200
        assert active.json()["session"]["session_id"] == started.json()["session_id"]
    finally:
        close_client(client_a)

    client_b = client_for(learner_b)
    try:
        empty_b = client_b.get("/api/v1/b/sessions/active")
        assert empty_b.status_code == 200
        assert empty_b.json()["session"] is None
    finally:
        close_client(client_b)


def test_get_active_role_boundary() -> None:
    upgrade()
    teacher = f"teacher-active-{uuid4()}"
    setup_teacher(teacher)
    client = client_for(teacher)
    try:
        assert client.get("/api/v1/b/sessions/active").status_code == 403
    finally:
        close_client(client)


# ---------------------------------------------------------------------------
# Complete / abandon
# ---------------------------------------------------------------------------


def test_complete_success_replay_path_mismatch_conflict_and_isolation() -> None:
    upgrade()
    learner, other_learner = f"learner-complete-{uuid4()}", f"learner-complete-other-{uuid4()}"
    setup_learner(learner)
    setup_learner(other_learner)
    insert_approved_bundle()
    started = start_session(learner)
    assert started.status_code == 201
    session_id = started.json()["session_id"]

    client = client_for(learner)
    try:
        key = str(uuid4())
        first = client.post(f"/api/v1/b/sessions/{session_id}/complete", json=None, headers=headers(key))
        replay = client.post(f"/api/v1/b/sessions/{session_id}/complete", json=None, headers=headers(key))
        assert first.status_code == replay.status_code == 200
        assert first.json() == replay.json()
        assert first.json()["state"] == "completed"

        # Non-active -> conflict on a further transition attempt with a fresh key.
        already_completed = client.post(f"/api/v1/b/sessions/{session_id}/complete", json=None, headers=headers(str(uuid4())))
        assert already_completed.status_code == 409

        # Path mismatch: the SAME actor reusing `key` against a different (owned)
        # session -- now that the first session is completed, this learner can start a
        # new one -- must conflict rather than replay the first session's response.
        second_started = client.post("/api/v1/b/sessions", json=None, headers=headers(str(uuid4())))
        assert second_started.status_code == 201
        second_session_id = second_started.json()["session_id"]
        mismatch = client.post(f"/api/v1/b/sessions/{second_session_id}/complete", json=None, headers=headers(key))
        assert mismatch.status_code == 409
    finally:
        close_client(client)

    # Cross-learner ownership isolation -> 404, no enumeration.
    isolation_client = client_for(other_learner)
    try:
        assert isolation_client.post(f"/api/v1/b/sessions/{session_id}/complete", json=None, headers=headers(str(uuid4()))).status_code == 404
    finally:
        close_client(isolation_client)

    assert asyncio.run(audit_count("b_session.complete", UUID(session_id))) == 1


def test_abandon_success_and_non_active_conflict() -> None:
    upgrade()
    learner = f"learner-abandon-{uuid4()}"
    setup_learner(learner)
    insert_approved_bundle()
    started = start_session(learner)
    session_id = started.json()["session_id"]

    client = client_for(learner)
    try:
        response = client.post(f"/api/v1/b/sessions/{session_id}/abandon", json=None, headers=headers(str(uuid4())))
        assert response.status_code == 200
        assert response.json()["state"] == "abandoned"
        conflict = client.post(f"/api/v1/b/sessions/{session_id}/complete", json=None, headers=headers(str(uuid4())))
        assert conflict.status_code == 409
    finally:
        close_client(client)

    assert asyncio.run(audit_count("b_session.abandon", UUID(session_id))) == 1


def test_complete_and_abandon_require_learner_role_and_profile() -> None:
    upgrade()
    learner, teacher, no_profile = f"learner-role-{uuid4()}", f"teacher-role-{uuid4()}", f"no-profile-role-{uuid4()}"
    setup_learner(learner)
    setup_teacher(teacher)
    insert_approved_bundle()
    started = start_session(learner)
    session_id = started.json()["session_id"]

    teacher_client = client_for(teacher)
    try:
        assert teacher_client.post(f"/api/v1/b/sessions/{session_id}/complete", json=None, headers=headers(str(uuid4()))).status_code == 403
    finally:
        close_client(teacher_client)

    unknown_client = client_for(no_profile)
    try:
        assert unknown_client.post(f"/api/v1/b/sessions/{session_id}/complete", json=None, headers=headers(str(uuid4()))).status_code == 404
    finally:
        close_client(unknown_client)


def test_complete_rollback_on_injected_failure_leaves_state_unchanged() -> None:
    upgrade()
    learner = f"learner-complete-rollback-{uuid4()}"
    setup_learner(learner)
    insert_approved_bundle()
    started = start_session(learner)
    session_id = started.json()["session_id"]

    injected = BSessionLifecycleService()
    injected._audit = _failing_audit
    key, request_id = str(uuid4()), f"complete-rollback-{uuid4()}"
    client = client_for(learner, injected)
    try:
        failed = client.post(f"/api/v1/b/sessions/{session_id}/complete", json=None, headers=headers(key, request_id))
        assert failed.status_code == 500
        assert failed.json()["error"]["request_id"] == request_id
    finally:
        close_client(client)

    row = asyncio.run(fetch_session(UUID(session_id)))
    assert row.state == "active"
    assert row.row_version == 0
    assert asyncio.run(idempotency_row(learner, "b_session.complete", key)) is None

    retry = client_for(learner)
    try:
        assert retry.post(f"/api/v1/b/sessions/{session_id}/complete", json=None, headers=headers(key)).status_code == 200
    finally:
        close_client(retry)


def test_concurrent_complete_and_abandon_race_produces_exactly_one_transition() -> None:
    upgrade()
    learner = f"learner-race-{uuid4()}"
    setup_learner(learner)
    insert_approved_bundle()
    started = start_session(learner)
    session_id = started.json()["session_id"]

    client = multi_principal_client()
    barrier = Barrier(2)

    def act(op: str):
        barrier.wait()
        return client.post(f"/api/v1/b/sessions/{session_id}/{op}", json=None, headers=headers(str(uuid4()), subject=learner))

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(act, ["complete", "abandon"]))
        statuses = sorted(response.status_code for response in results)
        assert statuses == [200, 409]
    finally:
        close_client(client)

    row = asyncio.run(fetch_session(UUID(session_id)))
    assert row.state in ("completed", "abandoned")
    assert row.row_version == 1
