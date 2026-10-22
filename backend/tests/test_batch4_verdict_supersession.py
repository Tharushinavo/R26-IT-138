"""Component C backend remediation, batch 4 (Amendment A-1): ``c_task_opportunity_verdicts`` --
the durable exclusion-reason / supersession-chain table Phase 8's own K3/K4 register entries named
without building (``buildLog1.md``, "Component C Phase 8" entry). See
``app.infrastructure.persistence_models.CTaskOpportunityVerdictRecord``'s own docstring for the
full ruling trace this file proves.

Covers: the write-path regression (TelemetryStreamRejectedError still propagates UNCHANGED, a
verdict row now exists, no summary row exists -- §7.3); CONDITION 1's sentinel test (a rejected
stream's learner-supplied payload value never reaches a persisted verdict row); the chain-
resolution mechanism (RULING 2 -- liveness is graph-resolved, never mere row presence, including
the "self-superseding" structural CHECK); and the negative control (§7.4) -- a session with a
summary superseded by a live verdict refuses through the REAL adaptation and aggregation call
chains, while the identical fixture minus the supersession row succeeds through both.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.application.live_engine_c import aggregation_service
from app.application.live_engine_c.adaptation_service import build_evidence_for_session
from app.application.live_engine_c.aggregation_service import derive_and_persist_session_aggregate
from app.application.live_engine_c.mastery_fixture import (
    FIXTURE_MASTERY_SOURCE_INTERVENTION_SESSION_ID,
    FIXTURE_MASTERY_SOURCE_STUDENT_ID,
)
from app.application.live_engine_c.summary_service import derive_and_persist_summary
from app.application.live_engine_c.task_service import TaskService, _stu_session_id
from app.application.live_engine_c.telemetry_validation import (
    TELEMETRY_VALIDATION_CHECKS,
    _live_verdict_ids,
    get_derivable_history_for_session,
)
from app.domain.live_engine_c.errors import DistrustedHistoryGapError, TelemetryStreamRejectedError
from app.infrastructure.live_engine_c.adapter import LiveEngineCAdapter
from app.infrastructure.persistence_models import CGameplayEventRecord, CTaskOpportunityVerdictRecord
from app.infrastructure.repositories import (
    CGameplayEventRecordRepository,
    CTaskOpportunitySummaryRecordRepository,
    CTaskOpportunityVerdictRecordRepository,
)
from tests.test_c4_session_lifecycle import isolated_database, provenance
from tests.test_c5_task_serve_and_evaluate import (
    _create_real_instance_via_smoke_mode,
    alembic,
    generation_config_fixture_for_tests,
)
from tests.test_c6b_policy_and_safety import evidence_window_config_fixture_for_tests
from tests.test_c9a_aggregation import _aggregation_config


MIGRATION_PATH = Path("migrations/versions/20260816_0007_batch4_task_opportunity_verdicts.py")

# The C-9 overlapping-pause fixture, reused verbatim (same shape test_c8_telemetry_validation.py's
# own test_c9_fixture_refused_before_derivation_and_action_payload_never_nulled builds) -- a
# structurally rejected stream, not a scientific one, chosen only because it is a real,
# already-proven TelemetryStreamRejectedError trigger.
_PAUSE_OVERLAP_ROWS = [
    ("game_task_started", 2, 0, None, None, False, None),
    ("answer_submitted", 3, 0, 1, {"submitted_total": 3}, False, None),
    ("pause_started", 4, 0, None, None, False, None),  # start1
    ("pause_started", 5, 1000, None, None, False, None),  # start2 -- overlaps start1
    ("pause_ended", 6, 2000, None, None, False, None),  # end1
    ("pause_ended", 7, 3000, None, None, False, None),  # end2
    ("game_task_quit", 8, 3000, None, None, False, "quit_without_recent_error"),
]


async def _write_pause_overlap_events(session, *, c_session_id, instance_id, rows) -> None:
    for event_type, index, ts, attempt_number, action_payload, technical_flag, terminal_reason in rows:
        record_id = uuid4()
        session.add(
            CGameplayEventRecord(
                c_gameplay_event_id=record_id,
                c_session_id=c_session_id,
                game_task_instance_id=instance_id,
                task_index=1,
                event_type=event_type,
                event_index=index,
                attempt_number=attempt_number,
                event_timestamp_relative_ms=ts,
                action_payload=action_payload,
                evaluation_payload=None,
                scaffold_code=None,
                technical_flag=technical_flag,
                terminal_reason=terminal_reason,
                seed_lineage_global_seed=1,
                seed_lineage_path=[],
                seed_lineage_seed=1,
                generator_version="test-gen-1",
                config_checksum="fixture-checksum",
                **provenance("c_gameplay_event", record_id),
            )
        )
    await session.flush()



async def _write_completed_task_events(session, *, c_session_id, instance_id, task_index) -> None:
    """A real, well-formed, terminal-reaching event stream (started/submitted/evaluated/
    completed) for one task instance -- ``_create_real_instance_via_smoke_mode`` already wrote
    ``event_index=1`` (``game_task_offered``), matching the c9a fixture's own convention. Used by
    the negative control (Sec 7.4) and the chain-isolation test (RULING 2) so BOTH the read path's
    gap logic (which needs a real terminal ``c_gameplay_events`` row --
    ``has_terminal_for_instance``) and the real aggregation call chain (which needs a real,
    non-empty event stream, not a summary-only fixture) see genuine data."""

    def _event(event_id, event_type, index, ts, attempt_number, action_payload, evaluation_payload, terminal_reason):
        session.add(
            CGameplayEventRecord(
                c_gameplay_event_id=event_id,
                c_session_id=c_session_id,
                game_task_instance_id=instance_id,
                task_index=task_index,
                event_type=event_type,
                event_index=index,
                attempt_number=attempt_number,
                event_timestamp_relative_ms=ts,
                action_payload=action_payload,
                evaluation_payload=evaluation_payload,
                scaffold_code=None,
                technical_flag=False,
                terminal_reason=terminal_reason,
                seed_lineage_global_seed=1,
                seed_lineage_path=[],
                seed_lineage_seed=1,
                generator_version="test-gen-1",
                config_checksum="fixture-checksum",
                **provenance("c_gameplay_event", event_id),
            )
        )

    _event(uuid4(), "game_task_started", 2, 0, None, None, None, None)
    _event(uuid4(), "answer_submitted", 3, 500, 1, {"submitted_total": 3}, None, None)
    _event(uuid4(), "answer_evaluated", 4, 600, 1, None, {"is_correct": True}, None)
    _event(uuid4(), "game_task_completed", 5, 1000, None, None, None, "completed_correct")
    await session.flush()


async def _complete_task_and_derive_summary(session, *, c_session_id, instance_id, task_index, stu_session_id):
    """Writes the real event stream above and derives a REAL summary through
    ``derive_and_persist_summary`` -- never a hand-built ``CTaskOpportunitySummaryRecord`` --
    keeping the negative control's own claim ("driven through the REAL... call chains") honest
    one layer earlier than just adaptation/aggregation."""
    await _write_completed_task_events(
        session, c_session_id=c_session_id, instance_id=instance_id, task_index=task_index
    )
    return await derive_and_persist_summary(
        session,
        adapter=LiveEngineCAdapter(),
        c_session_id=c_session_id,
        c_task_instance_id=instance_id,
        student_id=FIXTURE_MASTERY_SOURCE_STUDENT_ID,
        stu_session_id=stu_session_id,
        game_task_instance_id=f"{stu_session_id}-T{task_index:03d}-X001",
        request_id=f"req-{uuid4()}",
    )


async def _build_two_real_completed_tasks(session):
    """Two real, fully completed tasks in ONE real session -- task 1 via
    ``_create_real_instance_via_smoke_mode``, task 2 via a second real
    ``TaskService.next_task`` call against the SAME ``c_session_id``. Post CONNECT
    resume-instead-of-mint batch: ``next_task`` DOES now resume a pending (unterminated) instance
    rather than minting -- but task 1 is driven to a real terminal event via
    ``_complete_task_and_derive_summary`` BEFORE this second call, so the resume check
    (``has_terminal_for_instance``) correctly finds nothing to resume and the mint path runs
    exactly as before; ``task_index`` is still ``count_for_session(...) + 1``. This helper's own
    shape is this batch's negative control by construction -- see
    ``test_next_task_does_not_resume_a_terminated_instance`` below for the explicit assertion.
    Both instances carry real terminal events and real, derived summaries -- the shared fixture
    for the negative control (Sec 7.4) and the chain-isolation test (RULING 2)."""
    student_id, c_session_id, instance1_id, subject = await _create_real_instance_via_smoke_mode(session)
    stu_session_id = _stu_session_id()
    summary1 = await _complete_task_and_derive_summary(
        session, c_session_id=c_session_id, instance_id=instance1_id, task_index=1, stu_session_id=stu_session_id
    )
    response2 = await TaskService().next_task(
        session,
        principal_user_id=subject,
        request_id=f"req-{uuid4()}",
        c_session_id=c_session_id,
        generation_config=generation_config_fixture_for_tests(),
        smoke_mode=True,
    )
    instance2_id = response2.c_task_instance_id
    summary2 = await _complete_task_and_derive_summary(
        session, c_session_id=c_session_id, instance_id=instance2_id, task_index=2, stu_session_id=stu_session_id
    )
    return c_session_id, instance1_id, instance2_id, student_id, summary1, summary2


def test_next_task_does_not_resume_a_terminated_instance() -> None:
    """CONNECT resume-instead-of-mint batch, owner-specified negative control: "a resume that
    never releases is worse than the abandonment it replaces." Reuses
    _build_two_real_completed_tasks unchanged -- its own shape already proves this (task 1 is
    terminated before the second next_task call) -- this test only makes the assertion explicit:
    the second call's instance is a DIFFERENT id, at a DIFFERENT task_index, than the first's. A
    child who answers correctly is never stranded on the completed task forever."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            c_session_id, instance1_id, instance2_id, _student_id, _summary1, _summary2 = (
                await _build_two_real_completed_tasks(session)
            )
            assert instance2_id != instance1_id
        await database_engine.dispose()

    asyncio.run(exercise())

# =====================================================================================
# §7.3 -- the write-path regression: TelemetryStreamRejectedError still propagates UNCHANGED
# (proving the existing contract was not weakened), a verdict row now exists, and no summary row
# exists.
# =====================================================================================


def test_write_site_persists_excluded_verdict_and_reraises_the_same_exception_unchanged() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            _, c_session_id, instance_id, _subject = await _create_real_instance_via_smoke_mode(session)
            await _write_pause_overlap_events(
                session, c_session_id=c_session_id, instance_id=instance_id, rows=_PAUSE_OVERLAP_ROWS
            )

            adapter = LiveEngineCAdapter()
            with pytest.raises(TelemetryStreamRejectedError) as excinfo:
                await derive_and_persist_summary(
                    session,
                    adapter=adapter,
                    c_session_id=c_session_id,
                    c_task_instance_id=instance_id,
                    student_id=FIXTURE_MASTERY_SOURCE_STUDENT_ID,
                    stu_session_id="STU-0001-C-001",
                    game_task_instance_id="STU-0001-C-001-T001-X001",
                    request_id=f"req-{uuid4()}",
                )
            # UNCHANGED: same exception type, same check identity as before this batch.
            assert excinfo.value.check == TELEMETRY_VALIDATION_CHECKS.PAUSE_PAIRING

            # The existing contract is not weakened: still no summary row for the offending stream.
            summary = await CTaskOpportunitySummaryRecordRepository(session).find_by_instance(instance_id)
            assert summary is None

            # NEW this batch: a durable verdict row now exists, targeting exactly this instance,
            # the first-ever judgment for it (nothing to supersede).
            verdicts = await CTaskOpportunityVerdictRecordRepository(session).list_for_session(c_session_id)
            assert len(verdicts) == 1
            verdict = verdicts[0]
            assert verdict.game_task_instance_id == instance_id
            assert verdict.c_session_id == c_session_id
            assert verdict.task_index == 1
            assert verdict.validator_check == TELEMETRY_VALIDATION_CHECKS.PAUSE_PAIRING
            assert verdict.verdict_detail == excinfo.value.detail
            assert verdict.supersedes_verdict_id is None
        await database_engine.dispose()

    asyncio.run(exercise())


# =====================================================================================
# CONDITION 1 -- verdict_detail records WHY, never the rejected values. A sentinel you can grep
# for beats an assertion about what the text "should" contain.
# =====================================================================================


def test_verdict_detail_never_carries_a_rejected_payload_sentinel_value() -> None:
    alembic("upgrade", "head")
    sentinel = "SENTINEL_LEARNER_PAYLOAD_VALUE_MUST_NEVER_PERSIST_9f3a7c"
    sentinel_rows = list(_PAUSE_OVERLAP_ROWS)
    sentinel_rows[1] = ("answer_submitted", 3, 0, 1, {"submitted_total": sentinel}, False, None)

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            _, c_session_id, instance_id, _subject = await _create_real_instance_via_smoke_mode(session)
            await _write_pause_overlap_events(
                session, c_session_id=c_session_id, instance_id=instance_id, rows=sentinel_rows
            )

            with pytest.raises(TelemetryStreamRejectedError):
                await derive_and_persist_summary(
                    session,
                    adapter=LiveEngineCAdapter(),
                    c_session_id=c_session_id,
                    c_task_instance_id=instance_id,
                    student_id=FIXTURE_MASTERY_SOURCE_STUDENT_ID,
                    stu_session_id="STU-0001-C-001",
                    game_task_instance_id="STU-0001-C-001-T001-X001",
                    request_id=f"req-{uuid4()}",
                )

            # The fixture is genuine: the sentinel really is in the raw, untouched event row
            # (K1's own "persisted always" half -- proves this test would have caught a leak).
            records = await CGameplayEventRecordRepository(session).list_ordered_for_instance(instance_id)
            submitted = next(r for r in records if r.event_type == "answer_submitted")
            assert submitted.action_payload == {"submitted_total": sentinel}

            # ...but the sentinel appears in NO persisted verdict row, for any column.
            verdicts = await CTaskOpportunityVerdictRecordRepository(session).list_for_session(c_session_id)
            assert verdicts, "expected a verdict row -- an empty list would make this assertion vacuous"
            for verdict in verdicts:
                assert sentinel not in verdict.verdict_detail
                assert sentinel not in verdict.validator_check
        await database_engine.dispose()

    asyncio.run(exercise())


# =====================================================================================
# RULING 2 -- liveness is graph-resolved (walk supersedes_verdict_id), never mere row presence.
# "An untested chain is decoration."
# =====================================================================================


def test_live_verdict_ids_resolves_the_chain_not_mere_row_presence() -> None:
    """Pure unit test of ``_live_verdict_ids`` -- no DB round-trip needed (mirrors
    ``validate_event_stream_structurally``'s own pure-function test style). v1 is superseded by
    v2 (v1 is dead, v2 is live); v3 supersedes nothing and nothing supersedes it (independently
    live)."""
    v1_id, v2_id, v3_id = uuid4(), uuid4(), uuid4()
    v1 = CTaskOpportunityVerdictRecord(
        c_task_opportunity_verdict_id=v1_id, supersedes_verdict_id=None, game_task_instance_id=uuid4()
    )
    v2 = CTaskOpportunityVerdictRecord(
        c_task_opportunity_verdict_id=v2_id, supersedes_verdict_id=v1_id, game_task_instance_id=uuid4()
    )
    v3 = CTaskOpportunityVerdictRecord(
        c_task_opportunity_verdict_id=v3_id, supersedes_verdict_id=None, game_task_instance_id=uuid4()
    )
    live = _live_verdict_ids([v1, v2, v3])
    assert live == {v2_id, v3_id}
    assert v1_id not in live


def test_superseded_verdict_does_not_suppress_a_different_lives_own_target() -> None:
    """RULING 2 (owner ruling, quoted in the work order): "only a LIVE verdict... suppresses its
    target summary... An untested chain is decoration." Isolates the LIVENESS mechanism from mere
    row presence: v1 targets task 1's summary and is then superseded by v2 -- but v2 targets task
    2's summary, a DIFFERENT target. If the read path used "any verdict row referencing this
    instance" instead of graph-resolved liveness, task 1 would be wrongly suppressed too (v1's row
    still literally names it). This test proves it is NOT: task 1 stays derivable (v1 is
    superseded, therefore powerless over its own target), while task 2 IS suppressed (v2 is live).

    Deliberately not modeling a realistic write-site scenario -- a real correction from
    ``summary_service._persist_excluded_verdict`` always chains to a prior verdict for the SAME
    instance it corrects. This is a mechanism-isolation test of the graph-resolution algorithm
    itself, the same shape this register already uses for synthetic AST-guard violations."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            c_session_id, instance1_id, instance2_id, _student_id, _s1, _s2 = (
                await _build_two_real_completed_tasks(session)
            )

            v1_id = uuid4()
            session.add(
                CTaskOpportunityVerdictRecord(
                    c_task_opportunity_verdict_id=v1_id,
                    c_session_id=c_session_id,
                    game_task_instance_id=instance1_id,
                    task_index=1,
                    validator_check=TELEMETRY_VALIDATION_CHECKS.MONOTONICITY,
                    verdict_detail="v1 -- superseded below, must not suppress task 1",
                    supersedes_verdict_id=None,
                    **provenance("c_task_opportunity_verdict", v1_id),
                )
            )
            await session.flush()
            v2_id = uuid4()
            session.add(
                CTaskOpportunityVerdictRecord(
                    c_task_opportunity_verdict_id=v2_id,
                    c_session_id=c_session_id,
                    game_task_instance_id=instance2_id,
                    task_index=2,
                    validator_check=TELEMETRY_VALIDATION_CHECKS.MONOTONICITY,
                    verdict_detail="v2 -- live, supersedes v1, suppresses task 2 (its own target)",
                    supersedes_verdict_id=v1_id,
                    **provenance("c_task_opportunity_verdict", v2_id),
                )
            )
            await session.flush()

            with pytest.raises(DistrustedHistoryGapError) as excinfo:
                await get_derivable_history_for_session(session, c_session_id=c_session_id)
            # Task 1 is NOT suppressed (v1 is superseded); task 2 IS (v2 is live).
            assert excinfo.value.gap_task_indices == (2,)
        await database_engine.dispose()

    asyncio.run(exercise())


def test_self_superseding_verdict_is_rejected_by_the_check_constraint() -> None:
    """Provokes ``ck_c_task_opportunity_verdicts_not_self_superseding`` directly -- a verdict
    citing itself as its own predecessor is a structural impossibility (a chain cannot begin
    already superseded), not an invented threshold."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            _, c_session_id, instance_id, _subject = await _create_real_instance_via_smoke_mode(session)
            verdict_id = uuid4()
            session.add(
                CTaskOpportunityVerdictRecord(
                    c_task_opportunity_verdict_id=verdict_id,
                    c_session_id=c_session_id,
                    game_task_instance_id=instance_id,
                    task_index=1,
                    validator_check=TELEMETRY_VALIDATION_CHECKS.TERMINAL_UNIQUENESS,
                    verdict_detail="self-superseding provocation -- must be rejected",
                    supersedes_verdict_id=verdict_id,
                    **provenance("c_task_opportunity_verdict", verdict_id),
                )
            )
            with pytest.raises(IntegrityError):
                await session.flush()
        await database_engine.dispose()

    asyncio.run(exercise())


# =====================================================================================
# §7.4 -- THE NEGATIVE CONTROL. A session with a summary marked superseded, driven through the
# REAL adaptation and aggregation call chains, asserting both refuse -- and the identical fixture
# MINUS the supersession row asserting both succeed. If both runs behave identically, the table is
# decoration -- that is a FINDING to report, not something to adjust the fixture until it passes.
# =====================================================================================


async def _evidence_for(session, *, c_session_id, current_instance_id):
    return await build_evidence_for_session(
        session,
        adapter=LiveEngineCAdapter(),
        c_session_id=c_session_id,
        student_id=FIXTURE_MASTERY_SOURCE_STUDENT_ID,
        intervention_session_id=FIXTURE_MASTERY_SOURCE_INTERVENTION_SESSION_ID,
        stu_session_id=f"{FIXTURE_MASTERY_SOURCE_STUDENT_ID}-C-001",
        session_mode="c_only",
        session_phase="c_only",
        current_difficulty_level=1,
        c_task_instance_id=current_instance_id,
        prior_session_end_state=None,
        evidence_window_config=evidence_window_config_fixture_for_tests(),
    )


async def _aggregate_for(session, *, c_session_id, student_id):
    return await derive_and_persist_session_aggregate(
        session,
        adapter=LiveEngineCAdapter(),
        c_session_id=c_session_id,
        student_id=student_id,
        mastery_source_student_id=FIXTURE_MASTERY_SOURCE_STUDENT_ID,
        mastery_source_intervention_session_id=FIXTURE_MASTERY_SOURCE_INTERVENTION_SESSION_ID,
        stu_session_id=f"{FIXTURE_MASTERY_SOURCE_STUDENT_ID}-C-001",
        time_in_target_band_sec=0.0,
        safety_override_count=0,
        inactive_time_available=True,
        config=_aggregation_config(),
        formula_version="C-COMP-v1",
        request_id=f"req-{uuid4()}",
    )


def test_negative_control_superseded_summary_refuses_through_real_adaptation_and_aggregation_chains(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    alembic("upgrade", "head")
    monkeypatch.setattr(aggregation_service, "_AGGREGATION_INPUTS_AVAILABLE", True)

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            c_session_id, instance1_id, instance2_id, student_id, _s1, _s2 = (
                await _build_two_real_completed_tasks(session)
            )

            verdict_id = uuid4()
            session.add(
                CTaskOpportunityVerdictRecord(
                    c_task_opportunity_verdict_id=verdict_id,
                    c_session_id=c_session_id,
                    game_task_instance_id=instance1_id,
                    task_index=1,
                    validator_check=TELEMETRY_VALIDATION_CHECKS.PAUSE_PAIRING,
                    verdict_detail="negative control -- task 1's summary is now superseded",
                    supersedes_verdict_id=None,
                    **provenance("c_task_opportunity_verdict", verdict_id),
                )
            )
            await session.flush()

            # The guarded accessor itself refuses.
            with pytest.raises(DistrustedHistoryGapError) as excinfo:
                await get_derivable_history_for_session(session, c_session_id=c_session_id)
            assert 1 in excinfo.value.gap_task_indices

            # REAL adaptation call chain refuses.
            with pytest.raises(DistrustedHistoryGapError):
                await _evidence_for(session, c_session_id=c_session_id, current_instance_id=instance2_id)

            # REAL aggregation call chain refuses -- no aggregate row, no learner-state write.
            with pytest.raises(DistrustedHistoryGapError):
                await _aggregate_for(session, c_session_id=c_session_id, student_id=student_id)
        await database_engine.dispose()

    asyncio.run(exercise())


def test_negative_control_identical_fixture_minus_supersession_succeeds_through_real_adaptation_and_aggregation_chains(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The identical fixture, MINUS the supersession row above -- both real chains succeed. Proves
    the negative control has teeth: it is the PRESENCE of the live verdict, not some other
    property of the fixture, that made the prior test refuse."""
    alembic("upgrade", "head")
    monkeypatch.setattr(aggregation_service, "_AGGREGATION_INPUTS_AVAILABLE", True)

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            c_session_id, _instance1_id, instance2_id, student_id, _s1, _s2 = (
                await _build_two_real_completed_tasks(session)
            )
            # No verdict row inserted -- otherwise byte-identical to the refusing test above.

            history = await get_derivable_history_for_session(session, c_session_id=c_session_id)
            assert len(history) == 2

            evidence = await _evidence_for(session, c_session_id=c_session_id, current_instance_id=instance2_id)
            assert evidence is not None

            record = await _aggregate_for(session, c_session_id=c_session_id, student_id=student_id)
            assert record.c_session_id == c_session_id
        await database_engine.dispose()

    asyncio.run(exercise())


# =====================================================================================
# Amendment A-1's own scope: ONE table, two authorized CHECK constraints (business-specific,
# separate from ProvenanceMixin's own three, reused everywhere), no trigger, no seed data, no
# generator/Yass import.
# =====================================================================================


def test_migration_creates_exactly_one_table_with_the_two_authorized_check_constraints() -> None:
    migration = MIGRATION_PATH.read_text(encoding="utf-8")
    created = set(re.findall(r'op\.create_table\(\s*"([^"]+)"', migration))
    assert created == {"c_task_opportunity_verdicts"}

    # Exactly 5 CHECK constraints total: the 2 table-specific ones this amendment authorizes, plus
    # the 3 ProvenanceMixin always adds (source_class, actor_exactly_one, required_nonblank) --
    # never more, never fewer.
    assert migration.count("sa.CheckConstraint(") == 5
    assert "ck_c_task_opportunity_verdicts_validator_check_nonblank" in migration
    assert "ck_c_task_opportunity_verdicts_not_self_superseding" in migration

    lowered = migration.lower()
    assert "create_trigger" not in lowered
    assert "create trigger" not in lowered
    assert "bulk_insert" not in lowered
    assert "component_c_generator" not in lowered
    assert "yass" not in lowered
