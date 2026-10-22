"""PERF-01: a scripted c_only session through the real services (``TaskService.next_task`` / ``submit_action``), shared by the
benchmark (``test_perf01_submit_benchmark.py``, ``PERF=1``) and the row-equivalence test (``test_perf01_row_equivalence.py``).

Each service call gets its OWN database session and is committed afterwards, exactly like the route handlers do (a fresh
identity map per request, so repeated reads inside one request are visible and reads across requests are not hidden).
Statements are counted only inside the service call, never in the scenario's own bookkeeping reads.
"""

from __future__ import annotations

import re
import time
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.types import DateTime

from app.application.live_engine_c.task_service import PRODUCTION_GENERATION_CONFIG, PRODUCTION_SCAFFOLD_CONFIG, TaskService
from app.infrastructure.live_engine_c.adapter import LiveEngineCAdapter
from app.infrastructure import persistence_models as pm
from tests.perf_helpers import QueryProfile
from tests.test_c4_session_lifecycle import isolated_database
from tests.test_c5_task_serve_and_evaluate import generation_config_fixture_for_tests, seed_active_session

TASKS = 8        # odd tasks: a wrong first attempt, then correct; even tasks: correct first time

C_TABLES = [
    pm.CTaskOpportunityRecord, pm.CTaskInstanceRecord, pm.CGameplayEventRecord, pm.CTaskOpportunitySummaryRecord,
    pm.CPolicyDecisionRecord, pm.CSafetyEventRecord, pm.CScaffoldEventRecord, pm.CTaskOpportunityVerdictRecord,
]


def _wrong_value(declared_type: str):
    if "|" in declared_type:
        options = declared_type.split("|")
        return options[-1] if len(options) > 1 else options[0] + "_wrong"
    if declared_type in ("int", "number"):
        return -999999
    if declared_type == "bool":
        return True
    if declared_type.startswith("list["):
        return []
    raise AssertionError(declared_type)


async def _payloads_for(factory, instance_id: UUID) -> tuple[Optional[dict], dict]:
    """(a payload the evaluator accepts as correct, or None; a payload it rejects) for a persisted instance."""
    from app.application.live_engine_c.task_service import _stu_session_id, _to_domain_task_instance
    from app.application.live_engine_c.mastery_fixture import FIXTURE_MASTERY_SOURCE_STUDENT_ID

    async with factory() as s:
        rec = await s.get(pm.CTaskInstanceRecord, instance_id)
        domain = _to_domain_task_instance(rec, student_id=FIXTURE_MASTERY_SOURCE_STUDENT_ID, c_session_id=_stu_session_id())
        adapter = LiveEngineCAdapter()
        space = dict(rec.valid_action_space)
        wrong = {k: _wrong_value(t) for k, t in space.items()}
        candidates = [{k: v for k, v in rec.correct_answer_payload.items() if k in space}, dict(rec.correct_answer_payload)]
        cap = rec.correct_answer_payload
        if {"jumps", "final_position"} <= set(space) and {"jump_unit", "expected_jump_count", "sum"} <= set(cap):
            candidates.append({"jumps": [cap["jump_unit"]] * cap["expected_jump_count"], "final_position": cap["sum"]})
        values = list(rec.correct_answer_payload.values())
        keys = list(space)
        if len(keys) == 1:                       # the action key and the answer key are named differently in some templates
            candidates += [{keys[0]: v} for v in values]
        elif len(keys) == len(values):           # same order
            candidates.append(dict(zip(keys, values)))
        correct = next((c for c in candidates if c and adapter.evaluate(domain, c).is_correct), None)
        if correct is None:                      # brute force over the declared space (small int ranges / choices / bools)
            import itertools

            def options(t: str):
                if "|" in t:
                    return t.split("|")
                return list(range(0, 31)) if t in ("int", "number") else ([True, False] if t == "bool" else [])

            pools = [options(t) for t in space.values()]
            if all(pools):
                for combo in itertools.product(*pools):
                    cand = dict(zip(space, combo))
                    if adapter.evaluate(domain, cand).is_correct:
                        correct = cand
                        break
        if adapter.evaluate(domain, wrong).is_correct:
            wrong = {}
        return correct, wrong


_UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def normalise(obj: Any, seen: dict) -> Any:
    """Replace every UUID-looking string by a stable placeholder numbered by first appearance."""
    if isinstance(obj, dict):
        return {k: normalise(v, seen) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [normalise(v, seen) for v in obj]
    if isinstance(obj, str) and _UUID_RE.search(obj):
        return _UUID_RE.sub(lambda m: seen.setdefault(m.group(0), f"<uuid-{len(seen) + 1}>"), obj)
    if isinstance(obj, UUID):
        return normalise(str(obj), seen)
    return obj


async def dump_rows(factory, c_session_id: UUID) -> dict:
    """Every row written for the session to every c_* table, without UUID / datetime / request-id columns."""
    out: dict[str, list] = {}
    async with factory() as s:
        opp_ids = [r.c_task_opportunity_id for r in (await s.scalars(
            select(pm.CTaskOpportunityRecord).where(pm.CTaskOpportunityRecord.c_session_id == c_session_id))).all()]
        for model in C_TABLES:
            cols = sa_inspect(model).columns
            if "c_session_id" in cols:
                stmt = select(model).where(model.c_session_id == c_session_id)
            elif "c_task_opportunity_id" in cols:
                stmt = select(model).where(model.c_task_opportunity_id.in_(opp_ids))
            else:
                continue
            rows = []
            for rec in (await s.scalars(stmt)).all():
                row = {}
                for c in cols:
                    if isinstance(c.type, (PGUUID, DateTime)) or c.name in ("request_id", "created_at_utc", "updated_at_utc"):
                        continue
                    if "uuid" in str(c.type).lower():
                        continue
                    row[c.name] = getattr(rec, c.name)
                rows.append(row)
            rows.sort(key=lambda r: repr(sorted((k, repr(v)) for k, v in r.items())))
            out[model.__tablename__] = rows
    return out


async def run_scenario(latency_ms: float = 0.0, profile: bool = True) -> dict:
    """Returns {"calls": [(label, n_statements, profile)], "responses": [...], "rows": {...}}."""
    engine, factory = isolated_database()
    calls, responses = [], []
    async with factory() as seed_session:
        subject = f"perf01-{uuid4()}"
        _student, c_session_id = await seed_active_session(seed_session, session_mode="c_only", subject=subject)
        await seed_session.commit()

    async def call(label: str, coro_factory):
        prof = QueryProfile(engine, latency_ms=latency_ms)
        t0 = time.perf_counter()
        async with factory() as s:
            if profile:
                with prof:
                    result = await coro_factory(s)
                    await s.commit()
            else:
                result = await coro_factory(s)
                await s.commit()
        prof.elapsed_ms = (time.perf_counter() - t0) * 1000.0
        calls.append((label, prof.count, prof))
        return result

    service = TaskService()
    for k in range(1, TASKS + 1):
        task = await call("next_task", lambda s: service.next_task(
            s, principal_user_id=subject, request_id=f"req-{uuid4()}", c_session_id=c_session_id,
            generation_config=generation_config_fixture_for_tests(), smoke_mode=True))
        responses.append(task.model_dump(mode="json"))
        correct, wrong = await _payloads_for(factory, task.c_task_instance_id)
        assert correct is not None, f"scenario cannot answer task {k} ({task.game_task_template_id}) correctly"
        script = ([("submit_wrong", wrong)] if (k % 2 == 1 and wrong) else []) + [("submit_correct", correct)]
        for label, payload in script:
            res = await call(label, lambda s, payload=payload: service.submit_action(
                s, principal_user_id=subject, request_id=f"req-{uuid4()}", c_session_id=c_session_id,
                c_task_instance_id=task.c_task_instance_id, action_payload=payload,
                generation_config=PRODUCTION_GENERATION_CONFIG, scaffold_config=PRODUCTION_SCAFFOLD_CONFIG))
            responses.append(res.model_dump(mode="json"))
    rows = await dump_rows(factory, c_session_id)
    await engine.dispose()
    seen: dict = {}
    return {"calls": calls, "responses": normalise(responses, seen), "rows": normalise(rows, seen)}
