"""PERF-01 benchmark: statements per Component C call, with a simulated 50 ms per statement.

Skipped unless ``PERF=1`` (it plays a whole scripted session). Run:
    docker compose run --rm --no-deps -e PERF=1 api-test python -m pytest -q -s tests/test_perf01_submit_benchmark.py
Prints, per call type, the statement count (min / median / max), the simulated time at 50 ms per statement, and the top
origins by count (innermost app/ frame, and the application-level caller)."""

from __future__ import annotations

import asyncio
import os
import statistics
import subprocess
from collections import Counter, defaultdict

import pytest

from tests.perf_scenario import run_scenario

pytestmark = [pytest.mark.perf, pytest.mark.skipif(os.environ.get("PERF") != "1", reason="set PERF=1 to run the benchmark")]

LATENCY_MS = 50.0
# PERF_LATENCY_MS=50 makes the profiler really sleep 50 ms per statement (the "measured" column); without it the table is
# computed (statements x 50 ms) and the run is fast.
REAL_SLEEP_MS = float(os.environ.get("PERF_LATENCY_MS", "0"))


def test_scripted_session_statement_counts() -> None:
    subprocess.run(["alembic", "upgrade", "head"], check=True)
    result = asyncio.run(run_scenario(latency_ms=REAL_SLEEP_MS, profile=True))
    by_label = defaultdict(list)
    for label, n, prof in result["calls"]:
        by_label[label].append((n, prof))
    print("\n=== PERF-01 benchmark: scripted c_only session, 8 tasks (odd: wrong then correct; even: correct first) ===")
    print(f"{'call':16}{'calls':>6}{'min':>6}{'median':>8}{'max':>6}   simulated @ {LATENCY_MS:.0f} ms/stmt (median)   wall time as run (median)")
    for label in ("next_task", "submit_wrong", "submit_correct"):
        ns = [n for n, _ in by_label[label]]
        if not ns:
            continue
        print(f"{label:16}{len(ns):>6}{min(ns):>6}{int(statistics.median(ns)):>8}{max(ns):>6}   {statistics.median(ns) * LATENCY_MS:7.0f} ms          {statistics.median(p.elapsed_ms for _, p in by_label[label]):6.0f} ms")
    for label in ("submit_correct", "submit_wrong", "next_task"):
        if not by_label[label]:
            continue
        origin, caller, kind = Counter(), Counter(), Counter()
        for _, prof in by_label[label]:
            for stmt, o, c in prof.statements:
                origin[o] += 1; caller[c] += 1; kind[stmt[:60]] += 1
        k = len(by_label[label])
        print(f"\n-- {label}: top origins per call (innermost app frame), averaged over {k} calls")
        for o, n in origin.most_common(14):
            print(f"   {n / k:5.2f}  {o}")
        print(f"-- {label}: top application-level callers")
        for o, n in caller.most_common(10):
            print(f"   {n / k:5.2f}  {o}")
        print(f"-- {label}: top statements")
        for o, n in kind.most_common(14):
            print(f"   {n / k:5.2f}  {o}")


def test_ordered_trace_of_one_call_of_each_type() -> None:
    """Prints the statements of one call of each type IN ORDER with the application-level caller, to plan reductions."""
    subprocess.run(["alembic", "upgrade", "head"], check=True)
    result = asyncio.run(run_scenario(latency_ms=0.0, profile=True))
    seen = set()
    for label, n, prof in result["calls"]:
        if label in seen or (label == "submit_correct" and len(seen) < 1):
            continue
        if label == "submit_correct" and "next_task" not in seen:
            continue
        seen.add(label)
        print(f"\n=== ordered statements of one {label} ({n}) ===")
        for i, (stmt, origin, caller) in enumerate(prof.statements, 1):
            print(f"{i:2d} {stmt[:75]:75s} {caller:48s} {origin}")
