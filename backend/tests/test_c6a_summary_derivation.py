"""Component C Phase 6a: task-opportunity summary derivation, wired to a real trigger.

Covers T1 (the terminal trigger, owner-ruled to completed_correct only, and the eight reasons
that fail closed), T3 (the parity test, NARROWED per the owner's own self-correction -- see that
test's docstring for exactly what a pass does and does not establish), T5 (the C-9
characterization case), and T6-c/T6-d (the derivation trigger point and the derived-only proof).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.application.live_engine_c.mastery_fixture import (
    FIXTURE_MASTERY_SOURCE_INTERVENTION_SESSION_ID,
    FIXTURE_MASTERY_SOURCE_STUDENT_ID,
)
from app.application.live_engine_c.summary_service import derive_and_persist_summary
from app.application.live_engine_c.task_service import (
    _CATALOGUE_PATH,
    PRODUCTION_GENERATION_CONFIG,
    PRODUCTION_SCAFFOLD_CONFIG,
    TaskService,
    _stu_session_id,
)
from app.application.live_engine_c.terminal_event import (
    TerminalReasonNotBuiltError,
    _BLOCKER_BY_TERMINAL_REASON,
    assert_terminal_reason_built,
)
from app.core.errors import ConflictError
from app.domain.live_engine_c.errors import TelemetryStreamRejectedError
from app.domain.live_engine_c.types import GameplayEvent, SeedLineage, TaskOpportunitySummary
from app.infrastructure.live_engine_c.adapter import LiveEngineCAdapter
from app.infrastructure.persistence_models import (
    CGameplayEventRecord,
    CTaskInstanceRecord,
    CTaskOpportunityRecord,
)
from app.infrastructure.repositories import (
    CGameplayEventRecordRepository,
    CTaskOpportunitySummaryRecordRepository,
)
from tests.test_c4_session_lifecycle import isolated_database, provenance
from tests.test_c5_task_serve_and_evaluate import (
    _create_real_instance_via_smoke_mode,
    alembic,
    generation_config_fixture_for_tests,
    seed_active_session,
)


# =====================================================================================
# T1-1 -- the nine-reason mapping, verified against the package's LIVE vocabulary (R-I pattern,
# R-7's precedent), never trusted as a hand-copy in perpetuity.
# =====================================================================================


def test_t1_1_blocker_mapping_covers_exactly_the_packages_own_nine_terminal_reasons() -> None:
    """Computed, not hardcoded: reads TERMINAL_REASON_EVENT_TYPE from
    component_c_generator.models.gameplay directly and asserts _BLOCKER_BY_TERMINAL_REASON's key
    set is exactly equal. Would FAIL if the package ever added/removed a terminal reason and this
    application-side mapping (which cannot import the package itself -- X-1 restricts that to the
    adapter) were left uncovering or over-covering it -- exactly the failure mode T1-1's own text
    warns against ("An enumeration that falls through silently is a comment with extra steps.")."""
    from component_c_generator.models.gameplay import TERMINAL_REASON_EVENT_TYPE

    assert set(_BLOCKER_BY_TERMINAL_REASON.keys()) == set(TERMINAL_REASON_EVENT_TYPE.keys())


def test_terminal_event_types_tuple_matches_the_packages_own_live_value() -> None:
    """R-I pattern: CGameplayEventRecordRepository._TERMINAL_EVENT_TYPES is a hand-copy (X-1
    forbids repositories.py importing the package) of
    component_c_generator.models.gameplay.TERMINAL_EVENT_TYPES -- verified here against the
    package's live value so the two cannot silently diverge."""
    from component_c_generator.models.gameplay import TERMINAL_EVENT_TYPES

    assert set(CGameplayEventRecordRepository._TERMINAL_EVENT_TYPES) == set(TERMINAL_EVENT_TYPES)


def test_t1_1_only_completed_correct_is_marked_built() -> None:
    built = [reason for reason, blocker in _BLOCKER_BY_TERMINAL_REASON.items() if blocker == "BUILT"]
    assert built == ["completed_correct"]


def test_t1_1_dispatch_raises_with_the_specific_blocker_for_all_eight_unbuilt_reasons() -> None:
    """Each of the eight unbuilt reasons raises TerminalReasonNotBuiltError carrying its OWN
    blocker text, never a generic "not implemented" -- proven per-reason, not just "it raises"."""
    for reason, blocker in _BLOCKER_BY_TERMINAL_REASON.items():
        if reason == "completed_correct":
            continue
        with pytest.raises(TerminalReasonNotBuiltError) as excinfo:
            assert_terminal_reason_built(reason)
        assert excinfo.value.terminal_reason == reason
        assert excinfo.value.blocker == blocker


def test_t1_1_dispatch_accepts_completed_correct_silently() -> None:
    assert_terminal_reason_built("completed_correct") is None


def test_t1_1_dispatch_fails_closed_on_an_unrecognized_reason() -> None:
    with pytest.raises(TerminalReasonNotBuiltError) as excinfo:
        assert_terminal_reason_built("not_a_real_terminal_reason")
    assert excinfo.value.blocker == "not a recognized terminal_reason"


# =====================================================================================
# T1-3 / T1-4 -- behavioral: a correct submission writes the terminal event + persists a summary;
# a SECOND submission against the same, now-terminal instance is a structured 409, never a
# second scoring (submission_spy proves evaluate() was not reached the second time).
# =====================================================================================


async def _create_real_instance_for_c_cc_03(session, *, subject: str) -> tuple[UUID, UUID, UUID, CTaskInstanceRecord]:
    """C-CC-03 "Count and Match Numeral" is built directly via build_task_instance (bypassing
    select_task's RNG-driven template choice, same discipline as S5) so this test does not depend
    on which of the 30 templates smoke selection happens to pick. Its own evaluator
    (tasks/count_and_collect.py::_evaluate_cc03) is a single scalar equality
    (action["selected_numeral"] == correct["cardinality"]) with NO key-name correspondence
    between correct_answer_payload and valid_action_space -- picked specifically because that
    correspondence must be read from the template's own evaluator, never assumed to be
    "submit the correct_answer_payload verbatim" (a premise that failed for exactly this
    class of template on the first attempt at this test)."""
    student_id, c_session_id = await seed_active_session(session, session_mode="c_only", subject=subject)
    adapter = LiveEngineCAdapter()
    catalogue = adapter.load(_CATALOGUE_PATH)
    instance = adapter.build_task_instance(
        catalogue=catalogue,
        game_task_template_id="C-CC-03",
        seed_lineage=SeedLineage(global_seed=1, path=(("task_index", "1"),), seed=1),
        grade=2,
        difficulty_level=1,
        student_id=FIXTURE_MASTERY_SOURCE_STUDENT_ID,
        c_session_id=_stu_session_id(),
        task_index=1,
        config=generation_config_fixture_for_tests(),
    )
    opportunity_id = uuid4()
    session.add(
        CTaskOpportunityRecord(
            c_task_opportunity_id=opportunity_id,
            c_session_id=c_session_id,
            task_index=1,
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
            task_index=1,
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
    return student_id, c_session_id, instance_id, persisted


def test_t1_3_t1_4_correct_answer_terminates_and_a_retry_is_a_structured_409_not_a_rescoring() -> None:
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            subject = f"c6a-t1-{uuid4()}"
            _, c_session_id, instance_id, instance = await _create_real_instance_for_c_cc_03(
                session, subject=subject
            )
            payload = {"selected_numeral": instance.correct_answer_payload["cardinality"]}

            spy: list = []
            result = await TaskService().submit_action(
                session, principal_user_id=subject, request_id=f"req-{uuid4()}",
                c_session_id=c_session_id, c_task_instance_id=instance_id,
                action_payload=payload, generation_config=PRODUCTION_GENERATION_CONFIG, scaffold_config=PRODUCTION_SCAFFOLD_CONFIG,
                submission_spy=spy,
            )
            assert result.response_matched is True, (
                "fixture assumption failed: the instance's own correct_answer_payload did not "
                "evaluate correct -- this test's premise (a guaranteed-correct submission) no "
                "longer holds for this template"
            )
            assert spy == [instance_id]

            events = await CGameplayEventRecordRepository(session).list_ordered_for_instance(instance_id)
            terminal_events = [e for e in events if e.event_type == "game_task_completed"]
            assert len(terminal_events) == 1
            assert terminal_events[0].terminal_reason == "completed_correct"

            summary = await CTaskOpportunitySummaryRecordRepository(session).find_by_instance(instance_id)
            assert summary is not None
            assert summary.task_completed is True
            assert summary.correct_task is True

            # T1-4: a retry (double-tap / network retry) never re-scores.
            spy2: list = []
            with pytest.raises(ConflictError) as excinfo:
                await TaskService().submit_action(
                    session, principal_user_id=subject, request_id=f"req-{uuid4()}",
                    c_session_id=c_session_id, c_task_instance_id=instance_id,
                    action_payload=payload, generation_config=PRODUCTION_GENERATION_CONFIG, scaffold_config=PRODUCTION_SCAFFOLD_CONFIG,
                    submission_spy=spy2,
                )
            assert spy2 == [], "evaluate() must never be reached against an already-terminal instance"
            assert excinfo.value.status_code == 409
            assert excinfo.value.details == [
                {"location": ["c_task_instance_id"], "type": "task_already_terminal"}
            ]

            # Still exactly one terminal event -- the retry did not duplicate it.
            events_after = await CGameplayEventRecordRepository(session).list_ordered_for_instance(instance_id)
            assert len([e for e in events_after if e.event_type == "game_task_completed"]) == 1
        await database_engine.dispose()

    asyncio.run(exercise())


def test_t1_2_only_completed_correct_writes_a_terminal_event_behaviorally() -> None:
    """Companion to the AST guard in test_be2_architecture_guards.py: an INCORRECT submission
    (never guaranteed correct) never writes a terminal event and never persists a summary --
    proven behaviorally, not just structurally."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            _, c_session_id, instance_id, subject = await _create_real_instance_via_smoke_mode(session)
            instance = await session.get(CTaskInstanceRecord, instance_id)

            def wrong_value(declared_type: str):
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

            payload = {key: wrong_value(t) for key, t in instance.valid_action_space.items()}
            # If this happens to coincide with the real answer (astronomically unlikely for the
            # numeric/enum templates), skip rather than assert a false premise.
            if payload == dict(instance.correct_answer_payload):
                await database_engine.dispose()
                return

            result = await TaskService().submit_action(
                session, principal_user_id=subject, request_id=f"req-{uuid4()}",
                c_session_id=c_session_id, c_task_instance_id=instance_id,
                action_payload=payload, generation_config=PRODUCTION_GENERATION_CONFIG, scaffold_config=PRODUCTION_SCAFFOLD_CONFIG,
            )
            assert result.response_matched is False

            events = await CGameplayEventRecordRepository(session).list_ordered_for_instance(instance_id)
            assert not any(e.event_type == "game_task_completed" for e in events)
            summary = await CTaskOpportunitySummaryRecordRepository(session).find_by_instance(instance_id)
            assert summary is None
        await database_engine.dispose()

    asyncio.run(exercise())


# =====================================================================================
# T6-c / SF-040 interaction -- a slot with no events (or events that never reach a terminal one)
# must never produce a summary row. Enforced by the derivation itself, not by application code.
# =====================================================================================


def test_t6c_sf040_analogue_an_instance_with_no_terminal_event_produces_no_summary() -> None:
    """SF-040 interaction (A5-c/T6-c): the C analogue of "a fully missed slot emits no row" is
    that an instance whose event stream never reaches a terminal event must never produce a
    summary.

    UPDATE (Phase 8): this used to be enforced by derive_task_opportunity_summary itself raising
    ValueError on a stream with zero terminal events (behaviour/summary.py:32-34). Phase 8's own
    telemetry validator now runs BEFORE that derivation call (H4-a's own requirement -- the stream
    must be refused before derive_task_opportunity_summary is reachable) and catches this same
    zero-terminal-events condition first, raising the more specific TelemetryStreamRejectedError
    instead -- the derivation's own ValueError is still there, still pinned, still fires if ever
    reached directly (untouched, H4-b), but this call site never reaches it anymore. The
    underlying guarantee this test proves -- no summary row for an instance that never reached a
    terminal event -- is unchanged and, if anything, now enforced one layer earlier."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            _, c_session_id, instance_id, _subject = await _create_real_instance_via_smoke_mode(session)
            # Only the game_task_offered event exists at this point -- next_task's own write,
            # never a terminal one.
            adapter = LiveEngineCAdapter()
            with pytest.raises(TelemetryStreamRejectedError):
                await derive_and_persist_summary(
                    session,
                    adapter=adapter,
                    c_session_id=c_session_id,
                    c_task_instance_id=instance_id,
                    student_id=FIXTURE_MASTERY_SOURCE_STUDENT_ID,
                    stu_session_id=_stu_session_id(),
                    game_task_instance_id=f"{_stu_session_id()}-T001-X001",
                    request_id=f"req-{uuid4()}",
                )
            summary = await CTaskOpportunitySummaryRecordRepository(session).find_by_instance(instance_id)
            assert summary is None
        await database_engine.dispose()

    asyncio.run(exercise())


# =====================================================================================
# T6-d -- "derived only, never sampled": every persisted field is a straight copy of the
# adapter's returned TaskOpportunitySummary. Proven with a stub adapter carrying a sentinel value
# no real derivation could produce, showing the record is a pure passthrough, not a
# recomputation.
# =====================================================================================


class _StubAdapter:
    def __init__(self, summary: TaskOpportunitySummary) -> None:
        self._summary = summary

    def derive_task_opportunity_summary(self, events) -> TaskOpportunitySummary:  # noqa: ARG002
        return self._summary


_SENTINEL_CONSECUTIVE_ERROR_MAX = 424242


def test_t6d_summary_record_fields_are_a_pure_passthrough_of_the_derivation_output() -> None:
    """UPDATE (Phase 8): this test isolates the PERSISTENCE layer's passthrough behaviour with a
    stub adapter, deliberately never exercising the real derivation logic. Phase 8's own telemetry
    validator now also runs before ANY adapter (stub or real) is called, on the REAL persisted
    event stream -- so this test's own setup must now persist a well-formed stream (reaching one
    terminal event) for the validator to pass, where previously only next_task's own
    game_task_offered write was needed (the stub adapter made what happened after that
    irrelevant). The test's own ASSERTIONS -- that every persisted field is the stub's sentinel
    value, verbatim -- are unchanged."""
    alembic("upgrade", "head")

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            _, c_session_id, instance_id, _subject = await _create_real_instance_via_smoke_mode(session)
            # Phase 8's validator requires a well-formed stream (one terminal event, consecutive
            # index, non-decreasing timestamp) before any adapter -- stub or real -- is reached.
            terminal_id = uuid4()
            session.add(
                CGameplayEventRecord(
                    c_gameplay_event_id=terminal_id,
                    c_session_id=c_session_id,
                    game_task_instance_id=instance_id,
                    task_index=1,
                    event_type="game_task_completed",
                    event_index=2,
                    attempt_number=None,
                    event_timestamp_relative_ms=0,
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
                    **provenance("c_gameplay_event", terminal_id),
                )
            )
            await session.flush()
            sentinel_summary = TaskOpportunitySummary(
                student_id=FIXTURE_MASTERY_SOURCE_STUDENT_ID,
                intervention_session_id=FIXTURE_MASTERY_SOURCE_INTERVENTION_SESSION_ID,
                c_session_id=_stu_session_id(),
                game_task_instance_id=f"{_stu_session_id()}-T001-X001",
                task_index=1,
                task_offered=True,
                task_started=True,
                task_completed=True,
                task_skipped=False,
                task_quit=False,
                technical_issue=False,
                correct_task=True,
                total_attempts=1,
                retry_count=0,
                scaffold_requested=False,
                scaffold_count=0,
                highest_scaffold_level=None,
                c_answer_changes=0,
                task_latency_sec=1.5,
                inactive_time_sec=0.0,
                inactivity_periods=0,
                quit_after_error=False,
                terminal_reason="completed_correct",
                first_attempt_correct=True,
                final_attempt_correct=True,
                consecutive_error_max_within_task=_SENTINEL_CONSECUTIVE_ERROR_MAX,
            )
            record = await derive_and_persist_summary(
                session,
                adapter=_StubAdapter(sentinel_summary),
                c_session_id=c_session_id,
                c_task_instance_id=instance_id,
                student_id=FIXTURE_MASTERY_SOURCE_STUDENT_ID,
                stu_session_id=_stu_session_id(),
                game_task_instance_id=f"{_stu_session_id()}-T001-X001",
                request_id=f"req-{uuid4()}",
            )
            assert record.consecutive_error_max_within_task == _SENTINEL_CONSECUTIVE_ERROR_MAX
            persisted = await CTaskOpportunitySummaryRecordRepository(session).find_by_instance(instance_id)
            assert persisted is not None
            assert persisted.consecutive_error_max_within_task == _SENTINEL_CONSECUTIVE_ERROR_MAX
            assert persisted.task_latency_sec == 1.5
        await database_engine.dispose()

    asyncio.run(exercise())


# =====================================================================================
# T3 -- THE PARITY TEST, NARROWED (owner's own self-correction, quoted in full in
# app/domain/live_engine_c/ports.py / the buildLog entry). "Both paths bottom out in the same
# shipped function, so a pass establishes that the backend persists events faithfully and
# reconstitutes the summary without dropping or mistranslating a field -- and establishes
# nothing whatever about whether the derivation is right. C-9 is standing proof of that." "The
# cannot-pass-by-construction property survives for the narrower claim, because path 1 bypasses
# every line of backend code."
# =====================================================================================


def _fixture_events(package_gameplay_event_cls, seed_lineage) -> list:
    """One small, deliberately simple event stream -- offered, started, one correct submission,
    completed_correct -- built directly as PACKAGE GameplayEvent objects (path 1's own input
    shape)."""
    common = dict(
        student_id=FIXTURE_MASTERY_SOURCE_STUDENT_ID,
        intervention_session_id=FIXTURE_MASTERY_SOURCE_INTERVENTION_SESSION_ID,
        c_session_id=_stu_session_id(),
        game_task_instance_id=f"{_stu_session_id()}-T001-X001",
        task_index=1,
        seed_lineage=seed_lineage,
        generator_version="test-gen-1",
        config_checksum="fixture-checksum",
    )
    return [
        package_gameplay_event_cls(
            event_id="evt-1", event_type="game_task_offered", event_index=1,
            attempt_number=None, event_timestamp_relative_ms=0,
            action_payload=None, evaluation_payload=None, scaffold_code=None,
            technical_flag=False, terminal_reason=None, **common,
        ),
        package_gameplay_event_cls(
            event_id="evt-2", event_type="game_task_started", event_index=2,
            attempt_number=None, event_timestamp_relative_ms=200,
            action_payload=None, evaluation_payload=None, scaffold_code=None,
            technical_flag=False, terminal_reason=None, **common,
        ),
        package_gameplay_event_cls(
            event_id="evt-3", event_type="answer_submitted", event_index=3,
            attempt_number=1, event_timestamp_relative_ms=1500,
            action_payload={"submitted_total": 3}, evaluation_payload=None, scaffold_code=None,
            technical_flag=False, terminal_reason=None, **common,
        ),
        package_gameplay_event_cls(
            event_id="evt-4", event_type="answer_evaluated", event_index=4,
            attempt_number=1, event_timestamp_relative_ms=1600,
            action_payload=None, evaluation_payload={"is_correct": True}, scaffold_code=None,
            technical_flag=False, terminal_reason=None, **common,
        ),
        package_gameplay_event_cls(
            event_id="evt-5", event_type="game_task_completed", event_index=5,
            attempt_number=None, event_timestamp_relative_ms=1700,
            action_payload=None, evaluation_payload=None, scaffold_code=None,
            technical_flag=False, terminal_reason="completed_correct", **common,
        ),
    ]


# NOTE ON FOUR OF THE FIELDS BELOW (student_id, intervention_session_id, c_session_id,
# game_task_instance_id): none is persisted in string form anywhere on
# c_task_opportunity_summaries (Phase 3a's own minimal-FK style -- only opaque UUIDs/ints are
# stored). For these four, path 2's own "value" below is the SAME literal constant supplied as
# input to both the oracle fixture and derive_and_persist_summary -- equality here is BY
# CONSTRUCTION, not an independently-verified round trip, and is disclosed as such (T3-b) rather
# than silently counted as a persistence proof it is not. The other 21 fields ARE independently
# verified: computed by the oracle from raw events on one side, and reconstituted from a real,
# separately-persisted-and-reread database row on the other.
def _mismatches(oracle, path2_values: dict) -> list[str]:
    from component_c_generator.models.gameplay import CTaskOpportunitySummary as PkgSummary

    mismatches = []
    for field in PkgSummary.model_fields:
        oracle_value = getattr(oracle, field)
        path2_value = path2_values[field]
        if oracle_value != path2_value:
            mismatches.append(field)
    return mismatches


def test_t3_parity_backend_persists_and_reconstitutes_without_dropping_or_mistranslating_a_field() -> None:
    """T3-b: STATES THE LIMIT IN ITS OWN WORDS. A pass establishes that the backend PERSISTS the
    event stream faithfully and RECONSTITUTES the summary from the persisted rows without
    dropping or mistranslating a field. A pass establishes NOTHING about whether the derivation
    itself is correct -- both paths bottom out in the exact same shipped
    derive_task_opportunity_summary, so a shared derivation defect (T5's C-9 case is a real,
    demonstrated example) would pass this test even though the produced value is wrong. The
    cannot-pass-by-construction property survives for this narrower claim regardless: path 1
    calls the pinned research function directly and bypasses EVERY line of this codebase, so a
    disagreement between the two paths can only be a backend defect -- a dropped field, a
    mistranslated type, or an event lost between submission and persistence. FOUR of the
    twenty-five fields (student_id, intervention_session_id, c_session_id,
    game_task_instance_id) are compared BY CONSTRUCTION, not by an independent round trip --
    c_task_opportunity_summaries never persists these in string form (Phase 3a's own minimal-FK
    style), so both paths receive the same literal constant as input; the other twenty-one are
    genuinely independently verified, computed from raw events on one side and reconstituted
    from a separately-persisted-and-reread database row on the other."""
    from component_c_generator.models.gameplay import GameplayEvent as PkgGameplayEvent

    alembic("upgrade", "head")
    seed_lineage_pkg_kwargs = dict(global_seed=1, path=(("task_index", "1"),), seed=1)

    async def exercise() -> None:
        database_engine, factory = isolated_database()
        async with factory() as session:
            # A MANUALLY-built opportunity/instance row, deliberately with NO event write (unlike
            # _create_real_instance_via_smoke_mode, whose own next_task call already writes a
            # game_task_offered event) -- this test supplies its own complete, self-consistent
            # 5-event fixture and must not have a 6th, colliding event_index=1 already present.
            _student_id, c_session_id = await seed_active_session(
                session, session_mode="c_only", subject=f"c6a-t3-{uuid4()}"
            )
            opportunity_id = uuid4()
            session.add(
                CTaskOpportunityRecord(
                    c_task_opportunity_id=opportunity_id,
                    c_session_id=c_session_id,
                    task_index=1,
                    selected_skill_id="counting",
                    selected_template_id="C-T3-FIXTURE",
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
                    game_family_id="C-GF-T3",
                    game_task_template_id="C-T3-FIXTURE",
                    template_version="v0",
                    catalogue_version="test-catalogue-1",
                    generator_version="test-gen-1",
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
                    correct_answer_payload={"submitted_total": 3},
                    correctness_function_id="_evaluate_fixture",
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

            # Path 1: the oracle, called directly, no backend code involved.
            from component_c_generator.models.seed import CSeedLineage as PkgSeedLineage

            pkg_seed_lineage = PkgSeedLineage(**seed_lineage_pkg_kwargs)
            oracle_events = _fixture_events(PkgGameplayEvent, pkg_seed_lineage)
            from component_c_generator.behaviour.summary import (
                derive_task_opportunity_summary as pkg_derive,
            )

            oracle_summary = pkg_derive(oracle_events)

            # Path 2: persist the SAME fixture as real rows, run the wired service, read back.
            for event in _fixture_events(
                PkgGameplayEvent, PkgSeedLineage(**seed_lineage_pkg_kwargs)
            ):
                record_id = uuid4()
                session.add(
                    CGameplayEventRecord(
                        c_gameplay_event_id=record_id,
                        c_session_id=c_session_id,
                        game_task_instance_id=instance_id,
                        task_index=event.task_index,
                        event_type=event.event_type,
                        event_index=event.event_index,
                        attempt_number=event.attempt_number,
                        event_timestamp_relative_ms=event.event_timestamp_relative_ms,
                        action_payload=event.action_payload,
                        evaluation_payload=event.evaluation_payload,
                        scaffold_code=event.scaffold_code,
                        technical_flag=event.technical_flag,
                        terminal_reason=event.terminal_reason,
                        seed_lineage_global_seed=event.seed_lineage.global_seed,
                        seed_lineage_path=[list(pair) for pair in event.seed_lineage.path],
                        seed_lineage_seed=event.seed_lineage.seed,
                        generator_version=event.generator_version,
                        config_checksum=event.config_checksum,
                        **provenance("c_gameplay_event", record_id),
                    )
                )
            await session.flush()

            adapter = LiveEngineCAdapter()
            summary_record = await derive_and_persist_summary(
                session,
                adapter=adapter,
                c_session_id=c_session_id,
                c_task_instance_id=instance_id,
                student_id=FIXTURE_MASTERY_SOURCE_STUDENT_ID,
                stu_session_id=_stu_session_id(),
                game_task_instance_id=f"{_stu_session_id()}-T001-X001",
                request_id=f"req-{uuid4()}",
            )

            path2_values = {
                "student_id": FIXTURE_MASTERY_SOURCE_STUDENT_ID,
                "intervention_session_id": FIXTURE_MASTERY_SOURCE_INTERVENTION_SESSION_ID,
                "c_session_id": _stu_session_id(),
                "game_task_instance_id": f"{_stu_session_id()}-T001-X001",
                "task_index": summary_record.task_index,
                "task_offered": summary_record.task_offered,
                "task_started": summary_record.task_started,
                "task_completed": summary_record.task_completed,
                "task_skipped": summary_record.task_skipped,
                "task_quit": summary_record.task_quit,
                "technical_issue": summary_record.technical_issue,
                "correct_task": summary_record.correct_task,
                "total_attempts": summary_record.total_attempts,
                "retry_count": summary_record.retry_count,
                "scaffold_requested": summary_record.scaffold_requested,
                "scaffold_count": summary_record.scaffold_count,
                "highest_scaffold_level": summary_record.highest_scaffold_level,
                "c_answer_changes": summary_record.c_answer_changes,
                "task_latency_sec": summary_record.task_latency_sec,
                "inactive_time_sec": summary_record.inactive_time_sec,
                "inactivity_periods": summary_record.inactivity_periods,
                "quit_after_error": summary_record.quit_after_error,
                "terminal_reason": summary_record.terminal_reason,
                "first_attempt_correct": summary_record.first_attempt_correct,
                "final_attempt_correct": summary_record.final_attempt_correct,
                "consecutive_error_max_within_task": summary_record.consecutive_error_max_within_task,
            }

            mismatches = _mismatches(oracle_summary, path2_values)
            assert not mismatches, mismatches

            # A2-c(1): a mutated fixture proves a COMPUTED field is actually exercised, not a
            # constant the oracle would emit regardless.
            mutated_events = _fixture_events(PkgGameplayEvent, pkg_seed_lineage)
            # Shift the submission later -- task_latency_sec is elapsed time since the preceding
            # milestone event, so this must change the computed value.
            mutated_events[2] = PkgGameplayEvent(
                **{**mutated_events[2].model_dump(), "event_timestamp_relative_ms": 5000}
            )
            mutated_oracle_summary = pkg_derive(mutated_events)
            assert mutated_oracle_summary.task_latency_sec != oracle_summary.task_latency_sec, (
                "the fixture's task_latency_sec must be sensitive to timestamp changes, or this "
                "parity test is not exercising a real computed field"
            )

            # A2-c(2): flipping a single field in path 2's own values must make the comparison
            # fail -- proves the comparison itself is sensitive, not vacuously true.
            flipped = dict(path2_values)
            flipped["total_attempts"] = path2_values["total_attempts"] + 1
            flipped_mismatches = _mismatches(oracle_summary, flipped)
            assert flipped_mismatches == ["total_attempts"], flipped_mismatches
        await database_engine.dispose()

    asyncio.run(exercise())


# =====================================================================================
# T5 -- THE C-9 CHARACTERIZATION TEST. Records the shipped derivation's PRESENT (wrong) behavior
# on overlapping pauses. Does NOT fix it -- the fix belongs to Phase 8's stricter validation
# layer. behaviour/summary.py:97-107 pairs pause_starts/pause_ends POSITIONALLY via zip, with no
# interval matching, so overlapping pauses are double-counted rather than unioned.
# =====================================================================================


def test_t5_c9_overlapping_pauses_are_double_counted_not_unioned() -> None:
    """CHARACTERIZATION, not a correctness assertion: asserts the value the shipped derivation
    ACTUALLY produces for a stream with positionally-ordered overlapping pauses
    (start1=0, start2=1000, end1=2000, end2=3000, both non-technical). zip pairs them
    (start1,end1)=(0,2000)=2000ms and (start2,end2)=(1000,3000)=2000ms, summing to 4000ms
    (4.0s) -- ACTUAL derivation output. The CORRECT value is the union of [0,2000] and
    [1000,3000], which overlap on [1000,2000]: union length 3000ms (3.0s). The derivation double
    -counts the overlapping 1000ms. This is the shipped, pinned function's present behavior; it
    is not fixed here (Phase 8's stricter telemetry-validation layer owns that), and this test is
    NOT marked xfail against the correct value -- a characterization test records present
    behavior so a future change to the pinned function becomes visible, not invisible."""
    seed_lineage = SeedLineage(global_seed=1, path=(), seed=1)
    common = dict(
        student_id=FIXTURE_MASTERY_SOURCE_STUDENT_ID,
        intervention_session_id=FIXTURE_MASTERY_SOURCE_INTERVENTION_SESSION_ID,
        c_session_id=_stu_session_id(),
        game_task_instance_id=f"{_stu_session_id()}-T001-X001",
        task_index=1,
        seed_lineage=seed_lineage,
        generator_version="test-gen-1",
        config_checksum="fixture-checksum",
    )
    events = [
        GameplayEvent(
            event_id="evt-1", event_type="game_task_offered", event_index=1,
            attempt_number=None, event_timestamp_relative_ms=0,
            action_payload=None, evaluation_payload=None, scaffold_code=None,
            technical_flag=False, terminal_reason=None, **common,
        ),
        GameplayEvent(
            event_id="evt-2", event_type="game_task_started", event_index=2,
            attempt_number=None, event_timestamp_relative_ms=0,
            action_payload=None, evaluation_payload=None, scaffold_code=None,
            technical_flag=False, terminal_reason=None, **common,
        ),
        GameplayEvent(  # start1
            event_id="evt-3", event_type="pause_started", event_index=3,
            attempt_number=None, event_timestamp_relative_ms=0,
            action_payload=None, evaluation_payload=None, scaffold_code=None,
            technical_flag=False, terminal_reason=None, **common,
        ),
        GameplayEvent(  # start2
            event_id="evt-4", event_type="pause_started", event_index=4,
            attempt_number=None, event_timestamp_relative_ms=1000,
            action_payload=None, evaluation_payload=None, scaffold_code=None,
            technical_flag=False, terminal_reason=None, **common,
        ),
        GameplayEvent(  # end1
            event_id="evt-5", event_type="pause_ended", event_index=5,
            attempt_number=None, event_timestamp_relative_ms=2000,
            action_payload=None, evaluation_payload=None, scaffold_code=None,
            technical_flag=False, terminal_reason=None, **common,
        ),
        GameplayEvent(  # end2
            event_id="evt-6", event_type="pause_ended", event_index=6,
            attempt_number=None, event_timestamp_relative_ms=3000,
            action_payload=None, evaluation_payload=None, scaffold_code=None,
            technical_flag=False, terminal_reason=None, **common,
        ),
        GameplayEvent(
            event_id="evt-7", event_type="game_task_quit", event_index=7,
            attempt_number=None, event_timestamp_relative_ms=3000,
            action_payload=None, evaluation_payload=None, scaffold_code=None,
            technical_flag=False, terminal_reason="quit_without_recent_error", **common,
        ),
    ]

    adapter = LiveEngineCAdapter()
    summary = adapter.derive_task_opportunity_summary(events)

    ACTUAL_DOUBLE_COUNTED_VALUE = 4.0
    CORRECT_UNIONED_VALUE = 3.0
    assert summary.inactive_time_sec == ACTUAL_DOUBLE_COUNTED_VALUE
    assert summary.inactive_time_sec != CORRECT_UNIONED_VALUE
