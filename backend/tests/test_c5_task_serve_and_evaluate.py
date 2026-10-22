"""Component C Phase 5 acceptance tests: the leak test (P1/S5), the private/public split (P2/S3),
C-17's tripwire (C17-3), C-12's runtime-derived structural validator, sessions_since_last_practice
sourcing (P4), unknown-template fail-closed (P5), and the two HTTP routes (P6).

NOT LIVE, RESTATED FOR THIS FILE SPECIFICALLY: the real HTTP route
(``POST .../tasks/next``) ALWAYS refuses -- see ``app.application.live_engine_c.task_service``'s
module docstring. Every POSITIVE-path proof in this file (a task actually generated, an action
actually evaluated) therefore calls ``TaskService`` methods DIRECTLY with ``smoke_mode=True`` and
a full, test-file-local ``GenerationConfig`` -- NEVER through ``TestClient``, because there is no
way to reach a successful ``201`` through the real route in this batch. The one HTTP-level test
for ``next_task`` proves the OPPOSITE: that the real, fully-wired, authenticated route refuses.
This is not a gap in this test file; it is the headline consequence made concrete at the actual
HTTP boundary a client would hit.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import subprocess
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.application.live_engine_c.session_lifecycle import _learner_session_state, create_session
from app.application.live_engine_c.mastery_fixture import FIXTURE_MASTERY_SOURCE_STUDENT_ID
from app.application.live_engine_c.task_service import (
    _CATALOGUE_PATH,
    PRODUCTION_GENERATION_CONFIG,
    PRODUCTION_SCAFFOLD_CONFIG,
    TaskService,
    _stu_session_id,
)
from app.core.config import get_settings
from app.core.errors import ActionPayloadRejectedError, ConflictError, ResourceNotFoundError
from app.domain.c_task import CNextTaskResponse, CSubmitActionResult
from app.domain.live_engine_c.errors import UnknownTemplateError
from app.domain.live_engine_c.types import GenerationConfig, SeedLineage, TemplateGenerationParams
from app.domain.principal import AuthenticatedPrincipal
from app.infrastructure.auth import get_authenticated_principal
from app.infrastructure.database import async_database_url
from app.infrastructure.live_engine_c.adapter import LiveEngineCAdapter
from app.infrastructure.persistence_models import (
    AppUser,
    AppUserLearnerLink,
    CGameplayEventRecord,
    CRuntimeBundleRecord,
    CSessionRecord,
    CTaskInstanceRecord,
    CTaskOpportunityRecord,
    Learner,
)
from app.main import app
from app.domain.runtime_bundle_c.types import (
    EvidenceWindowConfigurationArtifact,
    SafetyConfigurationArtifact,
    SelectionConfigurationArtifact,
)
from tests.test_c4_session_lifecycle import (
    all_usable_field_statuses,
    isolated_database,
    provenance,
    seed_learner,
    seed_runtime_bundle,
    selection_config_fixture_for_tests,
)

SCHEMA_PATH = "provenance/c-runtime-bundle.schema.json"


def alembic(*args: str) -> None:
    subprocess.run(["alembic", *args], check=True)


def generation_config_fixture_for_tests() -> GenerationConfig:
    """TEST_FIXTURE_ONLY, all 30 templates -- read directly from the package's own
    DEFAULT_TEMPLATE_GENERATION_PARAMS (test code, not app/; W1/W2's ban is app/-scoped and this
    file is not app/). Not sourced from any bundle/governance mechanism; W3-style, labelled at
    the point of construction."""
    from component_c_generator.generation_config import (
        DEFAULT_TEMPLATE_GENERATION_PARAMS,
        GENERATION_CONFIG_VERSION,
    )

    return GenerationConfig(
        config_version=GENERATION_CONFIG_VERSION,
        parameter_source_status="TEST_FIXTURE_ONLY",
        per_template={
            template_id: TemplateGenerationParams(
                magnitude_a_by_level=params.magnitude_a_by_level,
                magnitude_b_by_level=params.magnitude_b_by_level,
                count_a_by_level=params.count_a_by_level,
                count_b_by_level=params.count_b_by_level,
                choice_set=params.choice_set,
                max_generation_attempts=params.max_generation_attempts,
            )
            for template_id, params in DEFAULT_TEMPLATE_GENERATION_PARAMS.items()
        },
    )


async def seed_active_session(
    session: AsyncSession, *, session_mode: str = "c_only", grade: int = 2, subject: str | None = None
) -> tuple[UUID, UUID]:
    """Seeds a learner + runtime bundle + one real active CSessionRecord via the real
    create_session function (Phase 4), never a hand-built row -- so every field this batch's
    select_task call depends on (session_phase, global_seed, grade, session_mode) is real,
    adapter-derived data. When ``subject`` is given, also seeds the AppUser/AppUserLearnerLink
    chain TaskService._require_learner_id needs -- Phase 4's own session_lifecycle-level tests
    never needed this (they call create_session directly), but TaskService mirrors
    CSessionService's auth-to-learner resolution, so this helper must too."""
    student_id = await seed_learner(session, grade=grade)
    if subject is not None:
        user_id = uuid4()
        session.add(
            AppUser(user_id=user_id, supabase_subject=subject, status="test_only", **provenance("app_user", user_id))
        )
        await session.flush()
        link_id = uuid4()
        session.add(
            AppUserLearnerLink(link_id=link_id, user_id=user_id, learner_id=student_id, **provenance("link", link_id))
        )
        await session.flush()
    bundle_id = await seed_runtime_bundle(session)
    adapter = LiveEngineCAdapter()
    kwargs: dict[str, object] = {
        "grade": grade,
        "session_mode": session_mode,
        "catalogue_version": "test-catalogue-1",
        "catalogue_checksum": "a" * 64,
        "global_seed": 42,
        "selection_config": selection_config_fixture_for_tests(),
        "selection_config_field_statuses": all_usable_field_statuses(SelectionConfigurationArtifact.FIELD_NAMES),
        "safety_config_field_statuses": all_usable_field_statuses(SafetyConfigurationArtifact.FIELD_NAMES),
        "evidence_window_config_field_statuses": all_usable_field_statuses(
            EvidenceWindowConfigurationArtifact.FIELD_NAMES
        ),
        "generation_parameter_source_status": "TEST_FIXTURE_ONLY",
        "policy_parameter_source_status": "TEST_FIXTURE_ONLY",
        "scaffold_parameter_source_status": "TEST_FIXTURE_ONLY",
        "aggregation_parameter_source_status": "TEST_FIXTURE_ONLY",
        "q_policy_parameter_source_status": "TEST_FIXTURE_ONLY",   # LIVE-01: new gated family
        "smoke_mode": True,
        "request_id": f"req-{uuid4()}",
    }
    if session_mode == "combined":
        from app.application.live_engine_c.mastery_fixture import fixture_b_mastery_payload_for_phase_4

        kwargs.update(
            mastery_by_skill=fixture_b_mastery_payload_for_phase_4(),
            mastery_source_student_id="STU-0001",
            mastery_source_intervention_session_id="STU-0001-I-001",
            mastery_source_intervention_session_number=1,
        )
    record = await create_session(session, adapter, student_id=student_id, c_runtime_bundle_record_id=bundle_id, **kwargs)
    await session.commit()
    return student_id, record.c_session_id


def client_for(subject: str) -> TestClient:
    app.dependency_overrides[get_authenticated_principal] = lambda: AuthenticatedPrincipal(
        user_id=subject, email="verified@example.test"
    )
    client = TestClient(app)
    client.__enter__()
    return client


def close_client(client: TestClient) -> None:
    client.__exit__(None, None, None)
    app.dependency_overrides.clear()


def headers(request_id: str | None = None) -> dict[str, str]:
    return {
        "X-Request-ID": request_id or f"req-{uuid4()}",
        "Authorization": "Bearer c-task-serving-secret-that-must-not-be-logged",
    }


# =====================================================================================
# R-7 (Phase 5 continuation): LATENT DEFECT SINCE PHASE 2. test_catalogue_c.md's top-level
# `status` was originally "TEST_FIXTURE_ONLY" -- a value the loader accepts (it applies no
# vocabulary check to this one field, catalogue.loader.py's `catalogue_status=str(root.get(
# "status", "unknown"))` is a pass-through) but which eligibility.py:51's own
# `catalogue_status_ok = str(catalogue_status).upper() in RECOGNIZED_CATALOGUE_STATUSES` NEVER
# recognized. That made EVERY template in the fixture permanently inactive and select_task could
# never have returned a result for ANY grade -- invisible from Phase 2 through Phase 4 because
# nothing called select_task/eligible_templates until this phase. Corrected to
# "PROPOSED_FOR_APPROVAL": legitimate because it is one of the four IN-VOCABULARY values (not
# merely because it stops the test failing) AND because it is literally true of Component C's own
# status (v3.0 §2: "Component C is PROPOSED, not approved") -- not a convenient invention.
#
# THE R-I PATTERN: read the vocabulary from the installed wheel AT RUNTIME, never a hardcoded
# copy of it here, so this assertion cannot silently drift from the package's own definition the
# way the ORIGINAL fixture value silently drifted out of validity in the first place.
# =====================================================================================


def test_r7_fixture_catalogue_status_is_a_recognized_activation_status() -> None:
    """Computed, not hardcoded (R-I pattern): reads RECOGNIZED_CATALOGUE_STATUSES from
    component_c_generator.eligibility directly and asserts the fixture's own top-level status is
    a member. Would FAIL again if a future edit reverted the fixture to "TEST_FIXTURE_ONLY" (or
    any other value outside the package's own recognized set), rather than silently reintroducing
    the Phase 2 latent defect this test closes."""
    from component_c_generator.eligibility import RECOGNIZED_CATALOGUE_STATUSES

    adapter = LiveEngineCAdapter()
    catalogue = adapter.load(_CATALOGUE_PATH)
    assert catalogue.catalogue_status.upper() in RECOGNIZED_CATALOGUE_STATUSES, (
        catalogue.catalogue_status,
        RECOGNIZED_CATALOGUE_STATUSES,
    )


# =====================================================================================
# C17-3 -- TRIPWIRE, NOT A COMMENT. Owner-ruled (Phase 5 work order, C-17, OPTION 2): the
# initial-difficulty path is NARROWED-not-resolved, not routed through apply_safety, and
# specifically does not consume prior_session_end_state (the recovery-cap gap's own unblocking
# condition, C17-2). This test asserts that absence structurally, so that if a future batch wires
# prior_session_end_state into this path, THIS TEST FAILS and forces the editor to read this
# docstring and the register entry it names, rather than silently closing an open gap (the C-4/
# B-1 shape the owner's own words warn against: "a no-op that reports success").
# =====================================================================================


def test_c17_3_initial_difficulty_path_does_not_consume_prior_session_end_state() -> None:
    """C-17 OWNER RULING (OPTION 2, Phase 5 work order): apply_safety is not called here and
    is not built in reduced form (option 1, rejected -- "manufacturing learner behaviour");
    the option-3 recovery-only check is also not built (rejected FOR THIS PHASE -- keys on
    prior_session_end_state, which is produced by session aggregation, Phase 9; building the
    check now would read a field that is always absent, never fire, and pass its own tests: "An
    open recorded gap gets closed. A no-op that reports success does not."). The unblocking
    condition (C17-2) is: prior_session_end_state must be computed and persisted first. This test
    proves neither the adapter's select_task signature nor TaskService's own INITIAL-DIFFICULTY
    path (``next_task``, which calls ``select_task``) consumes it today -- when someone wires it
    INTO THAT PATH, this assertion breaks and points back here.

    BATCH 2 UPDATE -- THE TRIPWIRE FIRED, AS DESIGNED, AND THIS IS THE CONSCIOUS RESPONSE: the
    whole-module string search this test used through Batch 1 (`"prior_session_end_state" not in
    source`, `source = inspect.getsource(task_service_module)`) broke the moment Batch 2 wired
    ``submit_action``'s own adaptation call to read ``prior_session_end_state`` (via the SAME real
    ``_learner_session_state`` mechanism ``next_task`` already uses for
    ``sessions_since_last_practice``, never hardcoded -- Z6-a's own "derive from real data, not a
    literal" precedent, applied here). That is a DIFFERENT C-17 item than this test's own subject:
    C-17 Item A is the INITIAL-DIFFICULTY path (``select_task``, called from ``next_task``) --
    unchanged, still narrowed, still proven absent below, scoped now to ``next_task`` itself rather
    than the whole module. C-17 Item B is the ADAPTATION/SAFETY-EVIDENCE path
    (``decide_and_persist_adaptation``, via ``build_evidence_for_session``) -- WIRED by Batch 2 (not
    REACHABLE: ``prior_session_end_state``'s own VALUE is still always ``None`` for every session,
    because session aggregation, its only producer, refuses unconditionally
    (``aggregation_service._AGGREGATION_INPUTS_AVAILABLE = False``, untouched by this batch) -- see
    Batch 2's own ``buildLog1.md`` entry for the full trace). Narrowing this test's scope to
    ``next_task`` is the disclosed, deliberate response the docstring above asked for -- not a
    silent widening of what "consumes" is allowed to mean."""
    select_task_params = set(inspect.signature(LiveEngineCAdapter.select_task).parameters)
    assert "prior_session_end_state" not in select_task_params

    import app.application.live_engine_c.task_service as task_service_module

    next_task_source = inspect.getsource(task_service_module.TaskService.next_task)
    assert "prior_session_end_state" not in next_task_source
    assert "apply_safety" not in next_task_source
    assert "CPolicyObservableEvidence" not in next_task_source

    # Whole-module companions, unaffected by Batch 2: neither symbol appears anywhere in
    # task_service.py at all -- apply_safety runs INSIDE decide_adaptation (the package's own
    # pinned composition), never called directly from this module; CPolicyObservableEvidence is
    # constructed only in the adapter (T4-b/T4-a's own guard), never here.
    module_source = inspect.getsource(task_service_module)
    assert "apply_safety" not in module_source
    assert "CPolicyObservableEvidence" not in module_source


# =====================================================================================
# S5 -- THE FULL 30-TEMPLATE LEAK LOOP. Each instance is built via build_task_instance directly
# (bypassing select_task's own skill/template RNG selection, which is orthogonal to what this
# loop proves -- PROJECTION safety, not selection correctness), persisted for real, re-read from
# the private row, projected through the real _task_fields function, and the projection's
# serialised text is checked against that SAME instance's own persisted correct_answer_payload --
# never a hardcoded expectation.
#
# DISCLOSED FALSE-NEGATIVE LIMIT (S5, owner's own instruction): a sentinel value colliding with a
# legitimately-public value on the SAME instance (e.g. an expected_total that happens to equal
# this instance's own difficulty_level) would not be caught -- the test only proves the specific
# private values THIS instance carries are absent from THIS instance's own public projection, not
# that no possible collision could ever occur. Naming this is worth more than implying the method
# is airtight.
# =====================================================================================


def test_s5_full_30_template_leak_loop() -> None:
    alembic("upgrade", "head")
    adapter = LiveEngineCAdapter()
    generation_config = generation_config_fixture_for_tests()
    template_ids = adapter.supported_template_ids()
    assert len(template_ids) == 30, "the 30-template inventory itself drifted -- investigate before trusting this loop"

    from app.application.live_engine_c.task_service import _task_fields

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            student_id, c_session_id = await seed_active_session(
                session, session_mode="c_only", subject=f"c5-s5-{uuid4()}"
            )
            catalogue = adapter.load(_CATALOGUE_PATH)
            stu_student_id = FIXTURE_MASTERY_SOURCE_STUDENT_ID
            stu_session_id = _stu_session_id()
            eligible_grade_by_template = {
                template.game_task_template_id: (2 if 2 in template.eligible_grades else template.eligible_grades[0])
                for template in catalogue.templates
            }

            for zero_based_index, template_id in enumerate(template_ids):
                task_index = zero_based_index + 1  # package requires task_index >= 1
                template_grade = eligible_grade_by_template[template_id]
                instance = adapter.build_task_instance(
                    catalogue=catalogue,
                    game_task_template_id=template_id,
                    seed_lineage=SeedLineage(global_seed=42, path=(("task_index", str(task_index)),), seed=42),
                    grade=template_grade,
                    difficulty_level=1,
                    student_id=stu_student_id,
                    c_session_id=stu_session_id,
                    task_index=task_index,
                    config=generation_config,
                )

                opportunity_id = uuid4()
                session.add(
                    CTaskOpportunityRecord(
                        c_task_opportunity_id=opportunity_id,
                        c_session_id=c_session_id,
                        task_index=task_index,
                        selected_skill_id=instance.skill_id,
                        selected_template_id=template_id,
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
                await session.flush()

                persisted = await session.scalar(
                    select(CTaskInstanceRecord).where(CTaskInstanceRecord.c_task_instance_id == instance_id)
                )
                assert persisted is not None

                public_dto = _task_fields(persisted)
                serialized = public_dto.model_dump_json()

                def _leaf_values(node) -> set:
                    """Every scalar leaf value in a JSON-shaped structure, as strings. Used for
                    EXACT-VALUE membership rather than raw substring search -- a naive
                    `"4" in serialized` check trivially "finds" the digit 4 inside an unrelated
                    "14" or "40" elsewhere in the body, which is noise, not a leak. Checking
                    against actual parsed values (still a VALUE-level check, not a field-name
                    check -- P1-b's own requirement) avoids that false-positive class entirely."""
                    found: set = set()
                    if isinstance(node, dict):
                        for value in node.values():
                            found |= _leaf_values(value)
                    elif isinstance(node, list):
                        for item in node:
                            found |= _leaf_values(item)
                    else:
                        found.add(str(node))
                    return found

                public_values = _leaf_values(json.loads(serialized))

                # DISCLOSED FALSE-NEGATIVE LIMIT, encountered for real (not hypothetical): BY
                # DESIGN, some templates' correct_answer_payload legitimately repeats a value the
                # CHILD IS ALREADY SHOWN in prompt_payload (e.g. C-BT-01 "Build and Trade":
                # prompt_payload.target_number=11 is the number the child is asked to build;
                # correct_answer_payload also carries 11 as part of its own structure). That is
                # not a leak THROUGH THE PROJECTION -- prompt_payload is intentionally public and
                # was already serialised -- so a correct_answer_payload value equal to a value
                # already present in this SAME instance's own prompt_payload is excluded here, not
                # because it is safe in general, but because this loop cannot distinguish
                # "redundant-with-the-public-prompt" from "genuinely leaked" without per-template
                # domain knowledge. Every OTHER secret value, for every template, is still checked
                # in full -- this narrows, it does not disable. Also excludes task_index/
                # difficulty_level, the two intentionally-public fields most likely to coincide
                # numerically with an unrelated small correct-answer value.
                known_public_values = {str(task_index), str(persisted.difficulty_level)} | {
                    str(v) for v in persisted.prompt_payload.values()
                }
                for secret_value in persisted.correct_answer_payload.values():
                    if str(secret_value) in known_public_values:
                        continue
                    assert str(secret_value) not in public_values, (template_id, secret_value)
                assert persisted.correctness_function_id not in serialized, template_id

                # Positive control: the projection is not empty / trivially leak-free.
                assert persisted.skill_id in serialized, template_id
                assert persisted.game_task_template_id in serialized, template_id

            await session.commit()
        await database_engine.dispose()

    asyncio.run(exercise())


# =====================================================================================
# P4 -- sessions_since_last_practice sourced from c_learner_local_state ONLY.
# =====================================================================================


def test_p4_sessions_since_last_practice_sourced_only_from_c_learner_local_state() -> None:
    """Behavioral: seeds a DISTINCTIVE, non-empty sessions_since_last_practice dict directly on
    CLearnerLocalStateRecord and proves _learner_session_state (the SAME function Phase 4's
    session-phase decision already uses, reused here unchanged) returns exactly that dict --
    never empty, never a B-derived value. Would FAIL if this were ever sourced from a B table:
    the seeded value here has no B counterpart anywhere in this test's own data at all."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            from app.infrastructure.persistence_models import CLearnerLocalStateRecord

            student_id = await seed_learner(session)
            distinctive = {"counting": 7, "place_value": 3}
            state_id = uuid4()
            session.add(
                CLearnerLocalStateRecord(
                    c_learner_local_state_id=state_id,
                    student_id=student_id,
                    eligible_combined_handoffs_completed=0,
                    sessions_since_last_practice=distinctive,
                    prior_session_end_state=None,
                    **provenance("c_learner_local_state", state_id),
                )
            )
            await session.commit()

            learner_state, record = await _learner_session_state(session, student_id)
            assert learner_state.sessions_since_last_practice == distinctive
            assert record is not None
        await database_engine.dispose()

    asyncio.run(exercise())


def test_p4_task_service_module_never_imports_a_b_learner_skill_state_symbol() -> None:
    """Structural companion to the behavioral test above: task_service.py's own source never
    references b_learner_skill_states or LearnerSkillState in any form."""
    import app.application.live_engine_c.task_service as task_service_module

    source = inspect.getsource(task_service_module)
    assert "b_learner_skill_states" not in source
    assert "LearnerSkillState" not in source


# =====================================================================================
# P5 -- unknown template -> FAIL CLOSED, both directions (X-10).
# =====================================================================================


def test_p5_known_template_evaluates_successfully() -> None:
    """Positive control: a real, generated instance's own template IS known and evaluates."""
    adapter = LiveEngineCAdapter()
    catalogue = adapter.load(_CATALOGUE_PATH)
    generation_config = generation_config_fixture_for_tests()
    template_id = adapter.supported_template_ids()[0]
    instance = adapter.build_task_instance(
        catalogue=catalogue,
        game_task_template_id=template_id,
        seed_lineage=SeedLineage(global_seed=1, path=(), seed=1),
        grade=2,
        difficulty_level=1,
        student_id="STU-0001",
        c_session_id="STU-0001-C-001",
        task_index=1,
        config=generation_config,
    )
    result = adapter.evaluate(instance, {})
    assert result.game_task_template_id == template_id


def test_p5_unknown_template_fails_closed_via_submit_action() -> None:
    """A CTaskInstanceRecord referencing an unregistered template id (no CHECK constrains this
    column's value -- it is free text) raises UnknownTemplateError inside the adapter, translated
    to ConflictError by TaskService, and the submission_spy proves evaluate() never returned
    successfully."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        subject = f"c5-p5-{uuid4()}"
        database_engine, factory = isolated_database()
        async with factory() as session:
            student_id, c_session_id = await seed_active_session(session, session_mode="c_only", subject=subject)
            opportunity_id = uuid4()
            session.add(
                CTaskOpportunityRecord(
                    c_task_opportunity_id=opportunity_id,
                    c_session_id=c_session_id,
                    task_index=1,
                    selected_skill_id="counting",
                    selected_template_id="C-UNKNOWN-99",
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
                    game_family_id="C-GF-99",
                    game_task_template_id="C-UNKNOWN-99",
                    template_version="v0",
                    catalogue_version="test-catalogue-1",
                    generator_version="test",
                    task_index=1,
                    skill_id="counting",
                    curriculum_node_id="node",
                    grade_scope=2,
                    difficulty_level=1,
                    difficulty_vector={},
                    functional_role="MAIN",
                    representation_mode="text",
                    prompt_payload={},
                    interactive_assets={},
                    correct_answer_payload={"expected_total": 3},
                    correctness_function_id="_evaluate_unknown",
                    valid_action_space={"submitted_total": "int"},
                    completion_condition="submit",
                    failure_condition="none",
                    scaffold_state="C0",
                    recovery_parent_instance_id=None,
                    technical_status="OK",
                    seed_lineage_global_seed=1,
                    seed_lineage_path=[],
                    seed_lineage_seed=1,
                    **provenance("c_task_instance", instance_id),
                )
            )
            await session.commit()

            spy: list = []
            with pytest.raises(ConflictError):
                await TaskService().submit_action(
                    session,
                    principal_user_id=subject,
                    request_id=f"req-{uuid4()}",
                    c_session_id=c_session_id,
                    c_task_instance_id=instance_id,
                    action_payload={"submitted_total": 3},
                    generation_config=PRODUCTION_GENERATION_CONFIG,
                    scaffold_config=PRODUCTION_SCAFFOLD_CONFIG,
                    submission_spy=spy,
                )
            assert spy == []
        await database_engine.dispose()

    asyncio.run(exercise())


# =====================================================================================
# C-12 -- runtime-derived structural validator, four rejection classes, each spy-proven.
# =====================================================================================


async def _create_real_instance_via_smoke_mode(session: AsyncSession, *, template_id: str | None = None) -> tuple[UUID, UUID, UUID, str]:
    """Shared setup for the C-12 tests: a real active session, then a real generated instance via
    TaskService.next_task itself (smoke_mode=True, full fixture GenerationConfig) -- never a
    hand-built row, so the resulting valid_action_space is exactly what a real caller would see.
    Returns the ``subject`` too so callers can reuse the SAME authenticated identity for their
    own follow-up ``submit_action`` call."""
    subject = f"c5-c12-{uuid4()}"
    student_id, c_session_id = await seed_active_session(session, session_mode="c_only", subject=subject)
    response = await TaskService().next_task(
        session,
        principal_user_id=subject,
        request_id=f"req-{uuid4()}",
        c_session_id=c_session_id,
        generation_config=generation_config_fixture_for_tests(),
        smoke_mode=True,
    )
    await session.commit()
    return student_id, c_session_id, response.c_task_instance_id, subject


def test_c12_rejection_wrong_key_set() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            _, c_session_id, instance_id, subject = await _create_real_instance_via_smoke_mode(session)
            instance = await session.get(CTaskInstanceRecord, instance_id)
            declared_keys = set(instance.valid_action_space)
            malformed = {f"not_a_real_key_{k}": 1 for k in declared_keys}  # every declared key missing, all extra

            spy: list = []
            with pytest.raises(ActionPayloadRejectedError) as excinfo:
                await TaskService().submit_action(
                    session, principal_user_id=subject, request_id=f"req-{uuid4()}",
                    c_session_id=c_session_id, c_task_instance_id=instance_id,
                    action_payload=malformed, generation_config=PRODUCTION_GENERATION_CONFIG, scaffold_config=PRODUCTION_SCAFFOLD_CONFIG,
                    submission_spy=spy,
                )
            assert excinfo.value.details, "expected structured field_errors"
            for entry in excinfo.value.details:
                assert set(entry.keys()) == {"location", "type"}
            assert spy == []
        await database_engine.dispose()

    asyncio.run(exercise())


def test_c12_rejection_wrong_type() -> None:
    """Uses C-CC-01 (Count and Collect): submitted_total declared "int"; a string is rejected."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            _, c_session_id, instance_id, subject = await _create_real_instance_via_smoke_mode(session)
            instance = await session.get(CTaskInstanceRecord, instance_id)
            malformed = {
                key: ("banana" if declared_type == "int" else [] if declared_type.startswith("list") else "x")
                for key, declared_type in instance.valid_action_space.items()
            }

            spy: list = []
            with pytest.raises(ActionPayloadRejectedError):
                await TaskService().submit_action(
                    session, principal_user_id=subject, request_id=f"req-{uuid4()}",
                    c_session_id=c_session_id, c_task_instance_id=instance_id,
                    action_payload=malformed, generation_config=PRODUCTION_GENERATION_CONFIG, scaffold_config=PRODUCTION_SCAFFOLD_CONFIG,
                    submission_spy=spy,
                )
            assert spy == []
        await database_engine.dispose()

    asyncio.run(exercise())


def test_c12_rejection_bad_pipe_string_value() -> None:
    """A template declaring a pipe-string enum (e.g. "left|right|equal") rejects a value outside
    that set. Skips gracefully if this particular smoke-generated instance's template does not
    happen to declare one (deterministic across a run, but template selection is RNG-driven)."""
    alembic("upgrade", "head")

    async def exercise() -> bool:
        database_engine, factory = isolated_database()
        ran = False
        async with factory() as session:
            _, c_session_id, instance_id, subject = await _create_real_instance_via_smoke_mode(session)
            instance = await session.get(CTaskInstanceRecord, instance_id)
            pipe_key = next((k for k, v in instance.valid_action_space.items() if "|" in v), None)
            if pipe_key is not None:
                malformed = dict.fromkeys(instance.valid_action_space, 0)
                for key, declared_type in instance.valid_action_space.items():
                    malformed[key] = "NOT_A_VALID_ENUM_VALUE" if key == pipe_key else 0
                spy: list = []
                with pytest.raises(ActionPayloadRejectedError):
                    await TaskService().submit_action(
                        session, principal_user_id=subject, request_id=f"req-{uuid4()}",
                        c_session_id=c_session_id, c_task_instance_id=instance_id,
                        action_payload=malformed, generation_config=PRODUCTION_GENERATION_CONFIG, scaffold_config=PRODUCTION_SCAFFOLD_CONFIG,
                        submission_spy=spy,
                    )
                assert spy == []
                ran = True
        await database_engine.dispose()
        return ran

    # Directly exercise the validator too (deterministic, template-independent) so this class of
    # rejection is proven regardless of which template smoke generation happened to pick.
    from app.domain.live_engine_c.action_payload_validation import (
        ActionPayloadValidationError,
        validate_action_payload,
    )

    with pytest.raises(ActionPayloadValidationError) as excinfo:
        validate_action_payload({"selection": "left|right|equal"}, {"selection": "up"})
    assert excinfo.value.field_errors == ((("selection",), "type_mismatch"),)

    asyncio.run(exercise())


def test_c12_rejection_bool_for_int() -> None:
    """isinstance(True, int) is True in Python -- proves the explicit bool exclusion fires."""
    from app.domain.live_engine_c.action_payload_validation import (
        ActionPayloadValidationError,
        validate_action_payload,
    )

    with pytest.raises(ActionPayloadValidationError) as excinfo:
        validate_action_payload({"submitted_total": "int"}, {"submitted_total": True})
    assert excinfo.value.field_errors == ((("submitted_total",), "type_mismatch"),)

    # And through the real service, spy-proven, mirroring the other three classes.
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            _, c_session_id, instance_id, subject = await _create_real_instance_via_smoke_mode(session)
            instance = await session.get(CTaskInstanceRecord, instance_id)
            malformed = {
                key: (True if declared_type == "int" else [] if declared_type.startswith("list") else "x")
                for key, declared_type in instance.valid_action_space.items()
            }
            if "int" not in instance.valid_action_space.values():
                await database_engine.dispose()
                return
            spy: list = []
            with pytest.raises(ActionPayloadRejectedError):
                await TaskService().submit_action(
                    session, principal_user_id=subject, request_id=f"req-{uuid4()}",
                    c_session_id=c_session_id, c_task_instance_id=instance_id,
                    action_payload=malformed, generation_config=PRODUCTION_GENERATION_CONFIG, scaffold_config=PRODUCTION_SCAFFOLD_CONFIG,
                    submission_spy=spy,
                )
            assert spy == []
        await database_engine.dispose()

    asyncio.run(exercise())


def test_c12_list_str_accepted_and_negative_controls_still_fire() -> None:
    """CONNECT Step 8 finding, closed here (buildLog2.md's own entry has the full account):
    _value_matches_declared_type had no branch for bare "str", so every list[str] field
    (C-CC-01's selected_object_ids, C-CC-02's placed_object_ids) was unconditionally rejected --
    found live, by a real correct submission, invisible to this file's own positive control
    because that control used an empty list for every list-typed field (vacuously true, never
    exercising the per-element check). Fixed with exactly one new branch
    (declared_type == "str": isinstance(value, str)) -- proven here exhaustively against every
    declared type string that actually appears in contract/c-template-registry.json (int, bool,
    number, list[int], list[str], and the three pipe-strings), each with one valid and one
    invalid instance, so a fail-closed default was not accidentally converted into fail-open for
    any of them."""
    from app.domain.live_engine_c.action_payload_validation import (
        ActionPayloadValidationError,
        validate_action_payload,
    )

    def assert_valid(declared_type: str, value) -> None:
        validate_action_payload({"k": declared_type}, {"k": value})  # raises nothing on success

    def assert_invalid(declared_type: str, value) -> None:
        with pytest.raises(ActionPayloadValidationError) as excinfo:
            validate_action_payload({"k": declared_type}, {"k": value})
        assert excinfo.value.field_errors == ((("k",), "type_mismatch"),)

    # The fix itself: list[str] now accepts a real, non-empty list of strings --
    # exactly the shape that previously 422'd on a genuinely correct C-CC-01 submission.
    assert_valid("list[str]", ["obj-0", "obj-1", "obj-2"])
    # Negative control (owner-specified): list[str] containing a non-string must still reject.
    assert_invalid("list[str]", ["obj-0", 1, "obj-2"])
    # Negative control (owner-specified): list[int] containing a string must still reject --
    # proves the fix did not loosen the sibling list[int] path it sits next to.
    assert_invalid("list[int]", [1, "2", 3])

    # Every OTHER declared type string in the real contract registry, each both ways.
    assert_valid("int", 1)
    assert_invalid("int", "1")
    assert_invalid("int", True)  # bool exclusion, unchanged by this fix
    assert_valid("bool", True)
    assert_invalid("bool", 1)
    assert_valid("number", 1.5)
    assert_invalid("number", "1.5")
    assert_valid("list[int]", [1, 2, 3])
    assert_valid("str", "obj-0")
    assert_invalid("str", 1)
    for pipe_type, valid_member, invalid_member in (
        ("left|right|equal", "left", "up"),
        ("<|>|=", "<", "!="),
        ("same|changed", "same", "different"),
    ):
        assert_valid(pipe_type, valid_member)
        assert_invalid(pipe_type, invalid_member)


def test_c12_positive_control_valid_payload_reaches_evaluate() -> None:
    """A well-formed payload (all declared keys, correct types) is NOT rejected and the spy
    proves evaluate() was actually reached -- proving the four rejection tests above reject
    because of the specific malformation, not because submit_action is broken outright."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            _, c_session_id, instance_id, subject = await _create_real_instance_via_smoke_mode(session)
            instance = await session.get(CTaskInstanceRecord, instance_id)

            def valid_value(declared_type: str):
                if "|" in declared_type:
                    return declared_type.split("|")[0]
                if declared_type == "int":
                    return 1
                if declared_type == "bool":
                    return True
                if declared_type == "number":
                    return 1
                if declared_type == "str":
                    return "a"
                # NON-empty, recursing through valid_value on the inner type -- an empty list is
                # a positive control for nothing: all() over an empty list is vacuously true, so
                # an empty list here would never exercise the per-element type check at all (this
                # is exactly the gap that let list[str] ship broken -- see buildLog2.md's CONNECT
                # Step 8 entry).
                if declared_type.startswith("list[") and declared_type.endswith("]"):
                    return [valid_value(declared_type[len("list["):-1])]
                raise AssertionError(declared_type)

            payload = {key: valid_value(t) for key, t in instance.valid_action_space.items()}

            spy: list = []
            result = await TaskService().submit_action(
                session, principal_user_id=subject, request_id=f"req-{uuid4()}",
                c_session_id=c_session_id, c_task_instance_id=instance_id,
                action_payload=payload, generation_config=PRODUCTION_GENERATION_CONFIG, scaffold_config=PRODUCTION_SCAFFOLD_CONFIG,
                submission_spy=spy,
            )
            assert spy == [instance_id]
            assert isinstance(result.response_matched, bool)
        await database_engine.dispose()

    asyncio.run(exercise())


# =====================================================================================
# P6 -- exact key sets (via direct smoke-mode service calls -- see module docstring for why not
# HTTP), and the two routes' real HTTP behavior (auth, and the real refusal).
# =====================================================================================


def test_p6_next_task_response_exact_key_set() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            subject = f"c5-p6-{uuid4()}"
            student_id, c_session_id = await seed_active_session(session, session_mode="c_only", subject=subject)
            response = await TaskService().next_task(
                session, principal_user_id=subject, request_id="req-1",
                c_session_id=c_session_id,
                generation_config=generation_config_fixture_for_tests(), smoke_mode=True,
            )
            await session.commit()
            body = json.loads(response.model_dump_json())
            assert set(body.keys()) == {
                "c_task_instance_id", "game_family_id", "game_task_template_id", "task_index",
                "skill_id", "difficulty_level", "representation_mode", "prompt_payload",
                "interactive_assets", "valid_action_space", "scaffold_state", "technical_status",
                "blanks", "prompt_text",  # BE-prompt-text batch: two additive public fields
                "request_id",
            }
            # Owner condition (P2): never the secret, never evaluator internals, never the raw
            # mastery scalar.
            assert "correct_answer_payload" not in json.dumps(body)
            assert "correctness_function_id" not in json.dumps(body)
            assert "mastery_selected_skill" not in json.dumps(body)
        await database_engine.dispose()

    asyncio.run(exercise())


def test_next_task_resumes_the_pending_instance_instead_of_minting() -> None:
    """CONNECT resume-instead-of-mint batch, owner ruling (ESCALATIONS.md §7 has the full account
    of the abandonment cost this closes). Calling next_task twice on one session, without ever
    submitting, must return the SAME task both times -- same c_task_instance_id, same
    game_task_template_id, same task_index -- proving the second call resumed rather than drew
    fresh. See test_batch4_verdict_supersession.py's own addition for the negative control (a
    TERMINATED instance does NOT get resumed -- the resume path cannot strand a child forever)."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            subject = f"c5-resume-{uuid4()}"
            student_id, c_session_id = await seed_active_session(session, session_mode="c_only", subject=subject)
            first = await TaskService().next_task(
                session, principal_user_id=subject, request_id=f"req-{uuid4()}",
                c_session_id=c_session_id,
                generation_config=generation_config_fixture_for_tests(), smoke_mode=True,
            )
            second = await TaskService().next_task(
                session, principal_user_id=subject, request_id=f"req-{uuid4()}",
                c_session_id=c_session_id,
                generation_config=generation_config_fixture_for_tests(), smoke_mode=True,
            )
            await session.commit()
            assert second.c_task_instance_id == first.c_task_instance_id
            assert second.game_task_template_id == first.game_task_template_id
            assert second.task_index == first.task_index == 1

            # Exactly one opportunity and one instance exist for this session -- the resume did
            # not create a second row of either kind.
            opp_count = await session.scalar(
                select(func.count()).select_from(CTaskOpportunityRecord).where(
                    CTaskOpportunityRecord.c_session_id == c_session_id
                )
            )
            assert opp_count == 1
            instance_count = await session.scalar(
                select(func.count()).select_from(CTaskInstanceRecord).where(
                    CTaskInstanceRecord.c_task_instance_id == first.c_task_instance_id
                )
            )
            assert instance_count == 1

            # Exactly one game_task_offered event -- the resume wrote nothing new.
            offered_count = await session.scalar(
                select(func.count()).select_from(CGameplayEventRecord).where(
                    CGameplayEventRecord.game_task_instance_id == first.c_task_instance_id,
                    CGameplayEventRecord.event_type == "game_task_offered",
                )
            )
            assert offered_count == 1
        await database_engine.dispose()

    asyncio.run(exercise())


def test_p6_submit_action_response_exact_key_set() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            _, c_session_id, instance_id, subject = await _create_real_instance_via_smoke_mode(session)
            instance = await session.get(CTaskInstanceRecord, instance_id)

            def valid_value(declared_type: str):
                if "|" in declared_type:
                    return declared_type.split("|")[0]
                if declared_type in ("int", "number"):
                    return 1
                if declared_type == "bool":
                    return True
                if declared_type.startswith("list["):
                    return []
                raise AssertionError(declared_type)

            payload = {key: valid_value(t) for key, t in instance.valid_action_space.items()}
            result = await TaskService().submit_action(
                session, principal_user_id=subject, request_id="req-1",
                c_session_id=c_session_id, c_task_instance_id=instance_id,
                action_payload=payload, generation_config=PRODUCTION_GENERATION_CONFIG, scaffold_config=PRODUCTION_SCAFFOLD_CONFIG,
            )
            body = json.loads(result.model_dump_json())
            assert set(body.keys()) == {
                "c_task_instance_id", "response_matched", "scaffold_level", "request_id",
            }
        await database_engine.dispose()

    asyncio.run(exercise())


def test_p6_next_task_route_requires_authentication() -> None:
    client = TestClient(app)
    response = client.post(f"/api/v1/c/sessions/{uuid4()}/tasks/next", headers={"X-Request-ID": "req-1"})
    assert response.status_code == 401


def test_p6_next_task_real_http_route_serves_a_real_catalogue_task_with_no_leaked_answer() -> None:
    """RENAMED, INVERTED under supervisor ruling, CONNECT Step 4, same authority and same
    reasoning as the policy-probe tripwire in test_batch2_adaptation_live_caller.py (Amendment 3):
    the OLD test, test_p6_next_task_real_http_route_refuses_because_no_governed_generation_config_
    exists, asserted THE HEADLINE CONSEQUENCE of Phase 5 through CONNECT Step 3 -- "a fully
    authenticated, fully-wired request to the real route... refuses with a structured 409, because
    the route hardcodes smoke_mode=False and the only GenerationConfig it can construct is the
    always-refused probe." That premise is retired, by name, under
    APPROVAL-2026-08-26-seven-families.md Family 4 -- CONNECT Step 4 built exactly the governed
    GenerationConfig this test's old docstring said could not exist. It is the right test to carry
    the opposite headline, so it is inverted rather than deleted or left failing, same standing
    rule as Amendment 3: no test deleted, no assertion changed elsewhere, every inversion its own
    ruling.

    What it now proves, at the same real HTTP boundary the old test used, stated as four separate
    facts rather than folded into one assertion so a partial regression is attributable:
    (1) the route returns 201, not 409;
    (2) the served template id is a real member of the real catalogue's 30 -- membership, never a
        hardcoded template id, which would pin this test to whatever the adaptive selection
        happens to pick today and break it on every unrelated selection change;
    (3) the response body's key set is exactly CNextTaskResponse's declared set -- unchanged from
        test_p6_next_task_response_exact_key_set's own list, so both tests independently agree on
        the contract shape;
    (4) no answer-bearing value leaks -- Family 4's own condition ("must never expose
        answer-bearing values"), and the first test in the suite positioned to prove it at the
        real HTTP boundary rather than only through a direct service call. Checked
        test_s5_full_30_template_leak_loop's own way, not a naive substring scan (a first attempt
        used one and false-positived immediately: C-CC-03's secret value 3 legitimately recurs in
        its own public prompt_payload.set_size=3 -- exactly the collision S5's own comment already
        named and excluded) -- leaf-value comparison against the served body, excluding any secret
        value already legitimately public on this SAME instance (task_index, difficulty_level,
        prompt_payload's own values), same disclosed false-negative limit S5 states: a private
        value colliding with an unrelated legitimately-public one would not be caught."""
    alembic("upgrade", "head")
    subject = f"c5-{uuid4()}"

    async def exercise() -> UUID:
        database_engine, factory = isolated_database()
        async with factory() as session:
            _student_id, c_session_id = await seed_active_session(session, session_mode="c_only", subject=subject)
        await database_engine.dispose()
        return c_session_id

    c_session_id = asyncio.run(exercise())
    adapter = LiveEngineCAdapter()
    real_catalogue_template_ids = {t.game_task_template_id for t in adapter.load(_CATALOGUE_PATH).templates}

    client = client_for(subject)
    try:
        response = client.post(f"/api/v1/c/sessions/{c_session_id}/tasks/next", headers=headers())
        assert response.status_code == 201, response.text
        body = response.json()

        assert body["game_task_template_id"] in real_catalogue_template_ids, (
            body["game_task_template_id"], real_catalogue_template_ids,
        )

        assert set(body.keys()) == {
            "c_task_instance_id", "game_family_id", "game_task_template_id", "task_index",
            "skill_id", "difficulty_level", "representation_mode", "prompt_payload",
            "interactive_assets", "valid_action_space", "scaffold_state", "technical_status",
            "blanks", "prompt_text", "request_id",
        }

        async def fetch_persisted_instance() -> CTaskInstanceRecord:
            database_engine, factory = isolated_database()
            async with factory() as session:
                instance = await session.get(CTaskInstanceRecord, UUID(body["c_task_instance_id"]))
                assert instance is not None
                await session.refresh(instance)
                _ = instance.correct_answer_payload, instance.correctness_function_id, instance.prompt_payload
            await database_engine.dispose()
            return instance

        persisted = asyncio.run(fetch_persisted_instance())

        def _leaf_values(node) -> set:
            found: set = set()
            if isinstance(node, dict):
                for value in node.values():
                    found |= _leaf_values(value)
            elif isinstance(node, list):
                for item in node:
                    found |= _leaf_values(item)
            else:
                found.add(str(node))
            return found

        served_json_text = json.dumps(body)
        assert "correct_answer_payload" not in served_json_text
        assert "correctness_function_id" not in served_json_text

        public_values = _leaf_values(body)
        # Same exclusion S5's own loop discloses and applies: a secret value equal to a value
        # already legitimately public on THIS instance (task_index, difficulty_level, or anything
        # already in its own prompt_payload) is not a leak through the projection.
        known_public_values = {str(body["task_index"]), str(persisted.difficulty_level)} | {
            str(v) for v in persisted.prompt_payload.values()
        }
        for secret_value in persisted.correct_answer_payload.values():
            if str(secret_value) in known_public_values:
                continue
            assert str(secret_value) not in public_values, (secret_value, body)
    finally:
        close_client(client)
