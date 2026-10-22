"""C-GF-08 Share Fairly (Catalogue §5.8) -- C-SF-01..03. Grade-3-only (SPEC §7)."""

from __future__ import annotations

import random
from typing import Any, Dict

from ..generation_config import TemplateGenerationParams
from .base import GeneratedContent, TaskDefinition


def _generate_sf01(rng: random.Random, difficulty_level: int, params: TemplateGenerationParams) -> GeneratedContent:
    """C-SF-01 Equal Sharing.

    Learner action: "Distribute objects equally among recipients." Correctness: "All
    recipients have equal count and all objects are allocated when no remainder is allowed."
    (v1 always generates the no-remainder case -- explicitly named in the correctness prose
    itself as a legitimate configuration.)
    """
    recipient_count = params.count_a_by_level[difficulty_level - 1]
    per_recipient_max = params.magnitude_a_by_level[difficulty_level - 1]
    per_recipient = rng.randint(1, per_recipient_max)
    total = recipient_count * per_recipient
    return GeneratedContent(
        difficulty_vector={"recipient_count": recipient_count, "per_recipient_max": per_recipient_max},
        prompt_payload={"total": total, "recipient_count": recipient_count},
        correct_answer_payload={"recipient_count": recipient_count, "per_recipient": per_recipient, "total": total},
        valid_action_space={"allocations": "list[int]"},
    )


def _evaluate_sf01(correct: Dict[str, Any], action: Dict[str, Any]) -> bool:
    allocations = action.get("allocations")
    if not isinstance(allocations, list):
        return False
    return (
        len(allocations) == correct["recipient_count"]
        and all(a == correct["per_recipient"] for a in allocations)
        and sum(allocations) == correct["total"]
    )


def _generate_sf02(rng: random.Random, difficulty_level: int, params: TemplateGenerationParams) -> GeneratedContent:
    """C-SF-02 Form Equal Groups.

    Learner action: "Partition total into groups of configured size and determine group
    count." Correctness: "Each group has exact size; group count x group size = total."
    """
    group_size = params.magnitude_a_by_level[difficulty_level - 1]
    group_count = params.count_a_by_level[difficulty_level - 1]
    total = group_size * group_count
    return GeneratedContent(
        difficulty_vector={"group_size": group_size, "group_count": group_count},
        prompt_payload={"total": total, "group_size": group_size},
        correct_answer_payload={"group_size": group_size, "group_count": group_count, "total": total},
        valid_action_space={"groups": "list[int]", "submitted_group_count": "int"},
    )


def _evaluate_sf02(correct: Dict[str, Any], action: Dict[str, Any]) -> bool:
    groups = action.get("groups")
    submitted_group_count = action.get("submitted_group_count")
    if not isinstance(groups, list) or submitted_group_count is None:
        return False
    return (
        all(g == correct["group_size"] for g in groups)
        and len(groups) == submitted_group_count
        and submitted_group_count * correct["group_size"] == correct["total"]
    )


def _generate_sf03(rng: random.Random, difficulty_level: int, params: TemplateGenerationParams) -> GeneratedContent:
    """C-SF-03 Divide by 2 without Remainder.

    Learner action: "Solve approved even-number division-by-2 cases." Correctness: "Exact
    quotient; dividend even and within curriculum-approved range."
    """
    dividend_max = params.magnitude_a_by_level[difficulty_level - 1]
    quotient_max = max(dividend_max // 2, 0)
    quotient = rng.randint(0, quotient_max)
    dividend = quotient * 2
    return GeneratedContent(
        difficulty_vector={"dividend_max": dividend_max},
        prompt_payload={"dividend": dividend},
        correct_answer_payload={"dividend": dividend, "quotient": quotient},
        valid_action_space={"submitted_quotient": "int"},
    )


def _evaluate_sf03(correct: Dict[str, Any], action: Dict[str, Any]) -> bool:
    return action.get("submitted_quotient") == correct["quotient"]


ALL_TASKS = (
    TaskDefinition("C-SF-01", _generate_sf01, _evaluate_sf01),
    TaskDefinition("C-SF-02", _generate_sf02, _evaluate_sf02),
    TaskDefinition("C-SF-03", _generate_sf03, _evaluate_sf03),
)
