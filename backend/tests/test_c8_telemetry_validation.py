"""Component C Phase 8: server-side telemetry validation (v3.0 §11 Phase 8).

Covers: the five checks buildable on the domain ``GameplayEvent`` sequence
(``validate_event_stream_structurally``) with a violation + a clean control for each; the ordinal
half of clock discipline (``validate_clock_discipline``); H4-a/K2-i (Phase 6a's own C-9
characterization fixture, reused verbatim, proving the stream is refused BEFORE
``derive_task_opportunity_summary`` is reachable, and that no summary row is ever persisted for
it); H5-a (a positive test that ``action_payload`` is never nulled on a distrusted stream); H5-b's
three provocations (a technical-flagged event never becomes an error, a quit, or a contributor to
inactivity burden); and the guarded accessor's own gap-refusal behaviour (J1-4).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.application.live_engine_c.mastery_fixture import FIXTURE_MASTERY_SOURCE_STUDENT_ID
from app.application.live_engine_c.summary_service import derive_and_persist_summary
from app.application.live_engine_c.telemetry_validation import (
    TERMINAL_EVENT_TYPES,
    get_derivable_history_for_session,
    validate_clock_discipline,
    validate_event_stream_structurally,
)
from app.domain.live_engine_c.errors import DistrustedHistoryGapError, TelemetryStreamRejectedError
from app.domain.live_engine_c.types import GameplayEvent, SeedLineage
from app.infrastructure.live_engine_c.adapter import LiveEngineCAdapter
from app.infrastructure.persistence_models import CGameplayEventRecord
from app.infrastructure.repositories import (
    CGameplayEventRecordRepository,
    CTaskOpportunitySummaryRecordRepository,
)
from tests.test_c4_session_lifecycle import isolated_database, provenance
from tests.test_c5_task_serve_and_evaluate import _create_real_instance_via_smoke_mode, alembic


def _seed_lineage() -> SeedLineage:
    return SeedLineage(global_seed=1, path=(), seed=1)


_COMMON = dict(
    student_id=FIXTURE_MASTERY_SOURCE_STUDENT_ID,
    intervention_session_id="STU-0001-I-001",
    c_session_id="STU-0001-C-001",
    game_task_instance_id="STU-0001-C-001-T001-X001",
    task_index=1,
    seed_lineage=_seed_lineage(),
    generator_version="test-gen-1",
    config_checksum="fixture-checksum",
)


def _event(
    event_id: str,
    event_type: str,
    event_index: int,
    ts: int,
    *,
    attempt_number=None,
    action_payload=None,
    evaluation_payload=None,
    scaffold_code=None,
    technical_flag: bool = False,
    terminal_reason=None,
) -> GameplayEvent:
    return GameplayEvent(
        event_id=event_id,
        event_type=event_type,
        event_index=event_index,
        attempt_number=attempt_number,
        event_timestamp_relative_ms=ts,
        action_payload=action_payload,
        evaluation_payload=evaluation_payload,
        scaffold_code=scaffold_code,
        technical_flag=technical_flag,
        terminal_reason=terminal_reason,
        **_COMMON,
    )


def _clean_stream() -> list[GameplayEvent]:
    """A minimal, well-formed stream: offered, started, completed. Every violation test below
    starts from a variant of this shape so each test isolates exactly ONE broken property."""
    return [
        _event("e1", "game_task_offered", 1, 0),
        _event("e2", "game_task_started", 2, 0),
        _event(
            "e3", "game_task_completed", 3, 100,
            terminal_reason="completed_correct",
            evaluation_payload={"is_correct": True},
        ),
    ]


def test_clean_stream_passes_every_structural_check() -> None:
    """POSITIVE CONTROL for all five checks at once: a well-formed stream must not raise."""
    validate_event_stream_structurally(_clean_stream())


# =====================================================================================
# Terminal uniqueness
# =====================================================================================


def test_terminal_uniqueness_rejects_zero_terminal_events() -> None:
    stream = [_event("e1", "game_task_offered", 1, 0), _event("e2", "game_task_started", 2, 0)]
    with pytest.raises(TelemetryStreamRejectedError) as excinfo:
        validate_event_stream_structurally(stream)
    assert excinfo.value.check == "terminal_uniqueness"
    assert "found 0" in excinfo.value.detail


def test_terminal_uniqueness_rejects_two_terminal_events() -> None:
    """Domain-level construction only -- the DB's own partial unique index already prevents this
    at the persistence layer (uq_c_gameplay_events_at_most_one_terminal_per_instance); this proves
    the validator ALSO catches it, independent of that DB constraint ever running."""
    stream = _clean_stream() + [
        _event("e4", "game_task_quit", 4, 100, terminal_reason="quit_without_recent_error")
    ]
    with pytest.raises(TelemetryStreamRejectedError) as excinfo:
        validate_event_stream_structurally(stream)
    assert excinfo.value.check == "terminal_uniqueness"
    assert "found 2" in excinfo.value.detail


# =====================================================================================
# Index continuity
# =====================================================================================


def test_index_continuity_rejects_a_gap() -> None:
    stream = [
        _event("e1", "game_task_offered", 1, 0),
        _event("e2", "game_task_started", 2, 0),
        _event("e3", "game_task_completed", 4, 100, terminal_reason="completed_correct", evaluation_payload={"is_correct": True}),
    ]
    with pytest.raises(TelemetryStreamRejectedError) as excinfo:
        validate_event_stream_structurally(stream)
    assert excinfo.value.check == "index_continuity"


# =====================================================================================
# Monotonicity
# =====================================================================================


def test_monotonicity_rejects_a_timestamp_that_precedes_its_predecessor() -> None:
    stream = [
        _event("e1", "game_task_offered", 1, 0),
        _event("e2", "game_task_started", 2, 100),
        _event("e3", "game_task_completed", 3, 50, terminal_reason="completed_correct", evaluation_payload={"is_correct": True}),
    ]
    with pytest.raises(TelemetryStreamRejectedError) as excinfo:
        validate_event_stream_structurally(stream)
    assert excinfo.value.check == "monotonicity"


# =====================================================================================
# Pause pairing, including overlap -- the C-9 fix at the VALIDATION layer (H4-a/K2-i)
# =====================================================================================


def test_pause_pairing_rejects_an_unpaired_pause_started() -> None:
    stream = [
        _event("e1", "game_task_offered", 1, 0),
        _event("e2", "game_task_started", 2, 0),
        _event("e3", "pause_started", 3, 0),
        _event("e4", "game_task_quit", 4, 100, terminal_reason="quit_without_recent_error"),
    ]
    with pytest.raises(TelemetryStreamRejectedError) as excinfo:
        validate_event_stream_structurally(stream)
    assert excinfo.value.check == "pause_pairing"
    assert "no matching pause_ended" in excinfo.value.detail


def test_pause_pairing_rejects_a_pause_ended_with_no_open_pause() -> None:
    stream = [
        _event("e1", "game_task_offered", 1, 0),
        _event("e2", "game_task_started", 2, 0),
        _event("e3", "pause_ended", 3, 0),
        _event("e4", "game_task_quit", 4, 100, terminal_reason="quit_without_recent_error"),
    ]
    with pytest.raises(TelemetryStreamRejectedError) as excinfo:
        validate_event_stream_structurally(stream)
    assert excinfo.value.check == "pause_pairing"
    assert "no open pause_started" in excinfo.value.detail


def test_pause_pairing_rejects_overlapping_pauses_the_c9_characterization_case() -> None:
    """H4-a/K2-i: THE EXACT FIXTURE from test_c6a_summary_derivation.py::
    test_t5_c9_overlapping_pauses_are_double_counted_not_unioned, reused verbatim (start1=0,
    start2=1000, end1=2000, end2=3000, both non-technical). That test proves the shipped,
    pinned derivation MISCOUNTS this stream (4.0s instead of the correct 3.0s union) rather than
    rejecting it. This test proves Phase 8's own validator REJECTS it outright, before
    derive_task_opportunity_summary is ever reachable -- H4-b: the derivation itself is untouched,
    still pinned, still byte-identical, still miscounts if ever called directly against this same
    fixture (proven by the Phase 6a test, not re-proven here)."""
    stream = [
        _event("e1", "game_task_offered", 1, 0),
        _event("e2", "game_task_started", 2, 0),
        _event("e3", "pause_started", 3, 0),  # start1
        _event("e4", "pause_started", 4, 1000),  # start2 -- overlaps start1, still open
        _event("e5", "pause_ended", 5, 2000),  # end1
        _event("e6", "pause_ended", 6, 3000),  # end2
        _event("e7", "game_task_quit", 7, 3000, terminal_reason="quit_without_recent_error"),
    ]
    with pytest.raises(TelemetryStreamRejectedError) as excinfo:
        validate_event_stream_structurally(stream)
    assert excinfo.value.check == "pause_pairing"
    assert "overlapping" in excinfo.value.detail


# =====================================================================================
# Clock discipline, ordinal half -- operates on the raw persisted row (created_at_utc), not the
# domain GameplayEvent, hence a separate function and a lightweight stand-in here rather than the
# full CGameplayEventRecord (this test needs only .event_index/.created_at_utc, the only two
# attributes validate_clock_discipline reads).
# =====================================================================================


class _ReceiptStub:
    def __init__(self, event_index: int, created_at_utc: datetime) -> None:
        self.event_index = event_index
        self.created_at_utc = created_at_utc


def test_clock_discipline_passes_non_decreasing_receipt_order() -> None:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    validate_clock_discipline(
        [_ReceiptStub(1, base), _ReceiptStub(2, base + timedelta(seconds=1)), _ReceiptStub(3, base + timedelta(seconds=2))]
    )


def test_clock_discipline_rejects_receipt_order_that_contradicts_claimed_order() -> None:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    with pytest.raises(TelemetryStreamRejectedError) as excinfo:
        validate_clock_discipline(
            [_ReceiptStub(1, base + timedelta(seconds=5)), _ReceiptStub(2, base)]
        )
    assert excinfo.value.check == "clock_discipline_ordinal"


# =====================================================================================
# H4-a/K2-i + H5-a, COMBINED, against a real, persisted stream -- proves the WIRING (not just the
# pure function): the C-9 fixture is refused at the derivation trigger, no summary row is ever
# written, and the raw action_payload the child actually submitted is never nulled.
# =====================================================================================


def test_c9_fixture_refused_before_derivation_and_action_payload_never_nulled() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            _, c_session_id, instance_id, _subject = await _create_real_instance_via_smoke_mode(session)
            # _create_real_instance_via_smoke_mode already wrote event_index=1 (game_task_offered).
            event_repo = CGameplayEventRecordRepository(session)
            submitted_payload = {"submitted_total": 3}
            rows = [
                ("game_task_started", 2, 0, None, None, False, None),
                ("answer_submitted", 3, 0, 1, submitted_payload, False, None),
                ("pause_started", 4, 0, None, None, False, None),  # start1
                ("pause_started", 5, 1000, None, None, False, None),  # start2 -- overlaps start1
                ("pause_ended", 6, 2000, None, None, False, None),  # end1
                ("pause_ended", 7, 3000, None, None, False, None),  # end2
                ("game_task_quit", 8, 3000, None, None, False, "quit_without_recent_error"),
            ]
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
            assert excinfo.value.check == "pause_pairing"

            # K1, "scored never": no summary row was ever persisted for this instance.
            summary = await CTaskOpportunitySummaryRecordRepository(session).find_by_instance(instance_id)
            assert summary is None

            # K1, "persisted always" / H5-a: the raw events -- including the child's real
            # submitted action -- are untouched. A test that would FAIL if action_payload were
            # ever nulled on a distrusted stream (the exact regression C-5/B's own F2 names).
            records = await event_repo.list_ordered_for_instance(instance_id)
            submitted_record = next(r for r in records if r.event_type == "answer_submitted")
            assert submitted_record.action_payload == submitted_payload
            assert len(records) == 8  # offered (1, from setup) + the 7 rows above -- nothing dropped
        await database_engine.dispose()

    asyncio.run(exercise())


# =====================================================================================
# H5-b -- three provocations. Real derivation (adapter.derive_task_opportunity_summary, pure, no
# DB), since the exclusion logic itself is the PINNED derivation's own (H4-b: not reimplemented,
# not fixed, not touched) -- Phase 8's own job here is only to confirm its validator does not
# itself reject a well-formed technical-flagged stream (never conflating "technical" with
# "malformed").
# =====================================================================================


def test_h5b_technical_event_never_becomes_an_error() -> None:
    stream = [
        _event("e1", "game_task_offered", 1, 0),
        _event("e2", "game_task_started", 2, 0),
        _event("e3", "technical_issue", 3, 0, technical_flag=True),
        _event("e4", "answer_submitted", 4, 0, attempt_number=1, action_payload={"submitted_total": 3}),
        _event("e5", "answer_evaluated", 5, 0, attempt_number=1, evaluation_payload={"is_correct": True}),
        _event("e6", "game_task_completed", 6, 0, terminal_reason="completed_correct"),
    ]
    validate_event_stream_structurally(stream)  # must NOT reject a well-formed technical stream
    summary = LiveEngineCAdapter().derive_task_opportunity_summary(stream)
    assert summary.consecutive_error_max_within_task == 0, "a technical event must never count as an error"


def test_h5b_technical_terminal_never_becomes_a_quit() -> None:
    stream = [
        _event("e1", "game_task_offered", 1, 0),
        _event("e2", "game_task_started", 2, 0),
        _event(
            "e3", "game_task_quit", 3, 0,
            terminal_reason="technical_issue", technical_flag=True,
        ),
    ]
    validate_event_stream_structurally(stream)
    summary = LiveEngineCAdapter().derive_task_opportunity_summary(stream)
    assert summary.quit_after_error is False, "a technical termination must never be recorded as a quit-after-error"
    assert summary.technical_issue is True


def test_h5b_technical_pause_never_feeds_inactivity_burden() -> None:
    """C3 §10, quoted: "technical/app/network pauses are marked technical and must not increase
    learner inactivity burden." Proves a technical-flagged pause contributes ZERO to
    inactivity_periods/inactive_time_sec -- the concrete mechanism by which a technical event never
    becomes an input to whatever downstream disengagement/safety-relevant signal treats sustained
    inactivity as a risk factor."""
    stream = [
        _event("e1", "game_task_offered", 1, 0),
        _event("e2", "game_task_started", 2, 0),
        _event("e3", "pause_started", 3, 0, technical_flag=True),
        _event("e4", "pause_ended", 4, 5000, technical_flag=True),
        _event("e5", "game_task_completed", 5, 5000, terminal_reason="completed_correct"),
    ]
    validate_event_stream_structurally(stream)
    summary = LiveEngineCAdapter().derive_task_opportunity_summary(stream)
    assert summary.inactivity_periods == 0
    assert summary.inactive_time_sec == 0.0


# =====================================================================================
# J1-4 -- the guarded accessor refuses rather than truncates. Test-exercisable only (disclosed
# honestly): decide_and_persist_adaptation, build_evidence_for_session's own caller, has no live
# caller under app/ (register-reconciliation batch, this same register) -- this test calls the
# accessor directly, the same shape every other pre-live gap in this register is proven by.
# =====================================================================================


def test_gap_in_derivable_history_raises_rather_than_truncates() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            _, c_session_id, instance_id, _subject = await _create_real_instance_via_smoke_mode(session)
            event_repo = CGameplayEventRecordRepository(session)
            # A terminal event with NO summary derivation ever attempted for it (simulating a
            # distrusted stream, i.e. a task_index that reached terminal but never derived) --
            # the gap this test proves the accessor refuses on, rather than silently omitting.
            record_id = uuid4()
            session.add(
                CGameplayEventRecord(
                    c_gameplay_event_id=record_id,
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
                    **provenance("c_gameplay_event", record_id),
                )
            )
            await session.flush()

            with pytest.raises(DistrustedHistoryGapError) as excinfo:
                await get_derivable_history_for_session(session, c_session_id=c_session_id)
            assert excinfo.value.gap_task_indices == (1,)
        await database_engine.dispose()

    asyncio.run(exercise())


def test_derivable_history_returns_summaries_when_no_gap_exists() -> None:
    """CLEAN CONTROL for J1-4: a session with no offered-and-terminal-but-undervied task returns
    its (empty, here -- nothing derived yet) history without raising."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            _, c_session_id, _instance_id, _subject = await _create_real_instance_via_smoke_mode(session)
            history = await get_derivable_history_for_session(session, c_session_id=c_session_id)
            assert list(history) == []  # offered, never reached terminal -- not a gap, not derivable yet
        await database_engine.dispose()

    asyncio.run(exercise())


# =====================================================================================
# K2-e -- the four blocked sub-checks stay UNBUILT. SIGNAL: this guard would FAIL the moment
# someone adds a numeric-threshold check to this module without also updating this register (the
# I4 shape: adding a value nobody signed, quietly, because it became convenient mid-batch).
# =====================================================================================


def test_no_unbuilt_numeric_threshold_check_has_been_added() -> None:
    """Names the four blocked sub-checks explicitly (retry cap/I4, latency magnitude, inactivity
    magnitude, clock-drift tolerance) and asserts none of them exists as a callable in this
    module. Would FAIL the moment any of the four is added without a governing value ever having
    been sourced -- forcing whoever adds one to also address this test, not silently ship past it."""
    import app.application.live_engine_c.telemetry_validation as module

    blocked_names = (
        "validate_retry_bound",
        "validate_retry_cap",
        "validate_latency_plausibility",
        "validate_latency_magnitude",
        "validate_inactivity_magnitude",
        "validate_clock_drift",
        "validate_clock_discipline_magnitude",
    )
    for name in blocked_names:
        assert not hasattr(module, name), (
            f"{name} exists but no governing document specifies its bound (see module docstring) "
            "-- this must not ship without I4 (or its sibling) being resolved first"
        )
