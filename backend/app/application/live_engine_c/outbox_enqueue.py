"""Component C batch 9c-1b (`9c1b-work-order-v2.md`; ADDENDUM A §A0): the enqueue (write) half of
the shared outbox 9c-1a built the tables for. This module owns exactly two things -- D1, the sole
permitted writer to ``outbox_events``, and D3, the closed ``outcome`` vocabulary 9c-1a's own
docstrings recorded as an open dependency ("correct in shape and undefined in content").

**D1 -- THE GUARDED ENQUEUE ACCESSOR.** ``enqueue_outbox_event`` mirrors
``telemetry_validation.get_derivable_history_for_session`` exactly: one function, AST-proven
(``test_be2_architecture_guards.py``) that nothing else under ``app/`` constructs an
``OutboxEventRecord``. **It has ZERO real callers at the end of this batch -- deliberate, not an
oversight** (ADDENDUM A0): no payload constructor exists anywhere under ``app/`` yet (``emit_c_to_3``
is unbuilt, 9b-1), and B has no B->3 producer either (v2 §1.2, Ruling 1). Nothing becomes reachable
from a real request by this batch's own existence.

**D1's input stays ``Mapping[str, Any]`` -- approved specifically, not to be "improved" (ADDENDUM
A0, judgment 1).** Nothing in this signature prevents a caller enqueueing a payload derived from a
superseded session. That is the honest position, not an oversight papered over with invented
provenance checking. What protects condition 4 in THIS batch is that this function is unreachable
and no payload constructor exists anywhere to call it with a real aggregate's data. See Ruling 5
below for the named forward obligation that narrows this once 9b-1 lands.

**D1 refuses nothing beyond what the DB CHECKs already refuse.** ``owning_component IN ('B','C')``
and ``contract_name <> ''`` are enforced by the migration's own CHECK constraints
(``persistence_models.OutboxEventRecord.__table_args__``), not re-validated here. The
``Literal["B","C"]`` hint on ``owning_component`` is documentation for a type checker, not a runtime
gate -- the CHECK constraint remains the real backstop, the same discipline
``CTaskOpportunityVerdictRecord.validator_check`` already uses (no DB-level enum, a code-level
vocabulary instead) applied to the mirror case (a DB-level CHECK, no redundant application-level
re-check that could drift from it).

**RULING 5 -- D1's future narrowing is a NAMED FORWARD OBLIGATION**, worded so the batch that ships
``emit_c_to_3`` inherits it explicitly, quoted verbatim from ADDENDUM A: "The payload constructor
must take the session aggregate as its ONLY input, and ``enqueue_outbox_event``'s ``payload``
parameter should then narrow to that constructor's output type -- so that 'no aggregate' becomes
STRUCTURALLY 'no payload', rather than merely 'nothing sensible to build one from.'" Not done here;
recorded here because this is the module whose signature must change when it happens.

**D3 -- THE ``outcome`` VOCABULARY, RULING 3.** ``DELIVERY_OUTCOMES`` ships with exactly ONE member,
mirroring ``telemetry_validation.TelemetryValidationChecks``'s own shape (a code-level NamedTuple,
never a DB-level enum -- ``ContractDeliveryRecord.outcome`` carries only a nonblank CHECK, per its
own docstring, because "no dispatcher exists yet to define what values it may take"). ``DELIVERED``
is sourced from ``ContractDeliveryRecord``'s own docstring language, "a successful outcome" --
nothing invented. Candidates considered and EXCLUDED as unsourced: ``failed``, ``rejected``,
``retrying``, ``expired``, ``timed_out`` -- every one describes DISPATCHER behaviour (retry/backoff/
timeout are the v2 §3 prohibition itself), and no dispatcher exists in this batch, so nothing could
ever produce them. Whichever later batch builds the dispatcher adds the rest from the real error
semantics it introduces, after re-reading v2 §3's retry/backoff/timeout prohibition.

``is_delivered`` closes 9c-1a's own recorded dependency ("a successful outcome is not yet a defined
value... this derivation is correct in SHAPE but undefined in CONTENT"). "Not delivered" includes
the empty-deliveries case deliberately: until a dispatcher exists, "no row" and "no successful
delivery" are the same fact, not two different ones."""

from __future__ import annotations

from typing import Any, Iterable, Literal, Mapping, NamedTuple
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.live_engine_c.session_lifecycle import _provenance
from app.infrastructure.persistence_models import ContractDeliveryRecord, OutboxEventRecord


class _DeliveryOutcomes(NamedTuple):
    """D3/Ruling 3: the closed, code-level ``outcome`` vocabulary for ``contract_deliveries``.
    Exactly one member at this commit -- see the module docstring for the sourcing and the four
    excluded, unsourced candidates."""

    DELIVERED: str = "delivered"


DELIVERY_OUTCOMES = _DeliveryOutcomes()


def is_delivered(deliveries: Iterable[ContractDeliveryRecord]) -> bool:
    """D3: "delivered" means at least one ``ContractDeliveryRecord`` for the event carries
    ``outcome == DELIVERY_OUTCOMES.DELIVERED``. An empty ``deliveries`` iterable returns ``False``
    -- honest, since until a dispatcher exists, no row and no successful delivery are the same
    fact."""
    return any(delivery.outcome == DELIVERY_OUTCOMES.DELIVERED for delivery in deliveries)


async def enqueue_outbox_event(
    session: AsyncSession,
    *,
    owning_component: Literal["B", "C"],
    contract_name: str,
    payload: Mapping[str, Any],
    request_id: str,
) -> OutboxEventRecord:
    """D1: THE SOLE PERMITTED WRITER to ``outbox_events`` under ``app/`` -- enforced by the AST
    guard in ``test_be2_architecture_guards.py`` (D2), which flags any OTHER construction of
    ``OutboxEventRecord`` anywhere under ``app/`` (guard mechanism deviation from the
    ``list_ordered_for_session`` template, approved in ADDENDUM A0: guards the CONSTRUCTED CLASS,
    not a method name, because ``session.add`` is used by every repository and a method-name guard
    would false-positive on all of them).

    Stores the payload OPAQUELY -- this function does not construct one, route one, or attempt
    delivery (9c-1a's own docstring: "An outbox stores and delivers opaque payloads; it does not
    construct one"). Has zero real callers at the end of this batch, by design (see module
    docstring)."""
    outbox_event_id = uuid4()
    record = OutboxEventRecord(
        outbox_event_id=outbox_event_id,
        owning_component=owning_component,
        contract_name=contract_name,
        payload_json=dict(payload),
        **_provenance("outbox_event", outbox_event_id, request_id, "outbox.event_enqueued"),
    )
    session.add(record)
    await session.flush()
    return record
