"""Backend-owned domain types for the Component C live-engine ports (Phase 1 batch 1b).

Plain, immutable ``dataclasses`` — never the vendored package's Pydantic models (X-3). Field
sets are structural mirrors of the package types the 20 verified §7 calls return or accept,
inspected directly against the installed wheel, not assumed.

CONFIG TYPES CARRY NO DEFAULT ON ANY FIELD. Component C is PROPOSED, not approved
(Component_C_Master_Build_Plan_v3.0 §2); every field on ``EvidenceWindowConfig``,
``GenerationConfig``, ``TemplateGenerationParams``, ``SelectionConfig``, ``PolicyConfig``,
``SafetyConfig``, ``AggregationConfig``, ``ScaffoldConfig``, and ``RecoveryConfig`` is a
threshold, weight, window, or cap the owner has not signed off on. A default value on any of
these fields would be this adapter recording an unapproved scientific parameter — G1 forbids
that in any form, including a default. Every field below is therefore required with no default;
this is asserted by test, not left to review (see
``backend/tests/test_be2_architecture_guards.py::test_no_domain_config_field_carries_a_default``).

NO ``BToCMasteryPayload`` MIRROR HERE. §5 says Component C *consumes*
``models.contracts.BToCMasteryPayload`` and must not re-declare the contract; X-3 says no
package type may cross into ``app.domain``. These two rules conflict for this one type. The
supervisor's provisional resolution (pending owner confirmation) is that the adapter accepts the
seven mastery values as a plain ``Mapping[str, float]`` and constructs the package contract type
internally, in one named, isolated helper — see
``app.infrastructure.live_engine_c.adapter._to_pkg_mastery_payload``. No domain type is declared
for it here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal, Mapping, Optional

Grade = int  # 2 or 3, enforced by callers/validators at the boundary

# --------------------------------------------------------------------------------------
# Standalone enumerations — each is itself the return/parameter type of at least one §7 call,
# so the package's own value set is preserved exactly (verified against the installed wheel's
# Literal definitions). Fields that merely EMBED one of these inside a larger structure are
# typed ``str`` below, matching how app.domain.live_engine already treats embedded status
# strings (e.g. Catalogue.catalogue_status, SessionIdentity.status) — a structural mirror, not a
# byte-exact retyping of every nested Literal.
# --------------------------------------------------------------------------------------

SessionMode = Literal["combined", "c_only"]
SessionPhase = Literal["familiarization", "mastery_driven", "c_only"]
LearnerState = Literal["engaged", "productive_struggle", "overloaded", "disengaged"]
# Phase 4: verified live against the installed wheel's component_c_generator.models.enums.
AttendanceStatus = Literal["attended", "partial", "missed"]
PolicyMode = Literal["rule_based_baseline", "q_learning_offline", "frozen_q_evaluation"]
ScaffoldLevel = Literal["C0", "C1", "C2", "C3", "C4"]
CompositeFormulaVersion = Literal["C-COMP-v1", "C-COMP-v1-fallback-periods"]
TelemetryQualityStatus = Literal["complete", "insufficient_evidence", "technical_issue"]
StateReason = Literal[
    "technical_issue",
    "insufficient_session_evidence",
    "safety_override_with_error_burst",
    "quit_after_error",
    "repeated_floor_hits_with_low_completion",
    "high_behavioral_friction",
    "low_engagement_score",
    "inactivity_with_low_completion",
    "high_engagement_low_friction",
    "sustained_participation_under_challenge",
    "insufficient_sustained_participation",
]


# --------------------------------------------------------------------------------------
# Seeds — plain data only (Q1/C3: the adapter maps this shape; it never derives a seed value).
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class SeedLineage:
    """Mirrors ``component_c_generator.models.seed.CSeedLineage`` exactly (its only three
    fields, verified against the installed wheel). Holds no derivation logic — the adapter
    exposes no wrapper for ``seeds.derive_child_lineage``, ``seeds.SeedManager``,
    ``seeds.rng_from``, or ``seeds.SUBSTREAMS``; obtaining a real seed value is left to whichever
    future phase's work order explicitly authorizes that call."""

    global_seed: int
    path: tuple[tuple[str, str], ...]
    seed: int


# --------------------------------------------------------------------------------------
# Catalogue
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class GameFamily:
    game_family_id: str
    family_name: str
    template_id_prefix: str


@dataclass(frozen=True)
class GameTaskTemplate:
    game_family_id: str
    family_name: str
    game_task_template_id: str
    template_title: str
    primary_skill_ids: tuple[str, ...]
    curriculum_node_ids: tuple[str, ...]
    grade_scope_text: str
    status: str
    status_note: Optional[str]
    functional_role: str
    representations: tuple[str, ...]
    representations_note: Optional[str]
    learner_action: str
    correctness: str
    error_signatures: Optional[tuple[str, ...]]
    main_difficulty_levers: str
    recovery: str
    eligible_grades: tuple[int, ...]
    grade_gate_status: str


@dataclass(frozen=True)
class Catalogue:
    catalogue_version: str
    catalogue_status: str
    source_path: str
    skills: tuple[str, ...]
    families: tuple[GameFamily, ...]
    templates: tuple[GameTaskTemplate, ...]


# --------------------------------------------------------------------------------------
# Activation / eligibility
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ActivationDecision:
    game_task_template_id: str
    recognized: bool
    generation_supported: bool
    grade_eligible: bool
    curriculum_active: bool
    catalogue_status_ok: bool
    calibration_restricted: bool
    active: bool
    reason: str


# --------------------------------------------------------------------------------------
# Selection
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class SelectionResult:
    session_phase: str
    selected_skill_id: str
    selected_template_id: str
    initial_difficulty_level: int
    mastery_context_mode: str
    mastery_selected_skill: Optional[float]
    task_instance: "TaskInstance"


# --------------------------------------------------------------------------------------
# Deterministic task construction
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class TaskInstance:
    game_family_id: str
    game_task_template_id: str
    game_task_instance_id: str
    template_version: str
    catalogue_version: str
    generator_version: str
    seed_lineage: SeedLineage
    student_id: str
    c_session_id: str
    task_index: int
    skill_id: str
    curriculum_node_id: str
    grade_scope: int
    difficulty_level: int
    difficulty_vector: Mapping[str, object]
    functional_role: str
    representation_mode: str
    prompt_payload: Mapping[str, object]
    interactive_assets: Mapping[str, object]
    correct_answer_payload: Mapping[str, object]
    correctness_function_id: str
    valid_action_space: Mapping[str, object]
    completion_condition: str
    failure_condition: str
    scaffold_state: ScaffoldLevel
    recovery_parent_instance_id: Optional[str]
    technical_status: str


@dataclass(frozen=True)
class PrerequisiteRedirectContext:
    prerequisite_curriculum_node_id: str
    prerequisite_mastery_bucket: str


# --------------------------------------------------------------------------------------
# Evaluation
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class EvaluationResult:
    game_task_instance_id: str
    game_task_template_id: str
    correctness_function_id: str
    learner_action: Mapping[str, object]
    is_correct: bool
    details: Mapping[str, object]


# --------------------------------------------------------------------------------------
# Gameplay events and derived summary
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class GameplayEvent:
    event_id: str
    event_type: str
    event_index: int
    student_id: str
    intervention_session_id: str
    c_session_id: str
    game_task_instance_id: str
    task_index: int
    attempt_number: Optional[int]
    event_timestamp_relative_ms: int
    action_payload: Optional[Mapping[str, object]]
    evaluation_payload: Optional[Mapping[str, object]]
    scaffold_code: Optional[ScaffoldLevel]
    technical_flag: bool
    terminal_reason: Optional[str]
    seed_lineage: SeedLineage
    generator_version: str
    config_checksum: str


@dataclass(frozen=True)
class TaskOpportunitySummary:
    student_id: str
    intervention_session_id: str
    c_session_id: str
    game_task_instance_id: str
    task_index: int
    task_offered: bool
    task_started: bool
    task_completed: bool
    task_skipped: bool
    task_quit: bool
    technical_issue: bool
    correct_task: Optional[bool]
    total_attempts: int
    retry_count: int
    scaffold_requested: bool
    scaffold_count: int
    highest_scaffold_level: Optional[ScaffoldLevel]
    c_answer_changes: int
    task_latency_sec: Optional[float]
    inactive_time_sec: float
    inactivity_periods: int
    quit_after_error: bool
    terminal_reason: Optional[str]
    first_attempt_correct: Optional[bool]
    final_attempt_correct: Optional[bool]
    consecutive_error_max_within_task: int


# --------------------------------------------------------------------------------------
# Policy evidence and adaptation
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class PolicyObservableEvidence:
    session_mode: SessionMode
    session_phase: SessionPhase
    current_difficulty_level: int
    recent_correctness_rate: float
    recent_avg_attempts: float
    recent_inactivity_periods: int
    recent_scaffold_use_count: int
    recent_consecutive_error_max: int
    rolling_strain_score: float
    prior_session_end_state: Optional[LearnerState]
    is_recovery_context: bool
    technical_issue_current_task: bool
    safety_increase_block_remaining: int


@dataclass(frozen=True)
class AdaptationDecision:
    decision_id: str
    policy_mode: PolicyMode
    policy_version: str
    rl_state: Optional[Mapping[str, object]]
    selected_action: str
    applied_action: str
    action_overridden: bool
    safety_reason: Optional[str]
    difficulty_before: int
    difficulty_after: int
    rolling_strain_bucket: str
    session_start_state_bucket: Optional[LearnerState]
    increase_block_remaining: int
    internal_reward: Optional[float]
    seed_lineage: SeedLineage


@dataclass(frozen=True)
class AdaptationDecisionWithSafetyFlags:
    """WORKAROUND -- see the module docstring of ``app.infrastructure.live_engine_c.adapter``
    and that module's ``decide_adaptation_with_safety_flags`` for the full explanation.

    ``component_c_generator.adaptation.decide_adaptation`` computes a
    ``safety.controller.SafetyDecision`` internally and drops two of its fields
    (``activate_recovery_flag``, ``request_safe_termination``) when composing the
    ``AdaptationDecision`` it returns -- ``AdaptationDecision`` is ``frozen=True`` and
    ``extra="forbid"``, so neither field can be attached after the fact. This type carries the
    real, package-composed ``AdaptationDecision`` (mapped, never re-derived) PLUS the two
    otherwise-unreachable flags, reconstructed by calling the same pure, deterministic
    ``propose_action`` + ``apply_safety`` sequence a second time on an identical evidence object.

    NAMED FIELDS, NOT POSITIONAL BOOLEANS: ``activate_recovery_flag`` and
    ``request_safe_termination`` are two adjacent booleans in the source ``SafetyDecision`` --
    returning them positionally would be a transposition hazard, so both are named fields here.

    REMOVAL TRIGGER: delete this type, the adapter method that produces it, its port
    declaration, the parity test that proves it, and the manifest's forward-looking verification
    requirement, together, the moment the wheel is re-pinned to a Yass commit carrying the
    owner-authorized ``AdaptationDecision`` interface change (task_index,
    activate_recovery_flag, request_safe_termination as real fields on the package's own
    ``AdaptationDecision``)."""

    decision: AdaptationDecision
    activate_recovery_flag: bool
    request_safe_termination: bool


# --------------------------------------------------------------------------------------
# Scaffolds and rewards
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ScaffoldDecisionContext:
    consecutive_incorrect_current_task: int
    safety_forces_recovery: bool


@dataclass(frozen=True)
class RewardOutcomeContext:
    task_completed_correctly: bool
    is_recovery_task: bool
    retried_after_incorrect_then_continued: bool
    continued_after_safety_event_without_quitting: bool


@dataclass(frozen=True)
class ChildFacingReward:
    reward_reason: str


# --------------------------------------------------------------------------------------
# Aggregation and composites
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class SessionAggregate:
    task_opportunity_count: int
    completed_task_count: int
    correct_task_count: int
    total_attempt_count: int
    accuracy_rate: Optional[float]
    avg_attempts_per_task: Optional[float]
    task_completion_rate: float
    inactivity_periods: int
    inactive_time_sec: float
    inactive_time_available: bool
    session_duration_sec: float
    time_in_target_band_sec: float
    consecutive_error_max: int
    difficulty_floor_hits: int
    quit_after_error: bool
    safety_override_count: int
    c_mean_game_task_latency_sec: Optional[float]
    c_median_game_task_latency_sec: Optional[float]
    current_difficulty_level: int
    difficulty_trend: str
    session_technical_issue_flag: bool


@dataclass(frozen=True)
class EngagementComponents:
    completion_component: float
    activity_component: float
    target_band_component: float
    accuracy_component: float


@dataclass(frozen=True)
class FrustrationComponents:
    error_run_component: float
    excess_attempt_component: float
    inactivity_burden_component: float
    floor_hit_component: float
    quit_after_error_component: float
    safety_override_component: float


# --------------------------------------------------------------------------------------
# Config types — every field REQUIRED, NO default anywhere (see module docstring). These are
# structural pass-through shapes only: nothing in this batch constructs one with real values;
# no caller exists yet (X-6/G1 — Phase 1b wires no orchestration).
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class EvidenceWindowConfig:
    config_version: str
    parameter_source_status: str
    recent_window_task_count: int


@dataclass(frozen=True)
class TemplateGenerationParams:
    magnitude_a_by_level: Optional[tuple[int, int, int, int, int]]
    magnitude_b_by_level: Optional[tuple[int, int, int, int, int]]
    count_a_by_level: Optional[tuple[int, int, int, int, int]]
    count_b_by_level: Optional[tuple[int, int, int, int, int]]
    choice_set: Optional[tuple[int, ...]]
    max_generation_attempts: int


@dataclass(frozen=True)
class GenerationConfig:
    config_version: str
    parameter_source_status: str
    per_template: Mapping[str, TemplateGenerationParams]


@dataclass(frozen=True)
class LearnerSessionState:
    """Phase 4. Structural mirror of the package's ``CLearnerSessionState`` (cold-start
    assessment §5): the C-owned, non-B-derived cross-session state. Carries NO ``mastery_*`` /
    B-shaped field of any kind (SF-043) -- deliberate omission, exactly like the package type it
    mirrors."""

    eligible_combined_handoffs_completed: int
    sessions_since_last_practice: Mapping[str, int]
    prior_session_end_state: Optional[LearnerState]


@dataclass(frozen=True)
class SelectionConfig:
    config_version: str
    parameter_source_status: str
    familiarization_window_by_grade: Mapping[int, int]
    familiarization_difficulty_level: int
    fallback_difficulty_level: int
    familiarization_session_difficulty_cap: int
    fallback_difficulty_cap: int


@dataclass(frozen=True)
class PolicyConfig:
    config_version: str
    parameter_source_status: str
    increase_correctness_threshold: float
    increase_max_avg_attempts: float
    increase_max_strain: float
    decrease_correctness_threshold: float
    decrease_error_run_threshold: int
    decrease_min_strain: float


@dataclass(frozen=True)
class SafetyConfig:
    config_version: str
    parameter_source_status: str
    consecutive_error_trigger: int
    strain_trigger: float
    increase_block_window: int
    prior_overloaded_disengaged_cap: int
    safe_termination_error_threshold: int
    strain_bucket_low_max: float
    strain_bucket_moderate_max: float
    strain_bucket_high_max: float


@dataclass(frozen=True)
class AggregationConfig:
    config_version: str
    parameter_source_status: str
    min_completed_tasks_for_difficulty_trend: int


@dataclass(frozen=True)
class ScaffoldConfig:
    config_version: str
    parameter_source_status: str
    level_c1_min_consecutive_incorrect: int
    level_c2_min_consecutive_incorrect: int
    level_c3_min_consecutive_incorrect: int
    level_c4_min_consecutive_incorrect: int


@dataclass(frozen=True)
class RecoveryConfig:
    config_version: str
    parameter_source_status: str


# --------------------------------------------------------------------------------------
# C -> 3 emission payload and provenance (9b-1, v3.0 §11 Phase 9). Backend-owned structural
# mirrors of ``models.contracts.CToComponent3Payload`` / ``CToComponent3Provenance`` (X-3: no
# vendored package/pydantic type crosses into app.domain). Field sets are a 1:1 copy of the
# vendored contract model's own fields, verified directly against
# ``packaging/component_b_internal/models/contracts.py`` and
# ``packaging/component_c_internal/component_c_generator/c_to_3/inputs.py``. Neither type carries
# any validation logic of its own -- ``CToComponent3Payload.validate_deterministic_invariants``
# stays owned by the vendored, frozen contract model; this dataclass is populated only from an
# already-validated package payload (see
# ``app.infrastructure.live_engine_c.adapter._map_c_to_3_payload``).
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class CToComponent3Provenance:
    """Mirrors ``component_c_generator.c_to_3.inputs.CToComponent3Provenance`` exactly (its only
    three fields) -- no derivation logic, plain data only, same convention as ``SeedLineage``."""

    c_session_number: int
    policy_version: str
    production_timestamp: datetime


@dataclass(frozen=True)
class CToComponent3Payload:
    """Mirrors ``models.contracts.CToComponent3Payload`` field-for-field (39 fields)."""

    schema_version: str
    student_id: str
    intervention_session_id: str
    intervention_session_number: int
    intervention_session_date: date
    c_session_id: str
    c_session_number: int
    component_source: str
    production_timestamp: datetime
    policy_version: str
    composite_formula_version: CompositeFormulaVersion
    state_rule_version: str
    telemetry_quality_status: TelemetryQualityStatus
    session_technical_issue_flag: bool

    task_opportunity_count: int
    completed_task_count: int
    correct_task_count: int
    total_attempt_count: int
    accuracy_rate: Optional[float]
    avg_attempts_per_task: Optional[float]
    task_completion_rate: float

    inactivity_periods: int
    inactive_time_sec: float
    session_duration_sec: float
    time_in_target_band_sec: float

    consecutive_error_max: int
    difficulty_floor_hits: int
    quit_after_error: bool
    safety_override_count: int

    c_mean_game_task_latency_sec: Optional[float]
    c_median_game_task_latency_sec: Optional[float]

    current_difficulty_level: int
    difficulty_trend: str

    engagement_components: Optional[EngagementComponents]
    engagement_score: Optional[float]
    frustration_components: Optional[FrustrationComponents]
    frustration_index: Optional[float]

    learner_state: Optional[LearnerState]
    state_reason: StateReason
