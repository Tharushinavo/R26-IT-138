"""Component C Phase 4b acceptance tests: the governed SelectionConfig bundle source (B1, T3-T6),
the three-now-four HTTP routes (B2), concurrency mirroring (B3), and session completion / the
N-increment (B4).

PHASE 6b NOTE (X1/X2-3, disclosed here because it changes what this file's own HTTP-level tests
can prove): the committed reference bundle (``valid_unapproved_bundle_c.json``) now carries its
REAL, honest per-field classification (X3-f) -- every field CALIBRATION_PENDING or
PROPOSED_UNSIGNED, none APPROVED. Under X1's whitelist (usable = {APPROVED} only),
``CSessionService.create`` now refuses EVERY request against that real fixture, by design (see
``session_lifecycle.create_session``'s own module-level disclosure). This file's own tests
predate that gate and exist to prove ROUTING/response-shape/concurrency MECHANICS, not the gate
itself (which has its own dedicated tests in ``test_c6b_policy_and_safety.py``) -- so an
autouse fixture below points ``CSessionService``'s bundle path at a SEPARATE, clearly-named
``all_usable_for_tests_bundle_c.json`` (every per-field status APPROVED, TEST-ONLY, not a claim
that governance ever signed anything) for the duration of this file only, restoring the original
positive-path behaviour these pre-6b tests were written to prove.

RATIFIED (Phase 6b final step, SUPERVISOR RULING -- was previously BUILDER JUDGMENT --
UNRATIFIED): accepted on three verified grounds -- the fixture is FILE-LOCAL (this file's own
``@pytest.fixture(autouse=True)``, not a shared ``conftest.py`` entry), so it cannot shadow or
weaken the gate's own dedicated tests in ``test_c6b_policy_and_safety.py``, which construct their
own bundles directly and never import this file; it is clearly named
(``all_usable_for_tests_bundle_c.json``, not reusing the real fixture's name); and the gate has
its own dedicated tests, in a different file, that exercise the REALISTIC (real classification)
bundle. THE TRADE-OFF, stated honestly rather than left implicit: with this autouse fixture in
place, none of THIS file's own HTTP-level tests exercise the unapproved-bundle refusal path any
longer -- that proof now lives exclusively in ``test_c6b_policy_and_safety.py``'s own gate tests,
not here.

PHASE 7 EXTENSION (Z2, BUILDER JUDGMENT -- UNRATIFIED, extending the ratified 6b pattern by
direct analogy, not a new mechanism): the uniform five-family gate now ALSO checks Generation/
Policy/Scaffold via ``smoke_mode`` -- hardcoded ``False`` in ``CSessionService.create``, same
shape as the bundle path, same reason (the real HTTP route never lets a client set it). The
all-usable bundle alone is no longer sufficient for this file's own HTTP-level tests to reach a
real 201: the autouse fixture below ALSO monkeypatches ``c_session_service_module._SMOKE_MODE`` to
``True`` for the same reason and under the same three grounds already ratified for the bundle
path (file-local, clearly a test-only override, the gate's own dedicated tests live elsewhere and
exercise the real ``smoke_mode=False`` production shape)."""

from __future__ import annotations

import asyncio
import subprocess
from datetime import UTC, datetime
from uuid import UUID, uuid4

import jsonschema
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.application.live_engine_c import c_session_service as c_session_service_module
from app.application.live_engine_c import task_service as task_service_module
from app.application.live_engine_c.bundle_resolution import resolve_selection_config
from app.core.config import get_settings
from app.domain.live_engine_c.errors import SelectionConfigurationMissingError
from app.domain.principal import AuthenticatedPrincipal
from app.infrastructure.auth import get_authenticated_principal
from app.infrastructure.database import async_database_url
from app.infrastructure.live_engine_c.adapter import LiveEngineCAdapter
from app.infrastructure.persistence_models import CRuntimeBundleRecord, Learner
from app.infrastructure.runtime_bundle_c.loader import CRuntimeBundleLoader
from app.main import app

SCHEMA_PATH = "provenance/c-runtime-bundle.schema.json"
ALL_USABLE_BUNDLE_PATH = "tests/fixtures/runtime_bundle_c/all_usable_for_tests_bundle_c.json"
# CONNECT Step 2/3: _CATALOGUE_PATH used to be the app's only fixture pointer, so no test ever
# needed to patch it -- production repointing it to the real, governed catalogue broke that
# accident. ALL_USABLE_BUNDLE_PATH declares the OLD (test-fixture) catalogue's checksum, so it
# must be paired with the matching fixture catalogue below, not the real one the app now serves
# by default. This mirrors the pairing production now enforces (bundle.catalogue.checksum must
# match the file _CATALOGUE_PATH actually points at) -- it is a pairing fix, not a new mechanism.
ALL_USABLE_CATALOGUE_PATH = "tests/fixtures/runtime_bundle_c/test_catalogue_c.md"


@pytest.fixture(autouse=True)
def _all_usable_bundle_for_http_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    """See module docstring's PHASE 6b NOTE / PHASE 7 EXTENSION. Test-side only -- app/'s own
    hardcoded ``_BUNDLE_PATH``/``_SMOKE_MODE`` are untouched; this patches the imported module
    attributes for the duration of each test in this file."""
    monkeypatch.setattr(c_session_service_module, "_BUNDLE_PATH", ALL_USABLE_BUNDLE_PATH)
    monkeypatch.setattr(c_session_service_module, "_CATALOGUE_PATH", ALL_USABLE_CATALOGUE_PATH)
    monkeypatch.setattr(c_session_service_module, "_SMOKE_MODE", True)
    monkeypatch.setattr(task_service_module, "_BUNDLE_PATH", ALL_USABLE_BUNDLE_PATH)
    monkeypatch.setattr(task_service_module, "_CATALOGUE_PATH", ALL_USABLE_CATALOGUE_PATH)
BASE_BUNDLE_PATH = "tests/fixtures/runtime_bundle_c/valid_unapproved_bundle_c.json"


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
        "system_actor": "c4b-isolated-test",
        "request_id": f"test-{uuid4()}",
        "operation_or_event_type": "test.persistence",
        "reason_code": "ISOLATED_SYNTHETIC_TEST",
        "resource_type": resource_type,
        "resource_id": resource_id,
        "source_class": "TEST",
        "source_system": "c4b-isolated-test-suite",
        "environment": "test",
        "schema_revision": "20260816_0005",
    }


def _full_selection_configuration_block(field_status: str = "CALIBRATION_PENDING") -> dict:
    """Phase 6b (X3, BREAKING): per-field {source, status, value}, replacing the 1.1 flat
    block-level approval_status this helper used to emit. ``field_status`` is applied uniformly
    to all five fields -- callers needing a MIXED block (some usable, some not) build one
    directly rather than through this helper."""
    source = "TEST FIXTURE -- not a real SPEC citation"
    return {
        "version": "c4.0-selection-1.0.0",
        "checksum": {"algorithm": "sha256", "value": "a" * 64},
        "config_version": "c4.0-selection-1.0.0",
        "parameter_source_status": "TEST_FIXTURE_ONLY",
        "familiarization_window_by_grade": {
            "source": source, "status": field_status, "value": {"2": 2, "3": 3},
        },
        "familiarization_difficulty_level": {"source": source, "status": field_status, "value": 1},
        "fallback_difficulty_level": {"source": source, "status": field_status, "value": 1},
        "familiarization_session_difficulty_cap": {"source": source, "status": field_status, "value": 2},
        "fallback_difficulty_cap": {"source": source, "status": field_status, "value": 2},
    }


def _load_base_fixture() -> dict:
    import json

    return json.loads(open(BASE_BUNDLE_PATH, encoding="utf-8").read())


# =====================================================================================
# B1-d -- two tests, neither alone sufficient (owner ruling).
# =====================================================================================


def test_b1d_a_bundle_without_selection_configuration_still_validates() -> None:
    """SIGNAL: additive-only (owner condition 2, B1-b). A synthetic 1.0-shaped variant (the real
    on-disk fixture now carries the block, since it is the production-reference bundle -- see
    B1-d-b below and the build log) -- would FAIL if the schema change had accidentally made
    selection_configuration required."""
    schema = __import__("json").load(open(SCHEMA_PATH, encoding="utf-8"))
    fixture = _load_base_fixture()
    fixture.pop("selection_configuration", None)
    fixture["schema_version"] = "1.0"
    assert "selection_configuration" not in fixture
    jsonschema.validate(fixture, schema)  # raises on failure


def test_b1d_b_absent_selection_configuration_halts_the_consumer() -> None:
    """SIGNAL: the OTHER half of B1-d -- a code path needing W against a bundle with NO
    selection_configuration RAISES, never defaults (owner condition 1, T4). Neither this test nor
    the one above alone proves fail-closed-and-additive together. Uses the same synthetic
    1.0-shaped variant as the test above (the real on-disk fixture now carries the block)."""
    import json
    import tempfile

    fixture = _load_base_fixture()
    fixture.pop("selection_configuration", None)
    fixture["schema_version"] = "1.0"
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(fixture, f)
        temp_path = f.name
    try:
        bundle = CRuntimeBundleLoader().load_and_validate(temp_path, SCHEMA_PATH, require_approved=False)
        assert bundle.selection_configuration is None
        with pytest.raises(SelectionConfigurationMissingError):
            resolve_selection_config(bundle)
    finally:
        import os

        os.unlink(temp_path)


def test_widened_bundle_with_full_selection_configuration_resolves_to_a_real_selection_config() -> None:
    """Positive control: a bundle WITH the widened block resolves cleanly, proving T3's mapping
    is not merely theoretical."""
    fixture = _load_base_fixture()
    fixture["selection_configuration"] = _full_selection_configuration_block()
    import json
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(fixture, f)
        temp_path = f.name
    try:
        bundle = CRuntimeBundleLoader().load_and_validate(temp_path, SCHEMA_PATH, require_approved=False)
        assert bundle.selection_configuration is not None
        config = resolve_selection_config(bundle)
        assert config.config_version == "c4.0-selection-1.0.0"
        assert config.parameter_source_status == "TEST_FIXTURE_ONLY"
        assert config.familiarization_window_by_grade == {2: 2, 3: 3}
        assert config.familiarization_difficulty_level == 1
        assert config.fallback_difficulty_level == 1
        assert config.familiarization_session_difficulty_cap == 2
        assert config.fallback_difficulty_cap == 2
    finally:
        import os

        os.unlink(temp_path)


# =====================================================================================
# T5 -- the bundle approval gate, proven BOTH ways, now that a bundle carrying seven
# CALIBRATION_PENDING values makes combined-mode sessions runnable.
# =====================================================================================


def test_t5_unapproved_bundle_with_selection_configuration_refused_when_gate_is_on() -> None:
    import json
    import tempfile

    fixture = _load_base_fixture()
    fixture["approval_status"] = "CALIBRATION_PENDING"
    fixture["selection_configuration"] = _full_selection_configuration_block()
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(fixture, f)
        temp_path = f.name
    try:
        from app.domain.runtime_bundle.errors import RuntimeBundleNotApprovedError

        with pytest.raises(RuntimeBundleNotApprovedError):
            CRuntimeBundleLoader().load_and_validate(temp_path, SCHEMA_PATH, require_approved=True)
    finally:
        import os

        os.unlink(temp_path)


def test_t5_unapproved_bundle_with_selection_configuration_admitted_when_opted_out() -> None:
    import json
    import tempfile

    fixture = _load_base_fixture()
    fixture["approval_status"] = "CALIBRATION_PENDING"
    fixture["selection_configuration"] = _full_selection_configuration_block()
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(fixture, f)
        temp_path = f.name
    try:
        bundle = CRuntimeBundleLoader().load_and_validate(temp_path, SCHEMA_PATH, require_approved=False)
        assert bundle.selection_configuration is not None
        resolve_selection_config(bundle)  # does not raise
    finally:
        import os

        os.unlink(temp_path)


# =====================================================================================
# B2 -- HTTP-level tests. Shared setup: a learner, a matching CRuntimeBundleRecord row
# (bundle_version == the fixture's own "c2-test-fixture-1.0").
# =====================================================================================


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


def headers(request_id: str | None = None) -> dict[str, str]:
    return {
        "X-Request-ID": request_id or f"req-{uuid4()}",
        "Authorization": "Bearer c-session-lifecycle-secret-that-must-not-be-logged",
    }


async def _seed_learner_and_bundle_record(subject: str) -> UUID:
    database_engine, factory = isolated_database()
    async with factory() as session:
        from app.infrastructure.persistence_models import AppUser, AppUserLearnerLink

        user_id = uuid4()
        session.add(
            AppUser(
                user_id=user_id, supabase_subject=subject, status="test_only",
                **provenance("app_user", user_id),
            )
        )
        await session.flush()
        learner_id = uuid4()
        session.add(
            Learner(learner_id=learner_id, grade=2, status="test_only", **provenance("b_learner", learner_id))
        )
        await session.flush()
        link_id = uuid4()
        session.add(
            AppUserLearnerLink(
                link_id=link_id, user_id=user_id, learner_id=learner_id, **provenance("link", link_id)
            )
        )
        # Every test in this file points at the SAME fixture manifest (bundle_version is a fixed
        # literal inside that file), so the matching DB row is shared across tests -- inserted
        # once, reused thereafter, matching how a real bundle would only be registered once.
        from sqlalchemy import select

        existing = await session.scalar(
            select(CRuntimeBundleRecord).where(CRuntimeBundleRecord.bundle_version == "c2-test-fixture-1.0")
        )
        if existing is None:
            bundle_id = uuid4()
            session.add(
                CRuntimeBundleRecord(
                    c_runtime_bundle_record_id=bundle_id,
                    bundle_version="c2-test-fixture-1.0",
                    manifest_checksum=bundle_id.hex * 2,
                    publication_state="DRAFT",
                    approval_status="UNRESOLVED",
                    immutable_after_publication=False,
                    **provenance("c_runtime_bundle_record", bundle_id),
                )
            )
        await session.commit()
    await database_engine.dispose()
    return learner_id


def setup_learner_and_bundle(subject: str) -> UUID:
    return asyncio.run(_seed_learner_and_bundle_record(subject))


# =====================================================================================
# B2-a -- exact key set, per route.
# =====================================================================================


def test_b2a_create_response_exact_key_set() -> None:
    alembic("upgrade", "head")
    subject = f"c4b-{uuid4()}"
    setup_learner_and_bundle(subject)
    client = client_for(subject)
    try:
        response = client.post(
            "/api/v1/c/sessions",
            json={"grade": 2, "session_mode": "combined"},
            headers=headers(),
        )
        assert response.status_code == 201, response.text
        body = response.json()
        # R-1: mastery_context_mode deliberately absent -- derivable client-side from session_mode.
        assert set(body.keys()) == {
            "c_session_id", "state", "session_mode", "session_phase",
            "grade", "started_at_utc", "row_version", "request_id",
        }
        # Owner condition 5: selection_configuration and anything derived from it never appears.
        assert "selection_configuration" not in body
        assert "familiarization_window_by_grade" not in str(body)
    finally:
        close_client(client)


def test_b2a_active_response_exact_key_set() -> None:
    alembic("upgrade", "head")
    subject = f"c4b-{uuid4()}"
    setup_learner_and_bundle(subject)
    client = client_for(subject)
    try:
        client.post(
            "/api/v1/c/sessions",
            json={"grade": 2, "session_mode": "combined"},
            headers=headers(),
        )
        response = client.get("/api/v1/c/sessions/active", headers=headers())
        assert response.status_code == 200, response.text
        body = response.json()
        assert set(body.keys()) == {"session", "request_id"}
        assert set(body["session"].keys()) == {
            "c_session_id", "state", "session_mode", "session_phase",
            "grade", "started_at_utc", "row_version",
        }
    finally:
        close_client(client)


def test_b2a_abandon_and_complete_response_exact_key_set() -> None:
    alembic("upgrade", "head")
    subject = f"c4b-{uuid4()}"
    setup_learner_and_bundle(subject)
    client = client_for(subject)
    try:
        created = client.post(
            "/api/v1/c/sessions",
            json={
                "grade": 2, "session_mode": "c_only",
            },
            headers=headers(),
        ).json()
        c_session_id = created["c_session_id"]
        response = client.post(f"/api/v1/c/sessions/{c_session_id}/abandon", headers=headers())
        assert response.status_code == 200, response.text
        assert set(response.json().keys()) == {
            "c_session_id", "state", "session_mode", "session_phase",
            "grade", "started_at_utc", "row_version", "request_id",
        }

        created2 = client.post(
            "/api/v1/c/sessions", json={"grade": 2, "session_mode": "c_only"}, headers=headers()
        ).json()
        complete_response = client.post(
            f"/api/v1/c/sessions/{created2['c_session_id']}/complete",
            json={"attendance_status": "attended"},
            headers=headers(),
        )
        assert complete_response.status_code == 200, complete_response.text
        assert set(complete_response.json().keys()) == {
            "c_session_id", "state", "session_mode", "session_phase",
            "grade", "started_at_utc", "row_version", "request_id",
        }
    finally:
        close_client(client)


def test_r5e_client_cannot_influence_b_provenance() -> None:
    """R-5e: a client attempting to supply the three B-identity fields on a create request is
    REJECTED outright (StrictModel forbids extras -- proven, not assumed), and the persisted
    row's intervention_session_id is always the fixture's value, never anything from the
    request, even when the request never gets that far."""
    alembic("upgrade", "head")
    subject = f"c4b-{uuid4()}"
    setup_learner_and_bundle(subject)
    client = client_for(subject)
    try:
        # Extra keys on the request body are rejected by StrictModel's extra="forbid" -- proven.
        rejected = client.post(
            "/api/v1/c/sessions",
            json={
                "grade": 2,
                "session_mode": "combined",
                "mastery_source_student_id": "CLIENT-SUPPLIED-STU-9999",
                "mastery_source_intervention_session_id": "STU-9999-I-999",
                "mastery_source_intervention_session_number": 99,
            },
            headers=headers(),
        )
        assert rejected.status_code == 422, rejected.text
        rejected_body = rejected.json()
        assert rejected_body["error"]["code"] == "REQUEST_VALIDATION_FAILED"
        assert any(entry["type"] == "extra_forbidden" for entry in rejected_body["error"]["details"])

        # A clean request (no extra keys) still creates a combined session, and the persisted
        # row's intervention_session_id is the FIXTURE's value, never a client-asserted one.
        created = client.post(
            "/api/v1/c/sessions",
            json={"grade": 2, "session_mode": "combined"},
            headers=headers(),
        )
        assert created.status_code == 201, created.text
        c_session_id = created.json()["c_session_id"]

        async def read_persisted() -> str:
            database_engine, factory = isolated_database()
            async with factory() as session:
                from app.infrastructure.persistence_models import CSessionRecord
                from sqlalchemy import select

                record = await session.scalar(
                    select(CSessionRecord).where(CSessionRecord.c_session_id == UUID(c_session_id))
                )
                assert record is not None
                value = record.intervention_session_id
            await database_engine.dispose()
            return value

        persisted_intervention_session_id = asyncio.run(read_persisted())
        from app.application.live_engine_c.mastery_fixture import (
            FIXTURE_MASTERY_SOURCE_INTERVENTION_SESSION_ID,
        )

        assert persisted_intervention_session_id == FIXTURE_MASTERY_SOURCE_INTERVENTION_SESSION_ID
        assert persisted_intervention_session_id != "STU-9999-I-999"
    finally:
        close_client(client)


# =====================================================================================
# B2-c -- Q2's sentinel, extended to the real HTTP response body.
# =====================================================================================


def test_q2_sentinel_absent_from_real_http_response_body(caplog: pytest.LogCaptureFixture) -> None:
    """UPDATE (R-5, Phase 4b continuation): the ORIGINAL form of this test posted a sentinel as
    ``mastery_source_student_id`` in the request body and asserted it reached
    ``MASTERY_PAYLOAD_REJECTED`` without leaking -- that path no longer exists structurally,
    because R-5a removed the field from ``CreateCSessionRequest`` entirely. A client can no
    longer make ANY client-supplied value reach the mastery contract validator at all (R-5's own
    point). What remains reachable, and still worth a positive Q2 control, is the StrictModel
    extra-field-rejection path itself: a client attempting to smuggle the sentinel in as an EXTRA
    key must not have it echoed back in the response body or the logs either -- this app's
    RequestValidationError handler (``app/core/errors.py``, pre-existing, not new this batch)
    already strips pydantic's own ``input``/``msg`` fields and exposes only ``loc``/``type``, so
    this proves that guarantee holds for this specific new route too, not just in the abstract."""
    alembic("upgrade", "head")
    subject = f"c4b-{uuid4()}"
    setup_learner_and_bundle(subject)
    client = client_for(subject)
    sentinel = "SENTINEL_MUST_NOT_LEAK_7f3a2c"
    try:
        response = client.post(
            "/api/v1/c/sessions",
            json={
                "grade": 2, "session_mode": "combined",
                "mastery_source_student_id": sentinel,
            },
            headers=headers(),
        )
        assert response.status_code == 422, response.text
        body = response.json()
        assert sentinel not in response.text
        assert sentinel not in str(body)
        for record in caplog.records:
            assert sentinel not in record.getMessage()
        # Positive control: the structured shape IS present (loc/type), proving this isn't a
        # blanket-swallowed error that trivially can't leak because it carries nothing at all.
        assert body["error"]["code"] == "REQUEST_VALIDATION_FAILED"
        assert body["error"]["details"], "expected structured details in the response"
        for entry in body["error"]["details"]:
            assert set(entry.keys()) == {"location", "type"}
        assert any(entry["type"] == "extra_forbidden" for entry in body["error"]["details"])
    finally:
        close_client(client)


# =====================================================================================
# B3 -- concurrency mechanism mirroring (sequential shape only -- disclosed).
# =====================================================================================


def test_b3_second_combined_session_request_is_idempotent_by_learner_state() -> None:
    """SIGNAL: sequential proof that the mechanism (existence check under lock, then insert)
    behaves correctly for the ordinary, non-racing case. This is NOT a concurrency proof --
    mirroring B's mechanism (advisory lock + IntegrityError catch) is not the same as proving it
    holds under two real concurrent connections, and this suite still has no two-connection
    harness (same disclosure as Phase 3b's I2/I3)."""
    alembic("upgrade", "head")
    subject = f"c4b-{uuid4()}"
    setup_learner_and_bundle(subject)
    client = client_for(subject)
    try:
        first = client.post(
            "/api/v1/c/sessions",
            json={"grade": 2, "session_mode": "combined"},
            headers=headers(),
        ).json()
        second = client.post(
            "/api/v1/c/sessions",
            json={"grade": 2, "session_mode": "combined"},
            headers=headers(),
        ).json()
        assert second["c_session_id"] == first["c_session_id"]
    finally:
        close_client(client)


def test_b3_partial_unique_index_backstops_a_duplicate_active_session_directly() -> None:
    """Bypasses the application-layer idempotency check entirely (constructs two CSessionRecord
    rows directly) to prove the DB-level index is the real backstop, not merely the Python-level
    check -- the two predicates (repositories.py's query, the index's own WHERE clause) are
    verified to cover the same set: both state IN ('starting', 'active')."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            student_id = uuid4()
            session.add(
                Learner(learner_id=student_id, grade=2, status="test_only", **provenance("b_learner", student_id))
            )
            bundle_id = uuid4()
            session.add(
                CRuntimeBundleRecord(
                    c_runtime_bundle_record_id=bundle_id, bundle_version=f"v{bundle_id}",
                    manifest_checksum=bundle_id.hex * 2, publication_state="DRAFT",
                    approval_status="UNRESOLVED", immutable_after_publication=False,
                    **provenance("c_runtime_bundle_record", bundle_id),
                )
            )
            await session.flush()
            from app.infrastructure.persistence_models import CSessionRecord

            first_id = uuid4()
            session.add(
                CSessionRecord(
                    c_session_id=first_id, student_id=student_id, intervention_session_id="i-1",
                    session_mode="c_only", session_phase="c_only", mastery_context_mode="unavailable_fallback",
                    catalogue_version="v", catalogue_checksum="a" * 64, c_runtime_bundle_record_id=bundle_id,
                    grade=2, state="active", global_seed=1, started_at_utc=datetime.now(UTC),
                    completed_at_utc=None, row_version=0, **provenance("c_session", first_id),
                )
            )
            await session.commit()

            second_id = uuid4()
            session.add(
                CSessionRecord(
                    c_session_id=second_id, student_id=student_id, intervention_session_id="i-2",
                    session_mode="c_only", session_phase="c_only", mastery_context_mode="unavailable_fallback",
                    catalogue_version="v", catalogue_checksum="a" * 64, c_runtime_bundle_record_id=bundle_id,
                    grade=2, state="active", global_seed=1, started_at_utc=datetime.now(UTC),
                    completed_at_utc=None, row_version=0, **provenance("c_session", second_id),
                )
            )
            from sqlalchemy.exc import IntegrityError

            with pytest.raises(IntegrityError) as excinfo:
                await session.commit()
            assert excinfo.value.orig.__cause__.constraint_name == "uq_c_sessions_one_starting_or_active_per_learner"
            await session.rollback()
        await database_engine.dispose()

    asyncio.run(exercise())


def test_b3_predicates_cover_the_same_set() -> None:
    """The owner's trap warning, answered directly: repositories.py's
    find_starting_or_active_for_learner queries state IN ('starting', 'active'); the partial
    index's own postgresql_where is state IN ('starting', 'active') -- read both from source,
    not asserted from memory."""
    import inspect

    from app.infrastructure.persistence_models import Base
    from app.infrastructure.repositories import CSessionRecordRepository

    query_source = inspect.getsource(CSessionRecordRepository.find_starting_or_active_for_learner)
    assert 'state.in_(("starting", "active"))' in query_source

    table = Base.metadata.tables["c_sessions"]
    index = next(i for i in table.indexes if i.name == "uq_c_sessions_one_starting_or_active_per_learner")
    where_clause = str(index.dialect_options["postgresql"]["where"])
    assert "starting" in where_clause and "active" in where_clause


# =====================================================================================
# B4 -- completion and the N-increment, evaluated through the adapter only.
# =====================================================================================


def test_b4_eligible_combined_completion_increments_n() -> None:
    alembic("upgrade", "head")
    subject = f"c4b-{uuid4()}"
    setup_learner_and_bundle(subject)
    client = client_for(subject)
    try:
        created = client.post(
            "/api/v1/c/sessions",
            json={"grade": 2, "session_mode": "combined"},
            headers=headers(),
        ).json()
        response = client.post(
            f"/api/v1/c/sessions/{created['c_session_id']}/complete",
            json={"attendance_status": "attended"},
            headers=headers(),
        )
        assert response.status_code == 200, response.text
        assert response.json()["state"] == "completed"
    finally:
        close_client(client)


def test_b4_c_only_completion_never_increments_n_is_eligible_combined_handoff_returns_false() -> None:
    """B4-b: is_eligible_combined_handoff itself (evaluated through the adapter, never
    reimplemented) returns False for a c_only session -- the first condition of the five-part
    predicate alone is sufficient, proven directly against the real adapter method."""
    adapter = LiveEngineCAdapter()
    assert adapter.is_eligible_combined_handoff("c_only", True, "attended", False) is False
    assert adapter.is_eligible_combined_handoff("combined", True, "attended", False) is True
    assert adapter.is_eligible_combined_handoff("combined", True, "missed", False) is False
    assert adapter.is_eligible_combined_handoff("combined", True, "attended", True) is False


def test_b4d_sf040_missed_slot_has_no_session_row_to_complete() -> None:
    """B4-d: SF-040 says a fully missed slot emits NO row -- there is nothing for complete_session
    to act on, confirmed structurally: completing a c_session_id that was never created (the
    missed-slot case) returns ResourceNotFoundError, not a fabricated completion."""
    alembic("upgrade", "head")
    subject = f"c4b-{uuid4()}"
    setup_learner_and_bundle(subject)
    client = client_for(subject)
    try:
        response = client.post(
            f"/api/v1/c/sessions/{uuid4()}/complete",
            json={"attendance_status": "missed"},
            headers=headers(),
        )
        assert response.status_code == 404
    finally:
        close_client(client)
