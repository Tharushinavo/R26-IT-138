"""Comprehensive tests for the authorized classroom invite and membership batch.

Covers replay, body/path-parameter mismatch, concurrency, rollback, ownership
isolation, privacy/leakage, and read-boundary requirements for all nine authorized
endpoints, per component-b-invite-membership-authorization.json and the Version 1
human-readable join-code clarification.
"""

import asyncio
import logging
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import UUID, uuid4

from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.routes.classroom_membership import service as classroom_membership_service
from app.application.classroom_membership import ClassroomMembershipService, normalize_join_code
from app.core.config import get_settings
from app.domain.principal import AuthenticatedPrincipal
from app.infrastructure.auth import get_authenticated_principal
from app.infrastructure.database import async_database_url
from app.infrastructure.persistence_models import (
    AppUser,
    AuditEvent,
    ClassroomInvite,
    ClassroomMembership,
    IdempotencyRecord,
    Learner,
)
from app.main import app


_JOIN_CODE_CHAR_PATTERN = re.compile(r"^[23456789ABCDEFGHJKMNPQRSTUVWXYZ]+$")


def upgrade() -> None:
    subprocess.run(["alembic", "upgrade", "head"], check=True)


def client_for(subject: str, injected_service: ClassroomMembershipService | None = None) -> TestClient:
    app.dependency_overrides[get_authenticated_principal] = lambda: AuthenticatedPrincipal(
        user_id=subject, email="verified@example.test"
    )
    if injected_service is not None:
        app.dependency_overrides[classroom_membership_service] = lambda: injected_service
    client = TestClient(app)
    client.__enter__()
    return client


def close_client(client: TestClient) -> None:
    client.__exit__(None, None, None)
    app.dependency_overrides.clear()


def multi_principal_client() -> TestClient:
    """A single shared client whose simulated principal is chosen per-request via
    an X-Test-Subject header, so genuinely concurrent requests from different
    principals can be exercised against one TestClient/app instance."""

    def resolve_principal(request: Request) -> AuthenticatedPrincipal:
        subject = request.headers.get("X-Test-Subject", "unresolved-test-subject")
        return AuthenticatedPrincipal(user_id=subject, email="verified@example.test")

    app.dependency_overrides[get_authenticated_principal] = resolve_principal
    client = TestClient(app)
    client.__enter__()
    return client


def headers(key: str, request_id: str | None = None, subject: str | None = None) -> dict[str, str]:
    result = {
        "Idempotency-Key": key,
        "X-Request-ID": request_id or f"req-{uuid4()}",
        "Authorization": "Bearer classroom-membership-secret-that-must-not-be-logged",
    }
    if subject is not None:
        result["X-Test-Subject"] = subject
    return result


async def _engine():
    return create_async_engine(async_database_url(get_settings().database_url), poolclass=NullPool)


async def set_expired(classroom_invite_id: UUID) -> None:
    engine = await _engine()
    async with engine.connect() as connection:
        await connection.execute(
            text("UPDATE classroom_invites SET expires_at_utc = :expiry WHERE classroom_invite_id = :id"),
            {"expiry": datetime.now(UTC) - timedelta(minutes=1), "id": classroom_invite_id},
        )
        await connection.commit()
    await engine.dispose()


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
        conditions = [AuditEvent.operation_or_event_type == operation]
        if resource_id is not None:
            conditions.append(AuditEvent.resource_id == resource_id)
        count = await connection.scalar(select(func.count()).select_from(AuditEvent).where(*conditions))
    await engine.dispose()
    return count


async def membership_count(classroom_id: UUID, learner_id: UUID) -> int:
    engine = await _engine()
    async with engine.connect() as connection:
        count = await connection.scalar(
            select(func.count())
            .select_from(ClassroomMembership)
            .where(ClassroomMembership.classroom_id == classroom_id, ClassroomMembership.learner_id == learner_id)
        )
    await engine.dispose()
    return count


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


def create_classroom(subject: str, name: str, grade: str = "GRADE_2") -> UUID:
    client = client_for(subject)
    try:
        response = client.post("/api/v1/classrooms", json={"name": name, "grade": grade}, headers=headers(str(uuid4())))
        assert response.status_code == 201
        return UUID(response.json()["classroom_id"])
    finally:
        close_client(client)


def create_invite(subject: str, classroom_id: UUID, key: str | None = None) -> dict:
    client = client_for(subject)
    try:
        response = client.post(
            f"/api/v1/classrooms/{classroom_id}/invites", json={}, headers=headers(key or str(uuid4()))
        )
        assert response.status_code == 201
        return response.json()
    finally:
        close_client(client)


def request_membership(subject: str, invite_token: str, key: str | None = None):
    client = client_for(subject)
    try:
        return client.post(
            "/api/v1/classroom-memberships/requests", json={"invite_token": invite_token}, headers=headers(key or str(uuid4()))
        )
    finally:
        close_client(client)


# ---------------------------------------------------------------------------
# Invite creation
# ---------------------------------------------------------------------------


def test_invite_creation_role_and_ownership_boundary() -> None:
    upgrade()
    teacher_a, teacher_b, learner = f"teacher-a-{uuid4()}", f"teacher-b-{uuid4()}", f"learner-{uuid4()}"
    setup_teacher(teacher_a)
    setup_teacher(teacher_b)
    setup_learner(learner)
    classroom_id = create_classroom(teacher_a, "Class A")

    owner_client = client_for(teacher_a)
    try:
        created = owner_client.post(f"/api/v1/classrooms/{classroom_id}/invites", json={}, headers=headers(str(uuid4())))
        assert created.status_code == 201
        assert created.json()["token_already_issued"] is False
        assert created.json()["invite_token"]
    finally:
        close_client(owner_client)

    other_client = client_for(teacher_b)
    try:
        assert other_client.post(f"/api/v1/classrooms/{classroom_id}/invites", json={}, headers=headers(str(uuid4()))).status_code == 404
    finally:
        close_client(other_client)

    learner_client = client_for(learner)
    try:
        assert learner_client.post(f"/api/v1/classrooms/{classroom_id}/invites", json={}, headers=headers(str(uuid4()))).status_code == 403
    finally:
        close_client(learner_client)


def test_invite_creation_replay_path_mismatch_and_one_time_exposure() -> None:
    upgrade()
    teacher = f"teacher-invite-replay-{uuid4()}"
    setup_teacher(teacher)
    classroom_a = create_classroom(teacher, "Room A")
    classroom_b = create_classroom(teacher, "Room B")
    key = str(uuid4())
    client = client_for(teacher)
    try:
        first = client.post(f"/api/v1/classrooms/{classroom_a}/invites", json={}, headers=headers(key))
        replay = client.post(f"/api/v1/classrooms/{classroom_a}/invites", json={}, headers=headers(key))
        assert first.status_code == replay.status_code == 201
        assert replay.json()["classroom_invite_id"] == first.json()["classroom_invite_id"]
        assert replay.json()["invite_token"] is None
        assert replay.json()["token_already_issued"] is True
        # Path-resource mismatch: same key, different classroom -> stable conflict, never a replay.
        mismatch = client.post(f"/api/v1/classrooms/{classroom_b}/invites", json={}, headers=headers(key))
        assert mismatch.status_code == 409
        assert mismatch.json()["error"]["code"] == "CONFLICT"
    finally:
        close_client(client)
    token = first.json()["invite_token"]
    assert token and token == token.upper()
    assert "-" in token
    assert _JOIN_CODE_CHAR_PATTERN.match(token.replace("-", ""))
    for ambiguous in "0O1IL":
        assert ambiguous not in token
    # The persisted idempotency canonical response never contains the raw token.
    record = asyncio.run(idempotency_row(teacher, "classroom_invite.create", key))
    assert record is not None
    assert record.canonical_response["invite_token"] is None
    assert record.canonical_response["token_already_issued"] is True


def test_invite_creation_concurrent_same_key_and_different_key() -> None:
    upgrade()
    teacher = f"teacher-invite-concurrent-{uuid4()}"
    setup_teacher(teacher)
    classroom_id = create_classroom(teacher, "Concurrent Room")
    same_key, barrier = str(uuid4()), Barrier(2)
    client = client_for(teacher)

    def submit_same_key():
        barrier.wait()
        return client.post(f"/api/v1/classrooms/{classroom_id}/invites", json={}, headers=headers(same_key))

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _: submit_same_key(), range(2)))
        assert [response.status_code for response in responses] == [201, 201]
        assert len({response.json()["classroom_invite_id"] for response in responses}) == 1
        # D49 (2026-09-14): a different Idempotency-Key is still a separate command, but it must
        # NOT mint a second code -- a classroom has exactly one live join code for its whole life.
        # Both calls return the SAME invite, and neither re-exposes the plaintext: that was shown
        # once, at creation, and only its hash was kept. (This asserted two DISTINCT invites until
        # D49; two live codes would both resolve while the teacher could only read one back.)
        created_invite_id = responses[0].json()["classroom_invite_id"]
        different_a = client.post(f"/api/v1/classrooms/{classroom_id}/invites", json={}, headers=headers(str(uuid4())))
        different_b = client.post(f"/api/v1/classrooms/{classroom_id}/invites", json={}, headers=headers(str(uuid4())))
        assert different_a.status_code == different_b.status_code == 201
        assert different_a.json()["classroom_invite_id"] == created_invite_id
        assert different_b.json()["classroom_invite_id"] == created_invite_id
        for repeat in (different_a, different_b):
            assert repeat.json()["token_already_issued"] is True
            assert repeat.json()["invite_token"] is None
    finally:
        close_client(client)


def _failing_audit(*_args, **_kwargs):
    raise RuntimeError("controlled-test-failure")


def test_invite_creation_rollback_and_retry_succeeds() -> None:
    upgrade()
    teacher = f"teacher-invite-rollback-{uuid4()}"
    setup_teacher(teacher)
    classroom_id = create_classroom(teacher, "Rollback Room")
    key, request_id = str(uuid4()), f"rollback-{uuid4()}"
    injected = ClassroomMembershipService()
    injected._audit = _failing_audit
    client = client_for(teacher, injected)
    try:
        failed = client.post(f"/api/v1/classrooms/{classroom_id}/invites", json={}, headers=headers(key, request_id))
        assert failed.status_code == 500
        assert failed.json()["error"]["code"] == "INTERNAL_ERROR"
        assert failed.json()["error"]["request_id"] == request_id
    finally:
        close_client(client)
    assert asyncio.run(idempotency_row(teacher, "classroom_invite.create", key)) is None
    retry = client_for(teacher)
    try:
        assert retry.post(f"/api/v1/classrooms/{classroom_id}/invites", json={}, headers=headers(key)).status_code == 201
    finally:
        close_client(retry)


def test_invite_creation_code_is_permanent() -> None:
    """D49: a class join code does not expire on a clock.

    This asserted a 24-hour expiry until 2026-09-14, and was renamed rather than edited in place
    because the property itself inverted. Children write the code down and the teacher dashboard
    shows the same class key indefinitely, so a code now ends only when it is revoked -- which
    deleting the classroom does -- never on a timer. `expires_at_utc` is therefore null.
    """
    upgrade()
    teacher = f"teacher-invite-expiry-{uuid4()}"
    setup_teacher(teacher)
    classroom_id = create_classroom(teacher, "Expiry Room")
    payload = create_invite(teacher, classroom_id)
    assert payload["expires_at_utc"] is None
    assert payload["token_already_issued"] is False
    assert payload["invite_token"] is not None


def test_join_code_format_excludes_ambiguous_characters() -> None:
    upgrade()
    teacher = f"teacher-invite-format-{uuid4()}"
    setup_teacher(teacher)
    # D49: one live code per classroom, so twenty distinct codes need twenty classrooms. Calling
    # invites twice on a single classroom now returns the same code with the plaintext withheld,
    # which would have collapsed this sample to one.
    seen_codes = set()
    for index in range(20):
        payload = create_invite(teacher, create_classroom(teacher, f"Format Room {index}"))
        canonical = payload["invite_token"].replace("-", "")
        assert len(canonical) == 8
        assert canonical == canonical.upper()
        assert _JOIN_CODE_CHAR_PATTERN.match(canonical)
        for ambiguous in "0O1IL":
            assert ambiguous not in canonical
        seen_codes.add(canonical)
    assert len(seen_codes) == 20


# ---------------------------------------------------------------------------
# Invite resolve
# ---------------------------------------------------------------------------


def test_resolve_success_case_and_separator_insensitive_and_no_membership_side_effect() -> None:
    upgrade()
    teacher, learner = f"teacher-resolve-{uuid4()}", f"learner-resolve-{uuid4()}"
    setup_teacher(teacher)
    setup_learner(learner)
    classroom_id = create_classroom(teacher, "Resolve Room", "GRADE_3")
    invite = create_invite(teacher, classroom_id)
    token = invite["invite_token"]
    variants = [token, token.lower(), token.replace("-", ""), f"  {token}  ", token.lower().replace("-", " ")]
    client = client_for(learner)
    try:
        for variant in variants:
            response = client.post("/api/v1/classroom-invites/resolve", json={"invite_token": variant}, headers=headers(str(uuid4())))
            assert response.status_code == 200, variant
            assert response.json()["grade"] == "GRADE_3"
    finally:
        close_client(client)
    learner_id_row = asyncio.run(_learner_id_for_subject(learner))
    assert asyncio.run(membership_count(classroom_id, learner_id_row)) == 0


async def _learner_id_for_subject(subject: str) -> UUID:
    engine = await _engine()
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        user = await session.scalar(select(AppUser).where(AppUser.supabase_subject == subject))
        row = await session.execute(text("SELECT learner_id FROM app_user_learner_links WHERE user_id = :uid"), {"uid": user.user_id})
        learner_id = row.scalar_one()
    await engine.dispose()
    return learner_id


def test_resolve_unknown_revoked_and_expired() -> None:
    upgrade()
    teacher, learner = f"teacher-resolve-fail-{uuid4()}", f"learner-resolve-fail-{uuid4()}"
    setup_teacher(teacher)
    setup_learner(learner)
    classroom_id = create_classroom(teacher, "Fail Room")
    revoked_invite = create_invite(teacher, classroom_id)
    owner = client_for(teacher)
    try:
        assert owner.post(f"/api/v1/classroom-invites/{revoked_invite['classroom_invite_id']}/revoke", json={}, headers=headers(str(uuid4()))).status_code == 200
    finally:
        close_client(owner)
    # D49: one live code per classroom, so the second invite can only be minted once the first is
    # revoked. A code is created with `expires_at_utc` null now; `set_expired` back-dates it by
    # hand so the resolve-time expiry branch -- which still rejects a dated, past expiry -- stays
    # covered rather than becoming unreachable.
    expired_invite = create_invite(teacher, classroom_id)
    asyncio.run(set_expired(UUID(expired_invite["classroom_invite_id"])))
    client = client_for(learner)
    try:
        assert client.post("/api/v1/classroom-invites/resolve", json={"invite_token": "NOSUCH-CODE"}, headers=headers(str(uuid4()))).status_code == 404
        assert client.post("/api/v1/classroom-invites/resolve", json={"invite_token": revoked_invite["invite_token"]}, headers=headers(str(uuid4()))).status_code == 409
        assert client.post("/api/v1/classroom-invites/resolve", json={"invite_token": expired_invite["invite_token"]}, headers=headers(str(uuid4()))).status_code == 409
    finally:
        close_client(client)


def test_resolve_requires_learner_profile() -> None:
    upgrade()
    teacher_subject, empty_subject = f"teacher-resolve-role-{uuid4()}", f"no-profile-{uuid4()}"
    setup_teacher(teacher_subject)
    classroom_id = create_classroom(teacher_subject, "Role Room")
    invite = create_invite(teacher_subject, classroom_id)
    teacher_client = client_for(teacher_subject)
    try:
        assert teacher_client.post("/api/v1/classroom-invites/resolve", json={"invite_token": invite["invite_token"]}, headers=headers(str(uuid4()))).status_code == 403
    finally:
        close_client(teacher_client)
    unknown_client = client_for(empty_subject)
    try:
        assert unknown_client.post("/api/v1/classroom-invites/resolve", json={"invite_token": invite["invite_token"]}, headers=headers(str(uuid4()))).status_code == 404
    finally:
        close_client(unknown_client)


def test_resolve_replay_body_mismatch_rollback_and_leakage() -> None:
    upgrade()
    teacher, learner = f"teacher-resolve-replay-{uuid4()}", f"learner-resolve-replay-{uuid4()}"
    setup_teacher(teacher)
    setup_learner(learner)
    # D49: two separately resolvable codes require two classrooms -- a second invite call on one
    # classroom returns the first code with the plaintext withheld, so `invite_b` would carry no
    # token to resolve and the body-mismatch assertion below would stop testing anything.
    invite_a = create_invite(teacher, create_classroom(teacher, "Replay Room A"))
    invite_b = create_invite(teacher, create_classroom(teacher, "Replay Room B"))
    key = str(uuid4())
    client = client_for(learner)
    try:
        first = client.post("/api/v1/classroom-invites/resolve", json={"invite_token": invite_a["invite_token"]}, headers=headers(key))
        replay = client.post("/api/v1/classroom-invites/resolve", json={"invite_token": invite_a["invite_token"]}, headers=headers(key))
        assert first.status_code == replay.status_code == 200
        assert replay.json()["invite_resolution_id"] == first.json()["invite_resolution_id"]
        mismatch = client.post("/api/v1/classroom-invites/resolve", json={"invite_token": invite_b["invite_token"]}, headers=headers(key))
        assert mismatch.status_code == 409
    finally:
        close_client(client)

    request_id = f"resolve-rollback-{uuid4()}"
    rollback_key = str(uuid4())
    injected = ClassroomMembershipService()
    injected._audit = _failing_audit
    caplog_client = client_for(learner, injected)
    try:
        failed = caplog_client.post(
            "/api/v1/classroom-invites/resolve", json={"invite_token": invite_a["invite_token"]}, headers=headers(rollback_key, request_id)
        )
        assert failed.status_code == 500
    finally:
        close_client(caplog_client)
    assert asyncio.run(idempotency_row(learner, "classroom_invite.resolve", rollback_key)) is None
    retry = client_for(learner)
    try:
        assert retry.post("/api/v1/classroom-invites/resolve", json={"invite_token": invite_a["invite_token"]}, headers=headers(rollback_key)).status_code == 200
    finally:
        close_client(retry)


# ---------------------------------------------------------------------------
# Membership request
# ---------------------------------------------------------------------------


def test_membership_request_pending_creation_and_repeated_use_returns_existing() -> None:
    upgrade()
    teacher, learner = f"teacher-request-{uuid4()}", f"learner-request-{uuid4()}"
    setup_teacher(teacher)
    setup_learner(learner)
    classroom_id = create_classroom(teacher, "Request Room")
    invite = create_invite(teacher, classroom_id)
    first = request_membership(learner, invite["invite_token"])
    assert first.status_code == 201
    assert first.json()["state"] == "PENDING"
    membership_id = first.json()["classroom_membership_id"]
    # Repeated use of the classroom's code, under a NEW idempotency key, must return the existing
    # PENDING row rather than creating a duplicate. Before D49 this re-minted a fresh code for the
    # same classroom, to prove the dedupe keys on (classroom, learner) rather than on the invite
    # row. A classroom now has one code for its life, so re-entering that same code is also what a
    # child would actually do.
    repeated = request_membership(learner, invite["invite_token"])
    assert repeated.status_code == 201
    assert repeated.json()["classroom_membership_id"] == membership_id
    learner_id = asyncio.run(_learner_id_for_subject(learner))
    assert asyncio.run(membership_count(classroom_id, learner_id)) == 1


def test_membership_request_existing_approved_and_rejected_are_returned_safely() -> None:
    upgrade()
    teacher_a, teacher_b, learner = f"teacher-a-existing-{uuid4()}", f"teacher-b-existing-{uuid4()}", f"learner-existing-{uuid4()}"
    setup_teacher(teacher_a)
    setup_teacher(teacher_b)
    setup_learner(learner)
    classroom_a = create_classroom(teacher_a, "Existing A")
    classroom_b = create_classroom(teacher_b, "Existing B")
    invite_a = create_invite(teacher_a, classroom_a)
    request_a = request_membership(learner, invite_a["invite_token"])
    membership_a_id = request_a.json()["classroom_membership_id"]
    owner_a = client_for(teacher_a)
    try:
        approved = owner_a.post(f"/api/v1/classroom-memberships/{membership_a_id}/approve", json={}, headers=headers(str(uuid4())))
        assert approved.status_code == 200
    finally:
        close_client(owner_a)
    repeated_a = request_membership(learner, invite_a["invite_token"])
    assert repeated_a.status_code == 201
    assert repeated_a.json()["classroom_membership_id"] == membership_a_id
    assert repeated_a.json()["state"] == "APPROVED"

    invite_b = create_invite(teacher_b, classroom_b)
    request_b = request_membership(learner, invite_b["invite_token"])
    membership_b_id = request_b.json()["classroom_membership_id"]
    owner_b = client_for(teacher_b)
    try:
        rejected = owner_b.post(f"/api/v1/classroom-memberships/{membership_b_id}/reject", json={}, headers=headers(str(uuid4())))
        assert rejected.status_code == 200
    finally:
        close_client(owner_b)
    repeated_b = request_membership(learner, invite_b["invite_token"])
    assert repeated_b.status_code == 201
    assert repeated_b.json()["classroom_membership_id"] == membership_b_id
    assert repeated_b.json()["state"] == "REJECTED"


def test_membership_request_concurrent_duplicate_produces_one_row() -> None:
    upgrade()
    teacher, learner = f"teacher-request-concurrent-{uuid4()}", f"learner-request-concurrent-{uuid4()}"
    setup_teacher(teacher)
    setup_learner(learner)
    classroom_id = create_classroom(teacher, "Concurrent Request Room")
    invite = create_invite(teacher, classroom_id)
    barrier = Barrier(2)
    client = client_for(learner)

    def submit():
        barrier.wait()
        return client.post(
            "/api/v1/classroom-memberships/requests", json={"invite_token": invite["invite_token"]}, headers=headers(str(uuid4()))
        )

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _: submit(), range(2)))
        assert [response.status_code for response in responses] == [201, 201]
        assert len({response.json()["classroom_membership_id"] for response in responses}) == 1
    finally:
        close_client(client)
    learner_id = asyncio.run(_learner_id_for_subject(learner))
    assert asyncio.run(membership_count(classroom_id, learner_id)) == 1


def test_membership_request_unknown_revoked_and_expired_token() -> None:
    upgrade()
    teacher, learner = f"teacher-request-fail-{uuid4()}", f"learner-request-fail-{uuid4()}"
    setup_teacher(teacher)
    setup_learner(learner)
    classroom_id = create_classroom(teacher, "Request Fail Room")
    revoked_invite = create_invite(teacher, classroom_id)
    owner = client_for(teacher)
    try:
        assert owner.post(f"/api/v1/classroom-invites/{revoked_invite['classroom_invite_id']}/revoke", json={}, headers=headers(str(uuid4()))).status_code == 200
    finally:
        close_client(owner)
    # D49: see test_resolve_unknown_revoked_and_expired -- the expired code has to be minted after
    # the revoked one, and its past expiry is set by hand.
    expired_invite = create_invite(teacher, classroom_id)
    asyncio.run(set_expired(UUID(expired_invite["classroom_invite_id"])))
    assert request_membership(learner, "NOSUCH-CODE").status_code == 404
    assert request_membership(learner, revoked_invite["invite_token"]).status_code == 409
    assert request_membership(learner, expired_invite["invite_token"]).status_code == 409


def test_membership_request_no_automatic_approval_and_no_grade_mutation() -> None:
    upgrade()
    teacher, learner = f"teacher-request-noauto-{uuid4()}", f"learner-request-noauto-{uuid4()}"
    setup_teacher(teacher)
    setup_learner(learner)
    classroom_id = create_classroom(teacher, "No Auto Room", "GRADE_3")
    invite = create_invite(teacher, classroom_id)
    response = request_membership(learner, invite["invite_token"])
    assert response.status_code == 201 and response.json()["state"] == "PENDING"

    async def check_grade() -> None:
        engine = await _engine()
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            learner_id = await _learner_id_for_subject(learner)
            row = await session.get(Learner, learner_id)
            assert row.grade is None
        await engine.dispose()

    asyncio.run(check_grade())


def test_membership_request_replay_body_mismatch_and_rollback() -> None:
    upgrade()
    teacher, learner = f"teacher-request-replay-{uuid4()}", f"learner-request-replay-{uuid4()}"
    setup_teacher(teacher)
    setup_learner(learner)
    classroom_a = create_classroom(teacher, "Replay Request A")
    classroom_b = create_classroom(teacher, "Replay Request B")
    invite_a = create_invite(teacher, classroom_a)
    invite_b = create_invite(teacher, classroom_b)
    key = str(uuid4())
    client = client_for(learner)
    try:
        first = client.post("/api/v1/classroom-memberships/requests", json={"invite_token": invite_a["invite_token"]}, headers=headers(key))
        replay = client.post("/api/v1/classroom-memberships/requests", json={"invite_token": invite_a["invite_token"]}, headers=headers(key))
        assert first.status_code == replay.status_code == 201
        assert replay.json()["classroom_membership_id"] == first.json()["classroom_membership_id"]
        mismatch = client.post("/api/v1/classroom-memberships/requests", json={"invite_token": invite_b["invite_token"]}, headers=headers(key))
        assert mismatch.status_code == 409
    finally:
        close_client(client)

    rollback_key = str(uuid4())
    invite_c_classroom = create_classroom(teacher, "Replay Request C")
    invite_c = create_invite(teacher, invite_c_classroom)
    injected = ClassroomMembershipService()
    injected._audit = _failing_audit
    rollback_client = client_for(learner, injected)
    try:
        failed = rollback_client.post(
            "/api/v1/classroom-memberships/requests", json={"invite_token": invite_c["invite_token"]}, headers=headers(rollback_key)
        )
        assert failed.status_code == 500
    finally:
        close_client(rollback_client)
    learner_id = asyncio.run(_learner_id_for_subject(learner))
    assert asyncio.run(membership_count(invite_c_classroom, learner_id)) == 0
    retry = client_for(learner)
    try:
        assert retry.post(
            "/api/v1/classroom-memberships/requests", json={"invite_token": invite_c["invite_token"]}, headers=headers(rollback_key)
        ).status_code == 201
    finally:
        close_client(retry)


def test_no_token_or_hash_leakage_for_invite_and_membership_flows(caplog) -> None:
    upgrade()
    teacher, learner = f"teacher-leak-{uuid4()}", f"learner-leak-{uuid4()}"
    setup_teacher(teacher)
    setup_learner(learner)
    classroom_id = create_classroom(teacher, "Leak Room")
    caplog.set_level(logging.INFO)
    invite = create_invite(teacher, classroom_id)
    token = invite["invite_token"]
    client = client_for(learner)
    try:
        client.post("/api/v1/classroom-invites/resolve", json={"invite_token": token}, headers=headers(str(uuid4())))
        client.post("/api/v1/classroom-memberships/requests", json={"invite_token": token}, headers=headers(str(uuid4())))
    finally:
        close_client(client)
    log_text = caplog.text
    assert token not in log_text
    assert "classroom-membership-secret-that-must-not-be-logged" not in log_text
    assert "Authorization" not in log_text

    async def scan_db() -> None:
        engine = await _engine()
        async with engine.connect() as connection:
            audit_rows = await connection.execute(select(AuditEvent))
            for row in audit_rows:
                serialized = str(row)
                assert token not in serialized
            idem_rows = await connection.execute(select(IdempotencyRecord))
            for row in idem_rows:
                serialized = str(row)
                assert token not in serialized
        await engine.dispose()

    asyncio.run(scan_db())


# ---------------------------------------------------------------------------
# Teacher membership-request listing
# ---------------------------------------------------------------------------


def test_teacher_request_listing_ownership_states_and_privacy() -> None:
    upgrade()
    teacher_a, teacher_b, learner = f"teacher-a-list-{uuid4()}", f"teacher-b-list-{uuid4()}", f"learner-list-{uuid4()}"
    setup_teacher(teacher_a)
    setup_teacher(teacher_b)
    setup_learner(learner)
    classroom_id = create_classroom(teacher_a, "List Room")
    invite = create_invite(teacher_a, classroom_id)
    request_membership(learner, invite["invite_token"])

    owner = client_for(teacher_a)
    try:
        listing = owner.get(f"/api/v1/classrooms/{classroom_id}/membership-requests")
        assert listing.status_code == 200
        assert len(listing.json()["requests"]) == 1
        entry = listing.json()["requests"][0]
        assert entry["state"] == "PENDING"
        assert "email" not in entry
    finally:
        close_client(owner)

    other = client_for(teacher_b)
    try:
        assert other.get(f"/api/v1/classrooms/{classroom_id}/membership-requests").status_code == 404
    finally:
        close_client(other)

    learner_client = client_for(learner)
    try:
        assert learner_client.get(f"/api/v1/classrooms/{classroom_id}/membership-requests").status_code == 403
    finally:
        close_client(learner_client)


# ---------------------------------------------------------------------------
# Approval
# ---------------------------------------------------------------------------


def test_approval_success_replay_path_mismatch_and_isolation() -> None:
    upgrade()
    teacher_a, teacher_b, learner = f"teacher-a-approve-{uuid4()}", f"teacher-b-approve-{uuid4()}", f"learner-approve-{uuid4()}"
    setup_teacher(teacher_a)
    setup_teacher(teacher_b)
    setup_learner(learner)
    classroom_1 = create_classroom(teacher_a, "Approve Room 1")
    classroom_2 = create_classroom(teacher_a, "Approve Room 2")
    membership_1 = request_membership(learner, create_invite(teacher_a, classroom_1)["invite_token"]).json()["classroom_membership_id"]
    membership_2 = request_membership(learner, create_invite(teacher_a, classroom_2)["invite_token"]).json()["classroom_membership_id"]

    owner = client_for(teacher_a)
    try:
        key = str(uuid4())
        first = owner.post(f"/api/v1/classroom-memberships/{membership_1}/approve", json={}, headers=headers(key))
        replay = owner.post(f"/api/v1/classroom-memberships/{membership_1}/approve", json={}, headers=headers(key))
        assert first.status_code == replay.status_code == 200
        assert replay.json() == first.json()
        # Path mismatch: same key against a different (owned) membership must conflict, not replay.
        mismatch = owner.post(f"/api/v1/classroom-memberships/{membership_2}/approve", json={}, headers=headers(key))
        assert mismatch.status_code == 409
        # A different key against the now-decided membership_1 must conflict.
        already_decided = owner.post(f"/api/v1/classroom-memberships/{membership_1}/approve", json={}, headers=headers(str(uuid4())))
        assert already_decided.status_code == 409
    finally:
        close_client(owner)

    other = client_for(teacher_b)
    try:
        assert other.post(f"/api/v1/classroom-memberships/{membership_2}/approve", json={}, headers=headers(str(uuid4()))).status_code == 404
    finally:
        close_client(other)

    learner_client = client_for(learner)
    try:
        assert learner_client.post(f"/api/v1/classroom-memberships/{membership_2}/approve", json={}, headers=headers(str(uuid4()))).status_code == 403
    finally:
        close_client(learner_client)

    assert asyncio.run(audit_count("classroom_membership.approved", UUID(membership_1))) == 1


def test_approval_second_classroom_conflict_and_concurrent_cross_classroom_approvals() -> None:
    upgrade()
    teacher_a, teacher_b, learner = f"teacher-a-second-{uuid4()}", f"teacher-b-second-{uuid4()}", f"learner-second-{uuid4()}"
    setup_teacher(teacher_a)
    setup_teacher(teacher_b)
    setup_learner(learner)
    classroom_a = create_classroom(teacher_a, "Second Room A")
    classroom_b = create_classroom(teacher_b, "Second Room B")
    membership_a = request_membership(learner, create_invite(teacher_a, classroom_a)["invite_token"]).json()["classroom_membership_id"]
    membership_b = request_membership(learner, create_invite(teacher_b, classroom_b)["invite_token"]).json()["classroom_membership_id"]

    owner_a = client_for(teacher_a)
    try:
        assert owner_a.post(f"/api/v1/classroom-memberships/{membership_a}/approve", json={}, headers=headers(str(uuid4()))).status_code == 200
    finally:
        close_client(owner_a)
    owner_b = client_for(teacher_b)
    try:
        assert owner_b.post(f"/api/v1/classroom-memberships/{membership_b}/approve", json={}, headers=headers(str(uuid4()))).status_code == 409
    finally:
        close_client(owner_b)

    # Genuine concurrency: two different teachers approve two different pending
    # memberships for the same learner at the same time. Uses a fresh learner with
    # no pre-existing approval, since `learner` above is already APPROVED in
    # classroom_a and would correctly conflict on both branches regardless of timing.
    racer = f"learner-race-{uuid4()}"
    setup_learner(racer)
    classroom_c = create_classroom(teacher_a, "Concurrent Room C")
    classroom_d = create_classroom(teacher_b, "Concurrent Room D")
    membership_c = request_membership(racer, create_invite(teacher_a, classroom_c)["invite_token"]).json()["classroom_membership_id"]
    membership_d = request_membership(racer, create_invite(teacher_b, classroom_d)["invite_token"]).json()["classroom_membership_id"]

    client = multi_principal_client()
    barrier = Barrier(2)

    def approve_as(subject: str, membership_id: str):
        barrier.wait()
        return client.post(
            f"/api/v1/classroom-memberships/{membership_id}/approve",
            json={},
            headers=headers(str(uuid4()), subject=subject),
        )

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(
                pool.map(
                    lambda pair: approve_as(*pair),
                    [(teacher_a, membership_c), (teacher_b, membership_d)],
                )
            )
        statuses = sorted(response.status_code for response in results)
        assert statuses == [200, 409]
    finally:
        close_client(client)

    learner_id = asyncio.run(_learner_id_for_subject(racer))

    async def approved_count() -> int:
        engine = await _engine()
        async with engine.connect() as connection:
            count = await connection.scalar(
                select(func.count()).select_from(ClassroomMembership).where(
                    ClassroomMembership.learner_id == learner_id, ClassroomMembership.state == "APPROVED"
                )
            )
        await engine.dispose()
        return count

    assert asyncio.run(approved_count()) == 1


def test_approval_rollback_and_no_grade_mutation() -> None:
    upgrade()
    teacher, learner = f"teacher-approve-rollback-{uuid4()}", f"learner-approve-rollback-{uuid4()}"
    setup_teacher(teacher)
    setup_learner(learner)
    classroom_id = create_classroom(teacher, "Approve Rollback Room", "GRADE_3")
    membership_id = request_membership(learner, create_invite(teacher, classroom_id)["invite_token"]).json()["classroom_membership_id"]

    injected = ClassroomMembershipService()
    injected._audit = _failing_audit
    key, request_id = str(uuid4()), f"approve-rollback-{uuid4()}"
    client = client_for(teacher, injected)
    try:
        failed = client.post(f"/api/v1/classroom-memberships/{membership_id}/approve", json={}, headers=headers(key, request_id))
        assert failed.status_code == 500
        assert failed.json()["error"]["request_id"] == request_id
    finally:
        close_client(client)

    async def check_state_and_grade() -> None:
        engine = await _engine()
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            membership = await session.get(ClassroomMembership, UUID(membership_id))
            assert membership.state == "PENDING"
            learner_id = await _learner_id_for_subject(learner)
            row = await session.get(Learner, learner_id)
            assert row.grade is None
        await engine.dispose()

    asyncio.run(check_state_and_grade())

    retry = client_for(teacher)
    try:
        assert retry.post(f"/api/v1/classroom-memberships/{membership_id}/approve", json={}, headers=headers(key)).status_code == 200
    finally:
        close_client(retry)


# ---------------------------------------------------------------------------
# Rejection
# ---------------------------------------------------------------------------


def test_rejection_success_replay_path_mismatch_conflict_isolation_and_rollback() -> None:
    upgrade()
    teacher_a, teacher_b, learner = f"teacher-a-reject-{uuid4()}", f"teacher-b-reject-{uuid4()}", f"learner-reject-{uuid4()}"
    setup_teacher(teacher_a)
    setup_teacher(teacher_b)
    setup_learner(learner)
    classroom_1 = create_classroom(teacher_a, "Reject Room 1")
    classroom_2 = create_classroom(teacher_a, "Reject Room 2")
    membership_1 = request_membership(learner, create_invite(teacher_a, classroom_1)["invite_token"]).json()["classroom_membership_id"]
    membership_2 = request_membership(learner, create_invite(teacher_a, classroom_2)["invite_token"]).json()["classroom_membership_id"]

    owner = client_for(teacher_a)
    try:
        key = str(uuid4())
        first = owner.post(f"/api/v1/classroom-memberships/{membership_1}/reject", json={}, headers=headers(key))
        replay = owner.post(f"/api/v1/classroom-memberships/{membership_1}/reject", json={}, headers=headers(key))
        assert first.status_code == replay.status_code == 200
        assert replay.json() == first.json()
        mismatch = owner.post(f"/api/v1/classroom-memberships/{membership_2}/reject", json={}, headers=headers(key))
        assert mismatch.status_code == 409
        already_decided = owner.post(f"/api/v1/classroom-memberships/{membership_1}/reject", json={}, headers=headers(str(uuid4())))
        assert already_decided.status_code == 409
    finally:
        close_client(owner)

    other = client_for(teacher_b)
    try:
        assert other.post(f"/api/v1/classroom-memberships/{membership_2}/reject", json={}, headers=headers(str(uuid4()))).status_code == 404
    finally:
        close_client(other)
    learner_client = client_for(learner)
    try:
        assert learner_client.post(f"/api/v1/classroom-memberships/{membership_2}/reject", json={}, headers=headers(str(uuid4()))).status_code == 403
    finally:
        close_client(learner_client)
    assert asyncio.run(audit_count("classroom_membership.rejected", UUID(membership_1))) == 1

    injected = ClassroomMembershipService()
    injected._audit = _failing_audit
    rollback_key = str(uuid4())
    rollback_client = client_for(teacher_a, injected)
    try:
        failed = rollback_client.post(f"/api/v1/classroom-memberships/{membership_2}/reject", json={}, headers=headers(rollback_key))
        assert failed.status_code == 500
    finally:
        close_client(rollback_client)

    async def check_still_pending() -> None:
        engine = await _engine()
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            membership = await session.get(ClassroomMembership, UUID(membership_2))
            assert membership.state == "PENDING"
        await engine.dispose()

    asyncio.run(check_still_pending())
    retry = client_for(teacher_a)
    try:
        assert retry.post(f"/api/v1/classroom-memberships/{membership_2}/reject", json={}, headers=headers(rollback_key)).status_code == 200
    finally:
        close_client(retry)


# ---------------------------------------------------------------------------
# Invite revocation
# ---------------------------------------------------------------------------


def test_revocation_success_replay_path_mismatch_and_isolation() -> None:
    upgrade()
    teacher_a, teacher_b, learner = f"teacher-a-revoke-{uuid4()}", f"teacher-b-revoke-{uuid4()}", f"learner-revoke-{uuid4()}"
    setup_teacher(teacher_a)
    setup_teacher(teacher_b)
    setup_learner(learner)
    # D49: one live code per classroom, so the two invites revoked independently here live in two
    # classrooms -- both owned by teacher_a, which is what the path-mismatch and cross-teacher
    # isolation assertions below require.
    invite_1 = create_invite(teacher_a, create_classroom(teacher_a, "Revoke Room A"))
    invite_2 = create_invite(teacher_a, create_classroom(teacher_a, "Revoke Room B"))

    owner = client_for(teacher_a)
    try:
        key = str(uuid4())
        first = owner.post(f"/api/v1/classroom-invites/{invite_1['classroom_invite_id']}/revoke", json={}, headers=headers(key))
        replay = owner.post(f"/api/v1/classroom-invites/{invite_1['classroom_invite_id']}/revoke", json={}, headers=headers(key))
        assert first.status_code == replay.status_code == 200
        assert replay.json() == first.json()
        assert set(first.json()) == {"classroom_invite_id", "classroom_id", "revoked_at_utc", "row_version", "request_id"}
        # Path mismatch: same key against a different (owned) invite must conflict, not replay.
        mismatch = owner.post(f"/api/v1/classroom-invites/{invite_2['classroom_invite_id']}/revoke", json={}, headers=headers(key))
        assert mismatch.status_code == 409
        # A different key against the already-revoked invite_1 must conflict.
        already_revoked = owner.post(f"/api/v1/classroom-invites/{invite_1['classroom_invite_id']}/revoke", json={}, headers=headers(str(uuid4())))
        assert already_revoked.status_code == 409
    finally:
        close_client(owner)

    other = client_for(teacher_b)
    try:
        assert other.post(f"/api/v1/classroom-invites/{invite_2['classroom_invite_id']}/revoke", json={}, headers=headers(str(uuid4()))).status_code == 404
    finally:
        close_client(other)
    learner_client = client_for(learner)
    try:
        assert learner_client.post(f"/api/v1/classroom-invites/{invite_2['classroom_invite_id']}/revoke", json={}, headers=headers(str(uuid4()))).status_code == 403
    finally:
        close_client(learner_client)
    assert asyncio.run(audit_count("classroom_invite.revoked", UUID(invite_1["classroom_invite_id"]))) == 1


def test_revocation_expired_invite_conflict_and_does_not_mutate_memberships() -> None:
    upgrade()
    teacher, learner = f"teacher-revoke-expired-{uuid4()}", f"learner-revoke-expired-{uuid4()}"
    setup_teacher(teacher)
    setup_learner(learner)
    classroom_id = create_classroom(teacher, "Revoke Expired Room")
    invite = create_invite(teacher, classroom_id)
    membership = request_membership(learner, invite["invite_token"]).json()
    # D49: `invite` is this classroom's one live code and has to stay live, since the membership
    # above hangs off it. The expired invite under test therefore belongs to a second classroom.
    other_invite = create_invite(teacher, create_classroom(teacher, "Revoke Expired Room B"))
    asyncio.run(set_expired(UUID(other_invite["classroom_invite_id"])))
    owner = client_for(teacher)
    try:
        assert owner.post(f"/api/v1/classroom-invites/{other_invite['classroom_invite_id']}/revoke", json={}, headers=headers(str(uuid4()))).status_code == 409
        revoked = owner.post(f"/api/v1/classroom-invites/{invite['classroom_invite_id']}/revoke", json={}, headers=headers(str(uuid4())))
        assert revoked.status_code == 200
    finally:
        close_client(owner)

    async def check_invite_and_membership() -> None:
        engine = await _engine()
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            row = await session.get(ClassroomInvite, UUID(invite["classroom_invite_id"]))
            assert row is not None  # not deleted
            existing_membership = await session.get(ClassroomMembership, UUID(membership["classroom_membership_id"]))
            assert existing_membership.state == "PENDING"  # unaffected by revoking the invite that created it
        await engine.dispose()

    asyncio.run(check_invite_and_membership())


def test_revoked_invite_fails_resolve_and_membership_request() -> None:
    upgrade()
    teacher, learner = f"teacher-revoke-fail-{uuid4()}", f"learner-revoke-fail-{uuid4()}"
    setup_teacher(teacher)
    setup_learner(learner)
    classroom_id = create_classroom(teacher, "Revoke Fail Room")
    invite = create_invite(teacher, classroom_id)
    owner = client_for(teacher)
    try:
        assert owner.post(f"/api/v1/classroom-invites/{invite['classroom_invite_id']}/revoke", json={}, headers=headers(str(uuid4()))).status_code == 200
    finally:
        close_client(owner)
    client = client_for(learner)
    try:
        assert client.post("/api/v1/classroom-invites/resolve", json={"invite_token": invite["invite_token"]}, headers=headers(str(uuid4()))).status_code == 409
    finally:
        close_client(client)
    assert request_membership(learner, invite["invite_token"]).status_code == 409


def test_revocation_concurrent_same_key_produces_one_result() -> None:
    upgrade()
    teacher = f"teacher-revoke-concurrent-{uuid4()}"
    setup_teacher(teacher)
    classroom_id = create_classroom(teacher, "Revoke Concurrent Room")
    invite = create_invite(teacher, classroom_id)
    key, barrier = str(uuid4()), Barrier(2)
    client = client_for(teacher)

    def submit():
        barrier.wait()
        return client.post(f"/api/v1/classroom-invites/{invite['classroom_invite_id']}/revoke", json={}, headers=headers(key))

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _: submit(), range(2)))
        assert [response.status_code for response in responses] == [200, 200]
        assert responses[0].json() == responses[1].json()
    finally:
        close_client(client)

    async def check_single_revocation() -> None:
        engine = await _engine()
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            row = await session.get(ClassroomInvite, UUID(invite["classroom_invite_id"]))
            assert row.revoked_at_utc is not None
            assert row.row_version == 1
        await engine.dispose()

    asyncio.run(check_single_revocation())


def test_revocation_rollback_and_no_token_or_hash_leakage(caplog) -> None:
    upgrade()
    teacher = f"teacher-revoke-rollback-{uuid4()}"
    setup_teacher(teacher)
    classroom_id = create_classroom(teacher, "Revoke Rollback Room")
    invite = create_invite(teacher, classroom_id)
    injected = ClassroomMembershipService()
    injected._audit = _failing_audit
    key, request_id = str(uuid4()), f"revoke-rollback-{uuid4()}"
    caplog.set_level(logging.INFO)
    client = client_for(teacher, injected)
    try:
        failed = client.post(f"/api/v1/classroom-invites/{invite['classroom_invite_id']}/revoke", json={}, headers=headers(key, request_id))
        assert failed.status_code == 500
        assert invite["invite_token"] not in failed.text
    finally:
        close_client(client)
    assert invite["invite_token"] not in caplog.text
    assert "Authorization" not in caplog.text

    async def check_not_revoked() -> None:
        engine = await _engine()
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            row = await session.get(ClassroomInvite, UUID(invite["classroom_invite_id"]))
            assert row.revoked_at_utc is None
        await engine.dispose()

    asyncio.run(check_not_revoked())
    retry = client_for(teacher)
    try:
        revoked = retry.post(f"/api/v1/classroom-invites/{invite['classroom_invite_id']}/revoke", json={}, headers=headers(key))
        assert revoked.status_code == 200
        assert "token" not in revoked.json() and "token_hash" not in revoked.json()
    finally:
        close_client(retry)


# ---------------------------------------------------------------------------
# Read endpoints and cross-account isolation
# ---------------------------------------------------------------------------


def test_read_endpoints_teacher_learners_and_learner_memberships() -> None:
    upgrade()
    teacher, learner_a, learner_b = f"teacher-read-{uuid4()}", f"learner-a-read-{uuid4()}", f"learner-b-read-{uuid4()}"
    setup_teacher(teacher)
    setup_learner(learner_a)
    setup_learner(learner_b)
    classroom_1 = create_classroom(teacher, "Read Room 1")
    classroom_2 = create_classroom(teacher, "Read Room 2")

    approved_membership = request_membership(learner_a, create_invite(teacher, classroom_1)["invite_token"]).json()["classroom_membership_id"]
    owner = client_for(teacher)
    try:
        assert owner.post(f"/api/v1/classroom-memberships/{approved_membership}/approve", json={}, headers=headers(str(uuid4()))).status_code == 200
    finally:
        close_client(owner)
    pending_membership = request_membership(learner_a, create_invite(teacher, classroom_2)["invite_token"]).json()

    owner = client_for(teacher)
    try:
        learners_1 = owner.get(f"/api/v1/classrooms/{classroom_1}/learners")
        assert learners_1.status_code == 200
        assert len(learners_1.json()["learners"]) == 1
        assert learners_1.json()["learners"][0]["membership_state"] == "APPROVED"
        assert "email" not in learners_1.json()["learners"][0]
        learners_2 = owner.get(f"/api/v1/classrooms/{classroom_2}/learners")
        assert learners_2.status_code == 200 and learners_2.json()["learners"] == []
    finally:
        close_client(owner)

    learner_a_client = client_for(learner_a)
    try:
        memberships = learner_a_client.get("/api/v1/learner/classrooms")
        assert memberships.status_code == 200
        states = {entry["state"] for entry in memberships.json()["memberships"]}
        assert states == {"APPROVED", "PENDING"}
        assert len(memberships.json()["memberships"]) == 2
    finally:
        close_client(learner_a_client)

    learner_b_client = client_for(learner_b)
    try:
        empty = learner_b_client.get("/api/v1/learner/classrooms")
        assert empty.status_code == 200 and empty.json()["memberships"] == []
        assert learner_b_client.get(f"/api/v1/classrooms/{classroom_1}/learners").status_code == 403
    finally:
        close_client(learner_b_client)


def test_normalize_join_code_strips_separators_and_uppercases() -> None:
    assert normalize_join_code("m7kp-4x9d") == "M7KP4X9D"
    assert normalize_join_code(" M7KP 4X9D ") == "M7KP4X9D"
    assert normalize_join_code("M7KP4X9D") == "M7KP4X9D"
