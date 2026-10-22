"""Component C difficulty progression -- the loop ``buildLog2.md``'s 2026-10-10 entry recorded as
open, now closed.

WHAT WAS BROKEN. The adaptation policy decided a ``difficulty_after`` after every answered task
and persisted it; nothing ever read it back. ``select_task`` has no current-difficulty parameter
(asserted structurally below against the installed wheel, not read from a doc), so every task was
built at ``SelectionResult.initial_difficulty_level`` -- in ``c_only`` always
``fallback_difficulty_level``, i.e. 1. The policy's own evidence then reported "currently 1"
forever, because that evidence reads the previous INSTANCE's level. On the dev database that
produced 35 decisions of ``1 -> 2`` against 112 instances all at level 1.

WHAT THIS FILE PROVES. Three things, in increasing strength:
  1. the first task of a session still takes ``select_task``'s own level (nothing invented);
  2. a task minted after a ``difficulty_after = 2`` decision is BUILT at 2, and the opportunity
     row records 2 -- the behavioural proof the circle is closed;
  3. no escalation arithmetic lives in ``task_service`` at all -- the owner constraint. The level
     is carried, never computed. If someone later adds a step/clamp/cap in app code, test 3 fails
     and points here.

Test 2 deliberately drives the REAL path: a real session, a real ``next_task``, a real terminal
event stream (so the resume-instead-of-mint path correctly finds nothing to resume), and a real
persisted ``CPolicyDecisionRecord``. The only hand-built object is that decision row, which stands
in for the policy's own output -- its VALUE is what this test varies, so building it by hand is the
subject of the test rather than a shortcut around it.
"""

from __future__ import annotations

import asyncio
import inspect
from uuid import uuid4

from sqlalchemy import select

from app.application.live_engine_c.task_service import TaskService
from app.infrastructure.live_engine_c.adapter import LiveEngineCAdapter
from app.infrastructure.persistence_models import (
    CGameplayEventRecord,
    CPolicyDecisionRecord,
    CTaskInstanceRecord,
    CTaskOpportunityRecord,
)
from tests.test_c4_session_lifecycle import isolated_database, provenance
from tests.test_c5_task_serve_and_evaluate import (
    alembic,
    generation_config_fixture_for_tests,
    seed_active_session,
)


async def _terminate(session, *, c_session_id, instance_id, task_index) -> None:
    """A minimal but REAL terminal event, so ``has_terminal_for_instance`` finds one and the next
    ``next_task`` call takes the mint path instead of resuming. Same record shape
    ``test_batch4_verdict_supersession.py`` already writes.

    ``event_index=2`` because ``next_task`` itself already wrote index 1 (``game_task_offered``)
    and the table carries a CHECK that indices are consecutive from 1 within a task -- a real
    invariant this fixture has to respect, not a detail to work around."""
    event_id = uuid4()
    session.add(
        CGameplayEventRecord(
            c_gameplay_event_id=event_id,
            c_session_id=c_session_id,
            game_task_instance_id=instance_id,
            task_index=task_index,
            event_type="game_task_completed",
            event_index=2,
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
            **provenance("c_gameplay_event", event_id),
        )
    )
    await session.flush()


async def _persist_decision(session, *, c_session_id, opportunity_id, before, after) -> None:
    """Stands in for the policy's own persisted output. Everything except ``difficulty_before`` /
    ``difficulty_after`` mirrors ``test_c3a_persistence.py``'s own round-trip row verbatim."""
    decision_id = uuid4()
    session.add(
        CPolicyDecisionRecord(
            c_policy_decision_id=decision_id,
            c_session_id=c_session_id,
            c_task_opportunity_id=opportunity_id,
            policy_mode="rule_based_baseline",
            policy_version="1.0.0",
            rl_state=None,
            selected_action="increase_difficulty",
            applied_action="increase_difficulty",
            action_overridden=False,
            safety_reason=None,
            difficulty_before=before,
            difficulty_after=after,
            rolling_strain_bucket="low",
            session_start_state_bucket=None,
            increase_block_remaining=0,
            internal_reward=None,
            seed_lineage_global_seed=1,
            seed_lineage_path=[],
            seed_lineage_seed=1,
            evidence_snapshot={"current_difficulty_level": before},
            safety_forces_recovery=False,
            **provenance("c_policy_decision", decision_id),
        )
    )
    await session.flush()


async def _opportunity_for(session, *, c_session_id, task_index):
    return await session.scalar(
        select(CTaskOpportunityRecord).where(
            CTaskOpportunityRecord.c_session_id == c_session_id,
            CTaskOpportunityRecord.task_index == task_index,
        )
    )


def test_first_task_of_a_session_keeps_select_tasks_own_level() -> None:
    """No decision exists yet, so there is nothing to carry and nothing is invented: the level is
    whatever the engine chose. In ``c_only`` the approved bundle makes that
    ``fallback_difficulty_level``, which is 1 -- asserted as "equals what the opportunity row
    recorded", not as a hardcoded 1, so this stays true if the bundle's fallback ever changes."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            subject = f"cdiff-first-{uuid4()}"
            _student_id, c_session_id = await seed_active_session(
                session, session_mode="c_only", subject=subject
            )
            response = await TaskService().next_task(
                session,
                principal_user_id=subject,
                request_id=f"req-{uuid4()}",
                c_session_id=c_session_id,
                generation_config=generation_config_fixture_for_tests(),
                smoke_mode=True,
            )
            await session.flush()

            opportunity = await _opportunity_for(session, c_session_id=c_session_id, task_index=1)
            assert opportunity is not None
            # The response, the instance row and the opportunity row all agree -- no divergence
            # between what the child was served and what was recorded.
            assert response.difficulty_level == opportunity.initial_difficulty_level
            instance = await session.get(CTaskInstanceRecord, response.c_task_instance_id)
            assert instance is not None
            assert instance.difficulty_level == response.difficulty_level
        await database_engine.dispose()

    asyncio.run(exercise())


def test_next_task_is_built_at_the_most_recent_decisions_difficulty_after() -> None:
    """THE BEHAVIOURAL PROOF. Task 1 is served and terminated, a decision of ``1 -> 2`` is
    persisted, and task 2 is then minted through the real ``next_task``. Task 2 must be BUILT at
    2 -- which is exactly what never happened before this batch (112 instances, all level 1,
    against 35 decisions that said go to 2)."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            subject = f"cdiff-carry-{uuid4()}"
            _student_id, c_session_id = await seed_active_session(
                session, session_mode="c_only", subject=subject
            )
            first = await TaskService().next_task(
                session,
                principal_user_id=subject,
                request_id=f"req-{uuid4()}",
                c_session_id=c_session_id,
                generation_config=generation_config_fixture_for_tests(),
                smoke_mode=True,
            )
            await session.flush()
            first_opportunity = await _opportunity_for(session, c_session_id=c_session_id, task_index=1)
            assert first_opportunity is not None

            await _terminate(
                session, c_session_id=c_session_id, instance_id=first.c_task_instance_id, task_index=1
            )
            carried_to = first.difficulty_level + 1
            await _persist_decision(
                session,
                c_session_id=c_session_id,
                opportunity_id=first_opportunity.c_task_opportunity_id,
                before=first.difficulty_level,
                after=carried_to,
            )

            second = await TaskService().next_task(
                session,
                principal_user_id=subject,
                request_id=f"req-{uuid4()}",
                c_session_id=c_session_id,
                generation_config=generation_config_fixture_for_tests(),
                smoke_mode=True,
            )
            await session.flush()

            # It really is a new task, not a resume -- otherwise the level assertion below would
            # pass for the wrong reason.
            assert second.c_task_instance_id != first.c_task_instance_id
            assert second.task_index == 2

            assert second.difficulty_level == carried_to, (
                "the next task must be built at the most recent decision's difficulty_after; "
                f"expected {carried_to}, served {second.difficulty_level}"
            )

            # The audit trail agrees with what the child met, on both rows.
            second_opportunity = await _opportunity_for(session, c_session_id=c_session_id, task_index=2)
            assert second_opportunity is not None
            assert second_opportunity.initial_difficulty_level == carried_to
            second_instance = await session.get(CTaskInstanceRecord, second.c_task_instance_id)
            assert second_instance is not None
            assert second_instance.difficulty_level == carried_to

            # And the carry preserved the engine's own selection -- only difficulty moved.
            assert second_opportunity.selected_template_id == second_instance.game_task_template_id
        await database_engine.dispose()

    asyncio.run(exercise())


def test_no_escalation_arithmetic_lives_in_task_service() -> None:
    """OWNER CONSTRAINT, enforced structurally: ``task_service`` carries the engine's already-
    clamped ``difficulty_after`` and performs no arithmetic of its own. The safety controller has
    already computed ``clamp(target, floor, ceiling)`` with the session mode's cap applied; a
    step, floor or cap added here would be the orchestration layer implementing adaptive science.

    Narrow by construction: this looks for arithmetic or clamping APPLIED TO a difficulty
    expression, so ordinary unrelated code in the same method cannot trip it."""
    import app.application.live_engine_c.task_service as task_service_module

    raw = inspect.getsource(task_service_module.TaskService.next_task)
    # CODE ONLY. Comments in this method legitimately DISCUSS clamping -- they explain that the
    # engine does it and this layer must not -- so scanning the raw text would flag the very
    # reasoning that documents the constraint. Strip whole-line comments before matching.
    source = "\n".join(
        line for line in raw.splitlines() if not line.lstrip().startswith("#")
    )

    forbidden = [
        "difficulty_level + ",
        "difficulty_level - ",
        "difficulty_after + ",
        "difficulty_after - ",
        "min(carried",
        "max(carried",
        "clamp(",
    ]
    for fragment in forbidden:
        assert fragment not in source, f"escalation arithmetic in next_task: {fragment!r}"

    # The carry itself must still be present, read through the established repository method --
    # so this test cannot pass by the feature simply having been deleted.
    assert "most_recent_for_session" in source
    assert "difficulty_after" in source

    # And the engine still owns the decision: its selector takes no current-difficulty parameter,
    # which is WHY the carry has to happen at construction time.
    assert "current_difficulty_level" not in set(
        inspect.signature(LiveEngineCAdapter.select_task).parameters
    )


def test_the_rejection_bounds_are_the_engines_own_declared_domain() -> None:
    """``task_service``'s difficulty bounds must not be numbers someone picked -- they are the
    engine's own annotations, read here off the INSTALLED wheel so a wheel bump that widened or
    narrowed the domain breaks this test instead of silently disagreeing with production.

    Also pins the direction of the guard: out-of-domain values are DISCARDED in favour of the
    level the engine just selected, never clamped into range, because clamping would invent a
    level no policy chose."""
    from annotated_types import Ge, Le
    from component_c_generator.models.adaptation import CPolicyObservableEvidence
    from component_c_generator.selection.selector import SelectionResult

    import app.application.live_engine_c.task_service as task_service_module

    def bounds(model, field):
        meta = model.model_fields[field].metadata
        low = next(m.ge for m in meta if isinstance(m, Ge))
        high = next(m.le for m in meta if isinstance(m, Le))
        return low, high

    engine_bounds = bounds(SelectionResult, "initial_difficulty_level")
    assert engine_bounds == bounds(CPolicyObservableEvidence, "current_difficulty_level"), (
        "the engine's selection and evidence models disagree about the difficulty domain"
    )
    assert engine_bounds == (
        task_service_module._ENGINE_DIFFICULTY_MIN,
        task_service_module._ENGINE_DIFFICULTY_MAX,
    ), "task_service's difficulty bounds have drifted from the engine's own annotations"

    # The guard rejects; it does not clamp. (Comments stripped: the reasoning legitimately
    # discusses clamping in order to rule it out.)
    raw = inspect.getsource(task_service_module.TaskService.next_task)
    code = "\n".join(line for line in raw.splitlines() if not line.lstrip().startswith("#"))
    assert "carried_difficulty_level = result.initial_difficulty_level" in code
    assert "min(" not in code and "max(" not in code
