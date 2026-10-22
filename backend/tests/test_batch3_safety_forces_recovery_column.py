"""Component C backend remediation, batch 3: closes F-2 end to end.

THREE PARTS, PROVEN TOGETHER:
  1. THE COLUMN -- ``c_policy_decisions.safety_forces_recovery`` (migration ``20260816_0006``),
     mirroring the existing sibling column on ``c_scaffold_events`` exactly. Its round-trip and
     CHECK-case coverage is extended in ``tests/test_c3a_persistence.py`` (this file does not
     duplicate that).
  2. THE WRITE -- ``adaptation_service.decide_and_persist_adaptation`` now calls batch 1's
     ``decide_adaptation_with_safety_flags`` instead of ``decide_adaptation`` and persists the
     reconstructed ``activate_recovery_flag`` into the new column, never a literal.
  3. THE READ -- ``task_service.submit_action``'s incorrect-answer branch reads the most recent
     prior ``c_policy_decisions`` row for the session instead of passing a literal ``False``.

WIRED, NOT REACHABLE, same as every other Component C serving-path test file: the six-family
session-creation gate (``session_lifecycle.create_session``) still refuses every real HTTP
request. Every positive control below calls ``TaskService`` methods directly against a
``smoke_mode=True``/direct-call-constructed session, mirroring
``test_batch2_adaptation_live_caller.py``'s own precedent exactly.
"""

from __future__ import annotations

import asyncio
import subprocess
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.application.live_engine_c import task_service as task_service_module
from app.application.live_engine_c.adaptation_service import decide_and_persist_adaptation
from app.application.live_engine_c.mastery_fixture import FIXTURE_MASTERY_SOURCE_STUDENT_ID
from app.application.live_engine_c.task_service import (
    _CATALOGUE_PATH,
    PRODUCTION_GENERATION_CONFIG,
    PRODUCTION_SCAFFOLD_CONFIG,
    TaskService,
    _stu_session_id,
)
from app.domain.live_engine_c.types import PolicyObservableEvidence, SeedLineage
from app.infrastructure.live_engine_c.adapter import LiveEngineCAdapter
from app.infrastructure.persistence_models import CTaskInstanceRecord, CTaskOpportunityRecord
from app.infrastructure.repositories import CPolicyDecisionRecordRepository
from tests.test_c4_session_lifecycle import (
    isolated_database,
    provenance,
    safety_config_fixture_for_tests,
    selection_config_fixture_for_tests,
)
from tests.test_c5_task_serve_and_evaluate import generation_config_fixture_for_tests
from tests.test_c6a_summary_derivation import _create_real_instance_for_c_cc_03
from tests.test_c6b_policy_and_safety import policy_config_fixture_for_tests


def alembic(*args: str) -> None:
    subprocess.run(["alembic", *args], check=True)


def _baseline_evidence(**overrides: object) -> PolicyObservableEvidence:
    """Restated, not imported -- mirrors test_c6b_policy_and_safety.py's own private
    ``_baseline_evidence`` exactly, following test_adaptation_safety_flags_reconstruction.py's own
    precedent of restating this per-module rather than importing across test modules."""
    base: dict = dict(
        session_mode="c_only", session_phase="c_only", current_difficulty_level=2,
        recent_correctness_rate=0.6, recent_avg_attempts=1.2, recent_inactivity_periods=0,
        recent_scaffold_use_count=0, recent_consecutive_error_max=0, rolling_strain_score=0.1,
        prior_session_end_state=None, is_recovery_context=False, technical_issue_current_task=False,
        safety_increase_block_remaining=0,
    )
    base.update(overrides)
    return PolicyObservableEvidence(**base)


def _seed_lineage() -> SeedLineage:
    return SeedLineage(global_seed=1, path=(("task_index", "1"),), seed=1)


async def _second_task_instance(
    session, *, c_session_id: UUID, task_index: int
) -> tuple[UUID, CTaskInstanceRecord]:
    """A second real C-CC-03 task instance in an ALREADY-SEEDED session -- mirrors
    test_c6a_summary_derivation._create_real_instance_for_c_cc_03's own construction exactly, but
    parameterized by an existing c_session_id/task_index rather than seeding a fresh session.
    Needed here because the read-back tests below need TWO tasks in the SAME session: one to
    anchor a policy decision, a second whose incorrect answer reads it back -- never a second,
    independently-seeded session, which would not share a c_policy_decisions history at all."""
    adapter = LiveEngineCAdapter()
    catalogue = adapter.load(_CATALOGUE_PATH)
    instance = adapter.build_task_instance(
        catalogue=catalogue,
        game_task_template_id="C-CC-03",
        seed_lineage=SeedLineage(global_seed=1, path=(("task_index", str(task_index)),), seed=1),
        grade=2,
        difficulty_level=1,
        student_id=FIXTURE_MASTERY_SOURCE_STUDENT_ID,
        c_session_id=_stu_session_id(),
        task_index=task_index,
        config=generation_config_fixture_for_tests(),
    )
    opportunity_id = uuid4()
    session.add(
        CTaskOpportunityRecord(
            c_task_opportunity_id=opportunity_id,
            c_session_id=c_session_id,
            task_index=task_index,
            selected_skill_id=instance.skill_id,
            selected_template_id="C-CC-03",
            initial_difficulty_level=1,
            mastery_context_mode="unavailable_fallback",
            mastery_selected_skill=None,
            session_phase="c_only",
            terminal_reason=None,
            task_offered_at_utc=datetime.now(UTC),
            **provenance("c_task_opportunity", opportunity_id),
        )
    )
    await session.flush()
    instance_id = uuid4()
    session.add(
        CTaskInstanceRecord(
            c_task_instance_id=instance_id,
            c_task_opportunity_id=opportunity_id,
            game_family_id=instance.game_family_id,
            game_task_template_id=instance.game_task_template_id,
            template_version=instance.template_version,
            catalogue_version=instance.catalogue_version,
            generator_version=instance.generator_version,
            task_index=task_index,
            skill_id=instance.skill_id,
            curriculum_node_id=instance.curriculum_node_id,
            grade_scope=instance.grade_scope,
            difficulty_level=instance.difficulty_level,
            difficulty_vector=dict(instance.difficulty_vector),
            functional_role=instance.functional_role,
            representation_mode=instance.representation_mode,
            prompt_payload=dict(instance.prompt_payload),
            interactive_assets=dict(instance.interactive_assets),
            correct_answer_payload=dict(instance.correct_answer_payload),
            correctness_function_id=instance.correctness_function_id,
            valid_action_space=dict(instance.valid_action_space),
            completion_condition=instance.completion_condition,
            failure_condition=instance.failure_condition,
            scaffold_state=instance.scaffold_state,
            recovery_parent_instance_id=None,
            technical_status=instance.technical_status,
            seed_lineage_global_seed=instance.seed_lineage.global_seed,
            seed_lineage_path=[list(pair) for pair in instance.seed_lineage.path],
            seed_lineage_seed=instance.seed_lineage.seed,
            **provenance("c_task_instance", instance_id),
        )
    )
    await session.commit()
    persisted = await session.get(CTaskInstanceRecord, instance_id)
    return instance_id, persisted


# =====================================================================================
# THE WRITE -- a correct-answer submission persists the REAL flag value, asserted from the
# database against an independent spy on the adapter's own recomputation (never merely "a value
# exists").
# =====================================================================================


def test_correct_answer_persists_the_real_safety_forces_recovery_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    # LIVE-01: production now decides with the frozen Q policy, so the adapter call that produces the flag
    # on the live path is decide_with_proposed_action (the rule-path method is still exercised directly by
    # the other tests in this file and by test_adaptation_safety_flags_reconstruction.py).
    real_method = LiveEngineCAdapter.decide_with_proposed_action
    captured: dict = {}

    def spy_method(self, **kwargs):
        result = real_method(self, **kwargs)
        captured["result"] = result
        return result

    monkeypatch.setattr(LiveEngineCAdapter, "decide_with_proposed_action", spy_method)

    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            subject = f"batch3-correct-{uuid4()}"
            _, c_session_id, instance_id, instance = await _create_real_instance_for_c_cc_03(
                session, subject=subject
            )
            correct_payload = {"selected_numeral": instance.correct_answer_payload["cardinality"]}

            result = await TaskService().submit_action(
                session, principal_user_id=subject, request_id=f"req-{uuid4()}",
                c_session_id=c_session_id, c_task_instance_id=instance_id,
                action_payload=correct_payload, generation_config=PRODUCTION_GENERATION_CONFIG,
                scaffold_config=PRODUCTION_SCAFFOLD_CONFIG,
            )
            assert result.response_matched is True, (
                "fixture assumption failed: C-CC-03's own correct_answer_payload did not evaluate "
                "correct -- this test's premise no longer holds"
            )

            assert "result" in captured, "decide_with_proposed_action was never called"
            rows = await CPolicyDecisionRecordRepository(session).list_chronological_for_session(c_session_id)
            assert len(rows) == 1
            # The persisted column equals EXACTLY what the adapter's own reconstruction computed
            # for this real submission -- proves the real, per-decision value travels to the row,
            # not merely that some value landed there.
            assert rows[0].safety_forces_recovery == captured["result"].activate_recovery_flag
        await database_engine.dispose()

    asyncio.run(exercise())


# =====================================================================================
# THE READ -- proves the value read back from the most recent prior c_policy_decisions row
# actually ARRIVES as the safety_forces_recovery kwarg reaching decide_and_persist_scaffold_level,
# via a spy on the name task_service.py itself resolves -- proving ARRIVAL, not just that a row
# exists in the database.
# =====================================================================================


def test_read_back_flag_reaches_the_scaffold_decision(monkeypatch: pytest.MonkeyPatch) -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            subject = f"batch3-readback-{uuid4()}"
            _, c_session_id, instance_1_id, _instance_1 = await _create_real_instance_for_c_cc_03(
                session, subject=subject
            )
            opportunity_1 = await session.get(CTaskInstanceRecord, instance_1_id)

            adapter = LiveEngineCAdapter()
            safety_config = safety_config_fixture_for_tests()
            # Severe-trigger evidence via the ERROR arm -- the same trigger shape
            # test_adaptation_safety_flags_reconstruction.py's own severe_trigger_error_arm case
            # uses to force activate_recovery_flag=True. A genuine, config-derived trigger, never
            # an invented probe value.
            evidence = _baseline_evidence(recent_consecutive_error_max=safety_config.consecutive_error_trigger)
            await decide_and_persist_adaptation(
                session, adapter=adapter, c_session_id=c_session_id,
                c_task_opportunity_id=opportunity_1.c_task_opportunity_id,
                policy_mode="rule_based_baseline", evidence=evidence, current_difficulty_level=1,
                seed_lineage=_seed_lineage(), policy_config=policy_config_fixture_for_tests(),
                safety_config=safety_config, selection_config=selection_config_fixture_for_tests(),
                request_id=f"req-{uuid4()}",
            )
            await session.commit()
            prior = await CPolicyDecisionRecordRepository(session).most_recent_for_session(c_session_id)
            assert prior is not None and prior.safety_forces_recovery is True, (
                "fixture assumption failed: crafted evidence did not persist a True flag"
            )

            instance_2_id, instance_2 = await _second_task_instance(
                session, c_session_id=c_session_id, task_index=2
            )
            wrong_payload = {"selected_numeral": instance_2.correct_answer_payload["cardinality"] + 1000}

            captured_kwargs: dict = {}
            real_decide = task_service_module.decide_and_persist_scaffold_level

            async def spy_decide_and_persist_scaffold_level(*args, **kwargs):
                captured_kwargs.update(kwargs)
                return await real_decide(*args, **kwargs)

            monkeypatch.setattr(
                task_service_module, "decide_and_persist_scaffold_level", spy_decide_and_persist_scaffold_level
            )

            result = await TaskService().submit_action(
                session, principal_user_id=subject, request_id=f"req-{uuid4()}",
                c_session_id=c_session_id, c_task_instance_id=instance_2_id,
                action_payload=wrong_payload, generation_config=PRODUCTION_GENERATION_CONFIG,
                scaffold_config=PRODUCTION_SCAFFOLD_CONFIG,
            )
            assert result.response_matched is False
            # ARRIVAL, not just presence: the exact kwarg the incorrect branch passed downstream.
            assert captured_kwargs.get("safety_forces_recovery") is True
            assert result.scaffold_level == "C4"
        await database_engine.dispose()

    asyncio.run(exercise())


# =====================================================================================
# THE NEGATIVE CONTROL -- the condition this batch exists to satisfy. With the flag True the
# scaffold decision must DIFFER from the flag-False case on an otherwise IDENTICAL incorrect
# submission (one prior incorrect attempt on the current task -> C1 under
# PRODUCTION_SCAFFOLD_CONFIG's own level_c1_min_consecutive_incorrect=1). Restoring the
# literal `False` this batch replaces collapses the True case to C1 too, breaking this assertion.
# =====================================================================================


@pytest.mark.parametrize("prior_flag,expected_level", [(True, "C4"), (False, "C1")])
def test_negative_control_flag_changes_the_scaffold_outcome(prior_flag: bool, expected_level: str) -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            subject = f"batch3-negctrl-{prior_flag}-{uuid4()}"
            _, c_session_id, instance_1_id, _instance_1 = await _create_real_instance_for_c_cc_03(
                session, subject=subject
            )
            opportunity_1 = await session.get(CTaskInstanceRecord, instance_1_id)

            adapter = LiveEngineCAdapter()
            safety_config = safety_config_fixture_for_tests()
            error_max = safety_config.consecutive_error_trigger if prior_flag else 0
            evidence = _baseline_evidence(recent_consecutive_error_max=error_max)
            await decide_and_persist_adaptation(
                session, adapter=adapter, c_session_id=c_session_id,
                c_task_opportunity_id=opportunity_1.c_task_opportunity_id,
                policy_mode="rule_based_baseline", evidence=evidence, current_difficulty_level=1,
                seed_lineage=_seed_lineage(), policy_config=policy_config_fixture_for_tests(),
                safety_config=safety_config, selection_config=selection_config_fixture_for_tests(),
                request_id=f"req-{uuid4()}",
            )
            await session.commit()
            prior = await CPolicyDecisionRecordRepository(session).most_recent_for_session(c_session_id)
            assert prior is not None and prior.safety_forces_recovery is prior_flag, (
                "fixture assumption failed: crafted evidence did not produce the expected "
                "activate_recovery_flag"
            )

            instance_2_id, instance_2 = await _second_task_instance(
                session, c_session_id=c_session_id, task_index=2
            )
            wrong_payload = {"selected_numeral": instance_2.correct_answer_payload["cardinality"] + 1000}
            result = await TaskService().submit_action(
                session, principal_user_id=subject, request_id=f"req-{uuid4()}",
                c_session_id=c_session_id, c_task_instance_id=instance_2_id,
                action_payload=wrong_payload, generation_config=PRODUCTION_GENERATION_CONFIG,
                scaffold_config=PRODUCTION_SCAFFOLD_CONFIG,
            )
            assert result.response_matched is False
            assert result.scaffold_level == expected_level
        await database_engine.dispose()

    asyncio.run(exercise())


# =====================================================================================
# THE NO-PRIOR-ROW CASE -- as its own case, distinct from "a prior decision said False". The
# session's very FIRST incorrect answer, before any task has completed correctly: no
# c_policy_decisions row exists at all. Must fall back to the ordinary escalation ladder (C1, one
# consecutive incorrect), never a forced C4.
# =====================================================================================


def test_no_prior_policy_decision_row_does_not_force_recovery() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            subject = f"batch3-noprior-{uuid4()}"
            _, c_session_id, instance_id, instance = await _create_real_instance_for_c_cc_03(
                session, subject=subject
            )
            rows = await CPolicyDecisionRecordRepository(session).list_chronological_for_session(c_session_id)
            assert rows == [], (
                "fixture assumption failed: a policy decision already exists for this fresh session"
            )

            wrong_payload = {"selected_numeral": instance.correct_answer_payload["cardinality"] + 1000}
            result = await TaskService().submit_action(
                session, principal_user_id=subject, request_id=f"req-{uuid4()}",
                c_session_id=c_session_id, c_task_instance_id=instance_id,
                action_payload=wrong_payload, generation_config=PRODUCTION_GENERATION_CONFIG,
                scaffold_config=PRODUCTION_SCAFFOLD_CONFIG,
            )
            assert result.response_matched is False
            # Ordinary escalation, never a forced C4 -- the no-prior-row case reads as False, for
            # a stated reason (no safety computation has run yet), never a silent collapse.
            assert result.scaffold_level == "C1"
        await database_engine.dispose()

    asyncio.run(exercise())
