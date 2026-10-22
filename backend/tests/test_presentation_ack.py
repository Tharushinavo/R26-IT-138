"""POST .../opportunities/{id}/presented -- the learner-presentation acknowledgement.

The owner ruling (2026-09-27) moved the answering clock from SELECTION to the moment the question
is actually on the child's screen, because prefetching meant selection happened before the child
was looking at anything, and the governance register already rules that "infrastructure failure is
never learner failure". These prove the two properties that make a client-supplied start safe:
the first acknowledgement anchors, and nothing after it can move the deadline in either direction.
"""

import asyncio
import subprocess
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.application.opportunity_selection import DEFAULT_TIMEOUT
from app.core.config import get_settings
from app.domain.principal import AuthenticatedPrincipal
from app.infrastructure.auth import get_authenticated_principal
from app.infrastructure.database import async_database_url
from app.infrastructure.persistence_models import (
    AppUser,
    AppUserLearnerLink,
    ItemOpportunityRecord,
    Learner,
    RuntimeBundleRecord,
    SessionRecord,
)
from app.main import app


def upgrade() -> None:
    subprocess.run(["alembic", "upgrade", "head"], check=True)


def isolated_database():
    engine = create_async_engine(async_database_url(get_settings().database_url), poolclass=NullPool)
    return engine, async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


def provenance(resource_type: str, resource_id: UUID) -> dict[str, object]:
    return {
        "system_actor": "presentation-ack-isolated-test",
        "request_id": f"test-{uuid4()}",
        "operation_or_event_type": "test.presentation_ack",
        "reason_code": "ISOLATED_SYNTHETIC_TEST",
        "resource_type": resource_type,
        "resource_id": resource_id,
        "source_class": "TEST",
        "source_system": "presentation-ack-isolated-test-suite",
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


async def _bundle(session: AsyncSession) -> UUID:
    # An active session requires an ELIGIBLE bundle (published, approved, immutable) -- reusing
    # just any row picks up another suite's DRAFT and trips the check constraint.
    existing = await session.scalar(
        select(RuntimeBundleRecord)
        .where(
            RuntimeBundleRecord.publication_state == "PUBLISHED",
            RuntimeBundleRecord.approval_status == "APPROVED",
            RuntimeBundleRecord.immutable_after_publication.is_(True),
        )
        .limit(1)
    )
    if existing is not None:
        return existing.runtime_bundle_record_id
    record_id = uuid4()
    session.add(
        RuntimeBundleRecord(
            runtime_bundle_record_id=record_id,
            bundle_version=f"ack-test-{record_id}",
            manifest_checksum=uuid4().hex + uuid4().hex,
            publication_state="PUBLISHED",
            approval_status="APPROVED",
            immutable_after_publication=True,
            **provenance("b_runtime_bundle_record", record_id),
        )
    )
    await session.flush()
    return record_id


async def seed(state: str = "OPEN", *, session_state: str = "active"):
    """A learner with an active session holding one un-presented opportunity."""
    engine, factory = isolated_database()
    async with factory() as s:
        bundle_id = await _bundle(s)
        subject, user_id = f"subject-{uuid4()}", uuid4()
        s.add(AppUser(user_id=user_id, supabase_subject=subject, status="active", profile_type="LEARNER", **provenance("app_user", user_id)))
        learner_id = uuid4()
        s.add(Learner(learner_id=learner_id, grade=2, status="active", **provenance("b_learner", learner_id)))
        await s.flush()
        link_id = uuid4()
        s.add(AppUserLearnerLink(link_id=link_id, user_id=user_id, learner_id=learner_id, **provenance("app_user_learner_link", link_id)))
        session_id = uuid4()
        s.add(
            SessionRecord(
                session_id=session_id, learner_id=learner_id, runtime_bundle_record_id=bundle_id,
                state=session_state, expires_at_utc=None, row_version=0, **provenance("b_session", session_id),
            )
        )
        await s.flush()
        now = datetime.now(UTC)
        opportunity_id = uuid4()
        s.add(
            ItemOpportunityRecord(
                item_opportunity_id=opportunity_id, session_id=session_id, learner_id=learner_id,
                skill_id="counting", item_template_id="B-CNT01-SEQ-CONTINUE", opportunity_index=1,
                state=state,
                # As `open_opportunity` now writes it: not yet presented, with a provisional
                # deadline measured from selection.
                presented_at_utc=None,
                timeout_deadline_utc=now + DEFAULT_TIMEOUT,
                selection_provenance={"source": "test"}, row_version=0,
                **provenance("b_item_opportunity", opportunity_id),
            )
        )
        await s.commit()
    await engine.dispose()
    return subject, session_id, opportunity_id


async def read_opportunity(opportunity_id: UUID) -> ItemOpportunityRecord:
    engine, factory = isolated_database()
    async with factory() as s:
        record = await s.get(ItemOpportunityRecord, opportunity_id)
    await engine.dispose()
    return record


def ack(client: TestClient, session_id: UUID, opportunity_id: UUID):
    return client.post(f"/api/v1/b/sessions/{session_id}/opportunities/{opportunity_id}/presented")


def test_selection_no_longer_marks_the_question_as_presented() -> None:
    """The premise of the whole change: an opportunity is un-presented until the child sees it."""
    upgrade()
    _, _, opportunity_id = asyncio.run(seed())
    assert asyncio.run(read_opportunity(opportunity_id)).presented_at_utc is None


def test_first_acknowledgement_anchors_the_clock_at_the_render() -> None:
    upgrade()
    subject, session_id, opportunity_id = asyncio.run(seed())
    before = asyncio.run(read_opportunity(opportunity_id))
    client = client_for(subject)
    try:
        sent_at = datetime.now(UTC)
        response = ack(client, session_id, opportunity_id)
        assert response.status_code == 200
        body = response.json()
        assert body["anchored"] is True
        assert body["item_opportunity_id"] == str(opportunity_id)
        assert body["request_id"] == response.headers["X-Request-ID"]
    finally:
        close_client(client)

    after = asyncio.run(read_opportunity(opportunity_id))
    assert after.presented_at_utc is not None
    # The clock now runs from the render, so the deadline MOVED LATER than the one selection wrote.
    assert after.timeout_deadline_utc > before.timeout_deadline_utc
    # ...and it is the governed span from the acknowledgement, not an arbitrary extension.
    assert abs((after.timeout_deadline_utc - after.presented_at_utc) - DEFAULT_TIMEOUT) < timedelta(seconds=2)
    assert abs((after.presented_at_utc - sent_at)) < timedelta(seconds=30)


def test_later_acknowledgements_are_no_ops_and_cannot_buy_more_time() -> None:
    """The property that makes a client-supplied start safe. A remount, relaunch, retry or a
    deliberate reload must not extend the deadline -- nor shorten it."""
    upgrade()
    subject, session_id, opportunity_id = asyncio.run(seed())
    client = client_for(subject)
    try:
        first = ack(client, session_id, opportunity_id).json()
        anchored = asyncio.run(read_opportunity(opportunity_id))
        for _ in range(3):
            repeat = ack(client, session_id, opportunity_id)
            assert repeat.status_code == 200
            body = repeat.json()
            assert body["anchored"] is False
            assert body["server_timeout_deadline_utc"] == first["server_timeout_deadline_utc"]
    finally:
        close_client(client)

    settled = asyncio.run(read_opportunity(opportunity_id))
    assert settled.presented_at_utc == anchored.presented_at_utc
    assert settled.timeout_deadline_utc == anchored.timeout_deadline_utc


def test_a_closed_opportunity_cannot_be_re_anchored() -> None:
    """Its deadline has already done its job; moving it would rewrite a finished question."""
    upgrade()
    subject, session_id, opportunity_id = asyncio.run(seed(state="CLOSED"))
    client = client_for(subject)
    try:
        response = ack(client, session_id, opportunity_id)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "CONFLICT"
    finally:
        close_client(client)
    assert asyncio.run(read_opportunity(opportunity_id)).presented_at_utc is None


def test_another_learners_opportunity_is_not_found_and_is_not_anchored() -> None:
    upgrade()
    _, _, victim_opportunity = asyncio.run(seed())
    attacker_subject, attacker_session, _ = asyncio.run(seed())
    client = client_for(attacker_subject)
    try:
        assert ack(client, attacker_session, victim_opportunity).status_code == 404
    finally:
        close_client(client)
    assert asyncio.run(read_opportunity(victim_opportunity)).presented_at_utc is None


def test_unknown_session_and_unknown_opportunity_are_404() -> None:
    upgrade()
    subject, session_id, opportunity_id = asyncio.run(seed())
    client = client_for(subject)
    try:
        assert ack(client, uuid4(), opportunity_id).status_code == 404
        assert ack(client, session_id, uuid4()).status_code == 404
    finally:
        close_client(client)


def test_unauthenticated_is_401_and_anchors_nothing() -> None:
    upgrade()
    _, session_id, opportunity_id = asyncio.run(seed())
    response = TestClient(app).post(
        f"/api/v1/b/sessions/{session_id}/opportunities/{opportunity_id}/presented"
    )
    assert response.status_code == 401
    assert asyncio.run(read_opportunity(opportunity_id)).presented_at_utc is None
