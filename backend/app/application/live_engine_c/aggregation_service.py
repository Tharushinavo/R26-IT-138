"""Component C Phase 9a: session aggregation, C-COMP-v1 composites, C-LS-v1 learner state (v3.0
§11 Phase 9's AGGREGATION half only -- never emit_c_to_3, never the outbox, never the wheel
rebuild; those are 9b/9c, later batches, not this one).

CITATION RULE (owner ruling, extending the filename-approval rule): "an approval citation must
name WHOSE approval and IN WHAT FORUM." The pinned ``aggregation/derive.py``'s own "Supervisor
confirmed (Phase C5.0 revision)" (``derive.py:9``, `:15-16`, `:21`, `:30`) refers to the
GENERATOR's own upstream supervisor, in the generator's own development process -- accurate at
that source, and misleading at THIS destination, where an unqualified "Supervisor confirmed" reads
as an approval given in this repository. Same defect shape as a filename asserting what its body
denies. FLAGGED here, not edited -- the pinned module is READ-ONLY. No other instance of this
citation shape was found in that module (searched: "supervisor", case-insensitive, whole file);
not hunted beyond it, per this batch's own scope.

P1 -- SHIP UNWIRED, BUT REFUSE AT RUNTIME (owner ruling, quoted in full because it is the
condition this module exists to satisfy, not a nicety): "AGGREGATION MUST REFUSE AT RUNTIME WHEN
ITS INPUTS ARE UNAVAILABLE, not merely be documented as unwired... This is the fifth mechanism
shipped complete and inert, and the register has not stopped any of the previous four from being
read as complete. A sixth register line will not either. What stops it is code that refuses."

Why this is NOT the sixth-parameter-family argument again (owner, quoted, because the two shapes
look alike): "those five families all gate the same event and are all blocked by the same thing --
governance signing -- so a sixth added nothing. These three inputs are blocked by something else
entirely, and they unblock, if ever, on a different event. When the parameter gates lift,
aggregation becomes reachable with these inputs still missing." The session-start gate (this
module's own AggregationConfig family, wired in ``session_lifecycle.create_session``) governs
whether a SESSION may be created at all; it says nothing about whether, once created, a real
``time_in_target_band_sec``/``safety_override_count`` exist for THIS function to consume. Hence a
second, independent refusal, load-bearing on its own.

P1-a -- THE REFUSAL CANNOT BE QUIETLY SATISFIED (owner: "if one is ever added, the refusal must be
deliberately removed rather than quietly satisfied... A check of the form 'raise if the value is
None' is satisfied the moment any caller passes a number, which is precisely the quiet path.").
``_AGGREGATION_INPUTS_AVAILABLE`` below is a MODULE-LEVEL CONSTANT, mirroring
``c_session_service.py:80``'s ``_SMOKE_MODE`` shape exactly -- never a parameter on this function
(a caller-supplied override flag would BE the quiet-satisfaction path this exists to resist).
Production ships this ``False`` unconditionally; someone adding a real source for either scalar
must edit THIS LINE, deliberately, not merely pass a number through the function's own signature.
Tests exercise the ``True`` branch via direct monkeypatch of this module attribute (the same
mechanism already established for ``_SMOKE_MODE``/``_BUNDLE_PATH`` elsewhere in this register),
never via a parameter.

P2 -- NO PROBES (owner, quoted, in these words, because the distinction is different in kind, not
degree, from the Generation-config precedent): "the generation-config probe is safe because its
own gate refuses it unconditionally before use; these two scalars have no gate, so an invented
value flows straight into frozen composites." No probe is built here for either scalar. The
function's own signature requires real values as REQUIRED, no-default parameters (mirroring the
pinned ``derive_session_aggregate``'s own shape exactly) -- it is the module constant above, not a
default or a probe, that keeps this unreachable until a real source exists.

P3 -- THE LOOP-LEVEL REGISTER ENTRY (R0 applied to a consequence, not only a mechanism): three
required inputs have no source in this backend's own plan, and this is not a fact about ONE
batch. Traced forward: aggregation cannot produce real composites -> 9b's C->3 payload has an
aggregate half that cannot be built from real data -> 9c delivers a payload that was never real.
Component 3 receives no genuine C payload until C6 and C7 -- the GENERATOR's own later phases,
with NO OWNER anywhere in this backend's plan -- exist.
  - ``time_in_target_band_sec`` -- no C7 phase exists in this backend, no pilot profile, no
    target-band telemetry anywhere in the schema (verified: neither ``c_gameplay_events`` nor
    ``c_task_opportunity_summaries`` carries any target-band/challenge-fit column).
  - ``safety_override_count`` -- no C6 accumulation exists anywhere in this backend's plan.
  - ``adaptation_decisions`` -- required by ``derive_session_aggregate``'s own signature, sourced
    from ``c_policy_decisions`` via ``CPolicyDecisionRecordRepository.list_chronological_for_session``
    (below) -- which nothing under ``app/`` writes live (the register-reconciliation batch's own
    finding, unchanged). This one DEGRADES GRACEFULLY rather than blocking: the pinned function
    tolerates an empty decision list (``difficulty_trend`` falls back to ``"stable"``,
    ``current_difficulty_level`` to 1) -- an honest "no decisions occurred," not a fabrication --
    so it is named here for completeness but does not itself need a runtime refusal the way the
    two scalars above do.
  - ``inactive_time_available`` -- DERIVABLE, not a fourth caller-supplied input: it is a plain
    boolean the caller can set from whether ANY derivable summary in the session's own history
    carries real (non-placeholder) inactive-time telemetry, which this codebase always has (Phase
    6a's own derivation always computes a real ``inactive_time_sec``, never a placeholder) --
    unlike the two scalars above, nothing blocks this one.

Severity, in the owner's own terms, recorded against the exclusion-reason register entry (Phase 8,
K3) so the two are comparable: "a missing value is a hole in the dataset; a composite computed
from invented inputs is a present-but-fictional value delivered to a risk model. The second is
worse, and it is what happens if anyone ever satisfies these inputs the easy way." This module's
own refusal exists to make the easy way structurally unavailable, not merely inadvisable.

P4 -- C-17 ITEM B, WITHDRAWN, both stopping points (SUPERVISOR CORRECTION of the prior planning
turn's own partial-closure finding, which stopped at the consumer and did not trace the
producer's own inputs): C-17 Item B closes on NEITHER half. The consumer
(``decide_and_persist_adaptation``) has no live caller -- unchanged from the register-
reconciliation batch. The PRODUCER (this module) cannot run on real data either -- it refuses,
by design, on every real invocation, because ``time_in_target_band_sec``/``safety_override_count``
have no source. Recording partial closure on "the mechanism is real" when the mechanism itself
cannot execute on anything but a fixture would overstate this batch's own result -- withdrawn.

N3's WIRING (into ``session_lifecycle.complete_session``, replacing the hardcoded
``prior_session_end_state=None``) IS OUT OF SCOPE, BLOCKED on the same three inputs -- this module
ships complete and correct, callable directly with real values once they exist, but nothing under
``app/`` calls it yet. ``prior_session_end_state`` stays exactly as it is (hardcoded ``None`` at
``session_lifecycle.py:347``), untouched this batch.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.live_engine_c.adaptation_service import _to_domain_summary
from app.application.live_engine_c.session_lifecycle import _provenance
from app.application.live_engine_c.summary_service import _to_domain_gameplay_event
from app.application.live_engine_c.telemetry_validation import get_derivable_history_for_session
from app.domain.live_engine_c.errors import AggregationInputsUnavailableError
from app.domain.live_engine_c.types import (
    AggregationConfig,
    AdaptationDecision,
    CompositeFormulaVersion,
    SeedLineage,
)
from app.infrastructure.live_engine_c.adapter import LiveEngineCAdapter
from app.infrastructure.persistence_models import CLearnerLocalStateRecord, CPolicyDecisionRecord, CSessionAggregateResultRecord
from app.infrastructure.repositories import (
    CGameplayEventRecordRepository,
    CLearnerLocalStateRepository,
    CPolicyDecisionRecordRepository,
)

# P1-a: mirrors c_session_service.py:80's _SMOKE_MODE constant shape exactly. Production ships
# this False, unconditionally, regardless of what any caller passes for time_in_target_band_sec /
# safety_override_count -- flipping it is the ONLY way this function ever proceeds past the
# refusal, and flipping it requires editing this line, not passing a parameter.
_AGGREGATION_INPUTS_AVAILABLE = False


def _to_domain_adaptation_decision(record: CPolicyDecisionRecord) -> AdaptationDecision:
    """Reconstructs the domain ``AdaptationDecision`` from one persisted ``c_policy_decisions``
    row -- the reverse of ``adaptation_service.decide_and_persist_adaptation``'s own
    ``record = CPolicyDecisionRecord(...)`` construction, every field a straight copy."""
    return AdaptationDecision(
        decision_id=str(record.c_policy_decision_id),
        policy_mode=record.policy_mode,  # type: ignore[arg-type]
        policy_version=record.policy_version,
        rl_state=record.rl_state,
        selected_action=record.selected_action,  # type: ignore[arg-type]
        applied_action=record.applied_action,  # type: ignore[arg-type]
        action_overridden=record.action_overridden,
        safety_reason=record.safety_reason,
        difficulty_before=record.difficulty_before,
        difficulty_after=record.difficulty_after,
        rolling_strain_bucket=record.rolling_strain_bucket,  # type: ignore[arg-type]
        session_start_state_bucket=record.session_start_state_bucket,  # type: ignore[arg-type]
        increase_block_remaining=record.increase_block_remaining,
        internal_reward=record.internal_reward,
        seed_lineage=SeedLineage(
            global_seed=record.seed_lineage_global_seed,
            path=tuple(tuple(pair) for pair in record.seed_lineage_path),
            seed=record.seed_lineage_seed,
        ),
    )


async def derive_and_persist_session_aggregate(
    session: AsyncSession,
    *,
    adapter: LiveEngineCAdapter,
    c_session_id: UUID,
    student_id: UUID,
    mastery_source_student_id: str,
    mastery_source_intervention_session_id: str,
    stu_session_id: str,
    time_in_target_band_sec: float,
    safety_override_count: int,
    inactive_time_available: bool,
    config: AggregationConfig,
    formula_version: CompositeFormulaVersion,
    request_id: str,
) -> CSessionAggregateResultRecord:
    """P1: refuses unconditionally while ``_AGGREGATION_INPUTS_AVAILABLE`` is ``False`` --
    REGARDLESS of what ``time_in_target_band_sec``/``safety_override_count`` a caller supplies
    (P1-a). Only past that gate does it call ``telemetry_validation.get_derivable_history_for_session``
    (P5-f: the ONLY code under app/ this module is allowed to reach ``c_task_opportunity_summaries``
    through, per the Phase 8 AST guard) -- which itself raises ``DistrustedHistoryGapError`` for a
    gapped session, refusing the WHOLE aggregate rather than computing over a hole (P5-f: no
    partial aggregate row, no partial learner-state write, ever, for a gapped session)."""
    if not _AGGREGATION_INPUTS_AVAILABLE:
        raise AggregationInputsUnavailableError(
            "time_in_target_band_sec/safety_override_count have no real source in this backend's "
            "own plan (see this module's own docstring, P3) -- refusing rather than computing "
            "over an invented value"
        )

    summaries = await get_derivable_history_for_session(session, c_session_id=c_session_id)
    domain_summaries = [
        _to_domain_summary(
            record,
            student_id=mastery_source_student_id,
            intervention_session_id=mastery_source_intervention_session_id,
            c_session_id=stu_session_id,
        )
        for record in summaries
    ]

    event_records = await CGameplayEventRecordRepository(session).list_all_events_for_session(c_session_id)
    domain_events = [
        _to_domain_gameplay_event(
            record,
            student_id=mastery_source_student_id,
            c_session_id=stu_session_id,
            game_task_instance_id=f"{stu_session_id}-T{record.task_index:03d}-X001",
        )
        for record in event_records
    ]

    decision_records = await CPolicyDecisionRecordRepository(session).list_chronological_for_session(c_session_id)
    domain_decisions = [_to_domain_adaptation_decision(record) for record in decision_records]

    aggregate = adapter.derive_session_aggregate(
        domain_events,
        domain_summaries,
        domain_decisions,
        time_in_target_band_sec=time_in_target_band_sec,
        safety_override_count=safety_override_count,
        inactive_time_available=inactive_time_available,
        config=config,
    )
    engagement_components, engagement_score = adapter.compute_engagement(aggregate, formula_version)
    frustration_components, frustration_index = adapter.compute_frustration(aggregate, formula_version)
    telemetry_quality_status = adapter.decide_telemetry_quality_status(
        aggregate.session_technical_issue_flag,
        aggregate.task_opportunity_count,
        aggregate.completed_task_count,
        aggregate.session_duration_sec,
        aggregate.accuracy_rate,
        aggregate.task_completion_rate,
    )
    learner_state, state_reason = adapter.decide_learner_state(
        telemetry_quality_status,
        aggregate.safety_override_count,
        aggregate.consecutive_error_max,
        aggregate.quit_after_error,
        aggregate.difficulty_floor_hits,
        aggregate.task_completion_rate,
        aggregate.inactivity_periods,
        engagement_score,
        frustration_index,
    )

    aggregate_id = uuid4()
    record = CSessionAggregateResultRecord(
        c_session_aggregate_result_id=aggregate_id,
        c_session_id=c_session_id,
        task_opportunity_count=aggregate.task_opportunity_count,
        completed_task_count=aggregate.completed_task_count,
        correct_task_count=aggregate.correct_task_count,
        total_attempt_count=aggregate.total_attempt_count,
        accuracy_rate=aggregate.accuracy_rate,
        avg_attempts_per_task=aggregate.avg_attempts_per_task,
        task_completion_rate=aggregate.task_completion_rate,
        inactivity_periods=aggregate.inactivity_periods,
        inactive_time_sec=aggregate.inactive_time_sec,
        inactive_time_available=aggregate.inactive_time_available,
        session_duration_sec=aggregate.session_duration_sec,
        time_in_target_band_sec=aggregate.time_in_target_band_sec,
        consecutive_error_max=aggregate.consecutive_error_max,
        difficulty_floor_hits=aggregate.difficulty_floor_hits,
        quit_after_error=aggregate.quit_after_error,
        safety_override_count=aggregate.safety_override_count,
        c_mean_game_task_latency_sec=aggregate.c_mean_game_task_latency_sec,
        c_median_game_task_latency_sec=aggregate.c_median_game_task_latency_sec,
        current_difficulty_level=aggregate.current_difficulty_level,
        difficulty_trend=aggregate.difficulty_trend,
        session_technical_issue_flag=aggregate.session_technical_issue_flag,
        engagement_score=engagement_score,
        engagement_completion_component=engagement_components.completion_component,
        engagement_activity_component=engagement_components.activity_component,
        engagement_target_band_component=engagement_components.target_band_component,
        engagement_accuracy_component=engagement_components.accuracy_component,
        frustration_index=frustration_index,
        frustration_error_run_component=frustration_components.error_run_component,
        frustration_excess_attempt_component=frustration_components.excess_attempt_component,
        frustration_inactivity_burden_component=frustration_components.inactivity_burden_component,
        frustration_floor_hit_component=frustration_components.floor_hit_component,
        frustration_quit_after_error_component=frustration_components.quit_after_error_component,
        frustration_safety_override_component=frustration_components.safety_override_component,
        telemetry_quality_status=telemetry_quality_status,
        learner_state=learner_state,
        state_reason=state_reason,
        **_provenance("c_session_aggregate_result", aggregate_id, request_id, "c_session.aggregated"),
    )
    session.add(record)

    # C-17 Item B's own producer half (P4: the mechanism, never claimed to close the guarantee --
    # decide_and_persist_adaptation, the one consumer, has no live caller, and this function itself
    # is unreachable from any live path per P1/N3). Upserts CLearnerLocalStateRecord.
    # prior_session_end_state from THIS session's own real, just-derived learner_state -- never a
    # hardcoded value.
    local_state_repo = CLearnerLocalStateRepository(session)
    local_state = await local_state_repo.find_by_student(student_id)
    if local_state is None:
        local_state_id = uuid4()
        local_state = CLearnerLocalStateRecord(
            c_learner_local_state_id=local_state_id,
            student_id=student_id,
            eligible_combined_handoffs_completed=0,
            sessions_since_last_practice={},
            prior_session_end_state=learner_state,
            **_provenance("c_learner_local_state", local_state_id, request_id, "c_session.aggregated"),
        )
        session.add(local_state)
    else:
        local_state.prior_session_end_state = learner_state

    await session.flush()
    return record
