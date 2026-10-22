"""PERF-01: the scripted c_only session writes exactly the same rows and returns exactly the same responses as before the
round-trip reduction.

``tests/fixtures/perf01_golden_session.json`` was captured from the code BEFORE any PERF-01 change (``PERF_CAPTURE=1``). The test
plays the same 8-task scripted session (odd tasks: wrong then correct; even tasks: correct first time) through the real services
and compares, per c_* table, every row (UUID / timestamp / request-id columns excluded; UUIDs inside values are renumbered by first
appearance) and every API response body."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
from pathlib import Path

from tests.perf_scenario import run_scenario

GOLDEN = Path(__file__).parent / "fixtures" / "perf01_golden_session.json"


def _canonical(obj) -> object:
    return json.loads(json.dumps(obj, sort_keys=True, default=str))


def test_scripted_session_rows_and_responses_are_identical_to_the_pre_change_golden() -> None:
    subprocess.run(["alembic", "upgrade", "head"], check=True)
    result = asyncio.run(run_scenario(profile=False))
    produced = _canonical({"responses": result["responses"], "rows": result["rows"]})
    if os.environ.get("PERF_CAPTURE") == "1":
        GOLDEN.write_text(json.dumps(produced, indent=1, sort_keys=True), encoding="utf-8")
        print(f"\ncaptured {GOLDEN}: {len(produced['responses'])} responses, rows per table "
              f"{ {t: len(r) for t, r in produced['rows'].items()} }")
        return
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert produced["responses"] == golden["responses"]
    assert set(produced["rows"]) == set(golden["rows"])
    for table in golden["rows"]:
        assert produced["rows"][table] == golden["rows"][table], table
