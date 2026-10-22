"""C-GF-06 Take Away and Compare (Catalogue §5.6) -- C-TC-01..04."""

from __future__ import annotations

import random
from typing import Any, Dict

from ..generation_config import TemplateGenerationParams
from .base import GeneratedContent, TaskDefinition

# C-TC-03's own prose fixes the minuend bound to <=9 ("Subtraction Within 9"); structural,
# not a TEST_FIXTURE_ONLY config value.
_TC03_MINUEND_MAX = 9


def _generate_tc01(rng: random.Random, difficulty_level: int, params: TemplateGenerationParams) -> GeneratedContent:
    """C-TC-01 Remove Objects.

    Learner action: "Remove specified quantity and identify remainder." Correctness:
    "remainder = initial_count - removed_count; removed count cannot exceed initial count."
    """
    initial_max = params.magnitude_a_by_level[difficulty_level - 1]
    initial = rng.randint(1, initial_max)
    removed = rng.randint(0, initial)
    return GeneratedContent(
        difficulty_vector={"initial_max": initial_max},
        prompt_payload={"initial_count": initial, "removed_count": removed},
        correct_answer_payload={"remainder": initial - removed},
        valid_action_space={"submitted_remainder": "int"},
    )


def _evaluate_tc01(correct: Dict[str, Any], action: Dict[str, Any]) -> bool:
    return action.get("submitted_remainder") == correct["remainder"]


def _generate_tc02(rng: random.Random, difficulty_level: int, params: TemplateGenerationParams) -> GeneratedContent:
    """C-TC-02 Compare and Find the Difference.

    Learner action: "Pair or align two quantities and identify how many more/less."
    Correctness: "Absolute or directed difference according to prompt."
    """
    value_max = params.magnitude_a_by_level[difficulty_level - 1]
    a = rng.randint(1, value_max)
    b = rng.randint(1, value_max)
    directed = rng.choice([True, False])
    expected = (a - b) if directed else abs(a - b)
    return GeneratedContent(
        difficulty_vector={"value_max": value_max, "directed": directed},
        prompt_payload={"value_a": a, "value_b": b, "directed": directed},
        correct_answer_payload={"expected_difference": expected},
        valid_action_space={"submitted_difference": "int"},
    )


def _evaluate_tc02(correct: Dict[str, Any], action: Dict[str, Any]) -> bool:
    return action.get("submitted_difference") == correct["expected_difference"]


def _generate_tc03(rng: random.Random, difficulty_level: int, params: TemplateGenerationParams) -> GeneratedContent:
    """C-TC-03 Subtraction Within 9.

    Learner action (implicit solve task). Correctness: "Solve a - b, with a <= 9, 0 <= b <= a.
    Exact non-negative difference."
    """
    a = rng.randint(0, _TC03_MINUEND_MAX)
    b = rng.randint(0, a)
    return GeneratedContent(
        difficulty_vector={"minuend_max": _TC03_MINUEND_MAX},
        prompt_payload={"minuend": a, "subtrahend": b},
        correct_answer_payload={"difference": a - b},
        valid_action_space={"submitted_difference": "int"},
    )


def _evaluate_tc03(correct: Dict[str, Any], action: Dict[str, Any]) -> bool:
    return action.get("submitted_difference") == correct["difference"]


def _generate_tc04(rng: random.Random, difficulty_level: int, params: TemplateGenerationParams) -> GeneratedContent:
    """C-TC-04 Two-Digit Subtraction and Borrowing.

    Learner action: "Subtract two numbers; ungroup where configured." Correctness: "Exact
    difference plus valid ungrouping sequence where manipulation is required." Borrow
    necessity is a mathematical fact (minuend's ones digit < subtrahend's ones digit).
    """
    minuend_max = params.magnitude_a_by_level[difficulty_level - 1]
    a = rng.randint(10, minuend_max)  # two-digit: >=10 structural
    b = rng.randint(0, a)
    borrow_required = (a % 10) < (b % 10)
    return GeneratedContent(
        difficulty_vector={"minuend_max": minuend_max},
        prompt_payload={"minuend": a, "subtrahend": b},
        correct_answer_payload={"difference": a - b, "borrow_required": borrow_required},
        valid_action_space={"submitted_difference": "int", "exchange_performed": "bool"},
    )


def _evaluate_tc04(correct: Dict[str, Any], action: Dict[str, Any]) -> bool:
    difference = action.get("submitted_difference")
    exchange = action.get("exchange_performed")
    if difference is None or not isinstance(exchange, bool):
        return False
    return difference == correct["difference"] and exchange == correct["borrow_required"]


ALL_TASKS = (
    TaskDefinition("C-TC-01", _generate_tc01, _evaluate_tc01),
    TaskDefinition("C-TC-02", _generate_tc02, _evaluate_tc02),
    TaskDefinition("C-TC-03", _generate_tc03, _evaluate_tc03),
    TaskDefinition("C-TC-04", _generate_tc04, _evaluate_tc04),
)
