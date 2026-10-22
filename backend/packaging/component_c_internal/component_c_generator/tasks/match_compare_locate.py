"""C-GF-03 Match, Compare and Locate (Catalogue §5.3) -- C-MCL-01..04."""

from __future__ import annotations

import random
from typing import Any, Dict

from ..generation_config import TemplateGenerationParams
from .base import GeneratedContent, TaskDefinition, TaskGenerationTechnicalError


def _generate_mcl01(rng: random.Random, difficulty_level: int, params: TemplateGenerationParams) -> GeneratedContent:
    """C-MCL-01 Numeral-Quantity Match.

    Learner action: "Match two equivalent number representations." Correctness: "Matched
    representations encode the same cardinal value."

    Fail-closed: if distinct distractor options cannot be produced within
    ``max_generation_attempts`` (SPEC §11 "no ambiguous correct answer" + "bounded retry ...
    hard technical failure after repeated failure"), raises ``TaskGenerationTechnicalError``.
    """
    value_max = params.magnitude_a_by_level[difficulty_level - 1]
    n_distractors = params.count_a_by_level[difficulty_level - 1]
    target = rng.randint(1, value_max)
    options = {target}
    attempts = 0
    while len(options) < n_distractors + 1:
        attempts += 1
        if attempts > params.max_generation_attempts:
            raise TaskGenerationTechnicalError(
                f"C-MCL-01: could not produce {n_distractors} unique distractor(s) for "
                f"target={target} within value_max={value_max} after {attempts - 1} attempts"
            )
        candidate = rng.randint(0, max(value_max, n_distractors * 3))
        options.add(candidate)
    options_sorted = sorted(options)
    return GeneratedContent(
        difficulty_vector={"value_max": value_max, "distractor_count": n_distractors},
        prompt_payload={"target_representation_value": target, "numeral_options": options_sorted},
        correct_answer_payload={"target_value": target},
        valid_action_space={"selected_value": "int"},
    )


def _evaluate_mcl01(correct: Dict[str, Any], action: Dict[str, Any]) -> bool:
    return action.get("selected_value") == correct["target_value"]


def _generate_mcl02(rng: random.Random, difficulty_level: int, params: TemplateGenerationParams) -> GeneratedContent:
    """C-MCL-02 Compare Quantities.

    Learner action: "Select larger, smaller, or equal quantity." Correctness: "Based on exact
    cardinalities, not visual area."
    """
    value_max = params.magnitude_a_by_level[difficulty_level - 1]
    left = rng.randint(1, value_max)
    right = rng.randint(1, value_max)
    correct_selection = "left" if left > right else "right" if right > left else "equal"
    return GeneratedContent(
        difficulty_vector={"value_max": value_max},
        prompt_payload={"left_count": left, "right_count": right},
        correct_answer_payload={"correct_selection": correct_selection},
        valid_action_space={"selection": "left|right|equal"},
    )


def _evaluate_mcl02(correct: Dict[str, Any], action: Dict[str, Any]) -> bool:
    return action.get("selection") == correct["correct_selection"]


def _generate_mcl03(rng: random.Random, difficulty_level: int, params: TemplateGenerationParams) -> GeneratedContent:
    """C-MCL-03 Compare Numerals.

    Learner action: "Choose larger/smaller/equal or place comparison sign." Correctness:
    "Exact integer comparison."
    """
    value_max = params.magnitude_a_by_level[difficulty_level - 1]
    a = rng.randint(0, value_max)
    b = rng.randint(0, value_max)
    correct_sign = "<" if a < b else ">" if a > b else "="
    return GeneratedContent(
        difficulty_vector={"value_max": value_max},
        prompt_payload={"value_a": a, "value_b": b},
        correct_answer_payload={"correct_sign": correct_sign},
        valid_action_space={"comparison_sign": "<|>|="},
    )


def _evaluate_mcl03(correct: Dict[str, Any], action: Dict[str, Any]) -> bool:
    return action.get("comparison_sign") == correct["correct_sign"]


def _generate_mcl04(rng: random.Random, difficulty_level: int, params: TemplateGenerationParams) -> GeneratedContent:
    """C-MCL-04 Number-Line Landing.

    Learner action: "Tap or move a marker to a target position." Correctness: "Mathematical
    interval/location error within configured tolerance; motor error tracked separately."
    """
    interval_max = params.magnitude_a_by_level[difficulty_level - 1]
    tolerance = params.magnitude_b_by_level[difficulty_level - 1]
    target = rng.randint(0, interval_max)
    return GeneratedContent(
        difficulty_vector={"interval_max": interval_max, "tolerance": tolerance},
        prompt_payload={"interval_max": interval_max, "target_position": target},
        correct_answer_payload={"target_position": target, "tolerance": tolerance},
        valid_action_space={"marker_position": "number"},
    )


def _evaluate_mcl04(correct: Dict[str, Any], action: Dict[str, Any]) -> bool:
    position = action.get("marker_position")
    if not isinstance(position, (int, float)) or isinstance(position, bool):
        return False
    return abs(position - correct["target_position"]) <= correct["tolerance"]


ALL_TASKS = (
    TaskDefinition("C-MCL-01", _generate_mcl01, _evaluate_mcl01),
    TaskDefinition("C-MCL-02", _generate_mcl02, _evaluate_mcl02),
    TaskDefinition("C-MCL-03", _generate_mcl03, _evaluate_mcl03),
    TaskDefinition("C-MCL-04", _generate_mcl04, _evaluate_mcl04),
)
