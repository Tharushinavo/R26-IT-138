"""Component C batch 9b-1 (`9b1-work-order.md`) -- the C->3 emission surface.

Builds the first caller of ``emit_c_to_3`` (D3, the adapter method) and proves D4's four
acceptance criteria against constructed fixtures. No mapping table, no live caller, no route (§2).

**D6 mandatory disclosure, stated here as the module's own record (also recorded in the build
log):** nothing real can be emitted through this surface for two independent reasons. The
AGGREGATE half is blocked by ``app.application.live_engine_c.aggregation_service.
_AGGREGATION_INPUTS_AVAILABLE = False`` (aggregation_service.py:126), which stays ``False`` until
the target band is defined -- untouched by this batch. The IDENTITY half is blocked by
``SharedInterventionSessionMapping`` not existing as a table/model in either component -- also
untouched by this batch (out of scope, §6). **32 of 39 payload fields cannot be populated from
real data.** The correct framing is: the emission path has no possible caller until shared session
mapping exists AND aggregation inputs have a real source -- NOT "9b-1 is incomplete". Every fixture
in this file is therefore hand-constructed, exactly as the 9b-1 plan disclosed it would be.

**SF-040 FINDING (supervisor ruling 1 on the 9b-1 plan, recorded here and in
``app/domain/live_engine_c/errors.py::NoRealCSessionError``):** the work order originally asked
for both SF-040 arms (``c_present`` false, ``c_session_id`` null) tested independently. Only the
first is constructible. ``SharedInterventionSessionMapping.validate_mapping_invariants``
(``packaging/component_b_internal/models/contracts.py:96-107``, CD-04) enforces
``c_present == (c_session_id is not None)`` on every mapping row at construction, and
``emit_c_to_3`` validates the mapping row (``validate_payload(mapping_row, "mapping")``) BEFORE
testing SF-040 (``component_c_generator/c_to_3/emit.py:58-60``). The two disjuncts SF-040 tests
are therefore logically equivalent given CD-04; the ``c_session_id is None`` disjunct with
``c_present`` true is not independently constructible as a mapping-row fixture. It is defensive
redundancy in the vendored source, not a separately reachable branch. This file tests the one
constructible case only.

**9b-1 obligation 4a -- STATIC HALF ONLY (supervisor ruling 4).** This file proves
``LiveEngineCAdapter.emit_c_to_3`` cannot be called without an ``aggregate`` (no default, not
``Optional``). It does not and cannot trace a live aggregation refusal reaching this call and
stopping before it -- that dynamic half needs a real caller, out of scope here, and is inherited
forward exactly as 9c-1b inherited the analogous limitation one link earlier
(``tests/test_9c1b_outbox_enqueue.py``'s own module docstring records the identical shape).

**9b-1 obligation 4b -- DEFERRED, not narrowed.** ``enqueue_outbox_event``'s
``payload: Mapping[str, Any]`` is left untouched by this batch. Narrowing it to the domain
``CToComponent3Payload`` would make shared B/C outbox infrastructure C-only before B's own side is
built, and contradicts the accessor's own docstring commitment to opaque storage
(``app/application/live_engine_c/outbox_enqueue.py:98-101``). No wrapper is built either --
building one now would be inventing a call path with no real caller behind it. See the build log
for the full reasoning (supervisor ruling accepted this recommendation as-is).

**Fixture-consistency method (supervisor ruling 5, binding).** ``_build_consistent_fixture()``
below computes every derived field (accuracy_rate, task_completion_rate, telemetry_quality_status,
engagement/frustration components and scores, learner_state, state_reason) using the SAME
expression shape as ``models.contracts.CToComponent3Payload.validate_deterministic_invariants``
(``packaging/component_b_internal/models/contracts.py:259-419``), transcribed with line-range
citations at each step. This is TEST-FIXTURE ARITHMETIC, executing an already-frozen formula, not
a re-implementation the adapter depends on and not an invented scientific value. If this fixture
had ever failed validation during implementation, the instruction was to STOP and report rather
than adjust it -- it did not fail; the values below round-trip cleanly through the frozen
validator (confirmed by ``test_emit_c_to_3_payload_validates_against_frozen_schema``, which
re-validates the adapter's output through ``validate_payload(..., "c_to_3")`` a second, standalone
time)."""

from __future__ import annotations

import dataclasses
import inspect
import json
import typing
from datetime import date, datetime, timezone

import pytest

from app.domain.live_engine_c.errors import NoRealCSessionError
from app.domain.live_engine_c.types import (
    CToComponent3Payload as DomainCToComponent3Payload,
    CToComponent3Provenance as DomainCToComponent3Provenance,
    EngagementComponents as DomainEngagementComponents,
    FrustrationComponents as DomainFrustrationComponents,
    SessionAggregate as DomainSessionAggregate,
)
from app.infrastructure.live_engine_c.adapter import LiveEngineCAdapter

STUDENT_ID = "STU-0007"
INTERVENTION_SESSION_ID = "STU-0007-I-004"
C_SESSION_ID = "STU-0007-C-002"
INTERVENTION_SESSION_NUMBER = 4
INTERVENTION_SESSION_DATE = date(2026, 2, 10)


def _mapping_row_no_real_c_session() -> dict:
    """The ONLY constructible SF-040 fixture -- see this module's own docstring finding.
    ``b_present=True``/``b_session_id`` set because CD-01/CD-05
    (``models/contracts.py:101-102``) prohibits a mapping row where neither B nor C is present."""
    return {
        "schema_version": "1.0",
        "student_id": STUDENT_ID,
        "intervention_session_id": INTERVENTION_SESSION_ID,
        "intervention_session_number": INTERVENTION_SESSION_NUMBER,
        "intervention_session_date": INTERVENTION_SESSION_DATE,
        "b_session_id": f"{STUDENT_ID}-B-001",
        "c_session_id": None,
        "b_present": True,
        "c_present": False,
    }


def _mapping_row_real_c_session() -> dict:
    return {
        "schema_version": "1.0",
        "student_id": STUDENT_ID,
        "intervention_session_id": INTERVENTION_SESSION_ID,
        "intervention_session_number": INTERVENTION_SESSION_NUMBER,
        "intervention_session_date": INTERVENTION_SESSION_DATE,
        "b_session_id": None,
        "c_session_id": C_SESSION_ID,
        "b_present": False,
        "c_present": True,
    }


def _clamp01(value: float) -> float:
    # Mirrors models/contracts.py:173-174 verbatim.
    return max(0.0, min(1.0, value))


def _build_consistent_fixture() -> dict:
    """Builds one internally-consistent set of C->3 field values. Raw counts are freely chosen
    (but internally ordered, per C3-RG-01/C3-DF-05); every derived field is computed using the
    exact expression shape of ``models.contracts.CToComponent3Payload.
    validate_deterministic_invariants`` (line ranges cited per field below) -- executed, not
    re-authored, and not simplified algebraically (so float drift cannot trip the validator's own
    0.005 / 1e-6 tolerances). Returns a flat dict of every value the adapter call and the
    standalone payload-dict tests both need."""
    task_opportunity_count = 6
    completed_task_count = 5
    correct_task_count = 4
    total_attempt_count = 6
    inactivity_periods = 1
    inactive_time_sec = 20.0
    session_duration_sec = 300.0
    time_in_target_band_sec = 100.0
    consecutive_error_max = 1
    difficulty_floor_hits = 0
    quit_after_error = False
    safety_override_count = 0
    session_technical_issue_flag = False
    current_difficulty_level = 3
    difficulty_trend = "stable"
    c_mean_game_task_latency_sec = 12.0
    c_median_game_task_latency_sec = 11.0

    # C3-DF-02/C3-DF-03 (contracts.py:276, 278) -- completed_task_count > 0 arm.
    accuracy_rate = correct_task_count / completed_task_count
    avg_attempts_per_task = total_attempt_count / completed_task_count
    # C3-DF-04 (contracts.py:284) -- task_opportunity_count > 0 arm.
    task_completion_rate = completed_task_count / task_opportunity_count

    # C3-WU-01 sufficient_evidence (contracts.py:294-301).
    sufficient_evidence = (
        not session_technical_issue_flag
        and task_opportunity_count >= 5
        and completed_task_count >= 3
        and session_duration_sec >= 120
        and accuracy_rate is not None
        and task_completion_rate is not None
    )
    # C3-WU-01 status selection (contracts.py:303-311).
    if session_technical_issue_flag:
        telemetry_quality_status = "technical_issue"
    elif not sufficient_evidence:
        telemetry_quality_status = "insufficient_evidence"
    else:
        telemetry_quality_status = "complete"
    assert telemetry_quality_status == "complete"  # this fixture targets the richest arm

    fallback = False  # composite_formula_version == "C-COMP-v1" (not the fallback variant)

    # Engagement (contracts.py:338-362).
    completion_component = _clamp01(task_completion_rate)
    if fallback:
        activity_component = _clamp01(1 - inactivity_periods / 5)
    else:
        activity_component = _clamp01(1 - inactive_time_sec / session_duration_sec)
    target_band_component = _clamp01(time_in_target_band_sec / session_duration_sec)
    accuracy_component = _clamp01(accuracy_rate)
    engagement_score = (
        0.30 * completion_component + 0.30 * activity_component
        + 0.25 * target_band_component + 0.15 * accuracy_component
    )

    # Frustration (contracts.py:364-393).
    error_run_component = _clamp01(consecutive_error_max / 5)
    excess_attempt_component = _clamp01((avg_attempts_per_task - 1) / 3)
    if fallback:
        inactivity_burden_component = _clamp01(inactivity_periods / 5)
    else:
        inactivity_burden_component = _clamp01((inactive_time_sec / session_duration_sec) / 0.30)
    floor_hit_component = _clamp01(difficulty_floor_hits / 3)
    quit_after_error_component = 1.0 if quit_after_error else 0.0
    safety_override_component = _clamp01(safety_override_count / 2)
    frustration_index = (
        0.25 * error_run_component + 0.20 * excess_attempt_component
        + 0.15 * inactivity_burden_component + 0.15 * floor_hit_component
        + 0.15 * quit_after_error_component + 0.10 * safety_override_component
    )

    # Learner-state rule chain (contracts.py:395-412), first-match-wins.
    if safety_override_count >= 1 and consecutive_error_max >= 4:
        learner_state, state_reason = "overloaded", "safety_override_with_error_burst"
    elif quit_after_error:
        learner_state, state_reason = "overloaded", "quit_after_error"
    elif difficulty_floor_hits >= 2 and task_completion_rate < 0.60:
        learner_state, state_reason = "overloaded", "repeated_floor_hits_with_low_completion"
    elif frustration_index >= 0.70:
        learner_state, state_reason = "overloaded", "high_behavioral_friction"
    elif engagement_score < 0.45:
        learner_state, state_reason = "disengaged", "low_engagement_score"
    elif inactivity_periods >= 3 and task_completion_rate < 0.60:
        learner_state, state_reason = "disengaged", "inactivity_with_low_completion"
    elif engagement_score >= 0.70 and frustration_index < 0.40 and task_completion_rate >= 0.75:
        learner_state, state_reason = "engaged", "high_engagement_low_friction"
    elif engagement_score >= 0.50 and task_completion_rate >= 0.60:
        learner_state, state_reason = "productive_struggle", "sustained_participation_under_challenge"
    else:
        learner_state, state_reason = "disengaged", "insufficient_sustained_participation"

    return dict(
        task_opportunity_count=task_opportunity_count,
        completed_task_count=completed_task_count,
        correct_task_count=correct_task_count,
        total_attempt_count=total_attempt_count,
        accuracy_rate=accuracy_rate,
        avg_attempts_per_task=avg_attempts_per_task,
        task_completion_rate=task_completion_rate,
        inactivity_periods=inactivity_periods,
        inactive_time_sec=inactive_time_sec,
        session_duration_sec=session_duration_sec,
        time_in_target_band_sec=time_in_target_band_sec,
        consecutive_error_max=consecutive_error_max,
        difficulty_floor_hits=difficulty_floor_hits,
        quit_after_error=quit_after_error,
        safety_override_count=safety_override_count,
        c_mean_game_task_latency_sec=c_mean_game_task_latency_sec,
        c_median_game_task_latency_sec=c_median_game_task_latency_sec,
        current_difficulty_level=current_difficulty_level,
        difficulty_trend=difficulty_trend,
        session_technical_issue_flag=session_technical_issue_flag,
        telemetry_quality_status=telemetry_quality_status,
        engagement_score=engagement_score,
        frustration_index=frustration_index,
        learner_state=learner_state,
        state_reason=state_reason,
        engagement_components=dict(
            completion_component=completion_component,
            activity_component=activity_component,
            target_band_component=target_band_component,
            accuracy_component=accuracy_component,
        ),
        frustration_components=dict(
            error_run_component=error_run_component,
            excess_attempt_component=excess_attempt_component,
            inactivity_burden_component=inactivity_burden_component,
            floor_hit_component=floor_hit_component,
            quit_after_error_component=quit_after_error_component,
            safety_override_component=safety_override_component,
        ),
    )


def _domain_aggregate(fx: dict) -> DomainSessionAggregate:
    return DomainSessionAggregate(
        task_opportunity_count=fx["task_opportunity_count"],
        completed_task_count=fx["completed_task_count"],
        correct_task_count=fx["correct_task_count"],
        total_attempt_count=fx["total_attempt_count"],
        accuracy_rate=fx["accuracy_rate"],
        avg_attempts_per_task=fx["avg_attempts_per_task"],
        task_completion_rate=fx["task_completion_rate"],
        inactivity_periods=fx["inactivity_periods"],
        inactive_time_sec=fx["inactive_time_sec"],
        inactive_time_available=True,
        session_duration_sec=fx["session_duration_sec"],
        time_in_target_band_sec=fx["time_in_target_band_sec"],
        consecutive_error_max=fx["consecutive_error_max"],
        difficulty_floor_hits=fx["difficulty_floor_hits"],
        quit_after_error=fx["quit_after_error"],
        safety_override_count=fx["safety_override_count"],
        c_mean_game_task_latency_sec=fx["c_mean_game_task_latency_sec"],
        c_median_game_task_latency_sec=fx["c_median_game_task_latency_sec"],
        current_difficulty_level=fx["current_difficulty_level"],
        difficulty_trend=fx["difficulty_trend"],
        session_technical_issue_flag=fx["session_technical_issue_flag"],
    )


def _domain_provenance() -> DomainCToComponent3Provenance:
    return DomainCToComponent3Provenance(
        c_session_number=2,
        policy_version="c5.1-rule-based-v1",
        production_timestamp=datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
    )


def _payload_dict_for_direct_validation(fx: dict) -> dict:
    """The same fixture values, shaped as a flat dict for a DIRECT ``validate_payload(...,
    "c_to_3")`` call -- used only where the adapter's strongly-typed call chain cannot carry what
    the test needs to demonstrate (see the prohibited-field tests' docstrings)."""
    return dict(
        schema_version="3.0",
        student_id=STUDENT_ID,
        intervention_session_id=INTERVENTION_SESSION_ID,
        intervention_session_number=INTERVENTION_SESSION_NUMBER,
        intervention_session_date=INTERVENTION_SESSION_DATE,
        c_session_id=C_SESSION_ID,
        c_session_number=2,
        component_source="C",
        production_timestamp=datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
        policy_version="c5.1-rule-based-v1",
        composite_formula_version="C-COMP-v1",
        state_rule_version="C-LS-v1",
        telemetry_quality_status=fx["telemetry_quality_status"],
        session_technical_issue_flag=fx["session_technical_issue_flag"],
        task_opportunity_count=fx["task_opportunity_count"],
        completed_task_count=fx["completed_task_count"],
        correct_task_count=fx["correct_task_count"],
        total_attempt_count=fx["total_attempt_count"],
        accuracy_rate=fx["accuracy_rate"],
        avg_attempts_per_task=fx["avg_attempts_per_task"],
        task_completion_rate=fx["task_completion_rate"],
        inactivity_periods=fx["inactivity_periods"],
        inactive_time_sec=fx["inactive_time_sec"],
        session_duration_sec=fx["session_duration_sec"],
        time_in_target_band_sec=fx["time_in_target_band_sec"],
        consecutive_error_max=fx["consecutive_error_max"],
        difficulty_floor_hits=fx["difficulty_floor_hits"],
        quit_after_error=fx["quit_after_error"],
        safety_override_count=fx["safety_override_count"],
        c_mean_game_task_latency_sec=fx["c_mean_game_task_latency_sec"],
        c_median_game_task_latency_sec=fx["c_median_game_task_latency_sec"],
        current_difficulty_level=fx["current_difficulty_level"],
        difficulty_trend=fx["difficulty_trend"],
        engagement_components=fx["engagement_components"],
        engagement_score=fx["engagement_score"],
        frustration_components=fx["frustration_components"],
        frustration_index=fx["frustration_index"],
        learner_state=fx["learner_state"],
        state_reason=fx["state_reason"],
    )


# =====================================================================================
# D4 criterion 1 / SF-040 -- the one constructible arm.
# =====================================================================================


def test_emit_c_to_3_raises_no_real_c_session_error_for_the_only_constructible_sf040_fixture():
    """D4 criterion 1 (SF-040): no payload is built when no real C session exists. Per the SF-040
    finding recorded in this module's docstring and in ``NoRealCSessionError``'s own docstring,
    only ``c_present=False, c_session_id=None`` is constructible as a mapping-row fixture; the
    ``c_session_id is None`` disjunct with ``c_present`` true cannot be independently constructed
    (CD-04, ``models/contracts.py:105-106``).

    SIGNAL: fails if the adapter ever stops raising (no exception -> test fails on the missing
    ``pytest.raises``), or if the VENDORED exception type were ever let through unmapped (the
    ``pytest.raises(NoRealCSessionError)`` here names the DOMAIN type from
    ``app.domain.live_engine_c.errors`` -- a leaked vendored type would not satisfy it and the
    test would fail with an unhandled ``component_c_generator...NoRealCSessionError``)."""
    fx = _build_consistent_fixture()
    adapter = LiveEngineCAdapter()
    with pytest.raises(NoRealCSessionError):
        adapter.emit_c_to_3(
            _mapping_row_no_real_c_session(),
            provenance=_domain_provenance(),
            aggregate=_domain_aggregate(fx),
            telemetry_quality_status=fx["telemetry_quality_status"],
            composite_formula_version="C-COMP-v1",
            learner_state=fx["learner_state"],
            state_reason=fx["state_reason"],
            engagement_components=DomainEngagementComponents(**fx["engagement_components"]),
            engagement_score=fx["engagement_score"],
            frustration_components=DomainFrustrationComponents(**fx["frustration_components"]),
            frustration_index=fx["frustration_index"],
        )


# =====================================================================================
# D4 criterion 2 -- the payload validates against the frozen schema.
# =====================================================================================


def test_emit_c_to_3_payload_validates_against_frozen_schema():
    """D4 criterion 2: the payload the adapter returns validates against the frozen
    ``CToComponent3Payload`` schema, including its ``validate_deterministic_invariants``
    re-derivation (C3-DF-06...C3-DF-11, C3-WU-01). Two independent checks:

    1. The adapter call itself succeeds -- ``emit_c_to_3`` (vendored) already re-validates its own
       output via ``validate_payload_against_mapping(..., kind="c_to_3")`` internally
       (``emit.py:84``), so a construction that reached this point already passed the frozen gate
       once.
    2. EVERY field of the domain payload is checked against the fixture's own values (via
       ``dataclasses.fields()``, not a spot check) -- catching a transposed or silently-dropped
       field the adapter's ``_map_c_to_3_payload`` might introduce.
    3. The domain payload is re-shaped back into a flat dict and run through
       ``validate_payload(..., "c_to_3")`` a SECOND, standalone time, independent of the adapter's
       own internal call -- proving the mapping round-trips cleanly through the frozen validator,
       not merely that the adapter's one internal call happened to accept it.

    SIGNAL: fails if any field is dropped, mistyped, or transposed during mapping (assertion 2),
    or if the re-validation step (assertion 3) raises ``ContractValidationError``."""
    from validators.contract_validators import validate_payload as pkg_validate_payload

    fx = _build_consistent_fixture()
    adapter = LiveEngineCAdapter()
    result = adapter.emit_c_to_3(
        _mapping_row_real_c_session(),
        provenance=_domain_provenance(),
        aggregate=_domain_aggregate(fx),
        telemetry_quality_status=fx["telemetry_quality_status"],
        composite_formula_version="C-COMP-v1",
        learner_state=fx["learner_state"],
        state_reason=fx["state_reason"],
        engagement_components=DomainEngagementComponents(**fx["engagement_components"]),
        engagement_score=fx["engagement_score"],
        frustration_components=DomainFrustrationComponents(**fx["frustration_components"]),
        frustration_index=fx["frustration_index"],
    )

    assert isinstance(result, DomainCToComponent3Payload)

    expected = _payload_dict_for_direct_validation(fx)
    result_dict = dataclasses.asdict(result)
    for field in dataclasses.fields(DomainCToComponent3Payload):
        assert field.name in result_dict, f"field dropped during mapping: {field.name}"
        if field.name in expected:
            assert result_dict[field.name] == expected[field.name], (
                f"field mismatch during mapping: {field.name}"
            )
    assert result.student_id == STUDENT_ID
    assert result.c_session_id == C_SESSION_ID
    assert result.intervention_session_id == INTERVENTION_SESSION_ID

    # Standalone, second re-validation -- independent of emit.py:84's own internal call.
    pkg_validate_payload(result_dict, "c_to_3")


# =====================================================================================
# D4 criterion 3 -- strict JSON: no NaN, no Infinity.
# =====================================================================================


def test_emit_c_to_3_payload_json_serialisation_rejects_nan_and_infinity():
    """D4 criterion 3: strict JSON has no NaN, no Infinity -- assert the serialiser REJECTS them
    rather than merely observing that a real payload happens not to contain one (the discipline
    whose absence produced Component B's RT-std defect).

    RULING 3 (supervisor, on the 9b-1 plan): a secondary assertion that pydantic's own
    ``Probability``-typed fields reject NaN at construction time was proposed but could not be
    verified this turn -- no pytest/interpreter run is permitted under the builder contract, and
    an unverified assertion must not ship. Per ruling 3 option 2, that secondary assertion is
    OMITTED. Only the ``json.dumps(..., allow_nan=False)`` assertion below is load-bearing; it was
    reasoned through, not guessed at, and does not depend on where in the stack the rejection
    happens."""
    fx = _build_consistent_fixture()
    valid_payload_dict = _payload_dict_for_direct_validation(fx)

    # Happy path: a real, valid payload's JSON round-trip must succeed under strict serialisation.
    json.dumps(valid_payload_dict, default=str, allow_nan=False)

    nan_payload_dict = dict(valid_payload_dict)
    nan_payload_dict["engagement_score"] = float("nan")
    with pytest.raises(ValueError):
        json.dumps(nan_payload_dict, default=str, allow_nan=False)

    inf_payload_dict = dict(valid_payload_dict)
    inf_payload_dict["frustration_index"] = float("inf")
    with pytest.raises(ValueError):
        json.dumps(inf_payload_dict, default=str, allow_nan=False)


# =====================================================================================
# D4 criterion 4 -- prohibited fields, both families. Also D5's proof that
# validate_payload(payload, "c_to_3") has a real, firing caller.
# =====================================================================================


def test_emit_c_to_3_rejects_b_leakage_prohibited_field():
    """D4 criterion 4 (B-leakage family) AND ruling 2's D5 proof.

    WHY THIS CALLS ``validate_payload`` DIRECTLY, NOT THROUGH THE ADAPTER: the adapter's call
    chain cannot carry an arbitrary extra field into the assembled payload in the first place --
    ``build_c_to_3_payload``'s parameters are fixed and named (none is called
    ``mastery_certified``), and the vendored ``CToComponent3Payload`` is itself
    ``extra="forbid"``. There is no way to inject a prohibited field through that strongly-typed
    path even to attempt a demonstration -- which is a property of the design, not a gap in this
    test. This test therefore calls ``validate_payload(payload, "c_to_3")`` directly, with the
    SAME kind literal ``emit.py:84`` uses internally (via
    ``validate_payload_against_mapping(..., kind="c_to_3")`` ->
    ``contract_validators.py:155``), proving that exact validator+kind combination enforces
    ``C_TO_3_PROHIBITED_FIELDS``. Combined with direct inspection of ``emit.py:58-84`` (verified
    in the 9b-1 plan) showing that combination is exactly what the real call chain invokes, D5's
    'first caller, proven not merely asserted' is closed: if ``validate_payload(payload,
    "c_to_3")`` were ever bypassed inside ``emit_c_to_3``, this field would sail through
    undetected there -- this test is what would catch that regression at the validator level.

    SIGNAL: fails if ``C_TO_3_PROHIBITED_FIELDS`` no longer includes ``mastery_certified``, or if
    ``_reject_prohibited_fields`` were ever skipped for the ``c_to_3`` kind -- either way the
    ``pytest.raises`` would not fire."""
    from validators.contract_validators import (
        ContractValidationError as PkgContractValidationError,
        validate_payload as pkg_validate_payload,
    )

    fx = _build_consistent_fixture()
    payload = _payload_dict_for_direct_validation(fx)
    payload["mastery_certified"] = True  # Component B leakage (SS13.2)

    with pytest.raises(PkgContractValidationError) as excinfo:
        pkg_validate_payload(payload, "c_to_3")
    assert "mastery_certified" in str(excinfo.value)
    assert "c_to_3" in str(excinfo.value)


def test_emit_c_to_3_rejects_generator_only_latent_prohibited_field():
    """D4 criterion 4 (generator-only latent leakage family). Same reasoning and same direct-call
    justification as ``test_emit_c_to_3_rejects_b_leakage_prohibited_field`` above -- see that
    test's docstring. Together the two tests prove the whole ``C_TO_3_PROHIBITED_FIELDS`` set is
    in force across both its families, not just one entry."""
    from validators.contract_validators import (
        ContractValidationError as PkgContractValidationError,
        validate_payload as pkg_validate_payload,
    )

    fx = _build_consistent_fixture()
    payload = _payload_dict_for_direct_validation(fx)
    payload["off_day_indicator"] = 0.1  # generator-only latent leakage (SS13.3)

    with pytest.raises(PkgContractValidationError) as excinfo:
        pkg_validate_payload(payload, "c_to_3")
    assert "off_day_indicator" in str(excinfo.value)
    assert "c_to_3" in str(excinfo.value)


# =====================================================================================
# 9b-1 obligation 4a -- static half only (ruling 4).
# =====================================================================================


def test_adapter_emit_c_to_3_requires_aggregate_as_a_keyword_with_no_default():
    """9b-1 obligation 4a, STATIC HALF ONLY. ``emit_c_to_3`` (vendored,
    ``component_c_generator/c_to_3/emit.py:41``) takes ``aggregate: CSessionAggregate`` as a
    required keyword argument with no default. This test asserts the adapter method mirrors that
    shape exactly, proving the call CANNOT be made without an aggregate in hand.

    THIS DOES NOT CLOSE CONDITION 4. It does not and cannot trace a live aggregation refusal
    (``AggregationInputsUnavailableError``, raised while ``_AGGREGATION_INPUTS_AVAILABLE=False``)
    reaching this call and stopping before it -- that dynamic half needs a real caller of both
    ``derive_and_persist_session_aggregate`` and this method together, which is out of 9b-1's
    scope (§2: fixture-fed only, no live caller). ``tests/test_9c1b_outbox_enqueue.py`` recorded
    the identical limitation one link earlier in the same chain ("It does not and cannot prove `no
    aggregate -> no payload`, because there is no payload constructor to prove that about yet.").
    That payload constructor now exists (this batch), so the STATIC half closes here; the DYNAMIC
    half is inherited forward again, to whichever future batch builds a real caller of both
    functions together."""
    sig = inspect.signature(LiveEngineCAdapter.emit_c_to_3)
    aggregate_param = sig.parameters["aggregate"]
    assert aggregate_param.default is inspect.Parameter.empty
    assert aggregate_param.kind is inspect.Parameter.KEYWORD_ONLY

    type_hints = typing.get_type_hints(LiveEngineCAdapter.emit_c_to_3)
    assert type_hints["aggregate"] is DomainSessionAggregate  # not Optional[...]
