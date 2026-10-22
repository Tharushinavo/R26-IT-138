"""C-GF-05 Join and Bridge (Catalogue §5.5) -- C-JB-01..04."""

from __future__ import annotations

import random
from typing import Any, Dict

from ..generation_config import TemplateGenerationParams
from .base import GeneratedContent, TaskDefinition

# C-JB-02's "configured strategy" (Catalogue prose, §5.5) -- the unit jump size used when
# counting on from the larger addend. Structural engineering choice (the prose explicitly
# delegates this to "configured strategy"), TEST_FIXTURE_ONLY, not a catalogue/governance value.
_JB02_JUMP_UNIT_SIZE = 1


def _generate_jb01(rng: random.Random, difficulty_level: int, params: TemplateGenerationParams) -> GeneratedContent:
    """C-JB-01 Combine Two Groups.

    Learner action: "Move/join two sets and identify total." Correctness: "Total equals
    cardinality of union of disjoint valid sets."
    """
    addend_max = params.magnitude_a_by_level[difficulty_level - 1]
    a = rng.randint(1, addend_max)
    b = rng.randint(1, addend_max)
    return GeneratedContent(
        difficulty_vector={"addend_max": addend_max},
        prompt_payload={"count_a": a, "count_b": b},
        correct_answer_payload={"total": a + b},
        valid_action_space={"submitted_total": "int"},
    )


def _evaluate_jb01(correct: Dict[str, Any], action: Dict[str, Any]) -> bool:
    return action.get("submitted_total") == correct["total"]


def _generate_jb02(rng: random.Random, difficulty_level: int, params: TemplateGenerationParams) -> GeneratedContent:
    """C-JB-02 Count On from an Addend.

    Learner action: "Start at one addend and make the required forward jumps." Correctness:
    "Final position equals sum; jump count/size matches configured strategy."
    """
    addend_max = params.magnitude_a_by_level[difficulty_level - 1]
    a = rng.randint(1, addend_max)
    b = rng.randint(1, addend_max)
    larger, smaller = (a, b) if a >= b else (b, a)
    total = a + b
    return GeneratedContent(
        difficulty_vector={"addend_max": addend_max, "jump_unit_size": _JB02_JUMP_UNIT_SIZE},
        prompt_payload={"start": larger, "addend_a": a, "addend_b": b},
        correct_answer_payload={
            "start": larger, "sum": total, "expected_jump_count": smaller, "jump_unit": _JB02_JUMP_UNIT_SIZE,
        },
        valid_action_space={"final_position": "int", "jumps": "list[int]"},
    )


def _evaluate_jb02(correct: Dict[str, Any], action: Dict[str, Any]) -> bool:
    final_position = action.get("final_position")
    jumps = action.get("jumps")
    if not isinstance(jumps, list) or final_position is None:
        return False
    return (
        final_position == correct["sum"]
        and len(jumps) == correct["expected_jump_count"]
        and all(j == correct["jump_unit"] for j in jumps)
        and correct["start"] + sum(jumps) == correct["sum"]
    )


def _generate_jb03(rng: random.Random, difficulty_level: int, params: TemplateGenerationParams) -> GeneratedContent:
    """C-JB-03 Single-Digit Addition.

    Learner action: "Solve two-single-digit-addend task within configured curriculum
    envelope." Correctness: "Exact integer sum." (single-digit addends: 0-9, structural.)
    """
    addend_max = min(params.magnitude_a_by_level[difficulty_level - 1], 9)
    a = rng.randint(0, addend_max)
    b = rng.randint(0, addend_max)
    return GeneratedContent(
        difficulty_vector={"addend_max": addend_max},
        prompt_payload={"addend_a": a, "addend_b": b},
        correct_answer_payload={"sum": a + b},
        valid_action_space={"submitted_sum": "int"},
    )


def _evaluate_jb03(correct: Dict[str, Any], action: Dict[str, Any]) -> bool:
    return action.get("submitted_sum") == correct["sum"]


def _generate_jb04(rng: random.Random, difficulty_level: int, params: TemplateGenerationParams) -> GeneratedContent:
    """C-JB-04 Two-Digit Addition and Regrouping.

    Learner action: "Add two numbers; regroup where configured." Correctness: "Exact sum plus
    valid exchange sequence where manipulation is required." Regroup necessity is a
    mathematical fact of the two operands (ones digits sum >= 10), not a config choice; the
    learner reports whether they performed the exchange and it must match that fact.
    """
    addend_max = params.magnitude_a_by_level[difficulty_level - 1]
    a = rng.randint(10, addend_max)  # two-digit: >=10 structural
    b = rng.randint(10, addend_max)
    regroup_required = (a % 10) + (b % 10) >= 10
    return GeneratedContent(
        difficulty_vector={"addend_max": addend_max},
        prompt_payload={"operand_a": a, "operand_b": b},
        correct_answer_payload={"sum": a + b, "regroup_required": regroup_required},
        valid_action_space={"submitted_sum": "int", "exchange_performed": "bool"},
    )


def _evaluate_jb04(correct: Dict[str, Any], action: Dict[str, Any]) -> bool:
    submitted_sum = action.get("submitted_sum")
    exchange = action.get("exchange_performed")
    if submitted_sum is None or not isinstance(exchange, bool):
        return False
    return submitted_sum == correct["sum"] and exchange == correct["regroup_required"]


ALL_TASKS = (
    TaskDefinition("C-JB-01", _generate_jb01, _evaluate_jb01),
    TaskDefinition("C-JB-02", _generate_jb02, _evaluate_jb02),
    TaskDefinition("C-JB-03", _generate_jb03, _evaluate_jb03),
    TaskDefinition("C-JB-04", _generate_jb04, _evaluate_jb04),
)
