"""C-GF-02 Number Path and Order (Catalogue §5.2) -- C-NP-01..04."""

from __future__ import annotations

import random
from typing import Any, Dict

from ..generation_config import TemplateGenerationParams
from .base import GeneratedContent, TaskDefinition


def _generate_np01(rng: random.Random, difficulty_level: int, params: TemplateGenerationParams) -> GeneratedContent:
    """C-NP-01 Continue a Forward Sequence.

    Learner action: "Select or enter the next number(s)." Correctness: "Each next value
    equals prior value + 1."
    """
    shown_length = params.count_a_by_level[difficulty_level - 1]
    blanks = params.count_b_by_level[difficulty_level - 1]
    start_max = params.magnitude_a_by_level[difficulty_level - 1]
    start = rng.randint(1, start_max)
    shown = [start + i for i in range(shown_length)]
    expected = [start + shown_length + i for i in range(blanks)]
    return GeneratedContent(
        difficulty_vector={"shown_length": shown_length, "blanks": blanks, "start": start},
        prompt_payload={"shown_sequence": shown},
        correct_answer_payload={"expected_values": expected},
        valid_action_space={"entered_values": "list[int]"},
    )


def _generate_np02(rng: random.Random, difficulty_level: int, params: TemplateGenerationParams) -> GeneratedContent:
    """C-NP-02 Continue a Backward Sequence.

    Learner action: "Select or enter preceding number(s)." Correctness: "Each next response
    equals prior value - 1."
    """
    shown_length = params.count_a_by_level[difficulty_level - 1]
    blanks = params.count_b_by_level[difficulty_level - 1]
    start_max = params.magnitude_a_by_level[difficulty_level - 1]
    # start must be large enough that the sequence (and its continuation) never goes negative.
    start = rng.randint(shown_length + blanks, start_max)
    shown = [start - i for i in range(shown_length)]
    expected = [start - shown_length - i for i in range(blanks)]
    return GeneratedContent(
        difficulty_vector={"shown_length": shown_length, "blanks": blanks, "start": start},
        prompt_payload={"shown_sequence": shown},
        correct_answer_payload={"expected_values": expected},
        valid_action_space={"entered_values": "list[int]"},
    )


def _generate_np03(rng: random.Random, difficulty_level: int, params: TemplateGenerationParams) -> GeneratedContent:
    """C-NP-03 Skip Count by 2, 5, or 10.

    Learner action: "Continue or repair an equal-step sequence." Correctness: "Consecutive
    values differ by the configured step 2, 5, or 10."
    """
    step = rng.choice(params.choice_set)
    shown_length = params.count_a_by_level[difficulty_level - 1]
    blanks = params.count_b_by_level[difficulty_level - 1]
    start_max = params.magnitude_a_by_level[difficulty_level - 1]
    start = rng.randint(0, start_max)
    shown = [start + i * step for i in range(shown_length)]
    expected = [start + (shown_length + i) * step for i in range(blanks)]
    return GeneratedContent(
        difficulty_vector={"step": step, "shown_length": shown_length, "blanks": blanks},
        prompt_payload={"shown_sequence": shown, "step": step},
        correct_answer_payload={"expected_values": expected},
        valid_action_space={"entered_values": "list[int]"},
    )


def _evaluate_sequence_continuation(correct: Dict[str, Any], action: Dict[str, Any]) -> bool:
    return action.get("entered_values") == correct["expected_values"]


def _generate_np04(rng: random.Random, difficulty_level: int, params: TemplateGenerationParams) -> GeneratedContent:
    """C-NP-04 Order Number Cards.

    Learner action: "Arrange values ascending or descending." Correctness: "Strict configured
    order; duplicates only when explicitly permitted." (v1: duplicates not permitted -- values
    are drawn distinct, TEST_FIXTURE_ONLY generation choice.)
    """
    length = params.count_a_by_level[difficulty_level - 1]
    value_max = params.magnitude_a_by_level[difficulty_level - 1]
    values = rng.sample(range(0, value_max + 1), length)
    direction = rng.choice(["ascending", "descending"])
    expected = sorted(values) if direction == "ascending" else sorted(values, reverse=True)
    return GeneratedContent(
        difficulty_vector={"length": length, "direction": direction},
        prompt_payload={"values": values, "direction": direction},
        correct_answer_payload={"expected_order": expected},
        valid_action_space={"arranged_values": "list[int]"},
    )


def _evaluate_np04(correct: Dict[str, Any], action: Dict[str, Any]) -> bool:
    return action.get("arranged_values") == correct["expected_order"]


ALL_TASKS = (
    TaskDefinition("C-NP-01", _generate_np01, _evaluate_sequence_continuation),
    TaskDefinition("C-NP-02", _generate_np02, _evaluate_sequence_continuation),
    TaskDefinition("C-NP-03", _generate_np03, _evaluate_sequence_continuation),
    TaskDefinition("C-NP-04", _generate_np04, _evaluate_np04),
)
