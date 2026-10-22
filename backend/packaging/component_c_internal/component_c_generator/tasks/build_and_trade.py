"""C-GF-04 Build and Trade (Catalogue §5.4) -- C-BT-01..04."""

from __future__ import annotations

import random
from typing import Any, Dict

from ..generation_config import TemplateGenerationParams
from .base import GeneratedContent, TaskDefinition


def _generate_bt01(rng: random.Random, difficulty_level: int, params: TemplateGenerationParams) -> GeneratedContent:
    """C-BT-01 Build Tens and Ones.

    Learner action: "Build a two-digit number or decode blocks into tens/ones." Correctness:
    "number = 10 x tens + ones, with canonical ones 0-9 unless non-canonical form is
    intentional." (v1 generates only the canonical form; the non-canonical exception is not
    implemented -- not specified anywhere with a concrete parameter.)
    """
    tens_max = params.magnitude_a_by_level[difficulty_level - 1]
    tens = rng.randint(0, tens_max)
    ones = rng.randint(0, 9)  # canonical ones digit -- structural (definitional), not config
    number = 10 * tens + ones
    return GeneratedContent(
        difficulty_vector={"tens_max": tens_max},
        prompt_payload={"target_number": number},
        correct_answer_payload={"target_number": number},
        valid_action_space={"tens": "int", "ones": "int"},
    )


def _evaluate_bt01(correct: Dict[str, Any], action: Dict[str, Any]) -> bool:
    tens, ones = action.get("tens"), action.get("ones")
    if not isinstance(tens, int) or not isinstance(ones, int) or isinstance(tens, bool) or isinstance(ones, bool):
        return False
    return (10 * tens + ones == correct["target_number"]) and (0 <= ones <= 9)


def _generate_bt02(rng: random.Random, difficulty_level: int, params: TemplateGenerationParams) -> GeneratedContent:
    """C-BT-02 Build Hundreds, Tens and Ones.

    Learner action: "Build/decompose a three-digit number." Correctness: "number = 100 x
    hundreds + 10 x tens + ones." (No canonical-digit clause is stated for this template in
    the catalogue -- unlike C-BT-01 -- so only the bare identity is enforced.)
    """
    hundreds_max = params.magnitude_a_by_level[difficulty_level - 1]
    hundreds = rng.randint(0, hundreds_max)
    tens = rng.randint(0, 9)
    ones = rng.randint(0, 9)
    number = 100 * hundreds + 10 * tens + ones
    return GeneratedContent(
        difficulty_vector={"hundreds_max": hundreds_max},
        prompt_payload={"target_number": number},
        correct_answer_payload={"target_number": number},
        valid_action_space={"hundreds": "int", "tens": "int", "ones": "int"},
    )


def _evaluate_bt02(correct: Dict[str, Any], action: Dict[str, Any]) -> bool:
    h, t, o = action.get("hundreds"), action.get("tens"), action.get("ones")
    if not all(isinstance(x, int) and not isinstance(x, bool) for x in (h, t, o)):
        return False
    return 100 * h + 10 * t + o == correct["target_number"]


def _generate_bt03(rng: random.Random, difficulty_level: int, params: TemplateGenerationParams) -> GeneratedContent:
    """C-BT-03 Trade Ten Ones for One Ten.

    Learner action: "Exchange exactly ten ones for one ten." Correctness: "Quantity conserved
    and post-trade place-value counts valid."

    Pre-trade ones is fixed to 10-19 -- structural/definitional (must be >=10 to trade a ten,
    and <20 keeps the pre-state itself canonical), not a TEST_FIXTURE_ONLY calibration value.
    """
    pre_tens_max = params.magnitude_a_by_level[difficulty_level - 1]
    pre_tens = rng.randint(0, pre_tens_max)
    pre_ones = rng.randint(10, 19)
    return GeneratedContent(
        difficulty_vector={"pre_tens_max": pre_tens_max},
        prompt_payload={"pre_tens": pre_tens, "pre_ones": pre_ones},
        correct_answer_payload={
            "pre_tens": pre_tens, "pre_ones": pre_ones,
            "expected_post_tens": pre_tens + 1, "expected_post_ones": pre_ones - 10,
        },
        valid_action_space={"post_tens": "int", "post_ones": "int"},
    )


def _evaluate_bt03(correct: Dict[str, Any], action: Dict[str, Any]) -> bool:
    post_tens, post_ones = action.get("post_tens"), action.get("post_ones")
    if not isinstance(post_tens, int) or not isinstance(post_ones, int) or isinstance(post_tens, bool) or isinstance(post_ones, bool):
        return False
    quantity_before = correct["pre_tens"] * 10 + correct["pre_ones"]
    quantity_after = post_tens * 10 + post_ones
    return (
        quantity_before == quantity_after
        and post_tens == correct["expected_post_tens"]
        and post_ones == correct["expected_post_ones"]
        and 0 <= post_ones <= 9
    )


def _generate_bt04(rng: random.Random, difficulty_level: int, params: TemplateGenerationParams) -> GeneratedContent:
    """C-BT-04 Ungroup One Ten into Ten Ones.

    Learner action: "Exchange one ten for ten ones." Correctness: "Quantity conserved and
    post-trade counts valid."

    Pre-trade tens is >=1 -- structural/definitional (must have a ten to ungroup).
    """
    pre_tens_max = params.magnitude_a_by_level[difficulty_level - 1]
    pre_tens = rng.randint(1, max(pre_tens_max, 1))
    pre_ones = rng.randint(0, 9)
    return GeneratedContent(
        difficulty_vector={"pre_tens_max": pre_tens_max},
        prompt_payload={"pre_tens": pre_tens, "pre_ones": pre_ones},
        correct_answer_payload={
            "pre_tens": pre_tens, "pre_ones": pre_ones,
            "expected_post_tens": pre_tens - 1, "expected_post_ones": pre_ones + 10,
        },
        valid_action_space={"post_tens": "int", "post_ones": "int"},
    )


def _evaluate_bt04(correct: Dict[str, Any], action: Dict[str, Any]) -> bool:
    post_tens, post_ones = action.get("post_tens"), action.get("post_ones")
    if not isinstance(post_tens, int) or not isinstance(post_ones, int) or isinstance(post_tens, bool) or isinstance(post_ones, bool):
        return False
    quantity_before = correct["pre_tens"] * 10 + correct["pre_ones"]
    quantity_after = post_tens * 10 + post_ones
    return (
        quantity_before == quantity_after
        and post_tens == correct["expected_post_tens"]
        and post_ones == correct["expected_post_ones"]
        and post_tens >= 0
        and post_ones >= 0
    )


ALL_TASKS = (
    TaskDefinition("C-BT-01", _generate_bt01, _evaluate_bt01),
    TaskDefinition("C-BT-02", _generate_bt02, _evaluate_bt02),
    TaskDefinition("C-BT-03", _generate_bt03, _evaluate_bt03),
    TaskDefinition("C-BT-04", _generate_bt04, _evaluate_bt04),
)
