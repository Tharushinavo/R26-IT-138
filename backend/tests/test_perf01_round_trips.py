"""PERF-01 regression guards (run in the normal suite): the per-call statement budget of the Component C services, and the
per-process cache of the (immutable, file-based) runtime bundle + catalogue resolution.

The budgets are the measured post-change counts for the scripted c_only session (see test_perf01_submit_benchmark.py) plus one
statement of slack; before PERF-01 the same calls cost 11 (next_task), 14 (wrong submit) and 24 (correct submit)."""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path

import pytest

from app.application.live_engine_c import bundle_resolution as br
from app.core.errors import ConflictError
from tests.perf_scenario import run_scenario

BUNDLE, SCHEMA = "provenance/c-runtime-bundle-approved-1.0.json", "provenance/c-runtime-bundle.schema.json"
CATALOGUE = "provenance/R26-IT-138_Component_C_Game_Task_Catalogue_v1.0.md"


def test_statement_budget_per_call_type() -> None:
    subprocess.run(["alembic", "upgrade", "head"], check=True)
    result = asyncio.run(run_scenario(profile=True))
    worst = defaultdict(int)
    for label, n, _ in result["calls"]:
        worst[label] = max(worst[label], n)
    assert worst["submit_correct"] <= 12, dict(worst)      # was 24-25
    assert worst["submit_wrong"] <= 7, dict(worst)         # was 14
    assert worst["next_task"] <= 10, dict(worst)           # was 10-11


def test_bundle_resolution_is_cached_per_process_and_revalidated_when_a_file_changes(tmp_path: Path) -> None:
    br.clear_resolution_cache()
    first = br.resolve_c_bundle_and_catalogue(bundle_path=BUNDLE, schema_path=SCHEMA, catalogue_path=CATALOGUE, require_approved=False)
    second = br.resolve_c_bundle_and_catalogue(bundle_path=BUNDLE, schema_path=SCHEMA, catalogue_path=CATALOGUE, require_approved=False)
    assert second is first                                                    # cached: the same validated result object

    # a copy of the inputs: touching a file changes its fingerprint, so the next call validates from scratch (new object)
    for name in (BUNDLE, SCHEMA, CATALOGUE):
        (tmp_path / Path(name).name).write_bytes(Path(name).read_bytes())
    args = dict(bundle_path=str(tmp_path / Path(BUNDLE).name), schema_path=str(tmp_path / Path(SCHEMA).name),
                catalogue_path=str(tmp_path / Path(CATALOGUE).name), require_approved=False)
    one = br.resolve_c_bundle_and_catalogue(**args)
    assert br.resolve_c_bundle_and_catalogue(**args) is one
    cat = tmp_path / Path(CATALOGUE).name
    cat.write_bytes(cat.read_bytes() + b"\n")                                  # tampered catalogue: checksum no longer matches
    with pytest.raises(ConflictError):
        br.resolve_c_bundle_and_catalogue(**args)                              # fails closed, not served from the cache
    cat.write_bytes(Path(CATALOGUE).read_bytes())                              # restored
    os.utime(cat, None)
    assert br.resolve_c_bundle_and_catalogue(**args) is not one                # re-validated, then cached again


def test_a_failed_resolution_is_never_cached(tmp_path: Path) -> None:
    br.clear_resolution_cache()
    missing = dict(bundle_path=str(tmp_path / "nope.json"), schema_path=SCHEMA, catalogue_path=CATALOGUE, require_approved=False)
    for _ in range(2):
        with pytest.raises(ConflictError):
            br.resolve_c_bundle_and_catalogue(**missing)
    assert not br._RESOLUTION_CACHE
