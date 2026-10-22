"""Component C Phase 4: session creation/start, resume, abandon; the two session modes;
mastery_context_mode determination; the cold-start gate (SF-043); C-16's closure.

W — OWNER-RULED, INJECTION, NO DEFAULT ANYWHERE (Phase 4 work order): every function below that
needs a ``SelectionConfig`` takes it as a REQUIRED, no-default parameter. This module never
calls ``default_selection_config()`` and never hardcodes ``familiarization_window_by_grade``
anywhere. That is asserted mechanically, not by convention -- see
``backend/tests/test_be2_architecture_guards.py::test_no_app_code_defaults_or_calls_default_selection_config``.

R3 — NO CACHING AT THIS LAYER. This module holds no module-level or instance-level mastery
state. Every mastery payload is validated fresh, used once (to satisfy the SF-043 gate and
determine ``mastery_context_mode``), and is never persisted to ``c_sessions`` or any other table
-- ``c_sessions`` has no ``mastery_*`` column (Phase 3a schema, unchanged this batch).

Q1 — the chokepoint this phase owns: session CREATION itself. A ``combined`` session's mastery
payload is validated BEFORE the ``CSessionRecord`` is ever added to the database session; if
validation fails, no row is created. Tests spy on ``CSessionRecordRepository.add`` to prove this
mechanically, not by inference from "an error was raised somewhere."
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Mapping, Optional
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.live_engine_c.bundle_resolution import assert_code_gated_family_usable, assert_family_usable
from app.core.errors import ConflictError, ResourceNotFoundError
from app.domain.live_engine_c.errors import SF043OrderingError
from app.domain.live_engine_c.types import AttendanceStatus, Grade, LearnerSessionState, SelectionConfig, SessionMode
from app.infrastructure.live_engine_c.adapter import LiveEngineCAdapter
from app.infrastructure.persistence_models import CLearnerLocalStateRecord, CSessionRecord
from app.infrastructure.repositories import CLearnerLocalStateRepository, CSessionRecordRepository

SCHEMA_REVISION = "20260816_0004"


def mastery_context_mode_for(session_mode: SessionMode) -> str:
    """v3.0 §11 Phase 4 hard constraint: fixed by mode, never inferred from anything else."""
    if session_mode == "combined":
        return "same_session_fresh"
    return "unavailable_fallback"


def _provenance(resource_type: str, resource_id: UUID, request_id: str, operation: str) -> dict[str, object]:
    return {
        "system_actor": "c-session-lifecycle",
        "request_id": request_id,
        "operation_or_event_type": operation,
        "reason_code": "AUTHORIZED_C_SESSION_LIFECYCLE_COMMAND",
        "resource_type": resource_type,
        "resource_id": resource_id,
        "source_class": "REAL",
        "source_system": "studentapp-api",
        "environment": "live-endpoint",
        "schema_revision": SCHEMA_REVISION,
    }


async def _learner_session_state(
    session: AsyncSession, student_id: UUID
) -> tuple[LearnerSessionState, Optional[CLearnerLocalStateRecord]]:
    record = await CLearnerLocalStateRepository(session).find_by_student(student_id)
    if record is None:
        return LearnerSessionState(
            eligible_combined_handoffs_completed=0,
            sessions_since_last_practice={},
            prior_session_end_state=None,
        ), None
    return LearnerSessionState(
        eligible_combined_handoffs_completed=record.eligible_combined_handoffs_completed,
        sessions_since_last_practice=dict(record.sessions_since_last_practice),
        prior_session_end_state=record.prior_session_end_state,
    ), record


async def create_session(
    session: AsyncSession,
    adapter: LiveEngineCAdapter,
    *,
    student_id: UUID,
    grade: Grade,
    session_mode: SessionMode,
    catalogue_version: str,
    catalogue_checksum: str,
    c_runtime_bundle_record_id: UUID,
    global_seed: int,
    selection_config: SelectionConfig,
    selection_config_field_statuses: Mapping[str, str],
    safety_config_field_statuses: Mapping[str, str],
    evidence_window_config_field_statuses: Mapping[str, str],
    generation_parameter_source_status: str,
    policy_parameter_source_status: str,
    scaffold_parameter_source_status: str,
    aggregation_parameter_source_status: str,
    q_policy_parameter_source_status: str,
    smoke_mode: bool,
    request_id: str,
    mastery_by_skill: Optional[Mapping[str, float]] = None,
    mastery_source_student_id: Optional[str] = None,
    mastery_source_intervention_session_id: Optional[str] = None,
    mastery_source_intervention_session_number: Optional[int] = None,
    session_creation_spy: Optional[list] = None,
) -> CSessionRecord:
    """v3.0 §11 Phase 4: ``POST /api/v1/c/sessions`` (idempotent by learner state -- an existing
    starting/active session for this student is returned unchanged rather than creating a
    second). ``session_creation_spy``, when supplied, has one item appended to it each time (and
    only when) a ``CSessionRecord`` is actually added -- Q1's non-arrival proof.

    Phase 4b concurrency (B3): mirrors ``app.application.b_session_lifecycle.start_session``'s
    own mechanism exactly -- a ``pg_advisory_xact_lock`` before the existence check serializes
    concurrent callers for the SAME student, and the eventual INSERT is wrapped in an
    ``IntegrityError`` catch translating a real race (two concurrent callers both passing the
    pre-lock check for different ``intervention_session_id`` values, or a duplicate) into
    ``ConflictError`` rather than an unhandled 500. Mirroring B's mechanism is NOT the same as
    proving it holds under two real concurrent connections -- this suite has no two-connection
    harness, so only the SEQUENTIAL shape (lock acquired, then checked) is exercised by test; the
    partial unique index on ``c_sessions`` (``uq_c_sessions_one_starting_or_active_per_learner``,
    migration 20260816_0005) is the actual, DB-enforced backstop if the advisory lock is ever
    bypassed or the race window is hit anyway.

    PHASE 6b, S2/X4 -- THE STRUCTURAL GATE, BOTH FAMILIES, HERE, BEFORE ANY CSessionRecord EXISTS:
    ``assert_family_usable`` is called TWICE below -- once for ``selection_config``'s five real
    fields, once for ``safety_config``'s nine -- inside THIS function, not merely ordered before
    it by a caller (S7's own finding: incidental ordering is not a gate, it holds only until
    someone reorders a call). Owner's inversion (S2), the reason this is here and not inside
    ``adapt``/the per-task call: "If safety config is unusable and the consuming path refuses,
    the session proceeds WITHOUT safety... for any protective capability, fail-closed must mean
    refuse the protected activity, never refuse the protection." No session exists to need
    protecting once this refuses.

    DISCLOSED PLAINLY (X2-3, same register position Phase 5 used for "endpoints deliberately not
    live"): under this batch's own real field classification (X3-f -- every SPEC-cited value is
    ``PROPOSED_UNSIGNED``, every uncited value is ``CALIBRATION_PENDING``, and the usable
    whitelist is ``{APPROVED}`` only, X1), NO bundle committed anywhere in this codebase can ever
    satisfy this gate today. As of this batch, Component C's backend cannot create a session in
    production at all -- not a bug, the direct, intended consequence of X1's whitelist applied to
    a project where nothing is yet signed. This is stated here, in the schema's own description,
    and in the batch's build-log headline -- not left for someone to discover as a defect and
    "fix" by loosening the whitelist.

    PHASE 7, Z1/Z2 -- CLASSIFICATION AND GATING ARE SEPARATE AXES. Owner ruling, quoted: "A
    parameter family containing at least one field a governing document specifies belongs in the
    bundle under per-field source/status. A family with no specified fields stays injection-only
    and smoke-gated... CLASSIFICATION decides where values LIVE... GATING is uniform and
    independent: EVERY parameter family gates SESSION START. One check at session creation, each
    family feeding it by its own mechanism -- bundle approval status, or the code gate." Z1's own
    verification found ZERO SPEC-stated fields for Generation, Policy, and Scaffold (§15 gives no
    numeric threshold for any of Scaffold's four fields, matching the same absence already found
    for Generation and Policy) -- all three stay injection-only, no bundle block, no schema
    widening. But all FIVE families gate HERE, at session start, now: two via
    ``assert_family_usable`` (bundle per-field status), three via
    ``assert_code_gated_family_usable`` (code gate, ``smoke_mode`` against
    ``parameter_source_status`` -- the exact mechanism ``generation_mode_guard.
    assert_generation_config_permitted`` already used for Generation alone, generalized). WHY
    Policy needs this and it is not obvious without tracing: "apply_safety is called INSIDE
    decide_adaptation at adaptation.py:46. If Policy's config is unusable and the policy path
    refuses, safety never runs at all -- even with safety config perfectly usable. Policy's gate
    is load-bearing for safety whether or not anyone intended that." Verified directly:
    ``component_c_generator/adaptation.py:46`` reads
    ``safety_decision = apply_safety(selected_action=selected_action, evidence=evidence, ...)``,
    called unconditionally, immediately after ``propose_action`` -- Policy failing before that
    line means Safety's own call is never reached. NO NEW PRODUCTION RESTRICTION: safety already
    refused session creation unconditionally (X2-3); uniform gating costs nothing today because
    nothing was reachable in production before this change either.

    PHASE 9a -- SIX FAMILIES, NOT FIVE (owner ruling, applying Z2's own existing rule, never
    extending it): supervisor-verified, five families were gated here and ``aggregation_config``
    was not, "because nothing consumed it when Z2 was written." Distinguished, in the record, from
    Phase 8's own telemetry family, which was NOT created (K2-e): telemetry's every candidate
    field was blocked, so a gate for it would have gated nothing the other five did not already
    gate -- ceremony. ``AggregationConfig`` is different in kind: it EXISTS (``domain/live_engine_c/
    types.py:472-475``), is CONSUMED by pinned code
    (``aggregation.derive._decide_difficulty_trend`` reads
    ``config.min_completed_tasks_for_difficulty_trend`` directly), and THIS BATCH USES IT
    (``aggregation_service.derive_and_persist_session_aggregate``). Gating five families and not
    this one was an inconsistency, not restraint -- Z2's own rule ("EVERY parameter family gates
    SESSION START") already covered it; this batch applies that existing rule rather than writing
    a new one.

    SEVENTH-FAMILY GATE BATCH -- SEVEN FAMILIES, NOT SIX (supervisor ruling, applying Z2's own
    existing rule a second time, never extending it): a follow-on batch found the SAME shape of
    gap ``AggregationConfig`` was in before Phase 9a -- ``build_evidence_for_session`` requires an
    ``EvidenceWindowConfig`` and no phase had ever wired a production source or a session-start
    gate for it, "because nothing consumed it when [Phase 7's gate] was written," the identical
    reason this docstring gives above for ``aggregation_config``. Unlike ``AggregationConfig``
    (zero SPEC-stated fields, code-gated), ``EvidenceWindowConfig`` is BUNDLE-classified
    (supervisor ruling): ``recent_window_task_count`` IS SPEC-cited (C Parameters §14,
    "recent_success_rate_bucket: over last N=5 completed tasks"), which is what makes a parameter
    family bundle-classified under the standing rule ("a parameter family containing at least one
    field a governing document specifies belongs in the bundle under per-field source/status").
    So this seventh family gates the SAME way Selection and Safety already do --
    ``assert_family_usable`` on its own per-field status map, not
    ``assert_code_gated_family_usable`` -- even though, like Safety's own
    ``prior_overloaded_disengaged_cap``, the cited value carries no ``const`` and its status stays
    PROPOSED_UNSIGNED (the SPEC itself is unapproved), never APPROVED, never a resolution recorded
    here. SCHEMA-OPTIONAL BUT GATE-REQUIRED, STATED EXPLICITLY SO NEITHER READS AS THE OTHER: a
    1.2 bundle with no ``evidence_window_configuration`` block still VALIDATES under schema_version
    1.3 (additive, exactly like ``safety_configuration`` was additive at 1.2) -- but a bundle
    lacking the block cannot CREATE A SESSION, because an absent block means this family's
    usability is unknown, and unknown is not usable. ``PRODUCTION_EVIDENCE_WINDOW_CONFIG_PROBE``
    (``task_service.py``, batch 2's own disclosed placeholder) is REMOVED by this batch, not left
    beside the real resolver -- ``task_service.submit_action`` now resolves
    ``EvidenceWindowConfig`` from the bundle on the same path ``safety_config``/``selection_config``
    already use."""
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:scope, 0))"),
        {"scope": f"c_session.create:{student_id}"},
    )
    repository = CSessionRecordRepository(session)
    existing = await repository.find_starting_or_active_for_learner(student_id)
    if existing is not None:
        return existing

    # X4/Z2: one mechanism (two entry points, one error type), called SEVEN times (the
    # SEVENTH-FAMILY GATE batch adds evidence_window_config, below), before any CSessionRecord is
    # constructed -- every family feeds the SAME gate, by its own mechanism.
    assert_family_usable(family_name="selection_config", field_statuses=selection_config_field_statuses)
    assert_family_usable(family_name="safety_config", field_statuses=safety_config_field_statuses)
    assert_family_usable(
        family_name="evidence_window_config", field_statuses=evidence_window_config_field_statuses
    )
    assert_code_gated_family_usable(
        family_name="generation_config",
        parameter_source_status=generation_parameter_source_status,
        smoke_mode=smoke_mode,
    )
    assert_code_gated_family_usable(
        family_name="policy_config",
        parameter_source_status=policy_parameter_source_status,
        smoke_mode=smoke_mode,
    )
    assert_code_gated_family_usable(
        family_name="scaffold_config",
        parameter_source_status=scaffold_parameter_source_status,
        smoke_mode=smoke_mode,
    )
    assert_code_gated_family_usable(
        family_name="aggregation_config",
        parameter_source_status=aggregation_parameter_source_status,
        smoke_mode=smoke_mode,
    )
    # LIVE-01: the frozen Q policy is a new config consumer (production decides difficulty with it); same
    # code-gated mechanism, status read from the hash-verified provenance/c_policy/MANIFEST.json.
    assert_code_gated_family_usable(
        family_name="q_policy_config",
        parameter_source_status=q_policy_parameter_source_status,
        smoke_mode=smoke_mode,
    )

    if session_mode == "c_only":
        if mastery_by_skill is not None:
            raise SF043OrderingError(
                "c_only session must not receive a B mastery payload (SF-043)"
            )
    else:
        if mastery_by_skill is None:
            raise SF043OrderingError(
                "combined session requires a same-session B mastery payload (SF-043)"
            )
        # R-5d: input validation must never use bare `assert` -- Python strips it under -O
        # (silently letting None reach validate_mastery_payload/CSessionRecord below), and
        # unstripped it surfaces as an unhandled 500 rather than a caught, translatable error.
        # A combined-mode caller (CSessionService.create, via the fixture producer) must always
        # pair mastery_by_skill with all three identity fields together; reaching here with one
        # present and another absent is a caller-contract violation of the same SF-043 ordering
        # this function already owns, so it is raised as the same SF043OrderingError type rather
        # than a new one.
        if (
            mastery_source_student_id is None
            or mastery_source_intervention_session_id is None
            or mastery_source_intervention_session_number is None
        ):
            raise SF043OrderingError(
                "combined session requires mastery_by_skill and all three B identity fields "
                "together (SF-043) -- caller supplied mastery_by_skill without a complete "
                "identity triple"
            )
        # Validated here, BEFORE any session row exists -- Q1's chokepoint. Raises the raw
        # domain MasteryPayloadContractValidationError (unchanged from Phase 4a, preserving its
        # own tests); the HTTP-facing translation into MasteryPayloadRejectedError (B2-c,
        # structured (loc, type) pairs only) happens at the route boundary, not here -- nothing
        # below this point executes on rejection, and nothing is added to `session`.
        adapter.validate_mastery_payload(
            mastery_by_skill,
            mastery_source_student_id=mastery_source_student_id,
            mastery_source_intervention_session_id=mastery_source_intervention_session_id,
            mastery_source_intervention_session_number=mastery_source_intervention_session_number,
        )

    learner_state, _ = await _learner_session_state(session, student_id)
    session_phase = adapter.decide_next_session_phase(
        session_mode=session_mode, grade=grade, state=learner_state, selection_config=selection_config,
    )

    c_session_id = uuid4()
    record = CSessionRecord(
        c_session_id=c_session_id,
        student_id=student_id,
        intervention_session_id=mastery_source_intervention_session_id,
        session_mode=session_mode,
        session_phase=session_phase,
        mastery_context_mode=mastery_context_mode_for(session_mode),
        catalogue_version=catalogue_version,
        catalogue_checksum=catalogue_checksum,
        c_runtime_bundle_record_id=c_runtime_bundle_record_id,
        grade=grade,
        state="active",
        global_seed=global_seed,
        started_at_utc=datetime.now(UTC),
        completed_at_utc=None,
        row_version=0,
        **_provenance("c_session", c_session_id, request_id, "c_session.started"),
    )
    try:
        await repository.add(record)
    except IntegrityError as exc:
        raise ConflictError() from exc
    if session_creation_spy is not None:
        session_creation_spy.append(c_session_id)
    return record


async def get_active_session(session: AsyncSession, student_id: UUID) -> Optional[CSessionRecord]:
    """v3.0 §11 Phase 4: ``GET /api/v1/c/sessions/active`` -- resume after a crash."""
    return await CSessionRecordRepository(session).find_active_for_learner(student_id)


async def abandon_session(session: AsyncSession, c_session_id: UUID, student_id: UUID) -> CSessionRecord:
    """v3.0 §11 Phase 4: ``POST /api/v1/c/sessions/{id}/abandon`` -- safe termination. Reachable
    Phase-4 states: active -> abandoned only (S-1). Never an eligible combined handoff (B4-b) --
    abandonment is deliberately excluded from N's increment, mirroring
    ``is_eligible_combined_handoff``'s own semantics (a session that did not complete is not an
    eligible completed combined handoff)."""
    repository = CSessionRecordRepository(session)
    record = await repository.get_owned(c_session_id, student_id)
    if record is None:
        raise ResourceNotFoundError()
    if record.state != "active":
        raise ConflictError()
    record.state = "abandoned"
    record.row_version += 1
    await session.flush()
    return record


async def complete_session(
    session: AsyncSession,
    adapter: LiveEngineCAdapter,
    c_session_id: UUID,
    student_id: UUID,
    *,
    attendance_status: AttendanceStatus,
    technical_blocked_bootstrap: bool = False,
) -> CSessionRecord:
    """Phase 4b, B4-a: ``POST /api/v1/c/sessions/{id}/complete``, mirroring
    ``app.api.routes.b_session``'s own ``complete_session`` route shape (``b_session.py:67``).
    v3.0 §11 Phase 4's own Scope names NO completion endpoint -- this fills a gap in that plan
    under the owner's ruling ("do Phase 4b for the three routes + legitimate production
    SelectionConfig source + completion/N-increment path"), not something v3.0 itself specifies.

    B4-b: N increments ONLY when ``is_eligible_combined_handoff`` holds, evaluated THROUGH THE
    ADAPTER (never reimplemented here) -- the five-condition predicate the cold-start assessment
    names, translated verbatim by ``LiveEngineCAdapter.is_eligible_combined_handoff``.
    ``b_payload_valid`` is derived from ``session_mode == "combined"`` (a fresh, validated payload
    is a precondition of ``create_session`` ever reaching `state="active"` in combined mode --
    SF-043 already enforced it at creation time; there is no cached payload to re-validate here,
    R3).

    B4-d / SF-040: a fully missed slot never reaches this function at all -- SF-040 says a fully
    missed slot emits NO row, so there is no ``CSessionRecord`` to complete; ``attendance_status``
    here describes THIS session's own completion context (used only by the eligibility
    predicate), not a substitute row for a missed one."""
    repository = CSessionRecordRepository(session)
    record = await repository.get_owned(c_session_id, student_id)
    if record is None:
        raise ResourceNotFoundError()
    if record.state != "active":
        raise ConflictError()

    eligible = adapter.is_eligible_combined_handoff(
        record.session_mode,
        record.session_mode == "combined",
        attendance_status,
        technical_blocked_bootstrap,
    )

    record.state = "completed"
    record.completed_at_utc = datetime.now(UTC)
    record.row_version += 1

    if eligible:
        state_repository = CLearnerLocalStateRepository(session)
        local_state = await state_repository.find_by_student(student_id)
        if local_state is None:
            local_state_id = uuid4()
            local_state = CLearnerLocalStateRecord(
                c_learner_local_state_id=local_state_id,
                student_id=student_id,
                eligible_combined_handoffs_completed=1,
                sessions_since_last_practice={},
                prior_session_end_state=None,
                **_provenance("c_learner_local_state", local_state_id, f"complete-{c_session_id}", "c_session.completed"),
            )
            session.add(local_state)
        else:
            local_state.eligible_combined_handoffs_completed += 1

    await session.flush()
    return record
