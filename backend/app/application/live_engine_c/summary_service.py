"""Component C Phase 6a, T6-b: task-opportunity summary derivation, split out of
``task_service.py`` ("task_service.py already carries three concerns in 459 lines" -- Phase 6a
work order). Derivation runs THROUGH THE ADAPTER (T6-a, SummaryPort, ``adapter.py:1056-1059`` --
built and unwired since Phase 1b, called for the first time by this module). C-4 is this
register's most repeated finding: this module never reimplements
``derive_task_opportunity_summary``'s own logic, it only translates persisted rows into the
package's input shape and the package's output back into a persisted row.

T6-c: a summary is derived ONLY on the terminal-event write -- ``derive_and_persist_summary`` is
called exactly once, from ``terminal_event.write_completed_correct_terminal_event``'s caller in
``task_service.py``, never by a sweep/cron/batch over task instances. A task instance with no
events, or with events that never reached a terminal one, must never produce a summary row; that
is enforced by the derivation itself (``derive_task_opportunity_summary`` raises ``ValueError`` on
an empty stream and on a stream without exactly one terminal event, ``behaviour/summary.py:19-34``)
-- not by any check in this module.

T6-d: "derived only, never sampled" (Phase 3a docstring) means every field on the persisted
``CTaskOpportunitySummaryRecord`` is copied verbatim from the adapter's returned
``TaskOpportunitySummary`` -- this module computes NOTHING itself. ``tests/
test_c6a_summary_derivation.py::test_t6d_summary_record_fields_are_a_pure_passthrough_of_the_
derivation_output`` proves this by substituting a stub adapter whose return carries a sentinel
value and asserting the persisted row carries that exact sentinel, not a recomputed one.

INTERVENTION_SESSION_ID (BUILDER JUDGMENT -- UNRATIFIED, disclosed prominently, not attributed
upward): ``component_c_generator.models.gameplay.GameplayEvent.intervention_session_id`` is a
required (non-Optional) field the installed package validates against B's
``^STU-[0-9]{4}-I-[0-9]{3}$`` format, but ``c_gameplay_events`` carries no such column (Phase
3a/3b's own schema) and a ``c_only`` session's ``CSessionRecord.intervention_session_id`` is
legitimately ``NULL`` (no B session exists to name). This module reuses
``mastery_fixture.FIXTURE_MASTERY_SOURCE_INTERVENTION_SESSION_ID`` ("STU-0001-I-001") for EVERY
session mode, by direct analogy to R-8's own resolution of the identical problem for
``student_id``/``c_session_id`` -- R-8's reasoning applies verbatim ("format-validated only, never
used for lookup, RNG, or cross-referencing anywhere the installed wheel or this codebase does")
but R-8 itself named only ``student_id``/``c_session_id``, not this field, so this extension is
NOT itself covered by R-8's own text and is disclosed here as a separate, unratified judgment
call rather than folded silently into R-8's authority.
"""

from __future__ import annotations

from typing import Optional, Sequence
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.live_engine_c.mastery_fixture import FIXTURE_MASTERY_SOURCE_INTERVENTION_SESSION_ID
from app.application.live_engine_c.session_lifecycle import _provenance
from app.application.live_engine_c.telemetry_validation import (
    _live_verdict_ids,
    validate_clock_discipline,
    validate_event_stream_structurally,
)
from app.domain.live_engine_c.errors import TelemetryStreamRejectedError
from app.domain.live_engine_c.types import GameplayEvent, SeedLineage, TaskOpportunitySummary
from app.infrastructure.live_engine_c.adapter import LiveEngineCAdapter
from app.infrastructure.persistence_models import (
    CGameplayEventRecord,
    CTaskInstanceRecord,
    CTaskOpportunitySummaryRecord,
    CTaskOpportunityVerdictRecord,
)
from app.infrastructure.repositories import (
    CGameplayEventRecordRepository,
    CTaskOpportunitySummaryRecordRepository,
    CTaskOpportunityVerdictRecordRepository,
)


def _to_domain_gameplay_event(
    record: CGameplayEventRecord, *, student_id: str, c_session_id: str, game_task_instance_id: str
) -> GameplayEvent:
    """Reconstructs the domain ``GameplayEvent`` the adapter's ``SummaryPort`` expects, from one
    persisted row. ``student_id``/``c_session_id``/``game_task_instance_id`` are not stored on
    this table in STU-shaped string form (Phase 3a's minimal-FK style, same reasoning as
    ``task_service._to_domain_task_instance``) and are supplied by the caller."""
    return GameplayEvent(
        event_id=str(record.c_gameplay_event_id),
        event_type=record.event_type,
        event_index=record.event_index,
        student_id=student_id,
        intervention_session_id=FIXTURE_MASTERY_SOURCE_INTERVENTION_SESSION_ID,
        c_session_id=c_session_id,
        game_task_instance_id=game_task_instance_id,
        task_index=record.task_index,
        attempt_number=record.attempt_number,
        event_timestamp_relative_ms=record.event_timestamp_relative_ms,
        action_payload=record.action_payload,
        evaluation_payload=record.evaluation_payload,
        scaffold_code=record.scaffold_code,
        technical_flag=record.technical_flag,
        terminal_reason=record.terminal_reason,
        seed_lineage=SeedLineage(
            global_seed=record.seed_lineage_global_seed,
            path=tuple(tuple(pair) for pair in record.seed_lineage_path),
            seed=record.seed_lineage_seed,
        ),
        generator_version=record.generator_version,
        config_checksum=record.config_checksum,
    )


def _summary_record(
    summary: TaskOpportunitySummary,
    *,
    c_session_id: UUID,
    c_task_instance_id: UUID,
    request_id: str,
) -> CTaskOpportunitySummaryRecord:
    """T6-d: every field below is ``summary.<field>`` -- a straight copy of the adapter's
    returned value, nothing computed or defaulted here."""
    summary_id = uuid4()
    return CTaskOpportunitySummaryRecord(
        c_task_opportunity_summary_id=summary_id,
        c_session_id=c_session_id,
        game_task_instance_id=c_task_instance_id,
        task_index=summary.task_index,
        task_offered=summary.task_offered,
        task_started=summary.task_started,
        task_completed=summary.task_completed,
        task_skipped=summary.task_skipped,
        task_quit=summary.task_quit,
        technical_issue=summary.technical_issue,
        correct_task=summary.correct_task,
        total_attempts=summary.total_attempts,
        retry_count=summary.retry_count,
        scaffold_requested=summary.scaffold_requested,
        scaffold_count=summary.scaffold_count,
        highest_scaffold_level=summary.highest_scaffold_level,
        c_answer_changes=summary.c_answer_changes,
        task_latency_sec=summary.task_latency_sec,
        inactive_time_sec=summary.inactive_time_sec,
        inactivity_periods=summary.inactivity_periods,
        quit_after_error=summary.quit_after_error,
        terminal_reason=summary.terminal_reason,
        first_attempt_correct=summary.first_attempt_correct,
        final_attempt_correct=summary.final_attempt_correct,
        consecutive_error_max_within_task=summary.consecutive_error_max_within_task,
        **_provenance("c_task_opportunity_summary", summary_id, request_id, "c_task.summary_derived"),
    )


async def _persist_excluded_verdict(
    session: AsyncSession,
    *,
    c_session_id: UUID,
    c_task_instance_id: UUID,
    exc: TelemetryStreamRejectedError,
    request_id: str,
) -> None:
    """Batch 4 (Amendment A-1, K3-b): writes the durable exclusion-reason row BEFORE
    ``derive_and_persist_summary``'s own caller ever sees ``TelemetryStreamRejectedError`` --
    K3-b's own deadline ("before first real data," stricter than every other pre-gate-lift item
    on this register). Covers BOTH of K4's faces with the identical write: a never-summarized
    instance (``supersedes_verdict_id`` stays ``NULL`` -- this is the first judgment) and a
    previously-summarized instance a later re-validation now finds bad (RULING 2: chains to
    whichever verdict is currently LIVE for this exact instance, found via
    ``telemetry_validation._live_verdict_ids`` -- the SAME liveness computation the read path
    uses, so the two can never disagree about what 'live' means).

    CONDITION 1: ``verdict_detail`` is ``exc.detail`` verbatim -- already structural-only by
    construction (every raise site in ``telemetry_validation.py`` states a check name, field path,
    index, or count, never a learner-supplied payload value). CONDITION 2: ``validator_check`` is
    ``exc.check`` verbatim, itself always one of ``telemetry_validation.
    TELEMETRY_VALIDATION_CHECKS``'s own members (every raise site draws from that one named
    tuple) -- this write site never invents or duplicates a check-name string of its own."""
    instance = await session.get(CTaskInstanceRecord, c_task_instance_id)
    prior_verdicts = await CTaskOpportunityVerdictRecordRepository(session).list_for_session(c_session_id)
    live_ids = _live_verdict_ids(prior_verdicts)
    prior_live_verdict = next(
        (
            v
            for v in prior_verdicts
            if v.game_task_instance_id == c_task_instance_id and v.c_task_opportunity_verdict_id in live_ids
        ),
        None,
    )
    verdict_id = uuid4()
    verdict = CTaskOpportunityVerdictRecord(
        c_task_opportunity_verdict_id=verdict_id,
        c_session_id=c_session_id,
        game_task_instance_id=c_task_instance_id,
        task_index=instance.task_index,
        validator_check=exc.check,
        verdict_detail=exc.detail,
        supersedes_verdict_id=(
            prior_live_verdict.c_task_opportunity_verdict_id if prior_live_verdict is not None else None
        ),
        **_provenance("c_task_opportunity_verdict", verdict_id, request_id, "c_task.stream_excluded"),
    )
    await CTaskOpportunityVerdictRecordRepository(session).add(verdict)


async def derive_and_persist_summary(
    session: AsyncSession,
    *,
    adapter: LiveEngineCAdapter,
    c_session_id: UUID,
    c_task_instance_id: UUID,
    student_id: str,
    stu_session_id: str,
    game_task_instance_id: str,
    request_id: str,
    records: Optional[Sequence[CGameplayEventRecord]] = None,
) -> CTaskOpportunitySummaryRecord:
    """PERF-01: ``records`` -- when the caller (``submit_action``) already holds this instance's complete, event_index-ordered
    stream in this transaction (it read the stream under the instance row lock and added its own events itself), it is passed
    in and the re-read below is skipped. Omitted -> unchanged behaviour.

    T6-a/T6-c: called ONLY after a terminal event write has succeeded (the caller's
    responsibility, not checked here) -- reads the full ordered event stream for the instance,
    translates it, derives THROUGH THE ADAPTER, and persists the result verbatim (T6-d).

    PHASE 8 (K1/K2-f/H4-a): the telemetry validator runs HERE, THE DERIVATION TRIGGER -- its own
    module, never task_service.py -- immediately before ``adapter.derive_task_opportunity_summary``
    is called, never after. A structural rejection propagates ``TelemetryStreamRejectedError`` to
    THIS function's own caller (``task_service.submit_action``'s terminal-event branch) and no
    ``CTaskOpportunitySummaryRecord`` is ever constructed or persisted for the offending stream --
    K1's "scored never" half. The raw ``c_gameplay_events`` rows already written by the caller
    BEFORE this function was ever invoked are untouched either way -- K1's "persisted always" half,
    already satisfied by the time this function runs, never undone by it.

    BATCH 4 (Amendment A-1): the SAME ``TelemetryStreamRejectedError`` is now also caught HERE,
    ONLY to write the durable ``c_task_opportunity_verdicts`` row (``_persist_excluded_verdict``
    above) before being RE-RAISED completely unchanged -- this function's own caller sees the
    identical exception it always did (proven by ``tests/test_batch4_verdict_supersession.py``'s
    own write-path regression: the existing contract is not weakened, only observed)."""
    event_repo = CGameplayEventRecordRepository(session)
    if records is None:
        records = await event_repo.list_ordered_for_instance(c_task_instance_id)
    try:
        validate_clock_discipline(records)
        domain_events = [
            _to_domain_gameplay_event(
                record,
                student_id=student_id,
                c_session_id=stu_session_id,
                game_task_instance_id=game_task_instance_id,
            )
            for record in records
        ]
        validate_event_stream_structurally(domain_events)
    except TelemetryStreamRejectedError as exc:
        await _persist_excluded_verdict(
            session,
            c_session_id=c_session_id,
            c_task_instance_id=c_task_instance_id,
            exc=exc,
            request_id=request_id,
        )
        raise
    summary = adapter.derive_task_opportunity_summary(domain_events)
    record = _summary_record(
        summary,
        c_session_id=c_session_id,
        c_task_instance_id=c_task_instance_id,
        request_id=request_id,
    )
    await CTaskOpportunitySummaryRecordRepository(session).add(record)
    return record
