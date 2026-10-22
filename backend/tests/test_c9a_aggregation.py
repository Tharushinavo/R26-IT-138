"""Component C Phase 9a: session aggregation, C-COMP-v1 composites, C-LS-v1 learner state, C-19.
SHIPS UNWIRED, WITH A RUNTIME REFUSAL (P1) -- see aggregation_service.py's own module docstring
for the full ruling this batch builds against.

Covers: P1-b (the refusal fires, and would fail if the constant were flipped); P5-c/N4-a (the
null-not-zero identity asymmetry); P5-d/N4-c (C-19's fixture, call-through proof); P5-e/N5-a (the
prior_session_end_state difference test, its stated limit); P5-f/N4-d (the guarded accessor is the
only path to derivable history, and a gapped session refuses the whole aggregate).
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from app.application.live_engine_c import aggregation_service
from app.application.live_engine_c.aggregation_service import derive_and_persist_session_aggregate
from app.application.live_engine_c.mastery_fixture import (
    FIXTURE_MASTERY_SOURCE_INTERVENTION_SESSION_ID,
    FIXTURE_MASTERY_SOURCE_STUDENT_ID,
)
from app.application.live_engine_c.task_service import _stu_session_id
from app.domain.live_engine_c.errors import AggregationInputsUnavailableError, DistrustedHistoryGapError
from app.domain.live_engine_c.types import (
    AdaptationDecision,
    AggregationConfig,
    GameplayEvent,
    SeedLineage,
    TaskOpportunitySummary,
)
from app.infrastructure.live_engine_c.adapter import LiveEngineCAdapter
from app.infrastructure.persistence_models import (
    CGameplayEventRecord,
    CSessionAggregateResultRecord,
)
from app.infrastructure.repositories import CGameplayEventRecordRepository, CLearnerLocalStateRepository
from tests.test_c4_session_lifecycle import isolated_database, provenance, safety_config_fixture_for_tests
from tests.test_c5_task_serve_and_evaluate import _create_real_instance_via_smoke_mode, alembic
from tests.test_c6b_policy_and_safety import _baseline_evidence, policy_config_fixture_for_tests
from tests.test_c4_session_lifecycle import selection_config_fixture_for_tests


def _seed_lineage() -> SeedLineage:
    return SeedLineage(global_seed=1, path=(), seed=1)


def _event(event_type: str, task_index: int, event_index: int, ts: int, **overrides: object) -> GameplayEvent:
    base = dict(
        event_id=f"e{event_index}",
        event_type=event_type,
        event_index=event_index,
        student_id=FIXTURE_MASTERY_SOURCE_STUDENT_ID,
        intervention_session_id=FIXTURE_MASTERY_SOURCE_INTERVENTION_SESSION_ID,
        c_session_id="STU-0001-C-001",
        game_task_instance_id=f"STU-0001-C-001-T{task_index:03d}-X001",
        task_index=task_index,
        attempt_number=None,
        event_timestamp_relative_ms=ts,
        action_payload=None,
        evaluation_payload=None,
        scaffold_code=None,
        technical_flag=False,
        terminal_reason=None,
        seed_lineage=_seed_lineage(),
        generator_version="test-gen-1",
        config_checksum="fixture-checksum",
    )
    base.update(overrides)
    return GameplayEvent(**base)


def _summary(task_index: int, *, task_completed: bool, correct_task: bool | None, **overrides: object) -> TaskOpportunitySummary:
    base = dict(
        student_id=FIXTURE_MASTERY_SOURCE_STUDENT_ID,
        intervention_session_id=FIXTURE_MASTERY_SOURCE_INTERVENTION_SESSION_ID,
        c_session_id="STU-0001-C-001",
        game_task_instance_id=f"STU-0001-C-001-T{task_index:03d}-X001",
        task_index=task_index,
        task_offered=True,
        task_started=True,
        task_completed=task_completed,
        task_skipped=False,
        task_quit=False,
        technical_issue=False,
        correct_task=correct_task,
        total_attempts=1,
        retry_count=0,
        scaffold_requested=False,
        scaffold_count=0,
        highest_scaffold_level=None,
        c_answer_changes=0,
        task_latency_sec=1.0,
        inactive_time_sec=0.0,
        inactivity_periods=0,
        quit_after_error=False,
        terminal_reason="completed_correct" if task_completed else None,
        first_attempt_correct=correct_task,
        final_attempt_correct=correct_task,
        consecutive_error_max_within_task=0,
    )
    base.update(overrides)
    return TaskOpportunitySummary(**base)


def _adaptation_decision(*, difficulty_before: int, difficulty_after: int, selected_action: str, applied_action: str) -> AdaptationDecision:
    return AdaptationDecision(
        decision_id="AD-1",
        policy_mode="rule_based_baseline",
        policy_version="test-policy-1.0.0",
        rl_state=None,
        selected_action=selected_action,
        applied_action=applied_action,
        action_overridden=applied_action != selected_action,
        safety_reason=None,
        difficulty_before=difficulty_before,
        difficulty_after=difficulty_after,
        rolling_strain_bucket="low",
        session_start_state_bucket=None,
        increase_block_remaining=0,
        internal_reward=None,
        seed_lineage=_seed_lineage(),
    )


def _aggregation_config() -> AggregationConfig:
    return AggregationConfig(
        config_version="c5.0-aggregation-1.0.0",
        parameter_source_status="TEST_FIXTURE_ONLY",
        min_completed_tasks_for_difficulty_trend=3,
    )


# =====================================================================================
# P5-c / N4-a -- the identity asymmetry: accuracy_rate/avg_attempts_per_task are NULL when
# completed_task_count=0; task_completion_rate is 0.0 (via task_opportunity_count=0), never
# null. A test that would FAIL if a zero were ever substituted for either null.
# =====================================================================================


def test_identities_null_not_zero_on_a_zero_denominator() -> None:
    """SPEC §18/C->3 §4.3 FROZEN identities, transcribed not re-derived (M2-c). With an empty
    summary list (task_opportunity_count=0, so completed_task_count=0 too), accuracy_rate and
    avg_attempts_per_task must be None -- NEVER 0.0 -- while task_completion_rate is genuinely
    0.0 (the explicit task_opportunity_count=0 export rule, a DIFFERENT identity, a DIFFERENT
    zero-denominator case). This is the discipline whose absence produced Component B's RT-std
    defect (F1/B-2): 'is None' fails immediately if the derivation ever substitutes a fabricated
    zero for a genuine null."""
    adapter = LiveEngineCAdapter()
    events = [
        _event("game_task_offered", 1, 1, 0),
        _event("game_task_started", 1, 2, 100),
    ]
    aggregate = adapter.derive_session_aggregate(
        events,
        [],  # no summaries at all -- task_opportunity_count=0
        [],
        time_in_target_band_sec=0.0,
        safety_override_count=0,
        inactive_time_available=True,
        config=_aggregation_config(),
    )
    assert aggregate.accuracy_rate is None
    assert aggregate.avg_attempts_per_task is None
    assert aggregate.task_completion_rate == 0.0
    assert aggregate.task_opportunity_count == 0
    assert aggregate.completed_task_count == 0


# =====================================================================================
# P5-d / N4-c -- C-19: a CALL-THROUGH PROOF (M4-b), not new counting logic. v3.0: "Floor-hit
# counting must not treat a cold-start session pinned at level 1 by a baseline cap as repeated
# floor hits... Acceptance criterion: a familiarization-session fixture asserts
# difficulty_floor_hits is NOT maxed."
# =====================================================================================


def test_c19_familiarization_baseline_cap_hold_is_not_a_floor_hit() -> None:
    """CONSEQUENCE STATED, not a bare assertion (v3.0's own framing): if a familiarization
    session pinned at difficulty level 1 by the SELECTION LAYER's own baseline cap (never a
    strain-driven decrease) were counted as repeated floor hits, difficulty_floor_hits would feed
    frustration_index (weight 0.15, C-COMP-v1) and C-LS-v1 rule 5
    ('difficulty_floor_hits>=2 AND task_completion_rate<0.60 -> overloaded'), MISLABELLING A
    FIRST-SESSION CHILD AS OVERLOADED for no reason but where the session started them. The
    pinned aggregation/derive.py already excludes this case (FIX 2, C5.0 revision --
    verified this batch, not re-derived): a difficulty_after==1 decision counts as a floor hit
    ONLY if a decrease was also proposed or applied; a baseline hold at level 1 with neither does
    not. Three decisions here all HOLD at level 1 -- zero strain, zero decreases -- and
    difficulty_floor_hits must be 0."""
    adapter = LiveEngineCAdapter()
    events = [_event("game_task_offered", i, i, (i - 1) * 100) for i in range(1, 4)]
    decisions = [
        _adaptation_decision(difficulty_before=1, difficulty_after=1, selected_action="hold", applied_action="hold")
        for _ in range(3)
    ]
    summaries = [_summary(i, task_completed=True, correct_task=True) for i in range(1, 4)]
    aggregate = adapter.derive_session_aggregate(
        events,
        summaries,
        decisions,
        time_in_target_band_sec=0.0,
        safety_override_count=0,
        inactive_time_available=True,
        config=_aggregation_config(),
    )
    assert aggregate.difficulty_floor_hits == 0, (
        "a baseline-cap hold at level 1 must never be counted as a floor hit, or a first-session "
        "child gets mislabelled overloaded (v3.0's own stated consequence)"
    )


# =====================================================================================
# P5-e / N5-a -- the difference test. F-2's condition 4: a value that travels and changes
# nothing is the defect a prior batch was cancelled over.
# =====================================================================================


def test_prior_session_end_state_overloaded_produces_a_different_difficulty_outcome() -> None:
    """M3-b, designed before any C-17 Item B closure was ever recorded (P4: none was, on either
    half). Two evidence fixtures, differing ONLY in prior_session_end_state, at
    current_difficulty_level=3 with an increase proposed (target=4): with prior_session_end_state
    unset, nothing caps the ceiling below the max (5), so difficulty_after=4. With
    prior_session_end_state="overloaded", safety_config.prior_overloaded_disengaged_cap=2 caps the
    ceiling, so difficulty_after=2 -- STRICTLY LESS than the uncapped case. session_mode="combined"/
    session_phase="mastery_driven" deliberately avoid the OTHER two ceiling caps (familiarization,
    c_only fallback) so this isolates prior_state_cap specifically.

    STATED LIMIT (recorded, not glossed over): this test constructs evidence directly and calls
    apply_safety/decide_adaptation through the adapter -- it proves the DOWNSTREAM CONSEQUENCE is
    genuine (the pinned safety controller really does consult prior_session_end_state and really
    does change its output), not that any write path is wired. It would pass identically whether
    or not aggregation_service ever wrote a real prior_session_end_state anywhere -- the write
    path (aggregation_service.derive_and_persist_session_aggregate's own upsert) needs, and has,
    its own separate proof (test_refusal_fires_and_a_flipped_constant_reaches_real_persistence,
    below)."""
    adapter = LiveEngineCAdapter()
    safety_config = safety_config_fixture_for_tests()
    policy_config = policy_config_fixture_for_tests()
    selection_config = selection_config_fixture_for_tests()
    common = dict(
        session_mode="combined", session_phase="mastery_driven", current_difficulty_level=3,
        recent_correctness_rate=0.95, recent_avg_attempts=1.0, recent_inactivity_periods=0,
        recent_scaffold_use_count=0, recent_consecutive_error_max=0, rolling_strain_score=0.05,
        is_recovery_context=False, technical_issue_current_task=False, safety_increase_block_remaining=0,
    )
    evidence_unset = _baseline_evidence(**common, prior_session_end_state=None)
    evidence_overloaded = _baseline_evidence(**common, prior_session_end_state="overloaded")

    decision_unset = adapter.decide_adaptation(
        policy_mode="rule_based_baseline", evidence=evidence_unset, current_difficulty_level=3,
        seed_lineage=_seed_lineage(), policy_config=policy_config, safety_config=safety_config,
        selection_config=selection_config,
    )
    decision_overloaded = adapter.decide_adaptation(
        policy_mode="rule_based_baseline", evidence=evidence_overloaded, current_difficulty_level=3,
        seed_lineage=_seed_lineage(), policy_config=policy_config, safety_config=safety_config,
        selection_config=selection_config,
    )
    assert decision_unset.selected_action == "increase_difficulty"
    assert decision_unset.difficulty_after == 4
    assert decision_overloaded.difficulty_after == 2
    assert decision_overloaded.difficulty_after != decision_unset.difficulty_after
    assert "prior_state_cap" in (decision_overloaded.safety_reason or "")


# =====================================================================================
# P1-b / P5-f -- the refusal fires unconditionally (regardless of what a caller passes), and
# flipping the module constant is the ONLY way past it -- proof it is load-bearing, not vacuous.
# =====================================================================================


def test_refusal_fires_even_with_real_looking_scalars_supplied() -> None:
    """P1-a: a caller passing real numbers for time_in_target_band_sec/safety_override_count
    must NOT quietly satisfy the refusal -- only editing _AGGREGATION_INPUTS_AVAILABLE does."""
    alembic("upgrade", "head")
    assert aggregation_service._AGGREGATION_INPUTS_AVAILABLE is False

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            _, c_session_id, _instance_id, _subject = await _create_real_instance_via_smoke_mode(session)
            with pytest.raises(AggregationInputsUnavailableError):
                await derive_and_persist_session_aggregate(
                    session,
                    adapter=LiveEngineCAdapter(),
                    c_session_id=c_session_id,
                    student_id=uuid4(),
                    mastery_source_student_id=FIXTURE_MASTERY_SOURCE_STUDENT_ID,
                    mastery_source_intervention_session_id=FIXTURE_MASTERY_SOURCE_INTERVENTION_SESSION_ID,
                    stu_session_id=_stu_session_id(),
                    time_in_target_band_sec=120.5,  # a real-looking number -- must not satisfy the refusal
                    safety_override_count=0,
                    inactive_time_available=True,
                    config=_aggregation_config(),
                    formula_version="C-COMP-v1",
                    request_id=f"req-{uuid4()}",
                )
            # No partial write of any kind on refusal.
            result = await session.execute(
                CSessionAggregateResultRecord.__table__.select().where(
                    CSessionAggregateResultRecord.c_session_id == c_session_id
                )
            )
            assert result.first() is None
        await database_engine.dispose()

    asyncio.run(exercise())


def test_refusal_fires_and_a_flipped_constant_reaches_real_persistence(monkeypatch: pytest.MonkeyPatch) -> None:
    """P1-b, second half: proves the constant is genuinely load-bearing, not dead code -- flip
    ONLY the module constant (monkeypatch, the same mechanism already established for _SMOKE_MODE/
    _BUNDLE_PATH elsewhere in this register; test-side construction, P1-c), supply real fixture
    scalars, and confirm the function THEN proceeds past the refusal and persists a real
    CSessionAggregateResultRecord AND upserts CLearnerLocalStateRecord.prior_session_end_state
    (C-17 Item B's own producer half, P4 -- proven here to be a real, correct mechanism, never
    claimed to close the consumer-side guarantee)."""
    alembic("upgrade", "head")
    monkeypatch.setattr(aggregation_service, "_AGGREGATION_INPUTS_AVAILABLE", True)

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            student_id, c_session_id, instance_id, _subject = await _create_real_instance_via_smoke_mode(session)
            # A minimal real terminal event so get_derivable_history_for_session finds no gap and
            # summary derivation (already Phase-8-validated) has something to work with.
            event_repo = CGameplayEventRecordRepository(session)
            started_id = uuid4()
            session.add(
                CGameplayEventRecord(
                    c_gameplay_event_id=started_id,
                    c_session_id=c_session_id,
                    game_task_instance_id=instance_id,
                    task_index=1,
                    event_type="game_task_started",
                    event_index=2,
                    attempt_number=None,
                    event_timestamp_relative_ms=0,
                    action_payload=None,
                    evaluation_payload=None,
                    scaffold_code=None,
                    technical_flag=False,
                    terminal_reason=None,
                    seed_lineage_global_seed=1,
                    seed_lineage_path=[],
                    seed_lineage_seed=1,
                    generator_version="test-gen-1",
                    config_checksum="fixture-checksum",
                    **provenance("c_gameplay_event", started_id),
                )
            )
            submitted_id = uuid4()
            session.add(
                CGameplayEventRecord(
                    c_gameplay_event_id=submitted_id,
                    c_session_id=c_session_id,
                    game_task_instance_id=instance_id,
                    task_index=1,
                    event_type="answer_submitted",
                    event_index=3,
                    attempt_number=1,
                    event_timestamp_relative_ms=500,
                    action_payload={"submitted_total": 3},
                    evaluation_payload=None,
                    scaffold_code=None,
                    technical_flag=False,
                    terminal_reason=None,
                    seed_lineage_global_seed=1,
                    seed_lineage_path=[],
                    seed_lineage_seed=1,
                    generator_version="test-gen-1",
                    config_checksum="fixture-checksum",
                    **provenance("c_gameplay_event", submitted_id),
                )
            )
            evaluated_id = uuid4()
            session.add(
                CGameplayEventRecord(
                    c_gameplay_event_id=evaluated_id,
                    c_session_id=c_session_id,
                    game_task_instance_id=instance_id,
                    task_index=1,
                    event_type="answer_evaluated",
                    event_index=4,
                    attempt_number=1,
                    event_timestamp_relative_ms=600,
                    action_payload=None,
                    evaluation_payload={"is_correct": True},
                    scaffold_code=None,
                    technical_flag=False,
                    terminal_reason=None,
                    seed_lineage_global_seed=1,
                    seed_lineage_path=[],
                    seed_lineage_seed=1,
                    generator_version="test-gen-1",
                    config_checksum="fixture-checksum",
                    **provenance("c_gameplay_event", evaluated_id),
                )
            )
            terminal_id = uuid4()
            session.add(
                CGameplayEventRecord(
                    c_gameplay_event_id=terminal_id,
                    c_session_id=c_session_id,
                    game_task_instance_id=instance_id,
                    task_index=1,
                    event_type="game_task_completed",
                    event_index=5,
                    attempt_number=None,
                    event_timestamp_relative_ms=1000,
                    action_payload=None,
                    evaluation_payload=None,
                    scaffold_code=None,
                    technical_flag=False,
                    terminal_reason="completed_correct",
                    seed_lineage_global_seed=1,
                    seed_lineage_path=[],
                    seed_lineage_seed=1,
                    generator_version="test-gen-1",
                    config_checksum="fixture-checksum",
                    **provenance("c_gameplay_event", terminal_id),
                )
            )
            await session.flush()
            from app.application.live_engine_c.summary_service import derive_and_persist_summary

            await derive_and_persist_summary(
                session,
                adapter=LiveEngineCAdapter(),
                c_session_id=c_session_id,
                c_task_instance_id=instance_id,
                student_id=FIXTURE_MASTERY_SOURCE_STUDENT_ID,
                stu_session_id=_stu_session_id(),
                game_task_instance_id=f"{_stu_session_id()}-T001-X001",
                request_id=f"req-{uuid4()}",
            )

            record = await derive_and_persist_session_aggregate(
                session,
                adapter=LiveEngineCAdapter(),
                c_session_id=c_session_id,
                student_id=student_id,
                mastery_source_student_id=FIXTURE_MASTERY_SOURCE_STUDENT_ID,
                mastery_source_intervention_session_id=FIXTURE_MASTERY_SOURCE_INTERVENTION_SESSION_ID,
                stu_session_id=_stu_session_id(),
                time_in_target_band_sec=0.0,
                safety_override_count=0,
                inactive_time_available=True,
                config=_aggregation_config(),
                formula_version="C-COMP-v1",
                request_id=f"req-{uuid4()}",
            )
            assert record.c_session_id == c_session_id
            assert record.learner_state is not None or record.telemetry_quality_status is not None

            local_state = await CLearnerLocalStateRepository(session).find_by_student(student_id)
            assert local_state is not None
            assert local_state.prior_session_end_state == record.learner_state
        await database_engine.dispose()

    asyncio.run(exercise())


# =====================================================================================
# P5-f / N4-d -- 9a is the first REAL consumer of the Phase 8 accessor. A gapped session
# refuses the WHOLE aggregate -- no partial aggregate row, no partial learner-state write.
# =====================================================================================


def test_gapped_session_does_not_aggregate_at_all(monkeypatch: pytest.MonkeyPatch) -> None:
    """P5-f: with _AGGREGATION_INPUTS_AVAILABLE monkeypatched True (isolating the gap-refusal
    behaviour from the inputs-refusal, Z2-d-style), a session containing a task that reached a
    terminal event but was never derived (Phase 8's own validator refused it -- simulated here by
    persisting a terminal event with no corresponding summary) makes
    derive_and_persist_session_aggregate raise DistrustedHistoryGapError, propagated from the
    guarded accessor -- and confirms NEITHER a CSessionAggregateResultRecord NOR a
    CLearnerLocalStateRecord write occurs. This refuses the protected activity (an aggregate/
    learner-state judgment about an untrustworthy session); Phase 8's own validator already ran
    and is why the gap exists -- refusing here is not refusing the protection."""
    alembic("upgrade", "head")
    monkeypatch.setattr(aggregation_service, "_AGGREGATION_INPUTS_AVAILABLE", True)

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            student_id, c_session_id, instance_id, _subject = await _create_real_instance_via_smoke_mode(session)
            terminal_id = uuid4()
            session.add(
                CGameplayEventRecord(
                    c_gameplay_event_id=terminal_id,
                    c_session_id=c_session_id,
                    game_task_instance_id=instance_id,
                    task_index=1,
                    event_type="game_task_quit",
                    event_index=2,
                    attempt_number=None,
                    event_timestamp_relative_ms=100,
                    action_payload=None,
                    evaluation_payload=None,
                    scaffold_code=None,
                    technical_flag=False,
                    terminal_reason="quit_without_recent_error",
                    seed_lineage_global_seed=1,
                    seed_lineage_path=[],
                    seed_lineage_seed=1,
                    generator_version="test-gen-1",
                    config_checksum="fixture-checksum",
                    **provenance("c_gameplay_event", terminal_id),
                )
            )
            await session.flush()
            # No summary derived for this instance -- terminal reached, but distrusted/absent.

            with pytest.raises(DistrustedHistoryGapError):
                await derive_and_persist_session_aggregate(
                    session,
                    adapter=LiveEngineCAdapter(),
                    c_session_id=c_session_id,
                    student_id=student_id,
                    mastery_source_student_id=FIXTURE_MASTERY_SOURCE_STUDENT_ID,
                    mastery_source_intervention_session_id=FIXTURE_MASTERY_SOURCE_INTERVENTION_SESSION_ID,
                    stu_session_id=_stu_session_id(),
                    time_in_target_band_sec=0.0,
                    safety_override_count=0,
                    inactive_time_available=True,
                    config=_aggregation_config(),
                    formula_version="C-COMP-v1",
                    request_id=f"req-{uuid4()}",
                )

            result = await session.execute(
                CSessionAggregateResultRecord.__table__.select().where(
                    CSessionAggregateResultRecord.c_session_id == c_session_id
                )
            )
            assert result.first() is None
            local_state = await CLearnerLocalStateRepository(session).find_by_student(student_id)
            assert local_state is None
        await database_engine.dispose()

    asyncio.run(exercise())
