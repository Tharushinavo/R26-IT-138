"""BE-G1 — the learner activation path, end-to-end through real FastAPI routes and real Postgres.

Regression proof for the blocker this batch fixes: ``Learner.grade`` was written in exactly one
place in ``backend/app/`` (``application/profile_classroom.py``, which writes ``grade=None``) and
membership approval never touched it, while ``application/opportunity_selection.py`` fails closed
with ``ConflictError``/409 when ``learner.grade is None``. A learner could therefore complete the
whole onboarding flow — profile, join code, membership request, teacher approval, session start —
and then have EVERY question request 409 forever. There was no path in the product to a usable
learner.

Scope note: the grade assigned on approval is ROSTER METADATA the teacher already chose when
creating the classroom (``Classroom.grade`` is NOT NULL). It selects which catalogue templates are
eligible; it sets no mastery prior, no BKT parameter, no difficulty ladder, no session bound, and
no attempt limit. This file clears no gate-B item and authorizes no real-child, pilot, or
production use — TEST-provenance DRAFT bundles only, per
``backend/provenance/component-b-be4-engineering-continuation-instruction.json``.
"""

from __future__ import annotations

import asyncio
import hashlib
import subprocess
from uuid import UUID, uuid4

import pytest

pytest.importorskip(
    "component_b_generator",
    reason="upadya-component-b-live-engine is not installed; see backend/requirements.in",
)

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.routes.b_session import service as b_session_service_dep
from app.application.b_session_lifecycle import BSessionLifecycleService
from app.application.opportunity_selection import _ENGINEERING_TEST_BUNDLES
from app.core.config import get_settings
from app.domain.principal import AuthenticatedPrincipal
from app.infrastructure.auth import get_authenticated_principal
from app.infrastructure.database import async_database_url
from app.infrastructure.persistence_models import (
    AppUser,
    AppUserLearnerLink,
    ClassroomMembership,
    Learner,
    RuntimeBundleRecord,
)
from app.main import app


ENGINEERING_BUNDLE_VERSION = "be3b-test-fixture-1.0"
assert ENGINEERING_BUNDLE_VERSION in _ENGINEERING_TEST_BUNDLES


def alembic(*args: str) -> None:
    subprocess.run(["alembic", *args], check=True)


def isolated_database():
    database_engine = create_async_engine(async_database_url(get_settings().database_url), poolclass=NullPool)
    factory = async_sessionmaker(database_engine, expire_on_commit=False, class_=AsyncSession)
    return database_engine, factory


def provenance(resource_type: str, resource_id: UUID) -> dict[str, object]:
    return {
        "system_actor": "be-g1-isolated-test",
        "request_id": f"test-{uuid4()}",
        "operation_or_event_type": "test.learner_activation_path",
        "reason_code": "ISOLATED_SYNTHETIC_TEST",
        "resource_type": resource_type,
        "resource_id": resource_id,
        "source_class": "TEST",
        "source_system": "be-g1-isolated-test-suite",
        "environment": "test",
        "schema_revision": "20260723_0001",
    }


async def _ensure_engineering_test_bundle() -> RuntimeBundleRecord:
    _, factory = isolated_database()
    async with factory() as session:
        existing = await session.scalar(
            select(RuntimeBundleRecord).where(RuntimeBundleRecord.bundle_version == ENGINEERING_BUNDLE_VERSION)
        )
        if existing is not None:
            return existing
        bundle_id = uuid4()
        record = RuntimeBundleRecord(
            runtime_bundle_record_id=bundle_id,
            bundle_version=ENGINEERING_BUNDLE_VERSION,
            manifest_checksum=hashlib.sha256(b"be-g1-engineering-test-bundle-db-stub").hexdigest(),
            publication_state="PUBLISHED",
            approval_status="APPROVED",
            immutable_after_publication=True,
            **provenance("b_runtime_bundle_record", bundle_id),
        )
        session.add(record)
        await session.commit()
        return record


def _pinned_lifecycle_service(bundle_record: RuntimeBundleRecord) -> BSessionLifecycleService:
    """``POST /api/v1/b/sessions`` pins to whichever bundle ``find_current_approved_published``
    (most-recently-created PUBLISHED+APPROVED) resolves to, and other test files in this shared
    dev database freely insert their own APPROVED bundles with later timestamps. Pin
    deterministically to the known BE3b TEST-provenance DRAFT fixture bundle, exactly as
    ``test_be4f_transactional_sweep.py`` already does."""

    async def _resolve(_session) -> RuntimeBundleRecord:
        return bundle_record

    service = BSessionLifecycleService()
    service._resolve_pinnable_bundle = _resolve
    return service


def client_for(subject: str, *, bundle_record: RuntimeBundleRecord | None = None) -> TestClient:
    app.dependency_overrides[get_authenticated_principal] = lambda: AuthenticatedPrincipal(
        user_id=subject, email="verified@example.test"
    )
    if bundle_record is not None:
        app.dependency_overrides[b_session_service_dep] = lambda: _pinned_lifecycle_service(bundle_record)
    client = TestClient(app)
    client.__enter__()
    return client


def close_client(client: TestClient) -> None:
    client.__exit__(None, None, None)
    app.dependency_overrides.clear()


def headers(key: str | None = None, request_id: str | None = None) -> dict[str, str]:
    result = {
        "X-Request-ID": request_id or f"req-{uuid4()}",
        "Authorization": "Bearer be-g1-learner-activation-secret-that-must-not-be-logged",
    }
    if key is not None:
        result["Idempotency-Key"] = key
    return result


# ---------------------------------------------------------------------------
# Direct database assertions (the fix is a DB write, not a response-shape change)
# ---------------------------------------------------------------------------


async def _learner_id_for_subject(subject: str) -> UUID:
    _, factory = isolated_database()
    async with factory() as session:
        user = await session.scalar(select(AppUser).where(AppUser.supabase_subject == subject))
        assert user is not None
        link = await session.scalar(select(AppUserLearnerLink).where(AppUserLearnerLink.user_id == user.user_id))
        assert link is not None
        return link.learner_id


async def _learner_grade(learner_id: UUID) -> int | None:
    _, factory = isolated_database()
    async with factory() as session:
        learner = await session.get(Learner, learner_id)
        assert learner is not None
        return learner.grade


async def _membership_state(membership_id: UUID) -> str:
    _, factory = isolated_database()
    async with factory() as session:
        membership = await session.get(ClassroomMembership, membership_id)
        assert membership is not None
        return membership.state


# ---------------------------------------------------------------------------
# Onboarding chain drivers (real HTTP, one authenticated principal per role)
# ---------------------------------------------------------------------------


def onboard_teacher_with_classroom(subject: str, classroom_name: str, grade: str) -> tuple[UUID, str]:
    """Teacher profile -> classroom -> invite. Returns (classroom_id, invite_token)."""
    client = client_for(subject)
    try:
        profile = client.post("/api/v1/teacher/profile", json={"name": "Owner"}, headers=headers(str(uuid4())))
        assert profile.status_code == 201, profile.text
        created = client.post(
            "/api/v1/classrooms", json={"name": classroom_name, "grade": grade}, headers=headers(str(uuid4()))
        )
        assert created.status_code == 201, created.text
        classroom_id = UUID(created.json()["classroom_id"])
        invite = client.post(f"/api/v1/classrooms/{classroom_id}/invites", json={}, headers=headers(str(uuid4())))
        assert invite.status_code == 201, invite.text
        assert invite.json()["invite_token"]
        return classroom_id, invite.json()["invite_token"]
    finally:
        close_client(client)


def onboard_learner_up_to_pending(subject: str, invite_token: str, expected_grade: str) -> UUID:
    """Learner profile -> resolve join code -> membership request. Returns the membership id."""
    client = client_for(subject)
    try:
        profile = client.post("/api/v1/learner/profile", json={"name": "Learner"}, headers=headers(str(uuid4())))
        assert profile.status_code == 201, profile.text
        resolved = client.post(
            "/api/v1/classroom-invites/resolve", json={"invite_token": invite_token}, headers=headers(str(uuid4()))
        )
        assert resolved.status_code == 200, resolved.text
        assert resolved.json()["grade"] == expected_grade
        requested = client.post(
            "/api/v1/classroom-memberships/requests",
            json={"invite_token": invite_token},
            headers=headers(str(uuid4())),
        )
        assert requested.status_code == 201, requested.text
        assert requested.json()["state"] == "PENDING"
        return UUID(requested.json()["classroom_membership_id"])
    finally:
        close_client(client)


def decide_membership(teacher_subject: str, membership_id: UUID, decision: str, key: str | None = None):
    client = client_for(teacher_subject)
    try:
        return client.post(
            f"/api/v1/classroom-memberships/{membership_id}/{decision}",
            json={},
            headers=headers(key or str(uuid4())),
        )
    finally:
        close_client(client)


# ---------------------------------------------------------------------------
# 1. The blocker itself: the complete chain must end in a served question
# ---------------------------------------------------------------------------


def _run_activation_chain(classroom_grade: str, expected_learner_grade: int) -> None:
    alembic("upgrade", "head")
    bundle_record = asyncio.run(_ensure_engineering_test_bundle())
    teacher = f"be-g1-teacher-{classroom_grade.lower()}-{uuid4()}"
    learner = f"be-g1-learner-{classroom_grade.lower()}-{uuid4()}"

    _, invite_token = onboard_teacher_with_classroom(teacher, f"Activation {uuid4()}", classroom_grade)
    membership_id = onboard_learner_up_to_pending(learner, invite_token, classroom_grade)

    learner_id = asyncio.run(_learner_id_for_subject(learner))
    # Precondition: the profile route leaves grade NULL, which is what used to strand the learner.
    assert asyncio.run(_learner_grade(learner_id)) is None

    approved = decide_membership(teacher, membership_id, "approve")
    assert approved.status_code == 200, approved.text
    assert approved.json()["state"] == "APPROVED"

    # The fix, asserted directly against the database.
    assert asyncio.run(_learner_grade(learner_id)) == expected_learner_grade

    client = client_for(learner, bundle_record=bundle_record)
    try:
        started = client.post("/api/v1/b/sessions", json=None, headers=headers(str(uuid4())))
        assert started.status_code == 201, started.text
        session_id = started.json()["session_id"]

        # The whole point of this file: this used to be a permanent 409.
        opportunity = client.post(
            f"/api/v1/b/sessions/{session_id}/opportunities", json=None, headers=headers(str(uuid4()))
        )
        assert opportunity.status_code == 201, opportunity.text
        assert opportunity.json()["item_opportunity_id"]
    finally:
        close_client(client)


def test_grade_2_learner_reaches_a_served_question_through_the_whole_onboarding_chain() -> None:
    _run_activation_chain("GRADE_2", 2)


def test_grade_3_learner_reaches_a_served_question_through_the_whole_onboarding_chain() -> None:
    _run_activation_chain("GRADE_3", 3)


# ---------------------------------------------------------------------------
# 2. Rejection must never touch grade
# ---------------------------------------------------------------------------


def test_rejection_leaves_learner_grade_null() -> None:
    alembic("upgrade", "head")
    teacher, learner = f"be-g1-teacher-reject-{uuid4()}", f"be-g1-learner-reject-{uuid4()}"
    _, invite_token = onboard_teacher_with_classroom(teacher, f"Reject {uuid4()}", "GRADE_3")
    membership_id = onboard_learner_up_to_pending(learner, invite_token, "GRADE_3")
    learner_id = asyncio.run(_learner_id_for_subject(learner))

    rejected = decide_membership(teacher, membership_id, "reject")
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["state"] == "REJECTED"

    assert asyncio.run(_membership_state(membership_id)) == "REJECTED"
    assert asyncio.run(_learner_grade(learner_id)) is None


# ---------------------------------------------------------------------------
# 3. Idempotency: replay writes the same grade, re-approval stays fail-closed
# ---------------------------------------------------------------------------


def test_approval_replay_and_double_approval_leave_the_same_grade() -> None:
    alembic("upgrade", "head")
    teacher, learner = f"be-g1-teacher-idem-{uuid4()}", f"be-g1-learner-idem-{uuid4()}"
    _, invite_token = onboard_teacher_with_classroom(teacher, f"Idempotent {uuid4()}", "GRADE_2")
    membership_id = onboard_learner_up_to_pending(learner, invite_token, "GRADE_2")
    learner_id = asyncio.run(_learner_id_for_subject(learner))

    key = str(uuid4())
    first = decide_membership(teacher, membership_id, "approve", key)
    assert first.status_code == 200, first.text
    assert asyncio.run(_learner_grade(learner_id)) == 2

    # Same key -> idempotent replay, returns before any grade write, byte-identical body.
    replay = decide_membership(teacher, membership_id, "approve", key)
    assert replay.status_code == 200, replay.text
    assert replay.json() == first.json()
    assert asyncio.run(_learner_grade(learner_id)) == 2

    # Fresh key -> the `state != "PENDING"` guard still fails closed, grade untouched.
    repeat = decide_membership(teacher, membership_id, "approve")
    assert repeat.status_code == 409, repeat.text
    assert asyncio.run(_learner_grade(learner_id)) == 2
    assert asyncio.run(_membership_state(membership_id)) == "APPROVED"


# ---------------------------------------------------------------------------
# 4. The mapping is explicit, and must fail loudly rather than mis-map
# ---------------------------------------------------------------------------


def test_classroom_grade_mapping_is_explicit_and_total_over_the_check_constraint() -> None:
    from app.application.classroom_membership import _CLASSROOM_GRADE_TO_LEARNER_GRADE

    assert _CLASSROOM_GRADE_TO_LEARNER_GRADE == {"GRADE_2": 2, "GRADE_3": 3}
    with pytest.raises(KeyError):
        _CLASSROOM_GRADE_TO_LEARNER_GRADE["GRADE_4"]
