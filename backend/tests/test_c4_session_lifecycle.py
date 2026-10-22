"""Component C Phase 4 acceptance tests: session creation/start, resume, abandon; the two
session modes; mastery_context_mode determination; the cold-start gate (SF-043); C-16's closure;
Q1 (non-arrival), Q2 (sentinel leak), S-1 (reachable c_sessions.state subset).

W — every test that needs a SelectionConfig builds and supplies it explicitly, labelled
TEST_FIXTURE_ONLY at the point of supply (W3). No production path exists that defaults it or
calls default_selection_config() -- see
test_be2_architecture_guards.py::test_no_app_code_defaults_or_calls_default_selection_config (W5).
"""

from __future__ import annotations

import asyncio
import subprocess
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.errors import ConflictError, ResourceNotFoundError
from app.domain.live_engine_c.errors import MasteryPayloadContractValidationError, SF043OrderingError
from app.domain.live_engine_c.types import SafetyConfig, SelectionConfig
from app.domain.runtime_bundle_c.types import (
    EvidenceWindowConfigurationArtifact,
    SafetyConfigurationArtifact,
    SelectionConfigurationArtifact,
)
from app.application.live_engine_c.mastery_fixture import fixture_b_mastery_payload_for_phase_4
from app.application.live_engine_c.session_lifecycle import (
    abandon_session,
    create_session,
    get_active_session,
    mastery_context_mode_for,
)
from app.infrastructure.database import async_database_url
from app.infrastructure.live_engine_c.adapter import LiveEngineCAdapter
from app.infrastructure.persistence_models import CRuntimeBundleRecord, Learner


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
        "system_actor": "c4-isolated-test",
        "request_id": f"test-{uuid4()}",
        "operation_or_event_type": "test.persistence",
        "reason_code": "ISOLATED_SYNTHETIC_TEST",
        "resource_type": resource_type,
        "resource_id": resource_id,
        "source_class": "TEST",
        "source_system": "c4-isolated-test-suite",
        "environment": "test",
        "schema_revision": "20260816_0004",
    }


# TEST_FIXTURE_ONLY -- W3: tests supply the config explicitly and labelled at the point of
# supply; production code may never call default_selection_config() (W2, W5).
def selection_config_fixture_for_tests() -> SelectionConfig:
    return SelectionConfig(
        config_version="c4.0-selection-1.0.0",
        parameter_source_status="TEST_FIXTURE_ONLY",
        familiarization_window_by_grade={2: 2, 3: 3},
        familiarization_difficulty_level=1,
        fallback_difficulty_level=1,
        familiarization_session_difficulty_cap=2,
        fallback_difficulty_cap=2,
    )


def safety_config_fixture_for_tests() -> SafetyConfig:
    """TEST_FIXTURE_ONLY -- mirrors component_c_generator.safety.config.default_safety_config()'s
    own values (never calling that factory from app/ or tests/ that exercise app/ code -- S8-a),
    labelled at the point of supply like every other config fixture in this suite."""
    return SafetyConfig(
        config_version="c4.1-safety-1.0.0",
        parameter_source_status="TEST_FIXTURE_ONLY",
        consecutive_error_trigger=5,
        strain_trigger=0.85,
        increase_block_window=3,
        prior_overloaded_disengaged_cap=2,
        safe_termination_error_threshold=7,
        strain_bucket_low_max=0.25,
        strain_bucket_moderate_max=0.50,
        strain_bucket_high_max=0.85,
    )


def all_usable_field_statuses(field_names: tuple) -> dict:
    """X1/X4 test helper: every field APPROVED -- the ONE status the whitelist accepts. The
    baseline every unusable-field test starts from and mutates one entry away from."""
    return {name: "APPROVED" for name in field_names}


def all_calibration_pending_field_statuses(field_names: tuple) -> dict:
    """The real, current classification (X3-f) for a bundle that has signed nothing -- every
    field CALIBRATION_PENDING/PROPOSED_UNSIGNED, i.e. unusable. Used as the default
    'nothing is signed' fixture shape, matching what any bundle actually committed in this
    codebase looks like today."""
    return {name: "CALIBRATION_PENDING" for name in field_names}


async def seed_learner(session: AsyncSession, *, grade: int = 2) -> UUID:
    learner_id = uuid4()
    session.add(
        Learner(learner_id=learner_id, grade=grade, status="test_only", **provenance("b_learner", learner_id))
    )
    await session.flush()
    return learner_id


async def seed_runtime_bundle(session: AsyncSession) -> UUID:
    bundle_id = uuid4()
    session.add(
        CRuntimeBundleRecord(
            c_runtime_bundle_record_id=bundle_id,
            bundle_version=f"test-{bundle_id}",
            manifest_checksum=bundle_id.hex * 2,
            publication_state="DRAFT",
            approval_status="UNRESOLVED",
            immutable_after_publication=False,
            **provenance("c_runtime_bundle_record", bundle_id),
        )
    )
    await session.flush()
    return bundle_id


async def _seed_learner_and_bundle(session: AsyncSession, *, grade: int = 2) -> tuple[UUID, UUID]:
    student_id = await seed_learner(session, grade=grade)
    bundle_id = await seed_runtime_bundle(session)
    return student_id, bundle_id


def _create_session_kwargs(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "grade": 2,
        "session_mode": "combined",
        "catalogue_version": "test-catalogue-1",
        "catalogue_checksum": "a" * 64,
        "global_seed": 42,
        "selection_config": selection_config_fixture_for_tests(),
        "selection_config_field_statuses": all_usable_field_statuses(SelectionConfigurationArtifact.FIELD_NAMES),
        "safety_config_field_statuses": all_usable_field_statuses(SafetyConfigurationArtifact.FIELD_NAMES),
        "evidence_window_config_field_statuses": all_usable_field_statuses(
            EvidenceWindowConfigurationArtifact.FIELD_NAMES
        ),
        "generation_parameter_source_status": "TEST_FIXTURE_ONLY",
        "policy_parameter_source_status": "TEST_FIXTURE_ONLY",
        "scaffold_parameter_source_status": "TEST_FIXTURE_ONLY",
        "aggregation_parameter_source_status": "TEST_FIXTURE_ONLY",
        "q_policy_parameter_source_status": "TEST_FIXTURE_ONLY",   # LIVE-01: new gated family
        "smoke_mode": True,
        "request_id": f"req-{uuid4()}",
        "mastery_by_skill": fixture_b_mastery_payload_for_phase_4(),
        "mastery_source_student_id": "STU-0001",
        "mastery_source_intervention_session_id": "STU-0001-I-001",
        "mastery_source_intervention_session_number": 1,
    }
    values.update(overrides)
    return values


# =====================================================================================
# mastery_context_mode -- fixed by mode, never inferred (v3.0 §11 Phase 4 hard constraint).
# =====================================================================================


def test_mastery_context_mode_fixed_by_session_mode() -> None:
    assert mastery_context_mode_for("combined") == "same_session_fresh"
    assert mastery_context_mode_for("c_only") == "unavailable_fallback"


# =====================================================================================
# session_phase X-10: both sides of the N/W boundary, derived not constant.
# =====================================================================================


def test_c4_familiarization_at_n_zero_and_mastery_driven_at_n_equals_w() -> None:
    """SIGNAL: N=0 (grade 2, W=2) yields familiarization; N=2 (>= W) yields mastery_driven --
    both sides of the assessment's condition asserted by the SAME test, X-10 style. Would FAIL if
    session_phase were ever hardcoded to a literal (the work order's own named anti-pattern) since
    a constant could satisfy at most one side.

    N=2 is seeded directly on c_learner_local_state rather than reached by advancing N through
    real sessions: cold-start step 4 ("at session close, evaluate is_eligible_combined_handoff and
    increment N") has no endpoint to hang off in this batch -- Phase 4 names only create/start,
    resume, and abandon; no "complete" endpoint exists yet, and abandonment is deliberately never
    eligible. This gap is recorded in the build log, not silently worked around."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        adapter = LiveEngineCAdapter()
        async with factory() as session:
            student_id, bundle_id = await _seed_learner_and_bundle(session)
            record_n0 = await create_session(
                session, adapter, student_id=student_id, c_runtime_bundle_record_id=bundle_id,
                **_create_session_kwargs(),
            )
            assert record_n0.session_phase == "familiarization"
            await abandon_session(session, record_n0.c_session_id, student_id)
            await session.commit()

            from app.infrastructure.persistence_models import CLearnerLocalStateRecord

            state_id = uuid4()
            session.add(
                CLearnerLocalStateRecord(
                    c_learner_local_state_id=state_id,
                    student_id=student_id,
                    eligible_combined_handoffs_completed=2,
                    sessions_since_last_practice={},
                    prior_session_end_state=None,
                    **provenance("c_learner_local_state", state_id),
                )
            )
            await session.commit()

            record_n2 = await create_session(
                session, adapter, student_id=student_id, c_runtime_bundle_record_id=bundle_id,
                **_create_session_kwargs(
                    request_id=f"req-{uuid4()}",
                    mastery_source_intervention_session_id="STU-0001-I-002",
                    mastery_source_intervention_session_number=2,
                ),
            )
            assert record_n2.session_phase == "mastery_driven"
        await database_engine.dispose()

    asyncio.run(exercise())


def test_c4_c_only_session_phase_is_always_c_only_regardless_of_n() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        adapter = LiveEngineCAdapter()
        async with factory() as session:
            student_id, bundle_id = await _seed_learner_and_bundle(session)
            record = await create_session(
                session, adapter, student_id=student_id, c_runtime_bundle_record_id=bundle_id,
                **_create_session_kwargs(
                    session_mode="c_only", mastery_by_skill=None, mastery_source_student_id=None,
                    mastery_source_intervention_session_id=None,
                    mastery_source_intervention_session_number=None,
                ),
            )
            assert record.session_phase == "c_only"
            assert record.mastery_context_mode == "unavailable_fallback"
            await session.commit()
        await database_engine.dispose()

    asyncio.run(exercise())


# =====================================================================================
# SF-043 ordering: combined without payload, c_only with payload -- both rejected.
# =====================================================================================


def test_c4_combined_session_without_payload_raises_sf043() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        adapter = LiveEngineCAdapter()
        async with factory() as session:
            student_id, bundle_id = await _seed_learner_and_bundle(session)
            with pytest.raises(SF043OrderingError):
                await create_session(
                    session, adapter, student_id=student_id, c_runtime_bundle_record_id=bundle_id,
                    **_create_session_kwargs(
                        mastery_by_skill=None, mastery_source_student_id=None,
                        mastery_source_intervention_session_id=None,
                        mastery_source_intervention_session_number=None,
                    ),
                )
        await database_engine.dispose()

    asyncio.run(exercise())


def test_r5d_combined_session_with_payload_but_incomplete_identity_raises_sf043_not_assertionerror() -> None:
    """X-10 provocation for R-5d (Phase 4b continuation): session_lifecycle.py:134-141 used to be
    three bare ``assert`` statements -- input validation via assert is stripped under -O (would
    silently let None flow into adapter.validate_mastery_payload) and, unstripped, raises
    AssertionError (an unhandled 500, not a caught/translatable error). Proves the replacement is
    a real, catchable SF043OrderingError, for each of the three identity fields missing
    independently while mastery_by_skill IS present -- the exact caller-contract violation the
    old asserts existed to catch."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        adapter = LiveEngineCAdapter()
        async with factory() as session:
            student_id, bundle_id = await _seed_learner_and_bundle(session)
            for missing_field in (
                "mastery_source_student_id",
                "mastery_source_intervention_session_id",
                "mastery_source_intervention_session_number",
            ):
                with pytest.raises(SF043OrderingError):
                    await create_session(
                        session, adapter, student_id=student_id, c_runtime_bundle_record_id=bundle_id,
                        **_create_session_kwargs(
                            request_id=f"req-{uuid4()}", **{missing_field: None},
                        ),
                    )
        await database_engine.dispose()

    asyncio.run(exercise())


def test_c4_c_only_session_with_payload_raises_sf043() -> None:
    """SF-043 / v3.0 §11 Phase 4: C-only must not receive a B payload at all."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        adapter = LiveEngineCAdapter()
        async with factory() as session:
            student_id, bundle_id = await _seed_learner_and_bundle(session)
            with pytest.raises(SF043OrderingError):
                await create_session(
                    session, adapter, student_id=student_id, c_runtime_bundle_record_id=bundle_id,
                    **_create_session_kwargs(session_mode="c_only"),
                )
        await database_engine.dispose()

    asyncio.run(exercise())


# =====================================================================================
# R3 -- no caching at the adapter/application layer. Two sessions, same student; the second
# supplies NO payload and must fail rather than silently reusing the first session's mastery.
# =====================================================================================


def test_c4_r3_second_session_does_not_reuse_first_sessions_mastery_payload() -> None:
    """SIGNAL: session 1 (combined, valid payload) succeeds and is abandoned; session 2 for the
    SAME student, combined mode, NO payload supplied, must FAIL with SF043OrderingError -- not
    silently succeed by reusing session 1's already-validated mastery. Would FAIL (wrongly
    succeed) if any module-level or instance-level mastery state existed anywhere on the call
    path, proving R3 as a behavioural regression guard, not only the earlier structural proof
    (zero self./--init--/cache hits in adapter.py)."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        adapter = LiveEngineCAdapter()
        async with factory() as session:
            student_id, bundle_id = await _seed_learner_and_bundle(session)
            first = await create_session(
                session, adapter, student_id=student_id, c_runtime_bundle_record_id=bundle_id,
                **_create_session_kwargs(),
            )
            await session.commit()
            await abandon_session(session, first.c_session_id, student_id)
            await session.commit()

            with pytest.raises(SF043OrderingError):
                await create_session(
                    session, adapter, student_id=student_id, c_runtime_bundle_record_id=bundle_id,
                    **_create_session_kwargs(
                        mastery_by_skill=None, mastery_source_student_id=None,
                        mastery_source_intervention_session_id=None,
                        mastery_source_intervention_session_number=None,
                        request_id=f"req-{uuid4()}",
                    ),
                )
        await database_engine.dispose()

    asyncio.run(exercise())


# =====================================================================================
# Q1 -- non-arrival. A spy on the real session-creation call site proves an invalid mastery
# payload never results in a session row -- not merely that an exception was raised somewhere.
# =====================================================================================


def test_q1_invalid_mastery_payload_never_reaches_session_creation() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        adapter = LiveEngineCAdapter()
        async with factory() as session:
            student_id, bundle_id = await _seed_learner_and_bundle(session)
            spy: list = []
            invalid_mastery = dict(fixture_b_mastery_payload_for_phase_4())
            invalid_mastery["counting"] = "not-a-float"  # type: ignore[assignment]
            with pytest.raises(MasteryPayloadContractValidationError):
                await create_session(
                    session, adapter, student_id=student_id, c_runtime_bundle_record_id=bundle_id,
                    **_create_session_kwargs(mastery_by_skill=invalid_mastery),
                    session_creation_spy=spy,
                )
            assert spy == [], "a session row was created despite an invalid mastery payload"
            # Positive control: the spy mechanism itself works when the payload IS valid.
            await create_session(
                session, adapter, student_id=student_id, c_runtime_bundle_record_id=bundle_id,
                **_create_session_kwargs(request_id=f"req-{uuid4()}"),
                session_creation_spy=spy,
            )
            assert len(spy) == 1
        await database_engine.dispose()

    asyncio.run(exercise())


def test_q1_wrong_schema_version_and_wrong_component_source_both_rejected() -> None:
    """Both frozen Literal boundary markers exercised, not just one (Q1: "testing one while
    leaving the other unexercised verifies half a gate"). Direct package-level calls -- these two
    fields are hardcoded correctly by the adapter on every real call path (F2 withdrawal), so the
    only way to prove BOTH are actually enforced by the frozen contract, not merely supplied
    correctly by convention, is to construct payloads that get them wrong and watch validate_payload
    itself reject each independently."""
    from validators.contract_validators import ContractValidationError, validate_payload

    base_payload = {
        "mastery_counting": 0.5, "mastery_number_sense": 0.5, "mastery_place_value": 0.5,
        "mastery_addition": 0.5, "mastery_subtraction": 0.5, "mastery_multiplication": 0.5,
        "mastery_division": 0.5, "schema_version": "2.1", "student_id": "STU-0001",
        "intervention_session_id": "STU-0001-I-001", "intervention_session_number": 1,
        "component_source": "B",
    }

    wrong_schema_version = {**base_payload, "schema_version": "9.9"}
    with pytest.raises(ContractValidationError):
        validate_payload(wrong_schema_version, "b_to_c")

    wrong_component_source = {**base_payload, "component_source": "C"}
    with pytest.raises(ContractValidationError):
        validate_payload(wrong_component_source, "b_to_c")

    # Positive control: the base payload (both fields correct) validates cleanly.
    validate_payload(base_payload, "b_to_c")


# =====================================================================================
# Q2 -- pydantic leakage. A sentinel appears in none of: the exception string, captured log
# records, or field_errors' structured data (which carries only loc/type, never input/msg).
# =====================================================================================


def test_q2_sentinel_never_leaks_into_exception_string_or_field_errors(caplog: pytest.LogCaptureFixture) -> None:
    adapter = LiveEngineCAdapter()
    sentinel = "SENTINEL_MUST_NOT_LEAK_7f3a2c"

    with pytest.raises(MasteryPayloadContractValidationError) as excinfo:
        adapter.validate_mastery_payload(
            fixture_b_mastery_payload_for_phase_4(),
            mastery_source_student_id=sentinel,
            mastery_source_intervention_session_id="STU-0001-I-001",
            mastery_source_intervention_session_number=1,
        )

    assert sentinel not in str(excinfo.value)
    for loc, code in excinfo.value.field_errors:
        assert sentinel not in str(loc)
        assert sentinel not in code
    for record in caplog.records:
        assert sentinel not in record.getMessage()


# =====================================================================================
# S-1 -- the reachable c_sessions.state subset Phase 4's own code can actually produce, per the
# SUPERVISOR RULING (lead): "Add a test asserting which subset Phase 4 can actually REACH, so the
# unreachable states are documented rather than assumed."
# =====================================================================================

PHASE_4_REACHABLE_STATES = frozenset({"active", "abandoned", "completed"})
ALL_SESSION_STATES = frozenset(
    {"starting", "active", "completing", "completed", "abandoned", "expired", "technical_failed"}
)


def test_s1_phase_4_reachable_state_subset_is_documented() -> None:
    """SIGNAL (UPDATED, Phase 4b/B4-c): Phase 4b's create_session/abandon_session/complete_session
    code paths produce {"active", "abandoned", "completed"} -- confirmed by grepping this module's
    own source for every string literal assigned to `.state` or `state="..."`. "completed" is new
    this batch (B4-a's completion path); "active" and "abandoned" are unchanged from Phase 4a --
    the underlying fact this test proves (which states Phase 4's code can actually reach) has
    genuinely moved, an UPDATE, not a weakening. The remaining SESSION_STATES values (starting,
    completing, expired, technical_failed) are NOT unreachable-by-mistake; they are simply not
    this phase's job to produce, and the CHECK constraint constrains what may be WRITTEN without
    requiring every value be reachable (S-1 ruling text)."""
    import re
    from pathlib import Path

    source = Path("app/application/live_engine_c/session_lifecycle.py").read_text(encoding="utf-8")
    literal_states = set(re.findall(r'state\s*=\s*"([a-z_]+)"', source))
    assert literal_states == PHASE_4_REACHABLE_STATES, literal_states
    assert PHASE_4_REACHABLE_STATES < ALL_SESSION_STATES
    assert ALL_SESSION_STATES - PHASE_4_REACHABLE_STATES == {
        "starting", "completing", "expired", "technical_failed",
    }


# =====================================================================================
# c_sessions.state CHECK -- provocation (X-10). Same table build helper as above, direct insert.
# =====================================================================================


def test_c4_state_check_rejects_value_outside_session_states() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            student_id, bundle_id = await _seed_learner_and_bundle(session)
            from app.infrastructure.persistence_models import CSessionRecord

            session_id = uuid4()
            session.add(
                CSessionRecord(
                    c_session_id=session_id,
                    student_id=student_id,
                    intervention_session_id=f"i-{session_id}",
                    session_mode="c_only",
                    session_phase="c_only",
                    mastery_context_mode="unavailable_fallback",
                    catalogue_version="v",
                    catalogue_checksum="a" * 64,
                    c_runtime_bundle_record_id=bundle_id,
                    grade=2,
                    state="not_a_real_state",
                    global_seed=1,
                    started_at_utc=datetime.now(UTC),
                    completed_at_utc=None,
                    row_version=0,
                    **provenance("c_session", session_id),
                )
            )
            with pytest.raises(IntegrityError) as excinfo:
                await session.commit()
            assert excinfo.value.orig.__cause__.constraint_name == "ck_c_sessions_state"
            await session.rollback()
        await database_engine.dispose()

    asyncio.run(exercise())


# =====================================================================================
# Resume / abandon lifecycle.
# =====================================================================================


def test_c4_resume_finds_active_session_and_abandon_transitions_it() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        adapter = LiveEngineCAdapter()
        async with factory() as session:
            student_id, bundle_id = await _seed_learner_and_bundle(session)
            created = await create_session(
                session, adapter, student_id=student_id, c_runtime_bundle_record_id=bundle_id,
                **_create_session_kwargs(),
            )
            await session.commit()

            active = await get_active_session(session, student_id)
            assert active is not None and active.c_session_id == created.c_session_id

            abandoned = await abandon_session(session, created.c_session_id, student_id)
            await session.commit()
            assert abandoned.state == "abandoned"

            assert await get_active_session(session, student_id) is None

            with pytest.raises(ConflictError):
                await abandon_session(session, created.c_session_id, student_id)

            with pytest.raises(ResourceNotFoundError):
                await abandon_session(session, uuid4(), student_id)
        await database_engine.dispose()

    asyncio.run(exercise())


def test_c4_create_session_idempotent_by_learner_state() -> None:
    """v3.0 §11 Phase 4: "idempotent by learner state" -- a second create_session call for a
    student who already has a starting/active session returns the EXISTING row, never a second
    one."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        adapter = LiveEngineCAdapter()
        async with factory() as session:
            student_id, bundle_id = await _seed_learner_and_bundle(session)
            first = await create_session(
                session, adapter, student_id=student_id, c_runtime_bundle_record_id=bundle_id,
                **_create_session_kwargs(),
            )
            await session.commit()
            second = await create_session(
                session, adapter, student_id=student_id, c_runtime_bundle_record_id=bundle_id,
                **_create_session_kwargs(request_id=f"req-{uuid4()}"),
            )
            assert second.c_session_id == first.c_session_id
        await database_engine.dispose()

    asyncio.run(exercise())
