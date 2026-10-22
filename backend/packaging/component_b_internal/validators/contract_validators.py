from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from typing import Any, Literal

from pydantic import ValidationError

from models.contracts import (
    BToCMasteryPayload,
    BToComponent3Payload,
    CToComponent3Payload,
    SKILLS,
    SharedInterventionSessionMapping,
)


class ContractValidationError(ValueError):
    """Validation failure carrying a research-rule identifier."""


RETIRED_FIELDS = {
    "session_number", "session_id", "avg_response_time_sec",
    "response_time", "average_response_time", "response_speed_trait",
}
COMMON_PROHIBITED_FIELDS = {
    "population", "dd_subtype", "true_ability", "true_mastery",
    "agent_archetype", "gameplay_mastery_estimate", "cognitive_profile",
    "memory", "attention", "processing_speed",
}
B_TO_C_PROHIBITED_FIELDS = {
    "mastery_certified", "error_class_dist", "hint_requests",
    "b_mean_item_response_time_sec", "b_median_item_response_time_sec",
    "b_item_response_time_std_sec", "b_answer_changes", "error_count",
    "total_attempts", "P(L0)", "P(T)", "P(G)", "P(S)",
}
B_TO_3_PROHIBITED_FIELDS = {
    "b_answer_changes", "error_count", "total_attempts",
    "b_response_speed_baseline", "learner_random_effect",
    "off_day_indicator", "guessing_propensity", "help_avoidance_trait",
}
C_TO_3_PROHIBITED_FIELDS = {
    # Component B leakage (Boundary_Contracts_v1.0 C->3 contract SS13.2)
    "b_mean_item_rt_sec", "b_median_item_rt_sec", "b_rt_iqr_sec",
    "hint_requests", "b_hint_count", "b_answer_changes", "b_error_class",
    "error_class_dist", "mastery_certified",
    # Generator-only latent leakage (SS13.3)
    "c_game_fluency_baseline", "c_persistence_tendency", "c_challenge_tolerance",
    "c_engagement_propensity", "session_context_c", "learner_random_effect",
    "off_day_indicator", "frustration_proneness", "engagement_tendency",
    "persistence_trait", "disengagement_tendency",
    # D3 profile leakage (SS13.4)
    "magnitude", "operations", "mixed", "magnitude_deficit",
    "operations_deficit", "mixed_deficit",
    # Component A / cognitive-profile leakage (SS13.5)
    "number_sense_profile",
    # RL internals (SS13.6)
    "q_values", "policy_logits", "action_probabilities",
    "reward_model_state", "exploration_rate", "agent_state",
}

PayloadKind = Literal["mapping", "b_to_c", "b_to_3", "c_to_3"]


def _walk_keys(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield str(key)
            yield from _walk_keys(child)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for child in value:
            yield from _walk_keys(child)


def _reject_prohibited_fields(payload: Mapping[str, Any], kind: PayloadKind) -> None:
    keys = set(_walk_keys(payload))
    retired = keys & RETIRED_FIELDS
    if retired:
        raise ContractValidationError(f"ID-06/PF-04: retired field prohibited: {sorted(retired)}")
    prohibited = keys & COMMON_PROHIBITED_FIELDS
    if prohibited:
        raise ContractValidationError(f"PF-01/PF-02/PF-06: prohibited field: {sorted(prohibited)}")
    edge_prohibited = {
        "b_to_c": B_TO_C_PROHIBITED_FIELDS,
        "b_to_3": B_TO_3_PROHIBITED_FIELDS,
        "c_to_3": C_TO_3_PROHIBITED_FIELDS,
    }.get(kind, set())
    found = keys & edge_prohibited
    if found:
        rule = {"b_to_c": "PF-05", "b_to_3": "PF-02/PF-06", "c_to_3": "C3-PF-02/C3-PF-03/C3-PF-04"}[kind]
        raise ContractValidationError(f"{rule}: field prohibited on {kind} edge: {sorted(found)}")


def validate_payload(payload: Mapping[str, Any], kind: PayloadKind):
    _reject_prohibited_fields(payload, kind)
    model = {
        "mapping": SharedInterventionSessionMapping,
        "b_to_c": BToCMasteryPayload,
        "b_to_3": BToComponent3Payload,
        "c_to_3": CToComponent3Payload,
    }[kind]
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        raise ContractValidationError(str(exc)) from exc


def validate_mapping_sequence(rows: Sequence[Mapping[str, Any]]) -> list[SharedInterventionSessionMapping]:
    validated = [validate_payload(row, "mapping") for row in rows]
    seen_intervention_ids: set[tuple[str, str]] = set()
    seen_b_ids: set[str] = set()
    seen_c_ids: set[str] = set()
    last_by_student: dict[str, tuple[int, date]] = {}
    for row in validated:
        key = (row.student_id, row.intervention_session_id)
        if key in seen_intervention_ids:
            raise ContractValidationError("CD-02/CD-03: duplicate intervention mapping row")
        seen_intervention_ids.add(key)
        if row.b_session_id and row.b_session_id in seen_b_ids:
            raise ContractValidationError("CD-02: B session maps more than once")
        if row.c_session_id and row.c_session_id in seen_c_ids:
            raise ContractValidationError("CD-03: C session maps more than once")
        if row.b_session_id:
            seen_b_ids.add(row.b_session_id)
        if row.c_session_id:
            seen_c_ids.add(row.c_session_id)
        previous = last_by_student.get(row.student_id)
        if previous and (row.intervention_session_number <= previous[0] or row.intervention_session_date < previous[1]):
            raise ContractValidationError("TM-02: session numbers must increase and dates must be non-decreasing")
        last_by_student[row.student_id] = (row.intervention_session_number, row.intervention_session_date)
    return validated


def validate_b_to_3_warmup(payload: Mapping[str, Any], mastery_observation_counts: Mapping[str, int]) -> BToComponent3Payload:
    model = validate_payload(payload, "b_to_3")
    if set(mastery_observation_counts) != set(SKILLS):
        raise ContractValidationError("RI-02/NL-04: observation counts must use exactly the seven skills")
    slopes = model.mastery_slope_w4.model_dump()
    for skill in SKILLS:
        count = mastery_observation_counts[skill]
        slope = slopes[skill]
        if count < 4 and slope is not None:
            raise ContractValidationError(f"NL-04: {skill} slope must be null before four observations")
        if count >= 4 and slope is None:
            raise ContractValidationError(f"NL-04: {skill} slope must be numeric after four observations")
    return model


def validate_payload_against_mapping(
    payload: Mapping[str, Any],
    mapping: Mapping[str, Any],
    kind: Literal["b_to_c", "b_to_3", "c_to_3"],
):
    mapping_model = validate_payload(mapping, "mapping")
    payload_model = validate_payload(payload, kind)
    if payload_model.student_id != mapping_model.student_id or payload_model.intervention_session_id != mapping_model.intervention_session_id:
        raise ContractValidationError("RI-01: payload references no matching intervention mapping row")
    if payload_model.intervention_session_number != mapping_model.intervention_session_number:
        raise ContractValidationError("RI-01: payload session number disagrees with mapping")
    if kind == "c_to_3":
        if not mapping_model.c_present:
            raise ContractValidationError("C3-ID-02/MC-01: no C payload may exist when c_present is false")
        if payload_model.c_session_id != mapping_model.c_session_id:
            raise ContractValidationError("C3-ID-02: c_session_id disagrees with mapping")
        return payload_model
    if not mapping_model.b_present:
        raise ContractValidationError("MC-01/MC-03: no B payload may exist when b_present is false")
    if kind == "b_to_3" and payload_model.b_session_id != mapping_model.b_session_id:
        raise ContractValidationError("RI-01: b_session_id disagrees with mapping")
    return payload_model
