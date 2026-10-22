"""C-GF-01 Count and Collect (Catalogue §5.1) -- C-CC-01..04.

Correctness/action semantics transcribed verbatim from the catalogue's per-template
"Correctness" / "Learner action" prose (see each function's docstring for the exact quoted
text). Numeric bounds come only from ``generation_config.TemplateGenerationParams``
(TEST_FIXTURE_ONLY).
"""

from __future__ import annotations

import random
from typing import Any, Dict

from ..generation_config import TemplateGenerationParams
from .base import GeneratedContent, TaskDefinition


def _generate_cc01(rng: random.Random, difficulty_level: int, params: TemplateGenerationParams) -> GeneratedContent:
    """C-CC-01 Mark and Count Objects.

    Catalogue prose -- Learner action: "Tap/select every object exactly once, then submit
    total." Correctness: "Every valid object selected once; no invalid object selected;
    submitted total equals set cardinality."
    """
    valid_count = params.magnitude_a_by_level[difficulty_level - 1]
    distractor_count = params.count_a_by_level[difficulty_level - 1]
    valid_ids = tuple(f"obj-{i}" for i in range(valid_count))
    distractor_ids = tuple(f"dist-{i}" for i in range(distractor_count))
    return GeneratedContent(
        difficulty_vector={"set_size": valid_count, "distractor_count": distractor_count},
        prompt_payload={"valid_object_ids": valid_ids, "distractor_object_ids": distractor_ids},
        correct_answer_payload={"valid_object_ids": list(valid_ids), "expected_total": valid_count},
        valid_action_space={"selected_object_ids": "list[str]", "submitted_total": "int"},
    )


def _evaluate_cc01(correct: Dict[str, Any], action: Dict[str, Any]) -> bool:
    selected = action.get("selected_object_ids")
    submitted_total = action.get("submitted_total")
    if not isinstance(selected, list):
        return False
    return (
        set(selected) == set(correct["valid_object_ids"])
        and len(selected) == len(set(selected))
        and submitted_total == correct["expected_total"]
    )


def _generate_cc02(rng: random.Random, difficulty_level: int, params: TemplateGenerationParams) -> GeneratedContent:
    """C-CC-02 Produce the Requested Set.

    Learner action: "Move/select exactly N objects into a target area." Correctness: "Final
    target area contains exactly N valid objects."
    """
    n = params.magnitude_a_by_level[difficulty_level - 1]
    valid_ids = tuple(f"obj-{i}" for i in range(n + 5))  # pool larger than N (bounded, TEST_FIXTURE_ONLY)
    return GeneratedContent(
        difficulty_vector={"target_n": n},
        prompt_payload={"available_object_ids": valid_ids, "target_n": n},
        correct_answer_payload={"valid_object_ids": list(valid_ids), "target_n": n},
        valid_action_space={"placed_object_ids": "list[str]"},
    )


def _evaluate_cc02(correct: Dict[str, Any], action: Dict[str, Any]) -> bool:
    placed = action.get("placed_object_ids")
    if not isinstance(placed, list):
        return False
    valid_placed = [pid for pid in placed if pid in correct["valid_object_ids"]]
    return len(valid_placed) == correct["target_n"] and len(set(valid_placed)) == correct["target_n"]


def _generate_cc03(rng: random.Random, difficulty_level: int, params: TemplateGenerationParams) -> GeneratedContent:
    """C-CC-03 Count and Match Numeral.

    Learner action: "Count a set and choose/enter the matching numeral." Correctness:
    "Selected numeral equals set cardinality."
    """
    cardinality = params.magnitude_a_by_level[difficulty_level - 1]
    n_distractors = params.count_a_by_level[difficulty_level - 1]
    options = {cardinality}
    while len(options) < n_distractors + 1:
        options.add(max(0, cardinality + rng.choice([-2, -1, 1, 2, 3])))
    return GeneratedContent(
        difficulty_vector={"cardinality": cardinality, "distractor_count": n_distractors},
        prompt_payload={"set_size": cardinality, "numeral_options": sorted(options)},
        correct_answer_payload={"cardinality": cardinality},
        valid_action_space={"selected_numeral": "int"},
    )


def _evaluate_cc03(correct: Dict[str, Any], action: Dict[str, Any]) -> bool:
    return action.get("selected_numeral") == correct["cardinality"]


def _generate_cc04(rng: random.Random, difficulty_level: int, params: TemplateGenerationParams) -> GeneratedContent:
    """C-CC-04 Conservation Rearrangement.

    Learner action: "Judge whether quantity changed after the same objects are rearranged."
    Correctness: "'Same' when object identity/count is preserved; 'changed' only in
    controlled add/remove trials."
    """
    object_count = params.magnitude_a_by_level[difficulty_level - 1]
    trial_type = rng.choice(["rearrange_only", "add_remove"])
    correct_judgment = "same" if trial_type == "rearrange_only" else "changed"
    return GeneratedContent(
        difficulty_vector={"object_count": object_count, "trial_type": trial_type},
        prompt_payload={"object_count": object_count, "trial_type": trial_type},
        correct_answer_payload={"correct_judgment": correct_judgment},
        valid_action_space={"judgment": "same|changed"},
    )


def _evaluate_cc04(correct: Dict[str, Any], action: Dict[str, Any]) -> bool:
    return action.get("judgment") == correct["correct_judgment"]


ALL_TASKS = (
    TaskDefinition("C-CC-01", _generate_cc01, _evaluate_cc01),
    TaskDefinition("C-CC-02", _generate_cc02, _evaluate_cc02),
    TaskDefinition("C-CC-03", _generate_cc03, _evaluate_cc03),
    TaskDefinition("C-CC-04", _generate_cc04, _evaluate_cc04),
)
