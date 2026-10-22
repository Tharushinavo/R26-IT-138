"""C-GF-07 Equal Groups and Arrays (Catalogue §5.7) -- C-EG-01..03. Grade-3-only (SPEC §7)."""

from __future__ import annotations

import random
from typing import Any, Dict

from ..generation_config import TemplateGenerationParams
from .base import GeneratedContent, TaskDefinition


def _generate_eg01(rng: random.Random, difficulty_level: int, params: TemplateGenerationParams) -> GeneratedContent:
    """C-EG-01 Build Equal Groups.

    Learner action: "Create number_of_groups groups of equal size." Correctness: "Every group
    has configured size and total equals product."
    """
    number_of_groups = params.count_a_by_level[difficulty_level - 1]
    group_size = params.count_b_by_level[difficulty_level - 1]
    return GeneratedContent(
        difficulty_vector={"number_of_groups": number_of_groups, "group_size": group_size},
        prompt_payload={"number_of_groups": number_of_groups, "group_size": group_size},
        correct_answer_payload={
            "number_of_groups": number_of_groups, "group_size": group_size,
            "product": number_of_groups * group_size,
        },
        valid_action_space={"groups": "list[int]"},
    )


def _evaluate_eg01(correct: Dict[str, Any], action: Dict[str, Any]) -> bool:
    groups = action.get("groups")
    if not isinstance(groups, list):
        return False
    return (
        len(groups) == correct["number_of_groups"]
        and all(g == correct["group_size"] for g in groups)
        and sum(groups) == correct["product"]
    )


def _generate_eg02(rng: random.Random, difficulty_level: int, params: TemplateGenerationParams) -> GeneratedContent:
    """C-EG-02 Build or Read an Array.

    Learner action: "Build rows/columns from an expression or identify expression/product
    from an array." Correctness: "Rectangular equal-row/column structure and correct
    product." "Orientation" is a named difficulty lever, so the build direction requires the
    exact (rows, cols) pair, not just a matching product.
    """
    rows = params.count_a_by_level[difficulty_level - 1]
    cols = params.count_b_by_level[difficulty_level - 1]
    direction = rng.choice(["build", "read"])
    return GeneratedContent(
        difficulty_vector={"rows": rows, "cols": cols, "direction": direction},
        prompt_payload={"rows": rows, "cols": cols, "direction": direction},
        correct_answer_payload={"rows": rows, "cols": cols, "product": rows * cols, "direction": direction},
        valid_action_space={"rows": "int", "cols": "int", "submitted_product": "int"},
    )


def _evaluate_eg02(correct: Dict[str, Any], action: Dict[str, Any]) -> bool:
    if correct["direction"] == "build":
        return action.get("rows") == correct["rows"] and action.get("cols") == correct["cols"]
    return action.get("submitted_product") == correct["product"]


def _generate_eg03(rng: random.Random, difficulty_level: int, params: TemplateGenerationParams) -> GeneratedContent:
    """C-EG-03 Facts for 2, 5, and 10.

    Learner action: "Complete equal-step facts or match fact to model." Correctness: "Exact
    product for multipliers 2, 5, or 10 within approved Grade 3 range."
    """
    multiplier = rng.choice(params.choice_set)
    multiplicand_max = params.magnitude_a_by_level[difficulty_level - 1]
    multiplicand = rng.randint(1, multiplicand_max)
    return GeneratedContent(
        difficulty_vector={"multiplier": multiplier, "multiplicand_max": multiplicand_max},
        prompt_payload={"multiplier": multiplier, "multiplicand": multiplicand},
        correct_answer_payload={"product": multiplier * multiplicand},
        valid_action_space={"submitted_product": "int"},
    )


def _evaluate_eg03(correct: Dict[str, Any], action: Dict[str, Any]) -> bool:
    return action.get("submitted_product") == correct["product"]


ALL_TASKS = (
    TaskDefinition("C-EG-01", _generate_eg01, _evaluate_eg01),
    TaskDefinition("C-EG-02", _generate_eg02, _evaluate_eg02),
    TaskDefinition("C-EG-03", _generate_eg03, _evaluate_eg03),
)
