"""BE4f (BEplan §9 BE4.7) — the full transactional sweep + Exit Gate, end-to-end through real
FastAPI routes (``TestClient``) and real Postgres, exercising the BE4a-e services together as one
integrated learner session rather than in isolation (each already has its own dedicated,
service-level test file: ``test_be4a_opportunity_persistence.py`` .. ``test_be4e_session_completion
.py``). This file adds only what BEplan §9 BE4.7 asks for and the earlier batches do not already
cover at the route level: a whole-session flow through every path, concurrency at the HTTP layer,
DB failure BEFORE the BKT/mastery calculation (BE4c/test_be4c only covers AFTER, at commit), clock
disagreement, grade-gate/deferred-template exclusion sustained across an entire session, and a
combined public-payload + structured-log field scan across every BE4 route in one place.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from uuid import UUID, uuid4

import pytest

pytest.importorskip(
    "component_b_generator",
    reason="upadya-component-b-live-engine is not installed; see backend/requirements.in",
)

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import app.application.opportunity_selection as opportunity_selection_module
from app.api.routes.b_session import (
    attempt_submission_service as attempt_submission_service_dep,
    service as b_session_service_dep,
)
from app.application.attempt_submission import AttemptSubmissionService
from app.application.b_session_lifecycle import BSessionLifecycleService
from app.application.opportunity_selection import _ENGINEERING_TEST_BUNDLES
from app.application.session_completion import MAX_OPPORTUNITIES_PER_SESSION
from app.core.config import get_settings
from app.domain.principal import AuthenticatedPrincipal
from app.infrastructure.auth import get_authenticated_principal
from app.infrastructure.database import async_database_url
from app.infrastructure.persistence_models import (
    AttemptRecord,
    HintEventRecord,
    ItemOpportunityRecord,
    LearnerSkillStateRecord,
    RuntimeBundleRecord,
    SkillStateTransitionRecord,
)
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from app.main import app


ENGINEERING_BUNDLE_VERSION = "be3b-test-fixture-1.0"
_MANIFEST_PATH, _CATALOGUE_PATH = _ENGINEERING_TEST_BUNDLES[ENGINEERING_BUNDLE_VERSION]
DEFERRED_TEMPLATE_ID = "B-CNT05-FORWARD-FROM-N"  # DEFERRED_CALIBRATION_PENDING in the fixture catalogue


def alembic(*args: str) -> None:
    subprocess.run(["alembic", *args], check=True)


def isolated_database():
    database_engine = create_async_engine(async_database_url(get_settings().database_url), poolclass=NullPool)
    factory = async_sessionmaker(database_engine, expire_on_commit=False, class_=AsyncSession)
    return database_engine, factory


def provenance(resource_type: str, resource_id: UUID) -> dict[str, object]:
    return {
        "system_actor": "be4f-isolated-test",
        "request_id": f"test-{uuid4()}",
        "operation_or_event_type": "test.be4f_transactional_sweep",
        "reason_code": "ISOLATED_SYNTHETIC_TEST",
        "resource_type": resource_type,
        "resource_id": resource_id,
        "source_class": "TEST",
        "source_system": "be4f-isolated-test-suite",
        "environment": "test",
        "schema_revision": "20260728_0004",
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
            manifest_checksum=hashlib.sha256(b"be4f-engineering-test-bundle-db-stub").hexdigest(),
            publication_state="PUBLISHED",
            approval_status="APPROVED",
            immutable_after_publication=True,
            **provenance("b_runtime_bundle_record", bundle_id),
        )
        session.add(record)
        await session.commit()
        return record


def _pinned_lifecycle_service(bundle_record: RuntimeBundleRecord) -> BSessionLifecycleService:
    """Route-level ``POST /api/v1/b/sessions`` pins to whichever bundle
    ``find_current_approved_published`` (most-recently-created PUBLISHED+APPROVED) resolves to —
    other test files in this shared dev database freely insert their own APPROVED bundles with
    later timestamps, so relying on that ordering here would be flaky. Deterministically pinning
    to the known BE3b TEST-provenance DRAFT fixture bundle, the same way
    ``test_b_session_lifecycle.py::test_start_fails_closed_when_no_approved_bundle_exists``
    already overrides ``_resolve_pinnable_bundle`` for its own deterministic scenario."""

    async def _resolve(_session) -> RuntimeBundleRecord:
        return bundle_record

    service = BSessionLifecycleService()
    service._resolve_pinnable_bundle = _resolve
    return service


def client_for(subject: str, *, bundle_record: RuntimeBundleRecord, overrides: dict | None = None) -> TestClient:
    app.dependency_overrides[get_authenticated_principal] = lambda: AuthenticatedPrincipal(
        user_id=subject, email="verified@example.test"
    )
    app.dependency_overrides[b_session_service_dep] = lambda: _pinned_lifecycle_service(bundle_record)
    for dependency, factory in (overrides or {}).items():
        app.dependency_overrides[dependency] = factory
    client = TestClient(app)
    client.__enter__()
    return client


def close_client(client: TestClient) -> None:
    client.__exit__(None, None, None)
    app.dependency_overrides.clear()


def headers(key: str | None = None, request_id: str | None = None) -> dict[str, str]:
    result = {
        "X-Request-ID": request_id or f"req-{uuid4()}",
        "Authorization": "Bearer be4f-transactional-sweep-secret-that-must-not-be-logged",
    }
    if key is not None:
        result["Idempotency-Key"] = key
    return result


def setup_learner(client: TestClient, subject: str, *, grade: int = 3, name: str = "Learner") -> None:
    """The ``/api/v1/learner/profile`` route creates a learner with ``grade=None`` (grade is
    only ever assigned via classroom-membership approval, which is out of this file's scope) —
    every BE4 opportunity-selection call requires a non-null grade
    (``opportunity_selection.OpportunitySelectionService`` fails closed with ``ConflictError``
    otherwise), so this directly sets it afterward, the same way ``test_be4b_adaptive_selection.
    py`` seeds ``Learner(grade=...)`` directly rather than routing through classroom membership."""
    assert client.post("/api/v1/learner/profile", json={"name": name}, headers=headers(str(uuid4()))).status_code == 201
    asyncio.run(_set_learner_grade(subject, grade))


async def _set_learner_grade(subject: str, grade: int) -> None:
    _, factory = isolated_database()
    async with factory() as session:
        from app.infrastructure.persistence_models import AppUser, AppUserLearnerLink, Learner

        user = await session.scalar(select(AppUser).where(AppUser.supabase_subject == subject))
        link = await session.scalar(select(AppUserLearnerLink).where(AppUserLearnerLink.user_id == user.user_id))
        learner = await session.get(Learner, link.learner_id)
        learner.grade = grade
        await session.commit()


async def _skill_state_transitions_for_session(session_id: UUID) -> list[SkillStateTransitionRecord]:
    _, factory = isolated_database()
    async with factory() as session:
        opportunity_ids = (
            await session.scalars(
                select(ItemOpportunityRecord.item_opportunity_id).where(ItemOpportunityRecord.session_id == session_id)
            )
        ).all()
        if not opportunity_ids:
            return []
        return (
            await session.scalars(
                select(SkillStateTransitionRecord).where(
                    SkillStateTransitionRecord.item_opportunity_id.in_(opportunity_ids)
                )
            )
        ).all()


async def _attempts_for_opportunity(item_opportunity_id: UUID) -> list[AttemptRecord]:
    _, factory = isolated_database()
    async with factory() as session:
        return (
            await session.scalars(select(AttemptRecord).where(AttemptRecord.item_opportunity_id == item_opportunity_id))
        ).all()


async def _skill_ids_and_templates_for_session(session_id: UUID) -> list[tuple[str, str]]:
    _, factory = isolated_database()
    async with factory() as session:
        rows = (
            await session.scalars(select(ItemOpportunityRecord).where(ItemOpportunityRecord.session_id == session_id))
        ).all()
        return [(row.skill_id, row.item_template_id) for row in rows]


# ---------------------------------------------------------------------------
# 1. Full session flow: correct / incorrect+retry / hint / timeout / completion
# ---------------------------------------------------------------------------


def test_full_session_flow_covers_every_path_and_updates_bkt_only_on_first_attempts() -> None:
    alembic("upgrade", "head")
    bundle_record = asyncio.run(_ensure_engineering_test_bundle())
    learner = f"learner-be4f-full-flow-{uuid4()}"

    client = client_for(learner, bundle_record=bundle_record)
    try:
        setup_learner(client, learner)
        started = client.post("/api/v1/b/sessions", json=None, headers=headers(str(uuid4())))
        assert started.status_code == 201
        session_id = started.json()["session_id"]

        first_attempt_response_count = 0

        # --- Opportunity 1: correct on the first attempt ---------------------------------
        opp1 = client.post(f"/api/v1/b/sessions/{session_id}/opportunities", json=None, headers=headers(str(uuid4())))
        assert opp1.status_code == 201
        opp1_id = opp1.json()["item_opportunity_id"]
        correct_answer_1 = _fetch_correct_answer(UUID(opp1_id))
        submit1 = client.post(
            f"/api/v1/b/sessions/{session_id}/opportunities/{opp1_id}/responses",
            json={"submitted_value": correct_answer_1, "client_elapsed_ms": 1000},
            headers=headers(str(uuid4())),
        )
        assert submit1.status_code == 201
        assert submit1.json()["attempt_index"] == 1
        assert submit1.json()["response_matched"] is True
        first_attempt_response_count += 1
        complete1 = client.post(
            f"/api/v1/b/sessions/{session_id}/opportunities/{opp1_id}/complete", json=None, headers=headers(str(uuid4()))
        )
        assert complete1.status_code == 201
        assert complete1.json()["session_state"] == "active"

        # --- Opportunity 2: wrong first attempt, then a correct retry ---------------------
        opp2_id = complete1.json()["next_opportunity"]["item_opportunity_id"]
        correct_answer_2 = _fetch_correct_answer(UUID(opp2_id))
        wrong_answer_2 = _some_wrong_answer(UUID(opp2_id))
        wrong1 = client.post(
            f"/api/v1/b/sessions/{session_id}/opportunities/{opp2_id}/responses",
            json={"submitted_value": wrong_answer_2},
            headers=headers(str(uuid4())),
        )
        assert wrong1.status_code == 201
        assert wrong1.json()["attempt_index"] == 1
        assert wrong1.json()["response_matched"] is False
        first_attempt_response_count += 1
        retry2 = client.post(
            f"/api/v1/b/sessions/{session_id}/opportunities/{opp2_id}/responses",
            json={"submitted_value": correct_answer_2},
            headers=headers(str(uuid4())),
        )
        assert retry2.status_code == 201
        assert retry2.json()["attempt_index"] == 2
        assert retry2.json()["response_matched"] is True
        complete2 = client.post(
            f"/api/v1/b/sessions/{session_id}/opportunities/{opp2_id}/complete", json=None, headers=headers(str(uuid4()))
        )
        assert complete2.status_code == 201

        # --- Opportunity 3: hint requested (never a BKT observation), then correct --------
        # Which item_template_id the real adaptive-selection algorithm lands on here is not
        # hand-controlled (unlike test_be4d_hint_events.py's dedicated, pinned-template hint
        # tests) — only 29 of the 36 fixture-catalogue templates carry catalogue hint content
        # (test_be3c_characterization.py), so a hint request against whichever template gets
        # selected legitimately fails closed (409) when it does not. Either outcome is asserted;
        # what must hold regardless is "never a BKT observation".
        opp3_id = complete2.json()["next_opportunity"]["item_opportunity_id"]
        hint3 = client.post(
            f"/api/v1/b/sessions/{session_id}/opportunities/{opp3_id}/assists", json=None, headers=headers(str(uuid4()))
        )
        assert hint3.status_code in (201, 409)
        if hint3.status_code == 201:
            assert hint3.json()["hint_level"] == 1
        correct_answer_3 = _fetch_correct_answer(UUID(opp3_id))
        submit3 = client.post(
            f"/api/v1/b/sessions/{session_id}/opportunities/{opp3_id}/responses",
            json={"submitted_value": correct_answer_3},
            headers=headers(str(uuid4())),
        )
        assert submit3.status_code == 201
        assert submit3.json()["attempt_index"] == 1
        first_attempt_response_count += 1

        # --- Opportunity 4: timeout (server-authoritative deadline, no BKT observation) ---
        # The timeout deadline is fixed at OPEN time (opportunity_selection.open_adaptive_
        # opportunity reads DEFAULT_TIMEOUT once, when the opportunity is created) — so the
        # patch must be in place BEFORE the opportunity-opening call, i.e. before THIS
        # complete-and-advance call (which closes opp3 and opens opp4 in one atomic transition),
        # not merely before the later attempt submission on opp4.
        original_timeout = opportunity_selection_module.DEFAULT_TIMEOUT
        opportunity_selection_module.DEFAULT_TIMEOUT = timedelta(seconds=0)
        try:
            complete3 = client.post(
                f"/api/v1/b/sessions/{session_id}/opportunities/{opp3_id}/complete", json=None, headers=headers(str(uuid4()))
            )
        finally:
            opportunity_selection_module.DEFAULT_TIMEOUT = original_timeout
        assert complete3.status_code == 201
        opp4_id = complete3.json()["next_opportunity"]["item_opportunity_id"]

        # ACKNOWLEDGE PRESENTATION FIRST (2026-10-10 rule, see attempt_submission.py).
        # A deadline only binds a learner who was CONFIRMED to have seen the question: an
        # opportunity with no `presented_at_utc` can no longer time out, because the deadline still
        # in force would be the fail-safe written at SELECTION, which measures server and prefetch
        # time rather than the child's. The real screen sends this the moment the question renders,
        # so a fixture that omits it is not modelling a timeout -- it is modelling the
        # failed-acknowledgement anomaly, which is deliberately NOT a timeout.
        #
        # The ack needs the zero timeout STILL PATCHED when it runs. `presentation_ack` imports
        # DEFAULT_TIMEOUT inside its own function, so it reads selection's value at CALL time --
        # and since 2026-10-10 the ack RE-ANCHORS the deadline
        # (`timeout_deadline_utc = now + timeout`). At the real five minutes it would hand this
        # opportunity a live deadline and the submission would never be late, which is the
        # opposite of what this fixture tests.
        original_ack_timeout = opportunity_selection_module.DEFAULT_TIMEOUT
        opportunity_selection_module.DEFAULT_TIMEOUT = timedelta(seconds=0)
        try:
            client.post(
                f"/api/v1/b/sessions/{session_id}/opportunities/{opp4_id}/presented",
                json=None,
                headers=headers(str(uuid4())),
            )
        finally:
            opportunity_selection_module.DEFAULT_TIMEOUT = original_ack_timeout

        import time

        time.sleep(0.05)
        timeout_submit = client.post(
            f"/api/v1/b/sessions/{session_id}/opportunities/{opp4_id}/responses",
            json={"submitted_value": "irrelevant", "client_elapsed_ms": 0},
            headers=headers(str(uuid4())),
        )
        assert timeout_submit.status_code == 201
        assert timeout_submit.json()["event_kind"] == "TIMEOUT"
        assert timeout_submit.json()["response_matched"] is None
        complete4 = client.post(
            f"/api/v1/b/sessions/{session_id}/opportunities/{opp4_id}/complete", json=None, headers=headers(str(uuid4()))
        )
        assert complete4.status_code == 201

        # --- Opportunity 5: reaches MAX_OPPORTUNITIES_PER_SESSION -> session completes ----
        assert MAX_OPPORTUNITIES_PER_SESSION == 5
        opp5_id = complete4.json()["next_opportunity"]["item_opportunity_id"]
        correct_answer_5 = _fetch_correct_answer(UUID(opp5_id))
        submit5 = client.post(
            f"/api/v1/b/sessions/{session_id}/opportunities/{opp5_id}/responses",
            json={"submitted_value": correct_answer_5},
            headers=headers(str(uuid4())),
        )
        assert submit5.status_code == 201
        first_attempt_response_count += 1
        complete5 = client.post(
            f"/api/v1/b/sessions/{session_id}/opportunities/{opp5_id}/complete", json=None, headers=headers(str(uuid4()))
        )
        assert complete5.status_code == 201
        assert complete5.json()["session_state"] == "completed"
        assert complete5.json()["next_opportunity"] is None

        summary = client.get(f"/api/v1/b/sessions/{session_id}/summary", headers=headers(str(uuid4())))
        assert summary.status_code == 200
        assert summary.json()["session_state"] == "completed"
        assert summary.json()["opportunities_completed"] == 5

        # --- Only genuine first-attempt RESPONSE events ever created a BKT transition -----
        transitions = asyncio.run(_skill_state_transitions_for_session(UUID(session_id)))
        assert len(transitions) == first_attempt_response_count == 4  # opp4's TIMEOUT never observes
    finally:
        close_client(client)


def _fetch_correct_answer(item_opportunity_id: UUID) -> str:
    from app.infrastructure.persistence_models import TaskInstanceRecord

    async def _fetch() -> str:
        _, factory = isolated_database()
        async with factory() as session:
            row = await session.scalar(
                select(TaskInstanceRecord).where(TaskInstanceRecord.item_opportunity_id == item_opportunity_id)
            )
            return row.correct_answer

    return asyncio.run(_fetch())


def _some_wrong_answer(item_opportunity_id: UUID) -> str:
    from app.infrastructure.persistence_models import TaskInstanceRecord

    async def _fetch() -> str:
        _, factory = isolated_database()
        async with factory() as session:
            row = await session.scalar(
                select(TaskInstanceRecord).where(TaskInstanceRecord.item_opportunity_id == item_opportunity_id)
            )
            if row.distractor_candidates:
                return row.distractor_candidates[0]
            return row.correct_answer + "-wrong"

    return asyncio.run(_fetch())


# ---------------------------------------------------------------------------
# 2. Concurrency: duplicate attempts and duplicate hints, at the route level
# ---------------------------------------------------------------------------


def test_concurrent_duplicate_attempts_via_routes_produce_exactly_one_transition() -> None:
    alembic("upgrade", "head")
    bundle_record = asyncio.run(_ensure_engineering_test_bundle())
    learner = f"learner-be4f-concurrent-attempts-{uuid4()}"

    client = client_for(learner, bundle_record=bundle_record)
    try:
        setup_learner(client, learner)
        started = client.post("/api/v1/b/sessions", json=None, headers=headers(str(uuid4())))
        session_id = started.json()["session_id"]
        opp = client.post(f"/api/v1/b/sessions/{session_id}/opportunities", json=None, headers=headers(str(uuid4())))
        opp_id = opp.json()["item_opportunity_id"]
        correct_answer = _fetch_correct_answer(UUID(opp_id))

        barrier = Barrier(2)

        def submit():
            barrier.wait()
            return client.post(
                f"/api/v1/b/sessions/{session_id}/opportunities/{opp_id}/responses",
                json={"submitted_value": correct_answer},
                headers=headers(str(uuid4())),
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _: submit(), range(2)))

        statuses = sorted(r.status_code for r in responses)
        assert statuses in ([201, 201], [201, 409])

        transitions = asyncio.run(_skill_state_transitions_for_session(UUID(session_id)))
        assert len(transitions) == 1
    finally:
        close_client(client)


def test_concurrent_hint_requests_via_routes_never_exceed_l3() -> None:
    alembic("upgrade", "head")
    bundle_record = asyncio.run(_ensure_engineering_test_bundle())
    learner = f"learner-be4f-concurrent-hints-{uuid4()}"

    client = client_for(learner, bundle_record=bundle_record)
    try:
        setup_learner(client, learner)
        started = client.post("/api/v1/b/sessions", json=None, headers=headers(str(uuid4())))
        session_id = started.json()["session_id"]
        opp = client.post(f"/api/v1/b/sessions/{session_id}/opportunities", json=None, headers=headers(str(uuid4())))
        opp_id = opp.json()["item_opportunity_id"]

        barrier = Barrier(5)

        def request_hint():
            barrier.wait()
            return client.post(
                f"/api/v1/b/sessions/{session_id}/opportunities/{opp_id}/assists",
                json=None,
                headers=headers(str(uuid4())),
            )

        with ThreadPoolExecutor(max_workers=5) as pool:
            responses = list(pool.map(lambda _: request_hint(), range(5)))

        successes = [r for r in responses if r.status_code == 201]
        conflicts = [r for r in responses if r.status_code == 409]
        assert len(successes) + len(conflicts) == 5
        assert len(successes) <= 3
        assert sorted(r.json()["hint_level"] for r in successes) == list(range(1, len(successes) + 1))

        async def _hint_event_count() -> int:
            _, factory = isolated_database()
            async with factory() as session:
                rows = (
                    await session.scalars(
                        select(HintEventRecord).where(HintEventRecord.item_opportunity_id == UUID(opp_id))
                    )
                ).all()
                return len(rows)

        assert asyncio.run(_hint_event_count()) == len(successes) <= 3
    finally:
        close_client(client)


# ---------------------------------------------------------------------------
# 3. DB/technical failure BEFORE and AFTER the BKT/mastery calculation
# ---------------------------------------------------------------------------


class _FailBeforeBktCalcService(AttemptSubmissionService):
    """Injects a technical failure at the very first statement of the BKT-calculation step —
    i.e. BEFORE any BKT compute (``adapter.predict``/``posterior``/``update``) runs, as opposed
    to ``test_be4c_attempt_submission.py``'s existing ``_FailAtCommitUnitOfWork`` (AFTER the BKT
    compute, at commit). The attempt row inserted just before this call is only ``flush()``-ed,
    never committed, so the whole transaction (attempt insert included) must roll back."""

    async def _apply_first_attempt_bkt(self, *args, **kwargs) -> None:
        raise SQLAlchemyError("simulated infra failure immediately before BKT calc")


class _FailAtCommitService(AttemptSubmissionService):
    def __init__(self, *, factory) -> None:
        super().__init__(uow_factory=_FailAtCommitUnitOfWorkFactory(factory))


class _FailAtCommitUnitOfWork(SqlAlchemyUnitOfWork):
    async def commit(self) -> None:
        raise SQLAlchemyError("simulated infra failure at commit, after BKT calc")


def _FailAtCommitUnitOfWorkFactory(factory):
    from functools import partial

    return partial(_FailAtCommitUnitOfWork, factory=factory)


def _run_failure_scenario(service_factory) -> tuple[str, str, dict]:
    alembic("upgrade", "head")
    bundle_record = asyncio.run(_ensure_engineering_test_bundle())
    learner = f"learner-be4f-failure-{uuid4()}"

    client = client_for(learner, bundle_record=bundle_record)
    try:
        setup_learner(client, learner)
        started = client.post("/api/v1/b/sessions", json=None, headers=headers(str(uuid4())))
        session_id = started.json()["session_id"]
        opp = client.post(f"/api/v1/b/sessions/{session_id}/opportunities", json=None, headers=headers(str(uuid4())))
        opp_id = opp.json()["item_opportunity_id"]
        correct_answer = _fetch_correct_answer(UUID(opp_id))
    finally:
        close_client(client)

    failing_client = client_for(
        learner,
        bundle_record=bundle_record,
        overrides={attempt_submission_service_dep: service_factory},
    )
    try:
        failed = failing_client.post(
            f"/api/v1/b/sessions/{session_id}/opportunities/{opp_id}/responses",
            json={"submitted_value": correct_answer},
            headers=headers(str(uuid4())),
        )
    finally:
        close_client(failing_client)

    return session_id, opp_id, failed.json()


def test_technical_failure_before_bkt_calc_rolls_back_attempt_and_creates_no_transition() -> None:
    session_id, opp_id, body = _run_failure_scenario(lambda: _FailBeforeBktCalcService())

    attempts = asyncio.run(_attempts_for_opportunity(UUID(opp_id)))
    assert attempts == []  # the whole transaction, attempt insert included, rolled back
    transitions = asyncio.run(_skill_state_transitions_for_session(UUID(session_id)))
    assert transitions == []
    assert body["error"]["code"] == "TECHNICAL_FAILURE"


def test_technical_failure_after_bkt_calc_rolls_back_everything_no_partial_state() -> None:
    _, factory = isolated_database()
    session_id, opp_id, body = _run_failure_scenario(lambda: _FailAtCommitService(factory=factory))

    attempts = asyncio.run(_attempts_for_opportunity(UUID(opp_id)))
    assert attempts == []
    transitions = asyncio.run(_skill_state_transitions_for_session(UUID(session_id)))
    assert transitions == []
    assert body["error"]["code"] == "TECHNICAL_FAILURE"


def test_technical_failure_is_never_recorded_as_learner_failure() -> None:
    """A technical failure must not leave behind an incorrect (or any) attempt row and must not
    alter the learner's skill state — it is never mistaken for a wrong learner response."""
    session_id, opp_id, _body = _run_failure_scenario(lambda: _FailBeforeBktCalcService())

    async def _skill_state_untouched() -> bool:
        _, factory = isolated_database()
        async with factory() as session:
            opportunity = await session.get(ItemOpportunityRecord, UUID(opp_id))
            state = await session.scalar(
                select(LearnerSkillStateRecord).where(
                    LearnerSkillStateRecord.learner_id == opportunity.learner_id,
                    LearnerSkillStateRecord.skill_id == opportunity.skill_id,
                )
            )
            return state is None or state.observation_count == 0

    assert asyncio.run(_skill_state_untouched())


# ---------------------------------------------------------------------------
# 4. Network retry + idempotent replay, across every command route
# ---------------------------------------------------------------------------


def test_network_retry_idempotent_replay_across_every_command_route() -> None:
    alembic("upgrade", "head")
    bundle_record = asyncio.run(_ensure_engineering_test_bundle())
    learner = f"learner-be4f-replay-{uuid4()}"

    client = client_for(learner, bundle_record=bundle_record)
    try:
        setup_learner(client, learner)
        start_key = str(uuid4())
        first_start = client.post("/api/v1/b/sessions", json=None, headers=headers(start_key))
        replay_start = client.post("/api/v1/b/sessions", json=None, headers=headers(start_key))
        assert first_start.json() == replay_start.json()
        session_id = first_start.json()["session_id"]

        opp = client.post(f"/api/v1/b/sessions/{session_id}/opportunities", json=None, headers=headers(str(uuid4())))
        opp_id = opp.json()["item_opportunity_id"]
        correct_answer = _fetch_correct_answer(UUID(opp_id))

        attempt_key = str(uuid4())
        first_attempt = client.post(
            f"/api/v1/b/sessions/{session_id}/opportunities/{opp_id}/responses",
            json={"submitted_value": correct_answer},
            headers=headers(attempt_key),
        )
        replay_attempt = client.post(
            f"/api/v1/b/sessions/{session_id}/opportunities/{opp_id}/responses",
            json={"submitted_value": correct_answer},
            headers=headers(attempt_key),
        )
        assert first_attempt.json() == replay_attempt.json()
        assert len(asyncio.run(_attempts_for_opportunity(UUID(opp_id)))) == 1

        hint_key = str(uuid4())
        first_hint = client.post(
            f"/api/v1/b/sessions/{session_id}/opportunities/{opp_id}/assists", json=None, headers=headers(hint_key)
        )
        replay_hint = client.post(
            f"/api/v1/b/sessions/{session_id}/opportunities/{opp_id}/assists", json=None, headers=headers(hint_key)
        )
        if first_hint.status_code == 201:
            assert first_hint.json() == replay_hint.json()
        else:
            # Whichever template real adaptive-selection chose for ``opp_id`` may legitimately
            # carry no catalogue hint content (see the full-session-flow test's own note) — a
            # failed, fail-closed lookup is never persisted (HintRequestService's
            # ``_reserve_idempotency`` record only commits on success), so nothing was recorded
            # the first time and a replay simply re-executes the same fail-closed path rather
            # than returning a byte-identical canonical response (its ``request_id`` legitimately
            # differs). There is no double side effect to guard against either way.
            assert first_hint.status_code == replay_hint.status_code == 409

        complete_key = str(uuid4())
        first_complete = client.post(
            f"/api/v1/b/sessions/{session_id}/opportunities/{opp_id}/complete", json=None, headers=headers(complete_key)
        )
        replay_complete = client.post(
            f"/api/v1/b/sessions/{session_id}/opportunities/{opp_id}/complete", json=None, headers=headers(complete_key)
        )
        assert first_complete.json() == replay_complete.json()

        transitions = asyncio.run(_skill_state_transitions_for_session(UUID(session_id)))
        assert len(transitions) == 1  # replays never doubled the BKT observation
    finally:
        close_client(client)


# ---------------------------------------------------------------------------
# 5. Server/client clock disagreement — server timestamps authoritative
# ---------------------------------------------------------------------------


def test_server_client_clock_disagreement_server_timestamps_authoritative() -> None:
    """The client's ``client_elapsed_ms`` is telemetry only. A learner client falsely claiming a
    near-instant response must not affect correctness, must not affect the BKT observation, and
    must not let a genuinely expired opportunity escape a server-side TIMEOUT."""
    alembic("upgrade", "head")
    bundle_record = asyncio.run(_ensure_engineering_test_bundle())
    learner = f"learner-be4f-clock-{uuid4()}"

    client = client_for(learner, bundle_record=bundle_record)
    try:
        setup_learner(client, learner)
        started = client.post("/api/v1/b/sessions", json=None, headers=headers(str(uuid4())))
        session_id = started.json()["session_id"]

        # (a) Client claims 0ms elapsed on a genuinely expired opportunity -> still TIMEOUT.
        # The server timeout deadline is fixed at OPEN time (opportunity_selection.
        # open_adaptive_opportunity reads DEFAULT_TIMEOUT once, when the opportunity row is
        # created) — the patch must be in place BEFORE this opening call, not merely before the
        # later attempt submission.
        original_timeout = opportunity_selection_module.DEFAULT_TIMEOUT
        opportunity_selection_module.DEFAULT_TIMEOUT = timedelta(seconds=0)
        try:
            opp_a = client.post(
                f"/api/v1/b/sessions/{session_id}/opportunities", json=None, headers=headers(str(uuid4()))
            )
        finally:
            opportunity_selection_module.DEFAULT_TIMEOUT = original_timeout
        opp_a_id = opp_a.json()["item_opportunity_id"]

        # ACKNOWLEDGE PRESENTATION FIRST (2026-10-10 rule, see attempt_submission.py).
        # A deadline only binds a learner who was CONFIRMED to have seen the question: an
        # opportunity with no `presented_at_utc` can no longer time out, because the deadline still
        # in force would be the fail-safe written at SELECTION, which measures server and prefetch
        # time rather than the child's. The real screen sends this the moment the question renders,
        # so a fixture that omits it is not modelling a timeout -- it is modelling the
        # failed-acknowledgement anomaly, which is deliberately NOT a timeout.
        #
        # The ack needs the zero timeout STILL PATCHED when it runs. `presentation_ack` imports
        # DEFAULT_TIMEOUT inside its own function, so it reads selection's value at CALL time --
        # and since 2026-10-10 the ack RE-ANCHORS the deadline
        # (`timeout_deadline_utc = now + timeout`). At the real five minutes it would hand this
        # opportunity a live deadline and the submission would never be late, which is the
        # opposite of what this fixture tests.
        original_ack_timeout = opportunity_selection_module.DEFAULT_TIMEOUT
        opportunity_selection_module.DEFAULT_TIMEOUT = timedelta(seconds=0)
        try:
            client.post(
                f"/api/v1/b/sessions/{session_id}/opportunities/{opp_a_id}/presented",
                json=None,
                headers=headers(str(uuid4())),
            )
        finally:
            opportunity_selection_module.DEFAULT_TIMEOUT = original_ack_timeout

        import time

        time.sleep(0.05)
        response_a = client.post(
            f"/api/v1/b/sessions/{session_id}/opportunities/{opp_a_id}/responses",
            json={"submitted_value": "0", "client_elapsed_ms": 0},
            headers=headers(str(uuid4())),
        )
        assert response_a.json()["event_kind"] == "TIMEOUT"
        before_server_submit = response_a.json()["server_submitted_at_utc"]
        assert before_server_submit  # server-generated, present regardless of the client's claim

        complete_a = client.post(
            f"/api/v1/b/sessions/{session_id}/opportunities/{opp_a_id}/complete", json=None, headers=headers(str(uuid4()))
        )

        # (b) Client claims the maximum allowed elapsed time on a fresh (non-expired) opportunity
        #     -> correctness is judged only on submitted_value, never on client_elapsed_ms.
        opp_b_id = complete_a.json()["next_opportunity"]["item_opportunity_id"]
        correct_answer_b = _fetch_correct_answer(UUID(opp_b_id))
        response_b = client.post(
            f"/api/v1/b/sessions/{session_id}/opportunities/{opp_b_id}/responses",
            json={"submitted_value": correct_answer_b, "client_elapsed_ms": 3_600_000},
            headers=headers(str(uuid4())),
        )
        assert response_b.json()["event_kind"] == "RESPONSE"
        assert response_b.json()["response_matched"] is True

        transitions = asyncio.run(_skill_state_transitions_for_session(UUID(session_id)))
        # (a)'s TIMEOUT created no observation; (b)'s first RESPONSE created exactly one.
        assert len(transitions) == 1
    finally:
        close_client(client)


# ---------------------------------------------------------------------------
# 6. Grade eligibility + deferred-template exclusion sustained across a whole session
# ---------------------------------------------------------------------------


def test_grade_2_never_offered_multiplication_division_or_deferred_template_across_whole_session() -> None:
    alembic("upgrade", "head")
    bundle_record = asyncio.run(_ensure_engineering_test_bundle())
    learner = f"learner-be4f-grade-gate-{uuid4()}"

    client = client_for(learner, bundle_record=bundle_record)
    try:
        setup_learner(client, learner, grade=2)
        started = client.post("/api/v1/b/sessions", json=None, headers=headers(str(uuid4())))
        session_id = started.json()["session_id"]

        opp = client.post(f"/api/v1/b/sessions/{session_id}/opportunities", json=None, headers=headers(str(uuid4())))
        assert opp.status_code == 201
        current_opp_id = opp.json()["item_opportunity_id"]
        for _ in range(MAX_OPPORTUNITIES_PER_SESSION):
            correct_answer = _fetch_correct_answer(UUID(current_opp_id))
            client.post(
                f"/api/v1/b/sessions/{session_id}/opportunities/{current_opp_id}/responses",
                json={"submitted_value": correct_answer},
                headers=headers(str(uuid4())),
            )
            advance = client.post(
                f"/api/v1/b/sessions/{session_id}/opportunities/{current_opp_id}/complete",
                json=None,
                headers=headers(str(uuid4())),
            )
            assert advance.status_code == 201
            next_opportunity = advance.json()["next_opportunity"]
            if next_opportunity is not None:
                current_opp_id = next_opportunity["item_opportunity_id"]

        skills_and_templates = asyncio.run(_skill_ids_and_templates_for_session(UUID(session_id)))
        assert len(skills_and_templates) == MAX_OPPORTUNITIES_PER_SESSION
        for skill_id, item_template_id in skills_and_templates:
            assert skill_id not in ("multiplication", "division"), (skill_id, item_template_id)
            assert item_template_id != DEFERRED_TEMPLATE_ID
    finally:
        close_client(client)


# ---------------------------------------------------------------------------
# 7. Public payload + structured-log field scan across EVERY BE4 route
# ---------------------------------------------------------------------------

FORBIDDEN_FIELD_NAMES = {
    "correct_answer",
    "allowed_equivalent_answers",
    "distractor_candidates",
    "distractor_rule_ids",
    "generated_operands",
    "generation_seed",
    "applied_guard_ids",
    "catalogue_version",
    "catalogue_checksum",
    "selection_provenance",
    "mastery_gap",
    "prerequisite_readiness",
    "spacing_due",
    "score",
    "tie_broken",
    "tie_break_basis",
    "p_l",
    "p_l_before",
    "p_l_after",
    "predicted_probability",
    "posterior_p_l",
    "theta_b",
    "winning_item_template_id",
    "winning_skill_id",
}
# The hint route legitimately carries catalogue_version/catalogue_checksum as its own governed
# reconstruction key (see app/domain/b_hint.py) — every OTHER route must never carry them.
HINT_ROUTE_ALLOWED_FIELDS = {"catalogue_version", "catalogue_checksum"}


def _scan_for_forbidden_keys(payload: object, *, allowed: set[str] = frozenset()) -> set[str]:
    found: set[str] = set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in FORBIDDEN_FIELD_NAMES and key not in allowed:
                found.add(key)
            found |= _scan_for_forbidden_keys(value, allowed=allowed)
    elif isinstance(payload, list):
        for item in payload:
            found |= _scan_for_forbidden_keys(item, allowed=allowed)
    return found


def test_public_payloads_and_structured_logs_carry_no_forbidden_fields_across_every_be4_route(
    caplog: pytest.LogCaptureFixture,
) -> None:
    alembic("upgrade", "head")
    bundle_record = asyncio.run(_ensure_engineering_test_bundle())
    learner = f"learner-be4f-privacy-scan-{uuid4()}"

    caplog.set_level(logging.INFO, logger="studentapp.http")
    client = client_for(learner, bundle_record=bundle_record)
    responses: list[tuple[str, dict]] = []
    try:
        setup_learner(client, learner)
        started = client.post("/api/v1/b/sessions", json=None, headers=headers(str(uuid4())))
        session_id = started.json()["session_id"]

        opp = client.post(f"/api/v1/b/sessions/{session_id}/opportunities", json=None, headers=headers(str(uuid4())))
        responses.append(("select", opp.json()))
        opp_id = opp.json()["item_opportunity_id"]

        hint = client.post(
            f"/api/v1/b/sessions/{session_id}/opportunities/{opp_id}/assists", json=None, headers=headers(str(uuid4()))
        )
        responses.append(("hint", hint.json()))

        correct_answer = _fetch_correct_answer(UUID(opp_id))
        attempt = client.post(
            f"/api/v1/b/sessions/{session_id}/opportunities/{opp_id}/responses",
            json={"submitted_value": correct_answer},
            headers=headers(str(uuid4())),
        )
        responses.append(("attempt", attempt.json()))

        complete = client.post(
            f"/api/v1/b/sessions/{session_id}/opportunities/{opp_id}/complete", json=None, headers=headers(str(uuid4()))
        )
        responses.append(("complete", complete.json()))

        summary = client.get(f"/api/v1/b/sessions/{session_id}/summary", headers=headers(str(uuid4())))
        responses.append(("summary", summary.json()))
    finally:
        close_client(client)

    for route_name, body in responses:
        allowed = HINT_ROUTE_ALLOWED_FIELDS if route_name == "hint" else frozenset()
        leaked = _scan_for_forbidden_keys(body, allowed=allowed)
        assert not leaked, (route_name, leaked, body)

    # Structured-log scan: JsonFormatter (app/core/logging.py) only ever emits a fixed
    # whitelisted field set (http_method/route/response_status/duration_ms/...) plus the request
    # id — but this asserts that invariant holds in practice, not merely by construction, by
    # scanning every log record this session's routes actually emitted.
    assert caplog.records
    for record in caplog.records:
        message = json.dumps(getattr(record, "__dict__", {}), default=str)
        for forbidden in FORBIDDEN_FIELD_NAMES:
            assert forbidden not in message, (forbidden, record.getMessage())
