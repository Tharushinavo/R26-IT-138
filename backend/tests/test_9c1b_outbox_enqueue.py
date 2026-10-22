"""Component C batch 9c-1b (`9c1b-work-order-v2.md`; ADDENDUM A): D4's condition-4 proof extending
``test_batch4_verdict_supersession.py:453/:498`` by one link, plus the four constraint-level tests
9c-1a's ``outbox_events``/``contract_deliveries`` tables never got.

**D4's honest limit, stated here rather than glossed (v2 §5).** The chain
``no aggregate -> no payload -> nothing enqueued`` cannot be closed end-to-end in this batch: the
C->3 payload constructor does not exist yet (``emit_c_to_3`` is unbuilt, blocked on 9b-0/9b-1). This
file proves ``superseded -> no aggregate -> nothing to enqueue`` (the refusing arm) and its
discrimination pair (the identical fixture minus the supersession, reaching the point an enqueue
WOULD occur -- the aggregate row exists). It does **not** and cannot prove ``no aggregate -> no
payload``, because there is no payload constructor to prove that about yet.

**D4's discrimination arm stops before calling D1 -- approved specifically (ADDENDUM A0, judgment
2).** Calling ``enqueue_outbox_event`` with a hand-built dict would prove nothing: a dict
constructed in a test is not the aggregate, and asserting D1 "would accept it" is a vacuous
positive. The discrimination arm asserts the aggregate row EXISTS and stops there.

Reuses ``test_batch4_verdict_supersession.py``'s own fixture helpers by import (per ADDENDUM A0:
"do not duplicate fixture logic")."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.application.live_engine_c import aggregation_service
from app.application.live_engine_c.outbox_enqueue import (
    DELIVERY_OUTCOMES,
    enqueue_outbox_event,
    is_delivered,
)
from app.infrastructure.persistence_models import (
    ContractDeliveryRecord,
    CSessionAggregateResultRecord,
    CTaskOpportunityVerdictRecord,
    OutboxEventRecord,
)
from app.application.live_engine_c.telemetry_validation import TELEMETRY_VALIDATION_CHECKS
from tests.test_c4_session_lifecycle import isolated_database, provenance
from tests.test_c5_task_serve_and_evaluate import alembic
from tests.test_batch4_verdict_supersession import (
    _aggregate_for,
    _build_two_real_completed_tasks,
)
from app.domain.live_engine_c.errors import DistrustedHistoryGapError


# =====================================================================================
# D4 -- the C-side condition-4 proof, extending test_batch4_verdict_supersession.py:453/:498 by
# one link: superseded fixture -> aggregation refuses -> NO aggregate row exists -> the enqueue
# accessor therefore has nothing to enqueue. The signal is the REFUSAL, not an empty table (v2 §5:
# "A test that merely observes outbox_events is empty proves nothing, because it is empty in both
# arms until something writes.").
# =====================================================================================


def test_superseded_session_refuses_and_leaves_no_aggregate_row_to_enqueue_from(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """THE REFUSING ARM. Byte-identical fixture to
    ``test_negative_control_superseded_summary_refuses_through_real_adaptation_and_aggregation_chains``
    (imported, not duplicated): a live verdict supersedes task 1's summary. Asserts (1) the REAL
    aggregation chain raises ``DistrustedHistoryGapError`` -- the refusal itself is the signal --
    and (2) no ``CSessionAggregateResultRecord`` row exists in this same transaction afterward, so
    D1's enqueue accessor has nothing to build a payload from. Never calls
    ``enqueue_outbox_event`` -- there is no aggregate for it to be called with."""
    alembic("upgrade", "head")
    monkeypatch.setattr(aggregation_service, "_AGGREGATION_INPUTS_AVAILABLE", True)

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            c_session_id, instance1_id, _instance2_id, student_id, _s1, _s2 = (
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
                    verdict_detail="9c-1b D4 -- task 1's summary is now superseded",
                    supersedes_verdict_id=None,
                    **provenance("c_task_opportunity_verdict", verdict_id),
                )
            )
            await session.flush()

            # THE SIGNAL: the real aggregation chain refuses.
            with pytest.raises(DistrustedHistoryGapError):
                await _aggregate_for(session, c_session_id=c_session_id, student_id=student_id)

            # No aggregate row exists -- there is nothing for the enqueue accessor to build a
            # payload from. This is corroborating, not the signal itself (v2 §5).
            result = await session.execute(
                CSessionAggregateResultRecord.__table__.select().where(
                    CSessionAggregateResultRecord.c_session_id == c_session_id
                )
            )
            assert result.first() is None
        await database_engine.dispose()

    asyncio.run(exercise())


def test_discrimination_pair_identical_fixture_minus_supersession_reaches_enqueue_point(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """THE DISCRIMINATION PAIR. The identical fixture, MINUS the supersession row above -- proves
    the refusing arm's refusal was caused by the supersession, not some other property of the
    fixture (same discipline as ``test_negative_control_identical_fixture_minus_supersession_...``,
    imported/reused rather than duplicated). Stops at asserting the aggregate row EXISTS --
    ADDENDUM A0 judgment 2: calling ``enqueue_outbox_event`` with a hand-built dict here would
    prove nothing, since a dict built in a test is not the aggregate."""
    alembic("upgrade", "head")
    monkeypatch.setattr(aggregation_service, "_AGGREGATION_INPUTS_AVAILABLE", True)

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            c_session_id, _instance1_id, _instance2_id, student_id, _s1, _s2 = (
                await _build_two_real_completed_tasks(session)
            )
            # No verdict row inserted -- otherwise byte-identical to the refusing arm above.

            record = await _aggregate_for(session, c_session_id=c_session_id, student_id=student_id)
            assert record.c_session_id == c_session_id

            result = await session.execute(
                CSessionAggregateResultRecord.__table__.select().where(
                    CSessionAggregateResultRecord.c_session_id == c_session_id
                )
            )
            # The aggregate row EXISTS -- this is the point an enqueue WOULD occur, once a
            # payload constructor exists (9b-1, not this batch). Stops here, per ADDENDUM A0
            # judgment 2 -- enqueue_outbox_event is never called with a hand-built dict.
            assert result.first() is not None
        await database_engine.dispose()

    asyncio.run(exercise())


# =====================================================================================
# D1 functional smoke test -- proves the sole writer actually writes a valid row (not merely that
# the AST guard sees a call to it). Zero real callers elsewhere in this batch, per design.
# =====================================================================================


def test_enqueue_outbox_event_writes_a_valid_row() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            record = await enqueue_outbox_event(
                session,
                owning_component="C",
                contract_name="c_to_3",
                payload={"example": "opaque-payload-not-a-real-contract"},
                request_id=f"test-{uuid4()}",
            )
            assert record.owning_component == "C"
            assert record.contract_name == "c_to_3"
            assert record.payload_json == {"example": "opaque-payload-not-a-real-contract"}

            # D3: no deliveries yet -- "no row" and "no successful delivery" are the same fact.
            assert is_delivered([]) is False
            delivery = ContractDeliveryRecord(
                contract_delivery_id=uuid4(),
                outbox_event_id=record.outbox_event_id,
                outcome=DELIVERY_OUTCOMES.DELIVERED,
                delivery_detail=None,
                **provenance("contract_delivery", record.outbox_event_id),
            )
            assert is_delivered([delivery]) is True
        await database_engine.dispose()

    asyncio.run(exercise())


# =====================================================================================
# 9c-1a constraint tests -- IN SCOPE, minimally (v2 §4, "Constraint-level tests for 9c-1a's
# tables"). 9c-1a's CHECKs/FK/nullability were verified once by a manual migration run pytest
# cannot repeat; D1 makes outbox_events writable for the first time, so this batch is the first
# that can exercise them honestly. Each test provokes exactly the value the CHECK/FK forbids, via
# pytest.raises(IntegrityError) on session.flush() -- the same idiom
# test_batch4_verdict_supersession.py:380 already uses.
# =====================================================================================


def test_outbox_events_owning_component_check_rejects_a_value_outside_b_or_c() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            event_id = uuid4()
            session.add(
                OutboxEventRecord(
                    outbox_event_id=event_id,
                    owning_component="X",  # forbidden -- CHECK allows only 'B' or 'C'
                    contract_name="c_to_3",
                    payload_json={},
                    **provenance("outbox_event", event_id),
                )
            )
            with pytest.raises(IntegrityError):
                await session.flush()
        await database_engine.dispose()

    asyncio.run(exercise())


def test_contract_deliveries_outcome_check_rejects_empty_string() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            event_id = uuid4()
            session.add(
                OutboxEventRecord(
                    outbox_event_id=event_id,
                    owning_component="C",
                    contract_name="c_to_3",
                    payload_json={},
                    **provenance("outbox_event", event_id),
                )
            )
            await session.flush()

            session.add(
                ContractDeliveryRecord(
                    contract_delivery_id=uuid4(),
                    outbox_event_id=event_id,
                    outcome="",  # forbidden -- CHECK requires outcome <> ''
                    delivery_detail=None,
                    **provenance("contract_delivery", event_id),
                )
            )
            with pytest.raises(IntegrityError):
                await session.flush()
        await database_engine.dispose()

    asyncio.run(exercise())


def test_contract_deliveries_delivery_detail_check_rejects_empty_string() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            event_id = uuid4()
            session.add(
                OutboxEventRecord(
                    outbox_event_id=event_id,
                    owning_component="C",
                    contract_name="c_to_3",
                    payload_json={},
                    **provenance("outbox_event", event_id),
                )
            )
            await session.flush()

            session.add(
                ContractDeliveryRecord(
                    contract_delivery_id=uuid4(),
                    outbox_event_id=event_id,
                    outcome=DELIVERY_OUTCOMES.DELIVERED,
                    delivery_detail="",  # forbidden -- CHECK requires NULL or <> ''
                    **provenance("contract_delivery", event_id),
                )
            )
            with pytest.raises(IntegrityError):
                await session.flush()
        await database_engine.dispose()

    asyncio.run(exercise())


def test_contract_deliveries_outbox_event_id_fk_rejects_an_orphan() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            orphan_event_id = uuid4()  # never inserted into outbox_events
            session.add(
                ContractDeliveryRecord(
                    contract_delivery_id=uuid4(),
                    outbox_event_id=orphan_event_id,
                    outcome=DELIVERY_OUTCOMES.DELIVERED,
                    delivery_detail=None,
                    **provenance("contract_delivery", orphan_event_id),
                )
            )
            with pytest.raises(IntegrityError):
                await session.flush()
        await database_engine.dispose()

    asyncio.run(exercise())
