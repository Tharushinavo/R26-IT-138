"""``LiveEngineCAdapter`` — binds every ``app.domain.live_engine_c`` port to the vendored,
reviewed live-safe subset of the Component C generator (``component_c_generator``, packaged as
``prabathi-component-c-live-engine``; see
``backend/provenance/component-c-live-engine-manifest.json``).

No formula is copied or rewritten here: every method below calls straight through to the
package's own pure functions. This module's job is exactly what
Component_C_Master_Build_Plan_v3.0.md §11 Phase 1 item 2 asks for: import surface and DTO
mapping. It contains no route, no service, no persistence, no caller, no session logic, no
orchestration, and no mutable instance state — every method is traceable to exactly one row of
the 20-call §7 table this batch verified against the installed wheel.

X-1: this is the ONLY file that imports ``component_c_generator`` (enforced by
``backend/tests/test_be2_architecture_guards.py``). X-3: no package type — neither
``component_c_generator``'s nor ``models.contracts.BToCMasteryPayload`` — crosses into
``app.domain``; every package object is mapped to/from a backend-owned dataclass before or after
crossing this boundary.

SEED DERIVATION IS OUT OF SCOPE. The domain ``SeedLineage`` type is a plain three-field mirror of
the package's ``CSeedLineage``. This file references none of
``component_c_generator.seeds.derive_child_lineage``, ``seeds.SeedManager``, ``seeds.rng_from``,
or ``seeds.SUBSTREAMS`` — none of the 20 verified §7 calls name them, and inventing a wrapper for
them here would be inventing a call not in §7 (G3). Obtaining a real seed value is left to
whichever future phase's work order explicitly authorizes that call
(``backend/tests/test_be2_architecture_guards.py::test_adapter_references_no_seed_derivation_symbol``
asserts this by AST, not by review).

MASTERY PAYLOAD — A DELIBERATELY ISOLATED, PROVISIONAL RESOLUTION. §5 says Component C consumes
``models.contracts.BToCMasteryPayload`` and must not re-declare that frozen contract; X-3 says no
package type may cross into ``app.domain``. These two rules conflict for this one type. The
supervisor's provisional ruling (pending owner confirmation) is that the seven mastery values
cross the adapter boundary as a plain ``Mapping[str, float]`` keyed by the seven frozen skill
names, and this ONE function — ``_to_pkg_mastery_payload`` — is the only place anywhere that
constructs ``models.contracts.BToCMasteryPayload``. If the owner overturns the ruling, this is
the only function that needs to change.

CONFIG TYPES CARRY NO DEFAULT. Every ``_to_pkg_*_config`` helper below performs a pure 1:1 field
copy from the caller-supplied domain config to the package's pydantic config model. No threshold,
weight, window, or cap is ever chosen or defaulted here — Component C is PROPOSED, not approved
(v3.0 §2), and a hardcoded value in this file would be recording an unapproved parameter (G1).
Unlike ``app.infrastructure.live_engine.adapter``, which legitimately hardcodes B's FROZEN,
already-approved sequencing weights, nothing here is approved, so nothing here is hardcoded.

WORKAROUND -- ``decide_adaptation_with_safety_flags`` (remediation batch 1). ``adaptation.py``'s
``decide_adaptation`` computes a ``safety.controller.SafetyDecision`` internally and drops two of
its fields -- ``activate_recovery_flag``, ``request_safe_termination`` -- when composing the
``AdaptationDecision`` it returns; that type is ``frozen=True``/``extra="forbid"``, so neither can
be recovered after the fact. ``propose_action`` (policy/rule_based.py) and ``apply_safety``
(safety/controller.py) are both pure and RNG-free, and ``decide_adaptation`` composes them
internally in exactly that order on exactly those arguments (verified by direct read of
adaptation.py, and structurally by
``tests/test_c6b_policy_and_safety.py::test_s8c_decide_adaptation_always_applies_safety_structurally``).
This method calls that same two-function sequence a second time, on a package-side evidence
object translated from the domain type EXACTLY ONCE and reused BY IDENTITY across all three
pinned calls, to recover the two dropped fields alongside the real, package-composed decision.

This relies on an UNPUBLISHED IMPLEMENTATION DETAIL of a pinned function, never a published
contract: if a future re-pin changes how ``decide_adaptation`` composes ``propose_action`` and
``apply_safety``, this reconstruction silently stops matching, and
``tests/test_adaptation_safety_flags_reconstruction.py`` is what catches it.

REMOVAL TRIGGER: delete this method (and its port declaration, its domain return type
``AdaptationDecisionWithSafetyFlags``, its parity test, and the manifest's forward-looking
verification requirement), together, the moment the wheel is re-pinned to a Yass commit carrying
the owner-authorized ``AdaptationDecision`` interface change (``task_index``,
``activate_recovery_flag``, ``request_safe_termination`` as real fields on the package's own
``AdaptationDecision``).
"""

from __future__ import annotations

from typing import Mapping, Optional, Sequence

from component_c_generator.adaptation import decide_adaptation as _pkg_decide_adaptation
from component_c_generator.aggregation.derive import (
    derive_session_aggregate as _pkg_derive_session_aggregate,
)
from component_c_generator.behaviour.summary import (
    derive_task_opportunity_summary as _pkg_derive_task_opportunity_summary,
)
from component_c_generator.c_to_3.emit import (
    NoRealCSessionError as _PkgNoRealCSessionError,
    emit_c_to_3 as _pkg_emit_c_to_3,
)
from component_c_generator.c_to_3.inputs import (
    CToComponent3Provenance as _PkgCToComponent3Provenance,
)
from component_c_generator.catalogue.loader import (
    CatalogueValidationError as _PkgCatalogueValidationError,
    catalogue_file_checksum as _pkg_catalogue_file_checksum,
    load_catalogue as _pkg_load_catalogue,
)
from component_c_generator.composites.engagement_frustration import (
    compute_engagement as _pkg_compute_engagement,
    compute_frustration as _pkg_compute_frustration,
)
from component_c_generator.composites.learner_state import (
    decide_learner_state as _pkg_decide_learner_state,
    decide_telemetry_quality_status as _pkg_decide_telemetry_quality_status,
)
from component_c_generator.eligibility import (
    decide_activation as _pkg_decide_activation,
    eligible_templates as _pkg_eligible_templates,
)
from component_c_generator.evaluation import (
    UnknownTemplateError as _PkgEvalUnknownTemplateError,
    evaluate as _pkg_evaluate,
)
from component_c_generator.generation import (
    TaskGenerationTechnicalError as _PkgTaskGenerationTechnicalError,
    UnsupportedTemplateError as _PkgUnsupportedTemplateError,
    build_task_instance as _pkg_build_task_instance,
)
from component_c_generator.pipeline.evidence import (
    build_policy_evidence as _pkg_build_policy_evidence,
    compute_rolling_strain as _pkg_compute_rolling_strain,
)
from component_c_generator.policy.rule_based import (
    QLearningDisabledError as _PkgQLearningDisabledError,
    UnknownPolicyModeError as _PkgUnknownPolicyModeError,
    propose_action as _pkg_propose_action,
)
from component_c_generator.rewards import (
    decide_child_facing_reward as _pkg_decide_child_facing_reward,
)
from component_c_generator.safety.controller import (
    SAFETY_CONTROLLER_VERSION as _PKG_SAFETY_CONTROLLER_VERSION,
    apply_safety as _pkg_apply_safety,
)
from component_c_generator.scaffolds.ladder import (
    decide_scaffold_level as _pkg_decide_scaffold_level,
)
from component_c_generator.scaffolds.recovery import (
    NoEligibleRecoveryTemplateError as _PkgNoEligibleRecoveryTemplateError,
    PrerequisiteRedirectContext as _PkgPrerequisiteRedirectContext,
    RecoveryPreconditionError as _PkgRecoveryPreconditionError,
    build_recovery_task as _pkg_build_recovery_task,
)
from component_c_generator.pipeline.session_state import (
    CLearnerSessionState as _PkgCLearnerSessionState,
    decide_next_session_phase as _pkg_decide_next_session_phase,
    is_eligible_combined_handoff as _pkg_is_eligible_combined_handoff,
)
from component_c_generator.selection.phase import (
    decide_session_phase as _pkg_decide_session_phase,
)
from component_c_generator.selection.selector import (
    SelectionInputError as _PkgSelectionInputError,
    select_task as _pkg_select_task,
)
from component_c_generator.tasks.registry import (
    supported_template_ids as _pkg_supported_template_ids,
)
# CONNECT Step 4, ruling on the #3 surprise: routed through the adapter rather than exempting
# task_service.py from the full-dotted-path guard (test_component_c_generator_full_dotted_path_
# enforcement, test_be2_architecture_guards.py:504) -- that guard restricts component_c_generator
# as an import root to this one file, deliberately, and weakening it to accommodate a new caller
# would be the first guard this work order actually loosened. generation_config is not among the
# 16 never-ship modules (test_c1a_wheel_provenance.NEVER_SHIP_MODULES) so this import is
# legitimate; it is module-qualified, never `from ... import DEFAULT_TEMPLATE_GENERATION_PARAMS`,
# so every read below names its source.
from component_c_generator import generation_config as _pkg_generation_config

from models.contracts import (
    BToCMasteryPayload as _PkgBToCMasteryPayload,
    EngagementComponents as _PkgCToComponent3EngagementComponents,
    FrustrationComponents as _PkgCToComponent3FrustrationComponents,
)
from validators.contract_validators import (
    ContractValidationError as _PkgContractValidationError,
    validate_payload as _pkg_validate_payload,
)

from app.domain.live_engine_c.errors import (
    CatalogueUnavailableError,
    MasteryPayloadContractValidationError,
    NoEligibleRecoveryTemplateError,
    NoRealCSessionError,
    QLearningDisabledError,
    RecoveryPreconditionError,
    SF043OrderingError,
    SelectionInputError,
    TaskGenerationTechnicalError,
    UnknownPolicyModeError,
    UnknownTemplateError,
    UnsupportedTemplateError,
)
from app.domain.live_engine_c.types import (
    ActivationDecision,
    AdaptationDecision,
    AdaptationDecisionWithSafetyFlags,
    AggregationConfig,
    AttendanceStatus,
    Catalogue,
    ChildFacingReward,
    CompositeFormulaVersion,
    CToComponent3Payload,
    CToComponent3Provenance,
    EngagementComponents,
    EvaluationResult,
    EvidenceWindowConfig,
    FrustrationComponents,
    GameFamily,
    GameTaskTemplate,
    GenerationConfig,
    Grade,
    LearnerSessionState,
    LearnerState,
    PolicyConfig,
    PolicyMode,
    PolicyObservableEvidence,
    PrerequisiteRedirectContext,
    RecoveryConfig,
    RewardOutcomeContext,
    SafetyConfig,
    ScaffoldConfig,
    ScaffoldDecisionContext,
    ScaffoldLevel,
    SeedLineage,
    SelectionConfig,
    SelectionResult,
    SessionAggregate,
    SessionMode,
    SessionPhase,
    StateReason,
    TaskInstance,
    TaskOpportunitySummary,
    TelemetryQualityStatus,
    TemplateGenerationParams,
)


def _load_package_catalogue(source_path: str):
    """Re-load the package's own ``LoadedCatalogue`` from the same governed path.

    Mirrors ``app.infrastructure.live_engine.adapter._load_package_catalogue``: every port
    method that needs a package-native catalogue/template object re-derives it from
    ``source_path`` rather than reconstructing a package Pydantic model by hand from the trimmed
    domain ``Catalogue`` — so the object handed to the reviewed package functions is always the
    real, fully-validated loader output.
    """
    try:
        return _pkg_load_catalogue(source_path)
    except _PkgCatalogueValidationError as exc:
        raise CatalogueUnavailableError(str(exc)) from exc


def _template_by_id(pkg_catalogue, game_task_template_id: str):
    template = pkg_catalogue.by_id(game_task_template_id)
    if template is None:
        raise UnknownTemplateError(f"unknown game_task_template_id: {game_task_template_id!r}")
    return template


def _map_game_family(family) -> GameFamily:
    return GameFamily(
        game_family_id=family.game_family_id,
        family_name=family.family_name,
        template_id_prefix=family.template_id_prefix,
    )


def _map_game_task_template(template) -> GameTaskTemplate:
    return GameTaskTemplate(
        game_family_id=template.game_family_id,
        family_name=template.family_name,
        game_task_template_id=template.game_task_template_id,
        template_title=template.template_title,
        primary_skill_ids=tuple(template.primary_skill_ids),
        curriculum_node_ids=tuple(template.curriculum_node_ids),
        grade_scope_text=template.grade_scope_text,
        status=template.status,
        status_note=template.status_note,
        functional_role=template.functional_role,
        representations=tuple(template.representations),
        representations_note=template.representations_note,
        learner_action=template.learner_action,
        correctness=template.correctness,
        error_signatures=(
            tuple(template.error_signatures) if template.error_signatures is not None else None
        ),
        main_difficulty_levers=template.main_difficulty_levers,
        recovery=template.recovery,
        eligible_grades=tuple(template.eligible_grades),
        grade_gate_status=template.grade_gate_status,
    )


def _map_catalogue(catalogue) -> Catalogue:
    return Catalogue(
        catalogue_version=catalogue.catalogue_version,
        catalogue_status=catalogue.catalogue_status,
        source_path=catalogue.source_path,
        skills=tuple(catalogue.skills),
        families=tuple(_map_game_family(f) for f in catalogue.families),
        templates=tuple(_map_game_task_template(t) for t in catalogue.templates),
    )


_PROPOSABLE_ACTIONS = ("decrease_difficulty", "hold", "increase_difficulty")
_KNOWN_POLICY_MODES = ("rule_based_baseline", "q_learning_offline", "frozen_q_evaluation")


def _to_pkg_seed_lineage(lineage: SeedLineage):
    from component_c_generator.models.seed import CSeedLineage as _PkgCSeedLineage

    return _PkgCSeedLineage(
        global_seed=lineage.global_seed,
        path=lineage.path,
        seed=lineage.seed,
    )


def _to_domain_seed_lineage(lineage) -> SeedLineage:
    return SeedLineage(
        global_seed=lineage.global_seed,
        path=tuple(lineage.path),
        seed=lineage.seed,
    )


def _map_activation_decision(decision) -> ActivationDecision:
    return ActivationDecision(
        game_task_template_id=decision.game_task_template_id,
        recognized=decision.recognized,
        generation_supported=decision.generation_supported,
        grade_eligible=decision.grade_eligible,
        curriculum_active=decision.curriculum_active,
        catalogue_status_ok=decision.catalogue_status_ok,
        calibration_restricted=decision.calibration_restricted,
        active=decision.active,
        reason=decision.reason,
    )


def _map_task_instance(instance) -> TaskInstance:
    return TaskInstance(
        game_family_id=instance.game_family_id,
        game_task_template_id=instance.game_task_template_id,
        game_task_instance_id=instance.game_task_instance_id,
        template_version=instance.template_version,
        catalogue_version=instance.catalogue_version,
        generator_version=instance.generator_version,
        seed_lineage=_to_domain_seed_lineage(instance.seed_lineage),
        student_id=instance.student_id,
        c_session_id=instance.c_session_id,
        task_index=instance.task_index,
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
        recovery_parent_instance_id=instance.recovery_parent_instance_id,
        technical_status=instance.technical_status,
    )


def _to_pkg_task_instance(instance: TaskInstance):
    from component_c_generator.models.task_instance import GameTaskInstance as _PkgGameTaskInstance

    return _PkgGameTaskInstance(
        game_family_id=instance.game_family_id,
        game_task_template_id=instance.game_task_template_id,
        game_task_instance_id=instance.game_task_instance_id,
        template_version=instance.template_version,
        catalogue_version=instance.catalogue_version,
        generator_version=instance.generator_version,
        seed_lineage=_to_pkg_seed_lineage(instance.seed_lineage),
        student_id=instance.student_id,
        c_session_id=instance.c_session_id,
        task_index=instance.task_index,
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
        recovery_parent_instance_id=instance.recovery_parent_instance_id,
        technical_status=instance.technical_status,
    )


def _map_selection_result(result) -> SelectionResult:
    return SelectionResult(
        session_phase=result.session_phase,
        selected_skill_id=result.selected_skill_id,
        selected_template_id=result.selected_template_id,
        initial_difficulty_level=result.initial_difficulty_level,
        mastery_context_mode=result.mastery_context_mode,
        mastery_selected_skill=result.mastery_selected_skill,
        task_instance=_map_task_instance(result.task_instance),
    )


def _map_evaluation_result(result) -> EvaluationResult:
    return EvaluationResult(
        game_task_instance_id=result.game_task_instance_id,
        game_task_template_id=result.game_task_template_id,
        correctness_function_id=result.correctness_function_id,
        learner_action=dict(result.learner_action),
        is_correct=result.is_correct,
        details=dict(result.details),
    )


def _to_pkg_gameplay_event(event):
    from component_c_generator.models.gameplay import GameplayEvent as _PkgGameplayEvent

    return _PkgGameplayEvent(
        event_id=event.event_id,
        event_type=event.event_type,
        event_index=event.event_index,
        student_id=event.student_id,
        intervention_session_id=event.intervention_session_id,
        c_session_id=event.c_session_id,
        game_task_instance_id=event.game_task_instance_id,
        task_index=event.task_index,
        attempt_number=event.attempt_number,
        event_timestamp_relative_ms=event.event_timestamp_relative_ms,
        action_payload=(dict(event.action_payload) if event.action_payload is not None else None),
        evaluation_payload=(
            dict(event.evaluation_payload) if event.evaluation_payload is not None else None
        ),
        scaffold_code=event.scaffold_code,
        technical_flag=event.technical_flag,
        terminal_reason=event.terminal_reason,
        seed_lineage=_to_pkg_seed_lineage(event.seed_lineage),
        generator_version=event.generator_version,
        config_checksum=event.config_checksum,
    )


def _map_task_opportunity_summary(summary) -> TaskOpportunitySummary:
    return TaskOpportunitySummary(
        student_id=summary.student_id,
        intervention_session_id=summary.intervention_session_id,
        c_session_id=summary.c_session_id,
        game_task_instance_id=summary.game_task_instance_id,
        task_index=summary.task_index,
        task_offered=summary.task_offered,
        task_started=summary.task_started,
        task_completed=summary.task_completed,
        task_skipped=summary.task_skipped,
        task_quit=summary.task_quit,
        technical_issue=summary.technical_issue,
        correct_task=summary.correct_task,
        total_attempts=summary.total_attempts,
        retry_count=summary.retry_count,
        scaffold_requested=summary.scaffold_requested,
        scaffold_count=summary.scaffold_count,
        highest_scaffold_level=summary.highest_scaffold_level,
        c_answer_changes=summary.c_answer_changes,
        task_latency_sec=summary.task_latency_sec,
        inactive_time_sec=summary.inactive_time_sec,
        inactivity_periods=summary.inactivity_periods,
        quit_after_error=summary.quit_after_error,
        terminal_reason=summary.terminal_reason,
        first_attempt_correct=summary.first_attempt_correct,
        final_attempt_correct=summary.final_attempt_correct,
        consecutive_error_max_within_task=summary.consecutive_error_max_within_task,
    )


def _to_pkg_task_opportunity_summary(summary: TaskOpportunitySummary):
    from component_c_generator.models.gameplay import (
        CTaskOpportunitySummary as _PkgCTaskOpportunitySummary,
    )

    return _PkgCTaskOpportunitySummary(
        student_id=summary.student_id,
        intervention_session_id=summary.intervention_session_id,
        c_session_id=summary.c_session_id,
        game_task_instance_id=summary.game_task_instance_id,
        task_index=summary.task_index,
        task_offered=summary.task_offered,
        task_started=summary.task_started,
        task_completed=summary.task_completed,
        task_skipped=summary.task_skipped,
        task_quit=summary.task_quit,
        technical_issue=summary.technical_issue,
        correct_task=summary.correct_task,
        total_attempts=summary.total_attempts,
        retry_count=summary.retry_count,
        scaffold_requested=summary.scaffold_requested,
        scaffold_count=summary.scaffold_count,
        highest_scaffold_level=summary.highest_scaffold_level,
        c_answer_changes=summary.c_answer_changes,
        task_latency_sec=summary.task_latency_sec,
        inactive_time_sec=summary.inactive_time_sec,
        inactivity_periods=summary.inactivity_periods,
        quit_after_error=summary.quit_after_error,
        terminal_reason=summary.terminal_reason,
        first_attempt_correct=summary.first_attempt_correct,
        final_attempt_correct=summary.final_attempt_correct,
        consecutive_error_max_within_task=summary.consecutive_error_max_within_task,
    )


def _map_policy_observable_evidence(evidence) -> PolicyObservableEvidence:
    return PolicyObservableEvidence(
        session_mode=evidence.session_mode,
        session_phase=evidence.session_phase,
        current_difficulty_level=evidence.current_difficulty_level,
        recent_correctness_rate=evidence.recent_correctness_rate,
        recent_avg_attempts=evidence.recent_avg_attempts,
        recent_inactivity_periods=evidence.recent_inactivity_periods,
        recent_scaffold_use_count=evidence.recent_scaffold_use_count,
        recent_consecutive_error_max=evidence.recent_consecutive_error_max,
        rolling_strain_score=evidence.rolling_strain_score,
        prior_session_end_state=evidence.prior_session_end_state,
        is_recovery_context=evidence.is_recovery_context,
        technical_issue_current_task=evidence.technical_issue_current_task,
        safety_increase_block_remaining=evidence.safety_increase_block_remaining,
    )


def _to_pkg_policy_observable_evidence(evidence: PolicyObservableEvidence):
    from component_c_generator.models.adaptation import (
        CPolicyObservableEvidence as _PkgCPolicyObservableEvidence,
    )

    return _PkgCPolicyObservableEvidence(
        session_mode=evidence.session_mode,
        session_phase=evidence.session_phase,
        current_difficulty_level=evidence.current_difficulty_level,
        recent_correctness_rate=evidence.recent_correctness_rate,
        recent_avg_attempts=evidence.recent_avg_attempts,
        recent_inactivity_periods=evidence.recent_inactivity_periods,
        recent_scaffold_use_count=evidence.recent_scaffold_use_count,
        recent_consecutive_error_max=evidence.recent_consecutive_error_max,
        rolling_strain_score=evidence.rolling_strain_score,
        prior_session_end_state=evidence.prior_session_end_state,
        is_recovery_context=evidence.is_recovery_context,
        technical_issue_current_task=evidence.technical_issue_current_task,
        safety_increase_block_remaining=evidence.safety_increase_block_remaining,
    )


def _map_adaptation_decision(decision) -> AdaptationDecision:
    return AdaptationDecision(
        decision_id=decision.decision_id,
        policy_mode=decision.policy_mode,
        policy_version=decision.policy_version,
        rl_state=(dict(decision.rl_state) if decision.rl_state is not None else None),
        selected_action=decision.selected_action,
        applied_action=decision.applied_action,
        action_overridden=decision.action_overridden,
        safety_reason=decision.safety_reason,
        difficulty_before=decision.difficulty_before,
        difficulty_after=decision.difficulty_after,
        rolling_strain_bucket=decision.rolling_strain_bucket,
        session_start_state_bucket=decision.session_start_state_bucket,
        increase_block_remaining=decision.increase_block_remaining,
        internal_reward=decision.internal_reward,
        seed_lineage=_to_domain_seed_lineage(decision.seed_lineage),
    )


def _to_pkg_adaptation_decision(decision: AdaptationDecision):
    from component_c_generator.models.adaptation import (
        AdaptationDecision as _PkgAdaptationDecision,
    )

    return _PkgAdaptationDecision(
        decision_id=decision.decision_id,
        policy_mode=decision.policy_mode,
        policy_version=decision.policy_version,
        rl_state=(dict(decision.rl_state) if decision.rl_state is not None else None),
        selected_action=decision.selected_action,
        applied_action=decision.applied_action,
        action_overridden=decision.action_overridden,
        safety_reason=decision.safety_reason,
        difficulty_before=decision.difficulty_before,
        difficulty_after=decision.difficulty_after,
        rolling_strain_bucket=decision.rolling_strain_bucket,
        session_start_state_bucket=decision.session_start_state_bucket,
        increase_block_remaining=decision.increase_block_remaining,
        internal_reward=decision.internal_reward,
        seed_lineage=_to_pkg_seed_lineage(decision.seed_lineage),
    )


def _to_pkg_scaffold_decision_context(context: ScaffoldDecisionContext):
    from component_c_generator.scaffolds.ladder import (
        ScaffoldDecisionContext as _PkgScaffoldDecisionContext,
    )

    return _PkgScaffoldDecisionContext(
        consecutive_incorrect_current_task=context.consecutive_incorrect_current_task,
        safety_forces_recovery=context.safety_forces_recovery,
    )


def _to_pkg_reward_outcome_context(context: RewardOutcomeContext):
    from component_c_generator.rewards import RewardOutcomeContext as _PkgRewardOutcomeContext

    return _PkgRewardOutcomeContext(
        task_completed_correctly=context.task_completed_correctly,
        is_recovery_task=context.is_recovery_task,
        retried_after_incorrect_then_continued=context.retried_after_incorrect_then_continued,
        continued_after_safety_event_without_quitting=(
            context.continued_after_safety_event_without_quitting
        ),
    )


def _map_child_facing_reward(reward) -> Optional[ChildFacingReward]:
    if reward is None:
        return None
    return ChildFacingReward(reward_reason=reward.reward_reason)


def _map_session_aggregate(aggregate) -> SessionAggregate:
    return SessionAggregate(
        task_opportunity_count=aggregate.task_opportunity_count,
        completed_task_count=aggregate.completed_task_count,
        correct_task_count=aggregate.correct_task_count,
        total_attempt_count=aggregate.total_attempt_count,
        accuracy_rate=aggregate.accuracy_rate,
        avg_attempts_per_task=aggregate.avg_attempts_per_task,
        task_completion_rate=aggregate.task_completion_rate,
        inactivity_periods=aggregate.inactivity_periods,
        inactive_time_sec=aggregate.inactive_time_sec,
        inactive_time_available=aggregate.inactive_time_available,
        session_duration_sec=aggregate.session_duration_sec,
        time_in_target_band_sec=aggregate.time_in_target_band_sec,
        consecutive_error_max=aggregate.consecutive_error_max,
        difficulty_floor_hits=aggregate.difficulty_floor_hits,
        quit_after_error=aggregate.quit_after_error,
        safety_override_count=aggregate.safety_override_count,
        c_mean_game_task_latency_sec=aggregate.c_mean_game_task_latency_sec,
        c_median_game_task_latency_sec=aggregate.c_median_game_task_latency_sec,
        current_difficulty_level=aggregate.current_difficulty_level,
        difficulty_trend=aggregate.difficulty_trend,
        session_technical_issue_flag=aggregate.session_technical_issue_flag,
    )


def _to_pkg_session_aggregate(aggregate: SessionAggregate):
    from component_c_generator.aggregation.models import CSessionAggregate as _PkgCSessionAggregate

    return _PkgCSessionAggregate(
        task_opportunity_count=aggregate.task_opportunity_count,
        completed_task_count=aggregate.completed_task_count,
        correct_task_count=aggregate.correct_task_count,
        total_attempt_count=aggregate.total_attempt_count,
        accuracy_rate=aggregate.accuracy_rate,
        avg_attempts_per_task=aggregate.avg_attempts_per_task,
        task_completion_rate=aggregate.task_completion_rate,
        inactivity_periods=aggregate.inactivity_periods,
        inactive_time_sec=aggregate.inactive_time_sec,
        inactive_time_available=aggregate.inactive_time_available,
        session_duration_sec=aggregate.session_duration_sec,
        time_in_target_band_sec=aggregate.time_in_target_band_sec,
        consecutive_error_max=aggregate.consecutive_error_max,
        difficulty_floor_hits=aggregate.difficulty_floor_hits,
        quit_after_error=aggregate.quit_after_error,
        safety_override_count=aggregate.safety_override_count,
        c_mean_game_task_latency_sec=aggregate.c_mean_game_task_latency_sec,
        c_median_game_task_latency_sec=aggregate.c_median_game_task_latency_sec,
        current_difficulty_level=aggregate.current_difficulty_level,
        difficulty_trend=aggregate.difficulty_trend,
        session_technical_issue_flag=aggregate.session_technical_issue_flag,
    )


def _map_engagement_components(components) -> EngagementComponents:
    return EngagementComponents(
        completion_component=components.completion_component,
        activity_component=components.activity_component,
        target_band_component=components.target_band_component,
        accuracy_component=components.accuracy_component,
    )


def _map_frustration_components(components) -> FrustrationComponents:
    return FrustrationComponents(
        error_run_component=components.error_run_component,
        excess_attempt_component=components.excess_attempt_component,
        inactivity_burden_component=components.inactivity_burden_component,
        floor_hit_component=components.floor_hit_component,
        quit_after_error_component=components.quit_after_error_component,
        safety_override_component=components.safety_override_component,
    )


def _to_pkg_provenance(provenance: CToComponent3Provenance) -> _PkgCToComponent3Provenance:
    return _PkgCToComponent3Provenance(
        c_session_number=provenance.c_session_number,
        policy_version=provenance.policy_version,
        production_timestamp=provenance.production_timestamp,
    )


def _to_pkg_c_to_3_engagement_components(
    components: EngagementComponents,
) -> _PkgCToComponent3EngagementComponents:
    """Reverse direction of ``_map_engagement_components`` above. Constructs
    ``models.contracts.EngagementComponents`` -- the SAME type ``emit_c_to_3`` type-hints (it is
    reused verbatim as the composites package's own output type, see
    ``component_c_generator.composites.engagement_frustration``'s module docstring), never a
    different, structurally-similar package type."""
    return _PkgCToComponent3EngagementComponents(
        completion_component=components.completion_component,
        activity_component=components.activity_component,
        target_band_component=components.target_band_component,
        accuracy_component=components.accuracy_component,
    )


def _to_pkg_c_to_3_frustration_components(
    components: FrustrationComponents,
) -> _PkgCToComponent3FrustrationComponents:
    """Reverse direction of ``_map_frustration_components`` above. Constructs
    ``models.contracts.FrustrationComponents`` -- see ``_to_pkg_c_to_3_engagement_components``."""
    return _PkgCToComponent3FrustrationComponents(
        error_run_component=components.error_run_component,
        excess_attempt_component=components.excess_attempt_component,
        inactivity_burden_component=components.inactivity_burden_component,
        floor_hit_component=components.floor_hit_component,
        quit_after_error_component=components.quit_after_error_component,
        safety_override_component=components.safety_override_component,
    )


def _map_c_to_3_payload(payload) -> CToComponent3Payload:
    """Straight 1:1 field copy from the vendored, already-validated ``models.contracts.
    CToComponent3Payload`` to the domain mirror (D1) -- no computation, same convention as every
    other ``_map_*`` helper in this file."""
    return CToComponent3Payload(
        schema_version=payload.schema_version,
        student_id=payload.student_id,
        intervention_session_id=payload.intervention_session_id,
        intervention_session_number=payload.intervention_session_number,
        intervention_session_date=payload.intervention_session_date,
        c_session_id=payload.c_session_id,
        c_session_number=payload.c_session_number,
        component_source=payload.component_source,
        production_timestamp=payload.production_timestamp,
        policy_version=payload.policy_version,
        composite_formula_version=payload.composite_formula_version,
        state_rule_version=payload.state_rule_version,
        telemetry_quality_status=payload.telemetry_quality_status,
        session_technical_issue_flag=payload.session_technical_issue_flag,
        task_opportunity_count=payload.task_opportunity_count,
        completed_task_count=payload.completed_task_count,
        correct_task_count=payload.correct_task_count,
        total_attempt_count=payload.total_attempt_count,
        accuracy_rate=payload.accuracy_rate,
        avg_attempts_per_task=payload.avg_attempts_per_task,
        task_completion_rate=payload.task_completion_rate,
        inactivity_periods=payload.inactivity_periods,
        inactive_time_sec=payload.inactive_time_sec,
        session_duration_sec=payload.session_duration_sec,
        time_in_target_band_sec=payload.time_in_target_band_sec,
        consecutive_error_max=payload.consecutive_error_max,
        difficulty_floor_hits=payload.difficulty_floor_hits,
        quit_after_error=payload.quit_after_error,
        safety_override_count=payload.safety_override_count,
        c_mean_game_task_latency_sec=payload.c_mean_game_task_latency_sec,
        c_median_game_task_latency_sec=payload.c_median_game_task_latency_sec,
        current_difficulty_level=payload.current_difficulty_level,
        difficulty_trend=payload.difficulty_trend,
        engagement_components=(
            _map_engagement_components(payload.engagement_components)
            if payload.engagement_components is not None
            else None
        ),
        engagement_score=payload.engagement_score,
        frustration_components=(
            _map_frustration_components(payload.frustration_components)
            if payload.frustration_components is not None
            else None
        ),
        frustration_index=payload.frustration_index,
        learner_state=payload.learner_state,
        state_reason=payload.state_reason,
    )


def _to_pkg_mastery_payload(
    mastery_by_skill: Mapping[str, float],
    *,
    mastery_source_student_id: str,
    mastery_source_intervention_session_id: str,
    mastery_source_intervention_session_number: int,
) -> _PkgBToCMasteryPayload:
    """PROVISIONAL, SUPERVISOR-RULED, ISOLATED (see module docstring). The only function in this
    codebase that produces a ``models.contracts.BToCMasteryPayload``. If the owner overturns
    this ruling, this is the only function that needs to change.

    The three ``mastery_source_*`` identity fields are B's own — B's ``student_id`` matches
    ``^STU-[0-9]{4}$`` and B's ``intervention_session_id`` matches ``^STU-[0-9]{4}-I-[0-9]{3}$``,
    neither of which is the same value space as C's own ``student_id``/``c_session_id``. They
    must be supplied by the caller; this function never derives or invents them from C's own
    identifiers (G3).

    VALIDATORS BATCH: this no longer constructs ``BToCMasteryPayload`` directly — it builds the
    same field values as a plain dict and calls ``validate_payload(payload, "b_to_c")``
    (Component_C_Master_Build_Plan_v3.0 §5), returning the validated instance that call produces.
    ``schema_version="2.1"`` and ``component_source="B"`` are KEPT, not removed: both are FROZEN
    ``Literal`` fields on the contract model itself, required for the payload to validate at all
    — this is not the adapter inventing or stamping a value, it is supplying the one value the
    frozen contract accepts. F2 (an earlier plan to forbid this literal outright) is WITHDRAWN;
    see the module docstring's mastery-payload note. The real forward concern — rejecting a
    payload that carries the WRONG schema_version once a real caller exists, rather than
    normalising it — is recorded for a future phase, not built here."""
    payload = {
        "mastery_counting": mastery_by_skill["counting"],
        "mastery_number_sense": mastery_by_skill["number_sense"],
        "mastery_place_value": mastery_by_skill["place_value"],
        "mastery_addition": mastery_by_skill["addition"],
        "mastery_subtraction": mastery_by_skill["subtraction"],
        "mastery_multiplication": mastery_by_skill["multiplication"],
        "mastery_division": mastery_by_skill["division"],
        "schema_version": "2.1",
        "student_id": mastery_source_student_id,
        "intervention_session_id": mastery_source_intervention_session_id,
        "intervention_session_number": mastery_source_intervention_session_number,
        "component_source": "B",
    }
    try:
        return _pkg_validate_payload(payload, "b_to_c")
    except _PkgContractValidationError as exc:
        # Phase 4 work order, Q2: never str(exc) -- a pydantic ValidationError's default message
        # echoes the rejected input value verbatim, which would put B mastery values in a
        # client-visible error. Extract ONLY (loc, type) pairs from the chained pydantic
        # ValidationError (never `msg`, never `input`); if no such chain exists (e.g. a
        # prohibited-field rejection, already identified by exact field name), carry no
        # field_errors at all rather than falling back to str(exc).
        pydantic_cause = exc.__cause__
        field_errors: list[tuple[tuple[object, ...], str]] = []
        if hasattr(pydantic_cause, "errors"):
            field_errors = [(tuple(e["loc"]), e["type"]) for e in pydantic_cause.errors()]
        raise MasteryPayloadContractValidationError(field_errors) from exc


def _to_pkg_evidence_window_config(config: EvidenceWindowConfig):
    from component_c_generator.pipeline.config import (
        CEvidenceWindowConfig as _PkgCEvidenceWindowConfig,
    )

    return _PkgCEvidenceWindowConfig(
        config_version=config.config_version,
        parameter_source_status=config.parameter_source_status,
        recent_window_task_count=config.recent_window_task_count,
    )


def _to_pkg_template_generation_params(params: TemplateGenerationParams):
    from component_c_generator.generation_config import (
        TemplateGenerationParams as _PkgTemplateGenerationParams,
    )

    return _PkgTemplateGenerationParams(
        magnitude_a_by_level=params.magnitude_a_by_level,
        magnitude_b_by_level=params.magnitude_b_by_level,
        count_a_by_level=params.count_a_by_level,
        count_b_by_level=params.count_b_by_level,
        choice_set=params.choice_set,
        max_generation_attempts=params.max_generation_attempts,
    )


def _to_pkg_generation_config(config: GenerationConfig):
    from component_c_generator.generation_config import CGenerationConfig as _PkgCGenerationConfig

    return _PkgCGenerationConfig(
        config_version=config.config_version,
        parameter_source_status=config.parameter_source_status,
        per_template={
            template_id: _to_pkg_template_generation_params(params)
            for template_id, params in config.per_template.items()
        },
    )


def _to_pkg_selection_config(config: SelectionConfig):
    from component_c_generator.selection.config import CSelectionConfig as _PkgCSelectionConfig

    return _PkgCSelectionConfig(
        config_version=config.config_version,
        parameter_source_status=config.parameter_source_status,
        familiarization_window_by_grade=dict(config.familiarization_window_by_grade),
        familiarization_difficulty_level=config.familiarization_difficulty_level,
        fallback_difficulty_level=config.fallback_difficulty_level,
        familiarization_session_difficulty_cap=config.familiarization_session_difficulty_cap,
        fallback_difficulty_cap=config.fallback_difficulty_cap,
    )


def _to_pkg_policy_config(config: PolicyConfig):
    from component_c_generator.policy.config import CPolicyConfig as _PkgCPolicyConfig

    return _PkgCPolicyConfig(
        config_version=config.config_version,
        parameter_source_status=config.parameter_source_status,
        increase_correctness_threshold=config.increase_correctness_threshold,
        increase_max_avg_attempts=config.increase_max_avg_attempts,
        increase_max_strain=config.increase_max_strain,
        decrease_correctness_threshold=config.decrease_correctness_threshold,
        decrease_error_run_threshold=config.decrease_error_run_threshold,
        decrease_min_strain=config.decrease_min_strain,
    )


def _to_pkg_safety_config(config: SafetyConfig):
    from component_c_generator.safety.config import CSafetyConfig as _PkgCSafetyConfig

    return _PkgCSafetyConfig(
        config_version=config.config_version,
        parameter_source_status=config.parameter_source_status,
        consecutive_error_trigger=config.consecutive_error_trigger,
        strain_trigger=config.strain_trigger,
        increase_block_window=config.increase_block_window,
        prior_overloaded_disengaged_cap=config.prior_overloaded_disengaged_cap,
        safe_termination_error_threshold=config.safe_termination_error_threshold,
        strain_bucket_low_max=config.strain_bucket_low_max,
        strain_bucket_moderate_max=config.strain_bucket_moderate_max,
        strain_bucket_high_max=config.strain_bucket_high_max,
    )


def _to_pkg_aggregation_config(config: AggregationConfig):
    from component_c_generator.aggregation.config import (
        CAggregationConfig as _PkgCAggregationConfig,
    )

    return _PkgCAggregationConfig(
        config_version=config.config_version,
        parameter_source_status=config.parameter_source_status,
        min_completed_tasks_for_difficulty_trend=config.min_completed_tasks_for_difficulty_trend,
    )


def _to_pkg_scaffold_config(config: ScaffoldConfig):
    from component_c_generator.scaffolds.config import CScaffoldConfig as _PkgCScaffoldConfig

    return _PkgCScaffoldConfig(
        config_version=config.config_version,
        parameter_source_status=config.parameter_source_status,
        level_c1_min_consecutive_incorrect=config.level_c1_min_consecutive_incorrect,
        level_c2_min_consecutive_incorrect=config.level_c2_min_consecutive_incorrect,
        level_c3_min_consecutive_incorrect=config.level_c3_min_consecutive_incorrect,
        level_c4_min_consecutive_incorrect=config.level_c4_min_consecutive_incorrect,
    )


def _to_pkg_recovery_config(config: RecoveryConfig):
    from component_c_generator.scaffolds.recovery import CRecoveryConfig as _PkgCRecoveryConfig

    return _PkgCRecoveryConfig(
        config_version=config.config_version,
        parameter_source_status=config.parameter_source_status,
    )


def _to_pkg_prerequisite_redirect_context(context: PrerequisiteRedirectContext):
    return _PkgPrerequisiteRedirectContext(
        prerequisite_curriculum_node_id=context.prerequisite_curriculum_node_id,
        prerequisite_mastery_bucket=context.prerequisite_mastery_bucket,
    )


class LiveEngineCAdapter:
    """Concrete adapter implementing every ``app.domain.live_engine_c`` port.

    Stateless: every method is a pure function of its arguments (plus, for catalogue-dependent
    calls, a re-read of the governed catalogue file at ``Catalogue.source_path``). No mutable
    instance state is held between calls.
    """

    # ---- CataloguePort ---------------------------------------------------------------

    def load(self, catalogue_path: str) -> Catalogue:
        return _map_catalogue(_load_package_catalogue(catalogue_path))

    def checksum(self, catalogue_path: str) -> str:
        try:
            return _pkg_catalogue_file_checksum(catalogue_path)
        except _PkgCatalogueValidationError as exc:
            raise CatalogueUnavailableError(str(exc)) from exc

    def supported_template_ids(self) -> tuple[str, ...]:
        """The 21st adapter method (Phase 2). Argument-free pass-through to
        ``component_c_generator.tasks.registry.supported_template_ids`` -- code-sourced, not
        catalogue-file-sourced; already a plain ``tuple[str, ...]``, so no type mapping is
        needed."""
        return _pkg_supported_template_ids()

    def production_generation_params_by_template(self) -> Mapping[str, TemplateGenerationParams]:
        """CONNECT Step 4 (supervisor ruling, correcting the #3 surprise): the sanctioned read of
        ``component_c_generator.generation_config.DEFAULT_TEMPLATE_GENERATION_PARAMS``, exposed to
        the application layer the same way ``supported_template_ids`` exposes the package's
        template-id list -- through this one adapter method, never a direct import elsewhere under
        app/ (``test_component_c_generator_full_dotted_path_enforcement``). Argument-free,
        code-sourced (not catalogue-file-sourced), field-by-field mapped into the domain
        ``TemplateGenerationParams`` shape, mirroring ``_to_pkg_template_generation_params``'s own
        reverse direction. Never calls ``default_generation_config()`` -- reads the raw table
        directly, same discipline the S8-a guard already enforces for every other config factory."""
        return {
            template_id: TemplateGenerationParams(
                magnitude_a_by_level=params.magnitude_a_by_level,
                magnitude_b_by_level=params.magnitude_b_by_level,
                count_a_by_level=params.count_a_by_level,
                count_b_by_level=params.count_b_by_level,
                choice_set=params.choice_set,
                max_generation_attempts=params.max_generation_attempts,
            )
            for template_id, params in _pkg_generation_config.DEFAULT_TEMPLATE_GENERATION_PARAMS.items()
        }

    def production_generation_config_version(self) -> str:
        """Companion to ``production_generation_params_by_template`` -- the package's own
        ``GENERATION_CONFIG_VERSION`` string, exposed the same way, so ``task_service.py`` never
        imports ``component_c_generator`` to read either."""
        return _pkg_generation_config.GENERATION_CONFIG_VERSION

    # ---- ActivationPort ---------------------------------------------------------------

    def decide_activation(
        self,
        catalogue: Catalogue,
        game_task_template_id: str,
        supported_template_ids: tuple[str, ...],
        grade: Grade,
    ) -> ActivationDecision:
        pkg_catalogue = _load_package_catalogue(catalogue.source_path)
        template = _template_by_id(pkg_catalogue, game_task_template_id)
        decision = _pkg_decide_activation(
            template, supported_template_ids, grade, pkg_catalogue.catalogue_status
        )
        return _map_activation_decision(decision)

    def eligible_templates(
        self, catalogue: Catalogue, grade: Grade, supported_template_ids: tuple[str, ...]
    ) -> tuple[GameTaskTemplate, ...]:
        pkg_catalogue = _load_package_catalogue(catalogue.source_path)
        templates = _pkg_eligible_templates(pkg_catalogue, grade, supported_template_ids)
        return tuple(_map_game_task_template(t) for t in templates)

    # ---- SessionPhasePort ---------------------------------------------------------------

    def decide_session_phase(self, eligible_combined_handoffs_completed: int, window_w: int) -> str:
        return _pkg_decide_session_phase(eligible_combined_handoffs_completed, window_w)

    def decide_next_session_phase(
        self,
        *,
        session_mode: SessionMode,
        grade: Grade,
        state: LearnerSessionState,
        selection_config: SelectionConfig,
    ) -> SessionPhase:
        pkg_state = _PkgCLearnerSessionState(
            eligible_combined_handoffs_completed=state.eligible_combined_handoffs_completed,
            sessions_since_last_practice=dict(state.sessions_since_last_practice),
            prior_session_end_state=state.prior_session_end_state,
        )
        phase = _pkg_decide_next_session_phase(
            session_mode=session_mode,
            grade=grade,
            state=pkg_state,
            selection_config=_to_pkg_selection_config(selection_config),
        )
        return phase  # type: ignore[return-value]

    def is_eligible_combined_handoff(
        self,
        session_mode: SessionMode,
        b_payload_valid: bool,
        attendance_status: AttendanceStatus,
        technical_blocked_bootstrap: bool,
    ) -> bool:
        return _pkg_is_eligible_combined_handoff(
            session_mode, b_payload_valid, attendance_status, technical_blocked_bootstrap
        )

    def validate_mastery_payload(
        self,
        mastery_by_skill: Mapping[str, float],
        *,
        mastery_source_student_id: str,
        mastery_source_intervention_session_id: str,
        mastery_source_intervention_session_number: int,
    ) -> None:
        """Phase 4's own public entry point to the SF-043 gate at session-creation time --
        distinct from ``select_task``'s internal call to the same private helper (Phase 5).
        Raises ``MasteryPayloadContractValidationError`` on an invalid payload; returns nothing
        on success (Phase 4 does not need or keep the validated instance -- it exists only to
        prove SF-043 ordering and derive ``mastery_context_mode``; R3 forbids caching it, so it
        is discarded, not returned to a caller who might carry it forward)."""
        _to_pkg_mastery_payload(
            mastery_by_skill,
            mastery_source_student_id=mastery_source_student_id,
            mastery_source_intervention_session_id=mastery_source_intervention_session_id,
            mastery_source_intervention_session_number=mastery_source_intervention_session_number,
        )

    # ---- SelectionPort ---------------------------------------------------------------

    def select_task(
        self,
        *,
        session_mode: SessionMode,
        session_phase: str,
        grade: Grade,
        catalogue: Catalogue,
        supported_template_ids: tuple[str, ...],
        student_id: str,
        c_session_id: str,
        task_index: int,
        mastery_payload: Optional[Mapping[str, float]],
        mastery_source_student_id: Optional[str],
        mastery_source_intervention_session_id: Optional[str],
        mastery_source_intervention_session_number: Optional[int],
        sessions_since_last_practice: Mapping[str, int],
        component_c_session_lineage: SeedLineage,
        task_opportunity_lineage: SeedLineage,
        generation_config: GenerationConfig,
        selection_config: SelectionConfig,
    ) -> SelectionResult:
        pkg_catalogue = _load_package_catalogue(catalogue.source_path)
        if mastery_payload is not None:
            # S4 (Phase 5 work order, same treatment as R-5d): `assert` is never a validation
            # mechanism -- stripped entirely under -O, and unstripped it surfaces as an uncaught
            # AssertionError (a 500) rather than a caught, translatable domain error. Phase 5 is
            # the batch that first makes this call path reachable from a real HTTP caller (via
            # TaskService), so the gap R-5d fixed one layer up in session_lifecycle.py is fixed
            # here too, in the one adapter method that had the same bare-assert shape.
            if (
                mastery_source_student_id is None
                or mastery_source_intervention_session_id is None
                or mastery_source_intervention_session_number is None
            ):
                raise SF043OrderingError(
                    "combined-mode select_task requires mastery_payload and all three B identity "
                    "fields together (SF-043) -- caller supplied mastery_payload without a "
                    "complete identity triple"
                )
            pkg_mastery_payload = _to_pkg_mastery_payload(
                mastery_payload,
                mastery_source_student_id=mastery_source_student_id,
                mastery_source_intervention_session_id=mastery_source_intervention_session_id,
                mastery_source_intervention_session_number=mastery_source_intervention_session_number,
            )
        else:
            pkg_mastery_payload = None
        try:
            result = _pkg_select_task(
                session_mode=session_mode,
                session_phase=session_phase,
                grade=grade,
                catalogue=pkg_catalogue,
                supported_template_ids=supported_template_ids,
                student_id=student_id,
                c_session_id=c_session_id,
                task_index=task_index,
                mastery_payload=pkg_mastery_payload,
                sessions_since_last_practice=dict(sessions_since_last_practice),
                component_c_session_lineage=_to_pkg_seed_lineage(component_c_session_lineage),
                task_opportunity_lineage=_to_pkg_seed_lineage(task_opportunity_lineage),
                generation_config=_to_pkg_generation_config(generation_config),
                selection_config=_to_pkg_selection_config(selection_config),
            )
        except _PkgSelectionInputError as exc:
            raise SelectionInputError(str(exc)) from exc
        return _map_selection_result(result)

    # ---- TaskConstructionPort ---------------------------------------------------------------

    def build_task_instance(
        self,
        catalogue: Catalogue,
        game_task_template_id: str,
        seed_lineage: SeedLineage,
        grade: Grade,
        difficulty_level: int,
        student_id: str,
        c_session_id: str,
        task_index: int,
        config: GenerationConfig,
    ) -> TaskInstance:
        pkg_catalogue = _load_package_catalogue(catalogue.source_path)
        template = _template_by_id(pkg_catalogue, game_task_template_id)
        try:
            instance = _pkg_build_task_instance(
                template,
                _to_pkg_seed_lineage(seed_lineage),
                grade,
                difficulty_level,
                student_id,
                c_session_id,
                task_index,
                pkg_catalogue.catalogue_version,
                _to_pkg_generation_config(config),
            )
        except _PkgUnsupportedTemplateError as exc:
            raise UnsupportedTemplateError(str(exc)) from exc
        except _PkgTaskGenerationTechnicalError as exc:
            raise TaskGenerationTechnicalError(str(exc)) from exc
        return _map_task_instance(instance)

    # ---- EvaluationPort ---------------------------------------------------------------

    def evaluate(
        self, task_instance: TaskInstance, learner_action: Mapping[str, object]
    ) -> EvaluationResult:
        try:
            result = _pkg_evaluate(_to_pkg_task_instance(task_instance), dict(learner_action))
        except _PkgEvalUnknownTemplateError as exc:
            raise UnknownTemplateError(str(exc)) from exc
        return _map_evaluation_result(result)

    # ---- SummaryPort ---------------------------------------------------------------

    def derive_task_opportunity_summary(self, events) -> TaskOpportunitySummary:
        pkg_events = [_to_pkg_gameplay_event(e) for e in events]
        summary = _pkg_derive_task_opportunity_summary(pkg_events)
        return _map_task_opportunity_summary(summary)

    # ---- PolicyEvidencePort ---------------------------------------------------------------

    def build_policy_evidence(
        self,
        *,
        session_mode: SessionMode,
        session_phase: SessionPhase,
        current_difficulty_level: int,
        history: Sequence[TaskOpportunitySummary],
        is_recovery_context: bool,
        prior_session_end_state: Optional[LearnerState],
        safety_increase_block_remaining: int,
        config: EvidenceWindowConfig,
    ) -> PolicyObservableEvidence:
        evidence = _pkg_build_policy_evidence(
            session_mode=session_mode,
            session_phase=session_phase,
            current_difficulty_level=current_difficulty_level,
            history=[_to_pkg_task_opportunity_summary(s) for s in history],
            is_recovery_context=is_recovery_context,
            prior_session_end_state=prior_session_end_state,
            safety_increase_block_remaining=safety_increase_block_remaining,
            config=_to_pkg_evidence_window_config(config),
        )
        return _map_policy_observable_evidence(evidence)

    def compute_rolling_strain(self, recent_summaries: Sequence[TaskOpportunitySummary]) -> float:
        return _pkg_compute_rolling_strain(
            [_to_pkg_task_opportunity_summary(s) for s in recent_summaries]
        )

    # ---- AdaptationPort ---------------------------------------------------------------

    def decide_adaptation(
        self,
        *,
        policy_mode: PolicyMode,
        evidence: PolicyObservableEvidence,
        current_difficulty_level: int,
        seed_lineage: SeedLineage,
        policy_config: PolicyConfig,
        safety_config: SafetyConfig,
        selection_config: SelectionConfig,
    ) -> AdaptationDecision:
        try:
            decision = _pkg_decide_adaptation(
                policy_mode=policy_mode,
                evidence=_to_pkg_policy_observable_evidence(evidence),
                current_difficulty_level=current_difficulty_level,
                seed_lineage=_to_pkg_seed_lineage(seed_lineage),
                policy_config=_to_pkg_policy_config(policy_config),
                safety_config=_to_pkg_safety_config(safety_config),
                selection_config=_to_pkg_selection_config(selection_config),
            )
        except _PkgQLearningDisabledError as exc:
            raise QLearningDisabledError(str(exc)) from exc
        except _PkgUnknownPolicyModeError as exc:
            raise UnknownPolicyModeError(str(exc)) from exc
        return _map_adaptation_decision(decision)

    def decide_adaptation_with_safety_flags(
        self,
        *,
        policy_mode: PolicyMode,
        evidence: PolicyObservableEvidence,
        current_difficulty_level: int,
        seed_lineage: SeedLineage,
        policy_config: PolicyConfig,
        safety_config: SafetyConfig,
        selection_config: SelectionConfig,
    ) -> AdaptationDecisionWithSafetyFlags:
        """WORKAROUND -- see this module's own docstring for the full explanation and removal
        trigger. Translates ``evidence`` to the package type EXACTLY ONCE and reuses that SAME
        object across all three pinned calls below (``propose_action``, ``apply_safety``,
        ``decide_adaptation``) -- never a second, independently-translated evidence object. This
        is deliberately ONE method, not two (a ``propose_action`` adapter method plus an
        ``apply_safety`` adapter method would each translate internally and produce two
        package-side evidence objects, destroying the identity guarantee by construction)."""
        pkg_evidence = _to_pkg_policy_observable_evidence(evidence)  # ONCE
        pkg_policy_config = _to_pkg_policy_config(policy_config)
        pkg_safety_config = _to_pkg_safety_config(safety_config)
        pkg_selection_config = _to_pkg_selection_config(selection_config)
        pkg_seed_lineage = _to_pkg_seed_lineage(seed_lineage)

        try:
            pkg_selected_action = _pkg_propose_action(policy_mode, pkg_evidence, pkg_policy_config)
        except _PkgQLearningDisabledError as exc:
            raise QLearningDisabledError(str(exc)) from exc
        except _PkgUnknownPolicyModeError as exc:
            raise UnknownPolicyModeError(str(exc)) from exc

        pkg_safety_decision = _pkg_apply_safety(
            selected_action=pkg_selected_action,
            evidence=pkg_evidence,  # SAME object
            current_difficulty_level=current_difficulty_level,
            selection_config=pkg_selection_config,
            safety_config=pkg_safety_config,
        )

        try:
            pkg_decision = _pkg_decide_adaptation(
                policy_mode=policy_mode,
                evidence=pkg_evidence,  # SAME object
                current_difficulty_level=current_difficulty_level,
                seed_lineage=pkg_seed_lineage,
                policy_config=pkg_policy_config,
                safety_config=pkg_safety_config,
                selection_config=pkg_selection_config,
            )
        except _PkgQLearningDisabledError as exc:
            raise QLearningDisabledError(str(exc)) from exc
        except _PkgUnknownPolicyModeError as exc:
            raise UnknownPolicyModeError(str(exc)) from exc

        return AdaptationDecisionWithSafetyFlags(
            decision=_map_adaptation_decision(pkg_decision),
            activate_recovery_flag=pkg_safety_decision.activate_recovery_flag,
            request_safe_termination=pkg_safety_decision.request_safe_termination,
        )

    # ---- LIVE-01: externally proposed action (frozen Q policy) ---------------------------

    def safety_controller_version(self) -> str:
        """The pinned hard-safety controller's version string (for composing ``policy_version``)."""
        return _PKG_SAFETY_CONTROLLER_VERSION

    def preview_allowed_actions(
        self,
        *,
        evidence: PolicyObservableEvidence,
        current_difficulty_level: int,
        safety_config: SafetyConfig,
        selection_config: SelectionConfig,
    ) -> tuple[str, ...]:
        """The actions (in the order decrease, hold, increase) the pinned ``apply_safety`` would NOT override
        for this evidence -- the ``allowed`` set the Q policy chooses among (as in training, where
        ``DifficultyEnv.allowed_actions`` did exactly this). Never empty: if safety would override all
        three, ``("hold",)`` is returned (training did the same), and safety then disposes of it."""
        pkg_evidence = _to_pkg_policy_observable_evidence(evidence)
        pkg_safety_config = _to_pkg_safety_config(safety_config)
        pkg_selection_config = _to_pkg_selection_config(selection_config)
        allowed = tuple(
            action
            for action in _PROPOSABLE_ACTIONS
            if not _pkg_apply_safety(
                selected_action=action,
                evidence=pkg_evidence,
                current_difficulty_level=current_difficulty_level,
                selection_config=pkg_selection_config,
                safety_config=pkg_safety_config,
            ).action_overridden
        )
        return allowed or ("hold",)

    def decide_with_proposed_action(
        self,
        *,
        selected_action: str,
        policy_mode: PolicyMode,
        policy_version: str,
        rl_state: Optional[Mapping[str, object]],
        evidence: PolicyObservableEvidence,
        current_difficulty_level: int,
        seed_lineage: SeedLineage,
        safety_config: SafetyConfig,
        selection_config: SelectionConfig,
    ) -> AdaptationDecisionWithSafetyFlags:
        """Applies the pinned ``apply_safety`` to an action proposed OUTSIDE the pinned package (the frozen Q
        policy) and composes the ``AdaptationDecision`` itself. The pinned ``decide_adaptation`` cannot be
        used: it raises ``QLearningDisabledError`` for every non-rule ``policy_mode``.

        Field-for-field this is what ``decide_adaptation`` composes for the same applied action (decision_id
        from the seed lineage, applied/overridden/reason/difficulty_after/strain bucket/increase-block from the
        safety decision, ``session_start_state_bucket`` = the evidence's prior session end state), except
        ``policy_mode``, ``policy_version`` and ``rl_state``, which the caller supplies;
        ``internal_reward`` stays ``None`` (frozen policy, no learning). The two flags
        ``decide_adaptation`` drops (``activate_recovery_flag``, ``request_safe_termination``) come straight
        from the same safety decision here -- no second reconstruction call is needed. Proven against the
        rule path by ``tests/test_live01_q_adapter.py``."""
        if selected_action not in _PROPOSABLE_ACTIONS:
            raise UnknownPolicyModeError(f"unknown action {selected_action!r}")
        if policy_mode not in _KNOWN_POLICY_MODES:
            raise UnknownPolicyModeError(f"unknown policy_mode {policy_mode!r}")
        safety = _pkg_apply_safety(
            selected_action=selected_action,
            evidence=_to_pkg_policy_observable_evidence(evidence),
            current_difficulty_level=current_difficulty_level,
            selection_config=_to_pkg_selection_config(selection_config),
            safety_config=_to_pkg_safety_config(safety_config),
        )
        decision = AdaptationDecision(
            decision_id=f"AD-{seed_lineage.seed:016x}",
            policy_mode=policy_mode,
            policy_version=policy_version,
            rl_state=(dict(rl_state) if rl_state is not None else None),
            selected_action=selected_action,
            applied_action=safety.applied_action,
            action_overridden=safety.action_overridden,
            safety_reason=safety.safety_reason,
            difficulty_before=current_difficulty_level,
            difficulty_after=safety.difficulty_after,
            rolling_strain_bucket=safety.rolling_strain_bucket,
            session_start_state_bucket=evidence.prior_session_end_state,
            increase_block_remaining=safety.increase_block_remaining_after,
            internal_reward=None,
            seed_lineage=seed_lineage,
        )
        return AdaptationDecisionWithSafetyFlags(
            decision=decision,
            activate_recovery_flag=safety.activate_recovery_flag,
            request_safe_termination=safety.request_safe_termination,
        )

    # ---- ScaffoldPort ---------------------------------------------------------------

    def decide_scaffold_level(
        self, context: ScaffoldDecisionContext, config: ScaffoldConfig
    ) -> ScaffoldLevel:
        return _pkg_decide_scaffold_level(
            _to_pkg_scaffold_decision_context(context), _to_pkg_scaffold_config(config)
        )

    # ---- RecoveryPort ---------------------------------------------------------------

    def build_recovery_task(
        self,
        parent_instance: TaskInstance,
        skill_id: str,
        task_index: int,
        catalogue: Catalogue,
        supported_template_ids: tuple[str, ...],
        generation_config: GenerationConfig,
        seed_lineage: SeedLineage,
        recovery_config: RecoveryConfig,
        *,
        safety_required: bool = False,
        prerequisite_context: Optional[PrerequisiteRedirectContext] = None,
    ) -> TaskInstance:
        pkg_catalogue = _load_package_catalogue(catalogue.source_path)
        try:
            instance = _pkg_build_recovery_task(
                _to_pkg_task_instance(parent_instance),
                skill_id,
                task_index,
                pkg_catalogue,
                supported_template_ids,
                _to_pkg_generation_config(generation_config),
                _to_pkg_seed_lineage(seed_lineage),
                _to_pkg_recovery_config(recovery_config),
                safety_required=safety_required,
                prerequisite_context=(
                    _to_pkg_prerequisite_redirect_context(prerequisite_context)
                    if prerequisite_context is not None
                    else None
                ),
            )
        except _PkgNoEligibleRecoveryTemplateError as exc:
            raise NoEligibleRecoveryTemplateError(str(exc)) from exc
        except _PkgRecoveryPreconditionError as exc:
            raise RecoveryPreconditionError(str(exc)) from exc
        return _map_task_instance(instance)

    # ---- RewardPort ---------------------------------------------------------------

    def decide_child_facing_reward(
        self, context: RewardOutcomeContext
    ) -> Optional[ChildFacingReward]:
        reward = _pkg_decide_child_facing_reward(_to_pkg_reward_outcome_context(context))
        return _map_child_facing_reward(reward)

    # ---- AggregationPort ---------------------------------------------------------------

    def derive_session_aggregate(
        self,
        events,
        summaries: Sequence[TaskOpportunitySummary],
        adaptation_decisions: Sequence[AdaptationDecision],
        *,
        time_in_target_band_sec: float,
        safety_override_count: int,
        inactive_time_available: bool,
        config: AggregationConfig,
    ) -> SessionAggregate:
        aggregate = _pkg_derive_session_aggregate(
            [_to_pkg_gameplay_event(e) for e in events],
            [_to_pkg_task_opportunity_summary(s) for s in summaries],
            [_to_pkg_adaptation_decision(d) for d in adaptation_decisions],
            time_in_target_band_sec=time_in_target_band_sec,
            safety_override_count=safety_override_count,
            inactive_time_available=inactive_time_available,
            config=_to_pkg_aggregation_config(config),
        )
        return _map_session_aggregate(aggregate)

    # ---- CompositePort ---------------------------------------------------------------

    def compute_engagement(
        self, aggregate: SessionAggregate, formula_version: CompositeFormulaVersion
    ) -> tuple[EngagementComponents, float]:
        components, score = _pkg_compute_engagement(
            _to_pkg_session_aggregate(aggregate), formula_version
        )
        return _map_engagement_components(components), score

    def compute_frustration(
        self, aggregate: SessionAggregate, formula_version: CompositeFormulaVersion
    ) -> tuple[FrustrationComponents, float]:
        components, score = _pkg_compute_frustration(
            _to_pkg_session_aggregate(aggregate), formula_version
        )
        return _map_frustration_components(components), score

    def decide_telemetry_quality_status(
        self,
        session_technical_issue_flag: bool,
        task_opportunity_count: int,
        completed_task_count: int,
        session_duration_sec: float,
        accuracy_rate: Optional[float],
        task_completion_rate: Optional[float],
    ) -> TelemetryQualityStatus:
        return _pkg_decide_telemetry_quality_status(
            session_technical_issue_flag,
            task_opportunity_count,
            completed_task_count,
            session_duration_sec,
            accuracy_rate,
            task_completion_rate,
        )

    def decide_learner_state(
        self,
        telemetry_quality_status: TelemetryQualityStatus,
        safety_override_count: int,
        consecutive_error_max: int,
        quit_after_error: bool,
        difficulty_floor_hits: int,
        task_completion_rate: float,
        inactivity_periods: int,
        engagement_score: Optional[float],
        frustration_index: Optional[float],
    ) -> tuple[Optional[LearnerState], StateReason]:
        return _pkg_decide_learner_state(
            telemetry_quality_status,
            safety_override_count,
            consecutive_error_max,
            quit_after_error,
            difficulty_floor_hits,
            task_completion_rate,
            inactivity_periods,
            engagement_score,
            frustration_index,
        )

    # ---- EmissionPort ---------------------------------------------------------------

    def emit_c_to_3(
        self,
        mapping_row: Mapping[str, object],
        *,
        provenance: CToComponent3Provenance,
        aggregate: SessionAggregate,
        telemetry_quality_status: TelemetryQualityStatus,
        composite_formula_version: CompositeFormulaVersion,
        learner_state: Optional[LearnerState],
        state_reason: StateReason,
        engagement_components: Optional[EngagementComponents] = None,
        engagement_score: Optional[float] = None,
        frustration_components: Optional[FrustrationComponents] = None,
        frustration_index: Optional[float] = None,
    ) -> CToComponent3Payload:
        """SF-040 (9b-1): calls the vendored ``component_c_generator.c_to_3.emit.emit_c_to_3``
        and maps its validated result to the domain ``CToComponent3Payload`` (D1). Translates the
        vendored ``NoRealCSessionError`` at the boundary exactly the way every other vendored
        exception in this file is translated (e.g. ``MasteryPayloadContractValidationError``) --
        it never escapes into ``app.domain``/``app.application`` unmapped.

        ``aggregate`` is REQUIRED with NO DEFAULT and is not ``Optional`` -- this is 9b-1
        obligation 4a's static proof: there is no way to call this method without an aggregate in
        hand. It does not by itself trace a live aggregation refusal reaching this call and
        stopping before it -- that dynamic half needs a real caller, which is out of this batch's
        scope (see this method's own build-log entry)."""
        try:
            pkg_payload = _pkg_emit_c_to_3(
                mapping_row,
                provenance=_to_pkg_provenance(provenance),
                aggregate=_to_pkg_session_aggregate(aggregate),
                telemetry_quality_status=telemetry_quality_status,
                composite_formula_version=composite_formula_version,
                learner_state=learner_state,
                state_reason=state_reason,
                engagement_components=(
                    _to_pkg_c_to_3_engagement_components(engagement_components)
                    if engagement_components is not None
                    else None
                ),
                engagement_score=engagement_score,
                frustration_components=(
                    _to_pkg_c_to_3_frustration_components(frustration_components)
                    if frustration_components is not None
                    else None
                ),
                frustration_index=frustration_index,
            )
        except _PkgNoRealCSessionError as exc:
            raise NoRealCSessionError(str(exc)) from exc
        return _map_c_to_3_payload(pkg_payload)
