"""LIVE-01: the frozen Q-learning policy replaces the rule policy in production (Q proposes, safety disposes).

Covers the artifact layer (``app.application.live_engine_c.q_policy``): golden vectors from the RL notebooks,
bucket edges, the allowed-set / tie-break / minimum-task rules, hash-verification and fail-closed behaviour,
the session-start gate for the new ``q_policy_config`` family, and an end-to-end submission that persists a
``frozen_q_evaluation`` row carrying the artifact hash. The adapter-level checks (safety still wins, the
composed decision equals the pinned rule path field-for-field) are in ``test_live01_q_adapter.py``.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

import pytest

from app.application.live_engine_c import q_policy as q_policy_module
from app.application.live_engine_c.q_policy import (
    ACTIONS,
    C_POLICY_DIR,
    QPolicyArtifactError,
    clear_cache,
    load_q_policy,
    state_of,
)
from app.domain.live_engine_c.errors import ConfigurationFamilyNotUsableError


def alembic(*args: str) -> None:
    subprocess.run(["alembic", *args], check=True)


@pytest.fixture(autouse=True)
def _fresh_cache():
    clear_cache()
    yield
    clear_cache()


GOLDEN = json.loads((C_POLICY_DIR / "golden_vectors.json").read_bytes())
MANIFEST = json.loads((C_POLICY_DIR / "MANIFEST.json").read_bytes())
MODE_OF = {"q_c_only": "c_only", "q_main": "combined"}


# ---- artifact integrity ---------------------------------------------------------------------------------


def test_manifest_hashes_match_the_files_on_disk() -> None:
    for name, entry in MANIFEST["artifacts"].items():
        assert hashlib.sha256((C_POLICY_DIR / entry["file"]).read_bytes()).hexdigest() == entry["sha256"], name
    assert hashlib.sha256((C_POLICY_DIR / "golden_vectors.json").read_bytes()).hexdigest() == MANIFEST["golden_vectors"]["sha256"]


def test_loaded_policy_carries_the_manifest_hash_and_status() -> None:
    for name, mode in MODE_OF.items():
        policy = load_q_policy(mode)
        assert policy.artifact_sha256 == MANIFEST["artifacts"][name]["sha256"]
        assert policy.artifact_file == MANIFEST["artifacts"][name]["file"]
        assert policy.parameter_source_status == "APPROVED_FOR_PROVISIONAL_IMPLEMENTATION"
        assert policy.min_tasks == 3
    assert load_q_policy("c_only") is load_q_policy("c_only")      # cached after the first load


# ---- golden vectors -------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(MODE_OF))
def test_golden_vectors_are_reproduced_exactly(name: str) -> None:
    policy = load_q_policy(MODE_OF[name])
    rows = GOLDEN["vectors"][name]
    assert len(rows) == 200
    for row in rows:
        o = row["obs"]
        state = state_of(o["difficulty"], o["first_try"], o["strain"], o["mastery"])
        assert ",".join(map(str, state)) == row["state_key"], row
        action, rl_state = policy.propose(state, row["allowed"], row["tasks_done"])
        assert action == row["expected_action"], row
        assert rl_state["q_values"] == row["q_values"], row
        assert rl_state["state"] == row["state_key"]
        assert rl_state["allowed"] == [a for a in ACTIONS if a in row["allowed"]]
        assert rl_state["artifact_sha256"] == policy.artifact_sha256


def test_state_of_bucket_edges_and_unknown_mastery() -> None:
    assert state_of(1, 0.39, 0.29, 0.32) == (1, 0, 0, 0)
    assert state_of(5, 0.4, 0.3, 0.33) == (5, 1, 1, 1)
    assert state_of(2, 0.69, 0.59, 0.65) == (2, 1, 1, 1)
    assert state_of(4, 0.7, 0.6, 0.66) == (4, 2, 2, 2)
    assert state_of(2, 0.5, 0.1, None) == (2, 1, 0, 3)          # c_only: mastery unknown


# ---- propose() rules -------------------------------------------------------------------------------------


@pytest.mark.parametrize("mode", ["c_only", "combined"])
def test_propose_never_returns_an_action_outside_allowed(mode: str) -> None:
    policy = load_q_policy(mode)
    subsets = [["hold"], ["decrease_difficulty"], ["increase_difficulty"], ["decrease_difficulty", "hold"],
               ["hold", "increase_difficulty"], ["decrease_difficulty", "increase_difficulty"], list(ACTIONS)]
    for d in range(1, 6):
        for ft in (0.0, 0.5, 0.9):
            for st in (0.0, 0.4, 0.9):
                for m in ((None,) if mode == "c_only" else (0.1, 0.5, 0.9)):
                    for allowed in subsets:
                        action, _ = policy.propose(state_of(d, ft, st, m), allowed, tasks_done=5)
                        assert action in allowed


def test_propose_holds_until_min_tasks_then_follows_q() -> None:
    policy = load_q_policy("c_only")
    state = state_of(1, 0.5, 0.1, None)
    for done in (0, 1, 2):
        assert policy.propose(state, list(ACTIONS), done)[0] == "hold"
    assert policy.propose(state, list(ACTIONS), 3)[1]["state"] == "1,1,0,3"


def test_ties_break_in_the_order_decrease_hold_increase() -> None:
    policy = load_q_policy("c_only")
    unseen = (5, 2, 2, 0)                                    # a state no c_only training visit can have
    assert policy.q_values(unseen) == (0.0, 0.0, 0.0)
    assert policy.propose(unseen, list(ACTIONS), 9)[0] == "decrease_difficulty"
    assert policy.propose(unseen, ["hold", "increase_difficulty"], 9)[0] == "hold"
    assert policy.propose(unseen, ["increase_difficulty"], 9)[0] == "increase_difficulty"


# ---- fail closed -----------------------------------------------------------------------------------------


def _copy_dir(tmp_path: Path) -> Path:
    target = tmp_path / "c_policy"
    shutil.copytree(C_POLICY_DIR, target)
    return target


def test_tampered_table_is_refused(tmp_path: Path) -> None:
    d = _copy_dir(tmp_path)
    p = d / MANIFEST["artifacts"]["q_c_only"]["file"]
    p.write_bytes(p.read_bytes().replace(b'"q":{', b'"q":{ ', 1))     # one byte added
    with pytest.raises(QPolicyArtifactError):
        load_q_policy("c_only", directory=d)
    assert load_q_policy("combined", directory=d).session_mode == "combined"      # the untouched table still loads


def test_missing_table_and_missing_manifest_are_refused(tmp_path: Path) -> None:
    d = _copy_dir(tmp_path)
    (d / "q_main.json").unlink()
    with pytest.raises(QPolicyArtifactError):
        load_q_policy("combined", directory=d)
    (d / "MANIFEST.json").unlink()
    with pytest.raises(QPolicyArtifactError):
        load_q_policy("c_only", directory=d)
    with pytest.raises(QPolicyArtifactError):
        load_q_policy("no_such_mode", directory=d)


def test_a_failed_load_is_not_cached(tmp_path: Path) -> None:
    d = _copy_dir(tmp_path)
    (d / "q_c_only_v2.json").write_bytes(b"{}")
    with pytest.raises(QPolicyArtifactError):
        load_q_policy("c_only", directory=d)
    shutil.copy(C_POLICY_DIR / "q_c_only_v2.json", d / "q_c_only_v2.json")
    assert load_q_policy("c_only", directory=d).session_mode == "c_only"


def test_there_is_no_rule_fallback_in_the_module() -> None:
    import inspect

    source = inspect.getsource(q_policy_module)
    assert "propose_action" not in source and "rule_based_baseline" not in source


# ---- session start: refuses up front --------------------------------------------------------------------


def test_session_creation_refuses_when_the_table_is_tampered(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from app.application.live_engine_c import c_session_service as c_session_service_module
    from app.application.live_engine_c import task_service as task_service_module
    from tests.test_c4b_routes_and_bundle_config import (
        ALL_USABLE_BUNDLE_PATH,
        ALL_USABLE_CATALOGUE_PATH,
        client_for,
        close_client,
        headers,
        setup_learner_and_bundle,
    )

    alembic("upgrade", "head")
    # same test-side pointers test_c4b_routes_and_bundle_config's autouse fixture sets (app/ is untouched)
    monkeypatch.setattr(c_session_service_module, "_BUNDLE_PATH", ALL_USABLE_BUNDLE_PATH)
    monkeypatch.setattr(c_session_service_module, "_CATALOGUE_PATH", ALL_USABLE_CATALOGUE_PATH)
    monkeypatch.setattr(c_session_service_module, "_SMOKE_MODE", True)
    monkeypatch.setattr(task_service_module, "_BUNDLE_PATH", ALL_USABLE_BUNDLE_PATH)
    monkeypatch.setattr(task_service_module, "_CATALOGUE_PATH", ALL_USABLE_CATALOGUE_PATH)
    subject = f"live01-{uuid4()}"
    setup_learner_and_bundle(subject)

    client = client_for(subject)
    try:
        ok = client.post("/api/v1/c/sessions", json={"grade": 2, "session_mode": "c_only"}, headers=headers())
        assert ok.status_code == 201, ok.text                       # the shipped artifacts pass
        client.post(f"/api/v1/c/sessions/{ok.json()['c_session_id']}/abandon", headers=headers())

        d = _copy_dir(tmp_path)
        p = d / "q_c_only_v2.json"
        p.write_bytes(p.read_bytes() + b" ")
        monkeypatch.setattr(q_policy_module, "C_POLICY_DIR", d)
        clear_cache()
        refused = client.post("/api/v1/c/sessions", json={"grade": 2, "session_mode": "c_only"}, headers=headers())
        assert refused.status_code == 409, refused.text
        active = client.get("/api/v1/c/sessions/active", headers=headers())
        assert active.json()["session"] is None                      # no session row was created
    finally:
        close_client(client)


# ---- the new gated family ---------------------------------------------------------------------------------


def test_q_policy_config_is_a_gated_family_at_session_start() -> None:
    from tests.test_c4_session_lifecycle import all_usable_field_statuses
    from tests.test_c6b_policy_and_safety import _TEST_ONLY_STATUS_OUTSIDE_DISALLOWED_SET as OK
    from tests.test_c6b_policy_and_safety import _create_bundle_and_session
    from tests.test_c4_session_lifecycle import isolated_database
    from app.domain.runtime_bundle_c.types import (
        EvidenceWindowConfigurationArtifact,
        SafetyConfigurationArtifact,
        SelectionConfigurationArtifact,
    )

    alembic("upgrade", "head")

    async def exercise(q_status: str):
        database_engine, factory = isolated_database()
        async with factory() as session:
            spy: list = []
            try:
                await _create_bundle_and_session(
                    session,
                    selection_statuses=all_usable_field_statuses(SelectionConfigurationArtifact.FIELD_NAMES),
                    safety_statuses=all_usable_field_statuses(SafetyConfigurationArtifact.FIELD_NAMES),
                    evidence_window_statuses=all_usable_field_statuses(EvidenceWindowConfigurationArtifact.FIELD_NAMES),
                    generation_status=OK, policy_status=OK, scaffold_status=OK, aggregation_status=OK,
                    q_policy_status=q_status, smoke_mode=False, session_creation_spy=spy,
                )
                outcome = ("created", spy)
            except ConfigurationFamilyNotUsableError as exc:
                outcome = (exc.family_name, spy)
        await database_engine.dispose()
        return outcome

    assert asyncio.run(exercise("TEST_FIXTURE_ONLY"))[0] == "q_policy_config"
    assert asyncio.run(exercise("TEST_FIXTURE_ONLY"))[1] == []
    assert asyncio.run(exercise("APPROVED_FOR_PROVISIONAL_IMPLEMENTATION"))[0] == "created"


def test_q_policy_status_must_match_the_session_gate() -> None:
    from app.application.live_engine_c.bundle_resolution import assert_q_policy_matches_session_gate

    assert_q_policy_matches_session_gate("APPROVED_FOR_PROVISIONAL_IMPLEMENTATION",
                                         session_gated_parameter_source_status="APPROVED_FOR_PROVISIONAL_IMPLEMENTATION")
    with pytest.raises(ConfigurationFamilyNotUsableError) as excinfo:
        assert_q_policy_matches_session_gate("TEST_FIXTURE_ONLY",
                                             session_gated_parameter_source_status="APPROVED_FOR_PROVISIONAL_IMPLEMENTATION")
    assert excinfo.value.family_name == "q_policy_config"


# ---- end to end: a real submission persists a frozen_q_evaluation decision ---------------------------------


def test_correct_answer_persists_a_frozen_q_decision_with_the_artifact_hash() -> None:
    from app.application.live_engine_c.task_service import (
        PRODUCTION_GENERATION_CONFIG,
        PRODUCTION_POLICY_MODE,
        PRODUCTION_SCAFFOLD_CONFIG,
        TaskService,
    )
    from app.infrastructure.repositories import CPolicyDecisionRecordRepository
    from tests.test_c4_session_lifecycle import isolated_database
    from tests.test_c6a_summary_derivation import _create_real_instance_for_c_cc_03

    assert PRODUCTION_POLICY_MODE == "frozen_q_evaluation"
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            subject = f"live01-e2e-{uuid4()}"
            _, c_session_id, instance_id, instance = await _create_real_instance_for_c_cc_03(session, subject=subject)
            result = await TaskService().submit_action(
                session, principal_user_id=subject, request_id=f"req-{uuid4()}", c_session_id=c_session_id,
                c_task_instance_id=instance_id, action_payload={"selected_numeral": instance.correct_answer_payload["cardinality"]},
                generation_config=PRODUCTION_GENERATION_CONFIG, scaffold_config=PRODUCTION_SCAFFOLD_CONFIG,
            )
            assert result.response_matched is True
            rows = await CPolicyDecisionRecordRepository(session).list_chronological_for_session(c_session_id)
            assert len(rows) == 1
            row = rows[0]
            assert row.policy_mode == "frozen_q_evaluation"
            assert row.policy_version.startswith("c-rl-q-v1+")
            assert row.internal_reward is None
            assert row.rl_state["artifact_sha256"] == MANIFEST["artifacts"]["q_c_only"]["sha256"]
            assert row.rl_state["artifact_file"] == "q_c_only_v2.json"      # LIVE-02: c_only ships v2
            assert row.rl_state["state"].endswith(",3")                     # c_only: mastery bucket unknown
            assert row.rl_state["allowed"] and row.selected_action in row.rl_state["allowed"] + ["hold"]
            assert row.selected_action == "hold"                           # task 1 < min_tasks (3): the policy holds
            assert row.difficulty_before == 1
        await database_engine.dispose()

    asyncio.run(exercise())
