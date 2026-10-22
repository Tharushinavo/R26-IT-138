from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

StudentId = Annotated[str, StringConstraints(pattern=r"^STU-[0-9]{4}$")]
InterventionSessionId = Annotated[str, StringConstraints(pattern=r"^STU-[0-9]{4}-I-[0-9]{3}$")]
BSessionId = Annotated[str, StringConstraints(pattern=r"^STU-[0-9]{4}-B-[0-9]{3}$")]
CSessionId = Annotated[str, StringConstraints(pattern=r"^STU-[0-9]{4}-C-[0-9]{3}$")]
Probability = Annotated[float, Field(ge=0.0, le=1.0)]
PositiveTiming = Annotated[float, Field(gt=0.0, le=90.0)]
Slope = Annotated[float, Field(ge=-0.2, le=0.2)]

SKILLS = (
    "counting", "number_sense", "place_value", "addition",
    "subtraction", "multiplication", "division",
)
ERROR_CLASSES = (
    "correct", "off_by_one", "place_value", "operator_confusion",
    "transposition", "fact_retrieval", "timeout_no_response", "random",
)


def _student_prefix(identifier: str) -> str:
    return identifier[:8]


class StrictContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SkillBooleans(StrictContractModel):
    counting: bool
    number_sense: bool
    place_value: bool
    addition: bool
    subtraction: bool
    multiplication: bool
    division: bool


class SkillSlopes(StrictContractModel):
    counting: Slope | None
    number_sense: Slope | None
    place_value: Slope | None
    addition: Slope | None
    subtraction: Slope | None
    multiplication: Slope | None
    division: Slope | None


class SkillCounts(StrictContractModel):
    counting: Annotated[int, Field(ge=0)]
    number_sense: Annotated[int, Field(ge=0)]
    place_value: Annotated[int, Field(ge=0)]
    addition: Annotated[int, Field(ge=0)]
    subtraction: Annotated[int, Field(ge=0)]
    multiplication: Annotated[int, Field(ge=0)]
    division: Annotated[int, Field(ge=0)]


class ErrorDistribution(StrictContractModel):
    correct: Probability
    off_by_one: Probability
    place_value: Probability
    operator_confusion: Probability
    transposition: Probability
    fact_retrieval: Probability
    timeout_no_response: Probability
    random: Probability


class MasteryFields(StrictContractModel):
    mastery_counting: Probability
    mastery_number_sense: Probability
    mastery_place_value: Probability
    mastery_addition: Probability
    mastery_subtraction: Probability
    mastery_multiplication: Probability
    mastery_division: Probability


class SharedInterventionSessionMapping(StrictContractModel):
    schema_version: Literal["1.0"]
    student_id: StudentId
    intervention_session_id: InterventionSessionId
    intervention_session_number: Annotated[int, Field(ge=1, le=25)]
    intervention_session_date: date
    b_session_id: BSessionId | None
    c_session_id: Annotated[str, StringConstraints(pattern=r"^STU-[0-9]{4}-C-[0-9]{3}$")] | None
    b_present: bool
    c_present: bool

    @model_validator(mode="after")
    def validate_mapping_invariants(self):
        ids = [self.intervention_session_id, self.b_session_id, self.c_session_id]
        if any(value is not None and _student_prefix(value) != self.student_id for value in ids):
            raise ValueError("ID-05: session identifier prefix must match student_id")
        if not (self.b_present or self.c_present):
            raise ValueError("CD-01/CD-05: an empty intervention session is prohibited")
        if self.b_present != (self.b_session_id is not None):
            raise ValueError("CD-04: b_present must equal b_session_id presence")
        if self.c_present != (self.c_session_id is not None):
            raise ValueError("CD-04: c_present must equal c_session_id presence")
        return self


class BToCMasteryPayload(MasteryFields):
    schema_version: Literal["2.1"]
    student_id: StudentId
    intervention_session_id: InterventionSessionId
    intervention_session_number: Annotated[int, Field(ge=1, le=25)]
    component_source: Literal["B"]
    production_timestamp: datetime | None = None

    @model_validator(mode="after")
    def validate_prefix(self):
        if _student_prefix(self.intervention_session_id) != self.student_id:
            raise ValueError("ID-05: intervention_session_id prefix must match student_id")
        return self


class BToComponent3Payload(MasteryFields):
    schema_version: Literal["2.1"]
    student_id: StudentId
    b_session_id: BSessionId
    b_session_number: Annotated[int, Field(ge=1)]
    intervention_session_id: InterventionSessionId
    intervention_session_number: Annotated[int, Field(ge=1, le=25)]
    intervention_session_date: date
    component_source: Literal["B"]
    total_questions: Annotated[int, Field(ge=1, le=40)]
    correct_responses: Annotated[int, Field(ge=0)]
    accuracy_rate: Probability
    hint_requests: Annotated[int, Field(ge=0)]
    # Nullable (SPEC §I0, resolved): an all-timeout attended session has no valid RT
    # observation to report. Null is the honest "no evidence" value -- never a fabricated
    # number -- and the row is still emitted with mastery/accuracy/error/hint data intact.
    # When present, the positivity constraint (PositiveTiming) still applies.
    b_mean_item_response_time_sec: PositiveTiming | None = None
    b_median_item_response_time_sec: PositiveTiming | None = None
    b_item_response_time_std_sec: PositiveTiming | None = None
    mastery_certified: SkillBooleans
    error_class_dist: ErrorDistribution
    mastery_slope_w4: SkillSlopes
    opportunities_w4: SkillCounts
    guess_guard_triggered: Annotated[int, Field(ge=0)] | None = None
    selection_reason: Literal[
        "mastery_gap", "prereq_gap", "spaced_review", "recommendation_override"
    ] | None = None

    @model_validator(mode="after")
    def validate_deterministic_invariants(self):
        if _student_prefix(self.intervention_session_id) != self.student_id or _student_prefix(self.b_session_id) != self.student_id:
            raise ValueError("ID-05: session identifier prefix must match student_id")
        if self.correct_responses > self.total_questions:
            raise ValueError("DF-01: correct_responses must not exceed total_questions")
        if abs(self.accuracy_rate - self.correct_responses / self.total_questions) > 1e-6:
            raise ValueError("DF-01: accuracy_rate must equal correct_responses / total_questions")
        if self.hint_requests > self.total_questions:
            raise ValueError("DF-02: hint_requests must not exceed total_questions")
        distribution = self.error_class_dist.model_dump()
        if abs(sum(distribution.values()) - 1.0) > 1e-6:
            raise ValueError("DF-03: error_class_dist values must sum to 1.0 +/- 1e-6")
        if self.b_median_item_response_time_sec is not None and self.b_mean_item_response_time_sec is not None:
            if self.b_median_item_response_time_sec > self.b_mean_item_response_time_sec * 1.5:
                raise ValueError("RG-04: B median timing exceeds the mean-times-1.5 sanity bound")
        return self


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


class EngagementComponents(StrictContractModel):
    completion_component: Probability
    activity_component: Probability
    target_band_component: Probability
    accuracy_component: Probability


class FrustrationComponents(StrictContractModel):
    error_run_component: Probability
    excess_attempt_component: Probability
    inactivity_burden_component: Probability
    floor_hit_component: Probability
    quit_after_error_component: Probability
    safety_override_component: Probability


class CToComponent3Payload(StrictContractModel):
    schema_version: Literal["3.0"]
    student_id: StudentId
    intervention_session_id: InterventionSessionId
    intervention_session_number: Annotated[int, Field(ge=1, le=25)]
    intervention_session_date: date
    c_session_id: CSessionId
    c_session_number: Annotated[int, Field(ge=1)]
    component_source: Literal["C"]
    production_timestamp: datetime
    policy_version: str
    composite_formula_version: Literal["C-COMP-v1", "C-COMP-v1-fallback-periods"]
    state_rule_version: Literal["C-LS-v1"]
    telemetry_quality_status: Literal["complete", "insufficient_evidence", "technical_issue"]
    session_technical_issue_flag: bool

    task_opportunity_count: Annotated[int, Field(ge=0)]
    completed_task_count: Annotated[int, Field(ge=0)]
    correct_task_count: Annotated[int, Field(ge=0)]
    total_attempt_count: Annotated[int, Field(ge=0)]
    accuracy_rate: Probability | None
    avg_attempts_per_task: Annotated[float, Field(ge=1.0)] | None
    task_completion_rate: Probability

    inactivity_periods: Annotated[int, Field(ge=0)]
    inactive_time_sec: Annotated[float, Field(ge=0.0)]
    session_duration_sec: Annotated[float, Field(gt=0.0)]
    time_in_target_band_sec: Annotated[float, Field(ge=0.0)]

    consecutive_error_max: Annotated[int, Field(ge=0)]
    difficulty_floor_hits: Annotated[int, Field(ge=0)]
    quit_after_error: bool
    safety_override_count: Annotated[int, Field(ge=0)]

    c_mean_game_task_latency_sec: PositiveTiming | None
    c_median_game_task_latency_sec: PositiveTiming | None

    current_difficulty_level: Annotated[int, Field(ge=1, le=5)]
    difficulty_trend: Literal["increasing", "stable", "decreasing"]

    engagement_components: EngagementComponents | None
    engagement_score: Probability | None
    frustration_components: FrustrationComponents | None
    frustration_index: Probability | None

    learner_state: Literal["engaged", "productive_struggle", "overloaded", "disengaged"] | None
    state_reason: Literal[
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

    @model_validator(mode="after")
    def validate_deterministic_invariants(self):
        ids = [self.intervention_session_id, self.c_session_id]
        if any(_student_prefix(value) != self.student_id for value in ids):
            raise ValueError("C3-ID-01: session identifier prefix must match student_id")

        if self.completed_task_count > self.task_opportunity_count:
            raise ValueError("C3-RG-01: completed_task_count must not exceed task_opportunity_count")
        if self.correct_task_count > self.completed_task_count:
            raise ValueError("C3-RG-01: correct_task_count must not exceed completed_task_count")
        if self.total_attempt_count < self.completed_task_count:
            raise ValueError("C3-RG-01: total_attempt_count must be at least completed_task_count")
        if self.inactive_time_sec > self.session_duration_sec:
            raise ValueError("C3-DF-05: inactive_time_sec must not exceed session_duration_sec")
        if self.time_in_target_band_sec > self.session_duration_sec:
            raise ValueError("C3-DF-05: time_in_target_band_sec must not exceed session_duration_sec")

        if self.completed_task_count == 0:
            if self.accuracy_rate is not None or self.avg_attempts_per_task is not None:
                raise ValueError("C3-NL-01: accuracy_rate/avg_attempts_per_task must be null when completed_task_count is 0")
        else:
            if self.accuracy_rate is None or self.avg_attempts_per_task is None:
                raise ValueError("C3-NL-01: accuracy_rate/avg_attempts_per_task must be numeric when completed_task_count > 0")
            if abs(self.accuracy_rate - self.correct_task_count / self.completed_task_count) > 1e-6:
                raise ValueError("C3-DF-02: accuracy_rate must equal correct_task_count / completed_task_count")
            if abs(self.avg_attempts_per_task - self.total_attempt_count / self.completed_task_count) > 1e-6:
                raise ValueError("C3-DF-03: avg_attempts_per_task must equal total_attempt_count / completed_task_count")

        if self.task_opportunity_count == 0:
            if abs(self.task_completion_rate - 0.0) > 1e-6:
                raise ValueError("C3-DF-04: task_completion_rate must be 0.0 when task_opportunity_count is 0")
        elif abs(self.task_completion_rate - self.completed_task_count / self.task_opportunity_count) > 1e-6:
            raise ValueError("C3-DF-04: task_completion_rate must equal completed_task_count / task_opportunity_count")

        if self.completed_task_count == 0:
            if self.c_mean_game_task_latency_sec is not None or self.c_median_game_task_latency_sec is not None:
                raise ValueError("C3-OW-01/C3-NL-01: C timing must be null when completed_task_count is 0")
        else:
            if self.c_mean_game_task_latency_sec is None or self.c_median_game_task_latency_sec is None:
                raise ValueError("C3-OW-01/C3-NL-01: C timing must be numeric when completed_task_count > 0")

        sufficient_evidence = (
            not self.session_technical_issue_flag
            and self.task_opportunity_count >= 5
            and self.completed_task_count >= 3
            and self.session_duration_sec >= 120
            and self.accuracy_rate is not None
            and self.task_completion_rate is not None
        )

        if self.session_technical_issue_flag:
            expected_status = "technical_issue"
            expected_reason = "technical_issue"
        elif not sufficient_evidence:
            expected_status = "insufficient_evidence"
            expected_reason = "insufficient_session_evidence"
        else:
            expected_status = "complete"
            expected_reason = None

        if self.telemetry_quality_status != expected_status:
            raise ValueError(f"C3-WU-01: telemetry_quality_status must be '{expected_status}' for this evidence")

        if expected_status != "complete":
            if self.learner_state is not None:
                raise ValueError("C3-TECH-01: learner_state must be null when quality status is not complete")
            if self.engagement_components is not None or self.engagement_score is not None:
                raise ValueError("C3-NL-01: engagement fields must be null when quality status is not complete")
            if self.frustration_components is not None or self.frustration_index is not None:
                raise ValueError("C3-NL-01: frustration fields must be null when quality status is not complete")
            if self.state_reason != expected_reason:
                raise ValueError(f"C3-DF-11: state_reason must be '{expected_reason}' when quality status is '{expected_status}'")
            return self

        if (
            self.learner_state is None
            or self.engagement_components is None
            or self.engagement_score is None
            or self.frustration_components is None
            or self.frustration_index is None
        ):
            raise ValueError("C3-NL-01: complete sessions require non-null engagement/frustration/state fields")

        fallback = self.composite_formula_version == "C-COMP-v1-fallback-periods"

        completion_component = _clamp01(self.task_completion_rate)
        if fallback:
            activity_component = _clamp01(1 - self.inactivity_periods / 5)
        else:
            activity_component = _clamp01(1 - self.inactive_time_sec / self.session_duration_sec)
        target_band_component = _clamp01(self.time_in_target_band_sec / self.session_duration_sec)
        accuracy_component = _clamp01(self.accuracy_rate)

        expected_engagement = self.engagement_components.model_dump()
        computed_engagement = {
            "completion_component": completion_component,
            "activity_component": activity_component,
            "target_band_component": target_band_component,
            "accuracy_component": accuracy_component,
        }
        for key, value in computed_engagement.items():
            if abs(expected_engagement[key] - value) > 0.005:
                raise ValueError(f"C3-DF-06: engagement_components.{key} does not match the C-COMP-v1 identity")

        engagement_score = (
            0.30 * completion_component + 0.30 * activity_component
            + 0.25 * target_band_component + 0.15 * accuracy_component
        )
        if abs(self.engagement_score - engagement_score) > 0.005:
            raise ValueError("C3-DF-07: engagement_score does not match the weighted C-COMP-v1 identity")

        error_run_component = _clamp01(self.consecutive_error_max / 5)
        excess_attempt_component = _clamp01((self.avg_attempts_per_task - 1) / 3)
        if fallback:
            inactivity_burden_component = _clamp01(self.inactivity_periods / 5)
        else:
            inactivity_burden_component = _clamp01((self.inactive_time_sec / self.session_duration_sec) / 0.30)
        floor_hit_component = _clamp01(self.difficulty_floor_hits / 3)
        quit_after_error_component = 1.0 if self.quit_after_error else 0.0
        safety_override_component = _clamp01(self.safety_override_count / 2)

        expected_frustration = self.frustration_components.model_dump()
        computed_frustration = {
            "error_run_component": error_run_component,
            "excess_attempt_component": excess_attempt_component,
            "inactivity_burden_component": inactivity_burden_component,
            "floor_hit_component": floor_hit_component,
            "quit_after_error_component": quit_after_error_component,
            "safety_override_component": safety_override_component,
        }
        for key, value in computed_frustration.items():
            if abs(expected_frustration[key] - value) > 0.005:
                raise ValueError(f"C3-DF-08: frustration_components.{key} does not match the C-COMP-v1 identity")

        frustration_index = (
            0.25 * error_run_component + 0.20 * excess_attempt_component
            + 0.15 * inactivity_burden_component + 0.15 * floor_hit_component
            + 0.15 * quit_after_error_component + 0.10 * safety_override_component
        )
        if abs(self.frustration_index - frustration_index) > 0.005:
            raise ValueError("C3-DF-09: frustration_index does not match the weighted C-COMP-v1 identity")

        if self.safety_override_count >= 1 and self.consecutive_error_max >= 4:
            expected_state, reason = "overloaded", "safety_override_with_error_burst"
        elif self.quit_after_error:
            expected_state, reason = "overloaded", "quit_after_error"
        elif self.difficulty_floor_hits >= 2 and self.task_completion_rate < 0.60:
            expected_state, reason = "overloaded", "repeated_floor_hits_with_low_completion"
        elif frustration_index >= 0.70:
            expected_state, reason = "overloaded", "high_behavioral_friction"
        elif engagement_score < 0.45:
            expected_state, reason = "disengaged", "low_engagement_score"
        elif self.inactivity_periods >= 3 and self.task_completion_rate < 0.60:
            expected_state, reason = "disengaged", "inactivity_with_low_completion"
        elif engagement_score >= 0.70 and frustration_index < 0.40 and self.task_completion_rate >= 0.75:
            expected_state, reason = "engaged", "high_engagement_low_friction"
        elif engagement_score >= 0.50 and self.task_completion_rate >= 0.60:
            expected_state, reason = "productive_struggle", "sustained_participation_under_challenge"
        else:
            expected_state, reason = "disengaged", "insufficient_sustained_participation"

        if self.learner_state != expected_state:
            raise ValueError(f"C3-DF-10: learner_state must be '{expected_state}' per the C-LS-v1 rule chain")
        if self.state_reason != reason:
            raise ValueError(f"C3-DF-11: state_reason must be '{reason}' (first triggered C-LS-v1 rule)")

        return self
