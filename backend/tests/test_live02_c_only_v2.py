"""LIVE-02: the c_only table is replaced by a retrained v2 (the v1 table bounced 1->2->1->2 for a child who succeeds).

The fix is in the TRAINING SIMULATOR (boredom dropout now also applies in c_only), not a hand-written rule here: these
tests only pin what the retrained artifact must do and how it is shipped (manifest, audit trail, fail-closed, end-to-end).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from app.application.live_engine_c import q_policy as q_policy_module
from app.application.live_engine_c.q_policy import ACTIONS, C_POLICY_DIR, QPolicyArtifactError, clear_cache, load_q_policy, state_of

MANIFEST = json.loads((C_POLICY_DIR / "MANIFEST.json").read_bytes())


def alembic(*args: str) -> None:
    subprocess.run(["alembic", *args], check=True)


@pytest.fixture(autouse=True)
def _fresh_cache():
    clear_cache()
    yield
    clear_cache()


def test_manifest_points_c_only_at_v2_and_keeps_v1_for_the_audit_trail() -> None:
    arts = MANIFEST["artifacts"]
    assert arts["q_c_only"]["file"] == "q_c_only_v2.json" and arts["q_c_only"]["artifact_version"] == "v2"
    assert arts["q_c_only_v1"]["file"] == "q_c_only.json" and arts["q_c_only_v1"]["superseded_by"] == "q_c_only_v2.json"
    assert arts["q_c_only_v1"]["sha256"] != arts["q_c_only"]["sha256"]
    assert "superseded_by" not in arts["q_main"] and arts["q_main"]["file"] == "q_main.json"          # combined untouched
    assert hashlib.sha256((C_POLICY_DIR / "q_c_only.json").read_bytes()).hexdigest() == arts["q_c_only_v1"]["sha256"]
    assert load_q_policy("c_only").artifact_file == "q_c_only_v2.json"


def test_c_only_greedy_action_where_a_level_2_child_succeeds_is_not_decrease() -> None:
    """State (2,2,0,3): level 2, first-try high, strain low, mastery unknown. v1 chose decrease here."""
    policy = load_q_policy("c_only")
    state = state_of(2, 0.9, 0.1, None)
    assert state == (2, 2, 0, 3)
    for tasks_done in (3, 5, 11):
        action, rl_state = policy.propose(state, list(ACTIONS), tasks_done)
        assert action != "decrease_difficulty", rl_state
        assert rl_state["state"] == "2,2,0,3" and rl_state["artifact_file"] == "q_c_only_v2.json"


def test_v1_file_still_has_the_bug_this_batch_fixes() -> None:
    """The superseded table is kept only as an audit record; pin what it did so nobody ships it back by accident."""
    v1 = json.loads((C_POLICY_DIR / "q_c_only.json").read_bytes())["q"]["2,2,0,3"]
    assert v1[0] > v1[1]            # decrease beat hold in v1


def test_tampered_v2_fails_closed(tmp_path: Path) -> None:
    d = tmp_path / "c_policy"
    shutil.copytree(C_POLICY_DIR, d)
    p = d / "q_c_only_v2.json"
    p.write_bytes(p.read_bytes() + b" ")
    with pytest.raises(QPolicyArtifactError):
        load_q_policy("c_only", directory=d)
    # the superseded v1 file is not loadable through the manifest's c_only entry any more
    shutil.copytree(C_POLICY_DIR, tmp_path / "c2")
    (tmp_path / "c2" / "q_c_only_v2.json").unlink()
    with pytest.raises(QPolicyArtifactError):
        load_q_policy("c_only", directory=tmp_path / "c2")      # no silent fallback to v1


def test_all_correct_c_only_session_of_8_tasks_does_not_alternate_between_levels() -> None:
    """Backend end-to-end through TaskService.submit_action: every answer correct, 8 tasks. The level of each next task is the
    most recent persisted decision's difficulty_after, exactly as next_task carries it (test_c_difficulty_progression.py)."""
    from app.application.live_engine_c.mastery_fixture import FIXTURE_MASTERY_SOURCE_STUDENT_ID
    from app.application.live_engine_c.task_service import (
        PRODUCTION_GENERATION_CONFIG,
        PRODUCTION_SCAFFOLD_CONFIG,
        TaskService,
        _stu_session_id,
    )
    from app.domain.live_engine_c.types import SeedLineage
    from app.infrastructure.live_engine_c.adapter import LiveEngineCAdapter
    from app.infrastructure.persistence_models import CTaskInstanceRecord, CTaskOpportunityRecord
    from app.infrastructure.repositories import CPolicyDecisionRecordRepository
    from tests.test_c4_session_lifecycle import isolated_database, provenance
    from tests.test_c5_task_serve_and_evaluate import _CATALOGUE_PATH, generation_config_fixture_for_tests
    from tests.test_c6a_summary_derivation import _create_real_instance_for_c_cc_03

    alembic("upgrade", "head")

    async def add_instance(session, c_session_id, task_index: int, difficulty: int):
        adapter = LiveEngineCAdapter()
        instance = adapter.build_task_instance(
            catalogue=adapter.load(_CATALOGUE_PATH), game_task_template_id="C-CC-03",
            seed_lineage=SeedLineage(global_seed=1, path=(("task_index", str(task_index)),), seed=task_index),
            grade=2, difficulty_level=difficulty, student_id=FIXTURE_MASTERY_SOURCE_STUDENT_ID,
            c_session_id=_stu_session_id(), task_index=task_index, config=generation_config_fixture_for_tests(),
        )
        opportunity_id, instance_id = uuid4(), uuid4()
        session.add(CTaskOpportunityRecord(
            c_task_opportunity_id=opportunity_id, c_session_id=c_session_id, task_index=task_index,
            selected_skill_id=instance.skill_id, selected_template_id="C-CC-03", initial_difficulty_level=difficulty,
            mastery_context_mode="unavailable_fallback", mastery_selected_skill=None, session_phase="c_only",
            terminal_reason=None, task_offered_at_utc=datetime.now(UTC), **provenance("c_task_opportunity", opportunity_id),
        ))
        await session.flush()
        session.add(CTaskInstanceRecord(
            c_task_instance_id=instance_id, c_task_opportunity_id=opportunity_id, game_family_id=instance.game_family_id,
            game_task_template_id=instance.game_task_template_id, template_version=instance.template_version,
            catalogue_version=instance.catalogue_version, generator_version=instance.generator_version, task_index=task_index,
            skill_id=instance.skill_id, curriculum_node_id=instance.curriculum_node_id, grade_scope=instance.grade_scope,
            difficulty_level=instance.difficulty_level, difficulty_vector=dict(instance.difficulty_vector),
            functional_role=instance.functional_role, representation_mode=instance.representation_mode,
            prompt_payload=dict(instance.prompt_payload), interactive_assets=dict(instance.interactive_assets),
            correct_answer_payload=dict(instance.correct_answer_payload), correctness_function_id=instance.correctness_function_id,
            valid_action_space=dict(instance.valid_action_space), completion_condition=instance.completion_condition,
            failure_condition=instance.failure_condition, scaffold_state=instance.scaffold_state, recovery_parent_instance_id=None,
            technical_status=instance.technical_status, seed_lineage_global_seed=instance.seed_lineage.global_seed,
            seed_lineage_path=[list(pair) for pair in instance.seed_lineage.path], seed_lineage_seed=instance.seed_lineage.seed,
            **provenance("c_task_instance", instance_id),
        ))
        await session.commit()
        return instance_id, await session.get(CTaskInstanceRecord, instance_id)

    async def exercise():
        database_engine, factory = isolated_database()
        levels, actions = [], []
        async with factory() as session:
            subject = f"live02-e2e-{uuid4()}"
            _, c_session_id, instance_id, instance = await _create_real_instance_for_c_cc_03(session, subject=subject)
            for k in range(1, 9):
                levels.append(instance.difficulty_level)
                result = await TaskService().submit_action(
                    session, principal_user_id=subject, request_id=f"req-{uuid4()}", c_session_id=c_session_id,
                    c_task_instance_id=instance_id,
                    action_payload={"selected_numeral": instance.correct_answer_payload["cardinality"]},
                    generation_config=PRODUCTION_GENERATION_CONFIG, scaffold_config=PRODUCTION_SCAFFOLD_CONFIG,
                )
                assert result.response_matched is True
                rows = await CPolicyDecisionRecordRepository(session).list_chronological_for_session(c_session_id)
                assert len(rows) == k
                assert rows[-1].policy_mode == "frozen_q_evaluation"
                assert rows[-1].rl_state["artifact_file"] == "q_c_only_v2.json"
                assert rows[-1].rl_state["artifact_sha256"] == MANIFEST["artifacts"]["q_c_only"]["sha256"]
                actions.append((rows[-1].selected_action, rows[-1].applied_action))
                if k < 8:
                    instance_id, instance = await add_instance(session, c_session_id, k + 1, rows[-1].difficulty_after)
        await database_engine.dispose()
        return levels, actions

    levels, actions = asyncio.run(exercise())
    print("\nLIVE-02 e2e difficulty sequence (level of tasks 1..8):", levels)
    print("LIVE-02 e2e decisions (selected, applied):", actions)
    assert len(levels) == 8
    assert not any(levels[i] == levels[i + 2] != levels[i + 1] for i in range(6)), levels        # no a,b,a bounce
    assert levels[-3:] == [2, 2, 2], levels                                                       # settles at level 2
