"""Component C Phase 7, Z5: the C0-C4 scaffold ladder, wired to a real trigger -- THROUGH THE
ADAPTER (``ScaffoldPort.decide_scaffold_level``, built and unwired since Phase 1b, called for the
first time here), never reimplemented.

SERVER DECIDES (Z5-a): this module is the ONLY place a scaffold level is decided. Nothing here
accepts a level, preference, or hint from a caller -- the request DTO carries none (verified: the
existing ``CSubmitActionRequest`` is a ``StrictModel`` with exactly one field, ``action_payload``;
extending it was explicitly out of scope and not done).

SCAFFOLD CONTENT HAS NO GOVERNED SOURCE (Z5-b, verified this phase's own planning turn): the
catalogue carries only ``allowed_scaffold_levels`` (which levels a template PERMITS, never
content), the ladder (``ladder.py``) returns a bare level string, and
``models/task_instance.py``'s own docstring says scaffolding content is "not yet owned by this
phase... not invented content." So THIS MODULE SERVES THE LEVEL ONLY -- never content -- and
mirrors ``hint_request.py:168-177``/``:242``'s fail-closed shape for the day content is wired: a
missing/invalid catalogue-side declaration must raise, be caught, and become a neutral
``ConflictError`` -- never synthesized, never a generic fallback. No such synthesis exists
anywhere in this module.

C SCAFFOLDS ARE NOT B HINTS (Z5-e): this module does not import, read, or call anything from
``app.application.hint_request`` -- verified by this file's own import list, and enforced
separately by an AST guard in ``tests/test_be2_architecture_guards.py``.
"""

from __future__ import annotations

from typing import Optional, Sequence
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.live_engine_c.session_lifecycle import _provenance
from app.domain.live_engine_c.types import ScaffoldConfig, ScaffoldDecisionContext, ScaffoldLevel
from app.infrastructure.live_engine_c.adapter import LiveEngineCAdapter
from app.infrastructure.persistence_models import CGameplayEventRecord, CScaffoldEventRecord
from app.infrastructure.repositories import CGameplayEventRecordRepository, CScaffoldEventRecordRepository


def _consecutive_incorrect(events: Sequence[CGameplayEventRecord]) -> int:
    """Trailing consecutive ``answer_evaluated`` misses on the CURRENT task opportunity, counted
    from the real, ordered persisted event stream -- never a separately-tracked counter that
    could drift from what the events actually say (same discipline C3's own summary derivation
    uses: event-derived, not independently sampled)."""
    evaluated = [e for e in events if e.event_type == "answer_evaluated"]
    count = 0
    for event in reversed(evaluated):
        is_correct = bool((event.evaluation_payload or {}).get("is_correct"))
        if is_correct:
            break
        count += 1
    return count


async def decide_and_persist_scaffold_level(
    session: AsyncSession,
    *,
    adapter: LiveEngineCAdapter,
    c_session_id: UUID,
    c_task_opportunity_id: UUID,
    c_task_instance_id: UUID,
    scaffold_config: ScaffoldConfig,
    safety_forces_recovery: bool,
    request_id: str,
    events: Optional[Sequence[CGameplayEventRecord]] = None,
) -> ScaffoldLevel:
    """Decides the scaffold level for the CURRENT task opportunity from the real, persisted
    event stream (never a caller-asserted count) and logs one ``c_scaffold_events`` row (Z5-f;
    table exists, Phase 3a -- no migration). ``safety_forces_recovery`` is caller-supplied
    (Z5-d's safety-forced path is proven directly against ``decide_scaffold_level`` in tests,
    the same test-side-construction discipline T4-d already established -- this function's own
    job is the ORDINARY escalation path, wired to real data; it does not itself assemble a full
    safety evidence/adaptation decision, which is Criterion 1's own domain, unchanged)."""
    if events is None:      # PERF-01: submit_action passes the stream it already holds under the instance lock
        events = await CGameplayEventRecordRepository(session).list_ordered_for_instance(c_task_instance_id)
    consecutive_incorrect = _consecutive_incorrect(events)
    context = ScaffoldDecisionContext(
        consecutive_incorrect_current_task=consecutive_incorrect,
        safety_forces_recovery=safety_forces_recovery,
    )
    level = adapter.decide_scaffold_level(context, scaffold_config)

    event_id = uuid4()
    scaffold_event = CScaffoldEventRecord(
        c_scaffold_event_id=event_id,
        c_session_id=c_session_id,
        c_task_opportunity_id=c_task_opportunity_id,
        # BUILDER JUDGMENT -- UNRATIFIED: this wiring decides and serves the level in the same
        # server turn, with no separate client-initiated "request" phase (Z5-a: the client never
        # chooses or asks for a level) -- "shown" is the one event_type this flow can honestly
        # log; "requested" would assert a request that never happened. c_scaffold_events'
        # event_type column carries no CHECK/enum (persistence_models.py's own disclosed
        # BUILDER JUDGMENT), so this is a value choice, not a schema change.
        event_type="shown",
        scaffold_level=level,
        consecutive_incorrect_current_task=consecutive_incorrect,
        safety_forces_recovery=safety_forces_recovery,
        **_provenance("c_scaffold_event", event_id, request_id, "c_task.scaffold_shown"),
    )
    await CScaffoldEventRecordRepository(session).add(scaffold_event)
    return level
