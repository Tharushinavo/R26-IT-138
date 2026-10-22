"""Counting samplers (Phase B2A / B2A.2).

Implemented: CNT01 (continue sequence), CNT02 (count objects), CNT03 (how many),
CNT04 (make requested set), CNT06 (skip count). All deterministic pure functions of
``(rng, grade)``. CNT05 (forward/backward from N) is DEFERRED (CNT-05 node CALIBRATION_PENDING).
"""

from __future__ import annotations

import random

from .base import ItemSampler, SampledContent

# ----- B-CNT01-SEQ-CONTINUE -----
MIN_VALUE, MAX_VALUE, MIN_LEN, MAX_LEN, STEP = 1, 50, 3, 6, 1


def sample_counting_sequence(rng: random.Random, grade: int) -> SampledContent:
    length = rng.randint(MIN_LEN, MAX_LEN)
    max_start = MAX_VALUE - length
    start = rng.randint(MIN_VALUE, max_start)
    sequence = [start + STEP * i for i in range(length)]
    stem = ", ".join(str(x) for x in sequence) + ", __"
    return SampledContent(
        operands={"sequence": sequence, "step": STEP, "start": start, "length": length},
        prompt={"stem": stem, "sequence_shown": sequence, "blank_position": "terminal"},
    )


# ----- B-CNT02-COUNT-OBJECTS / B-CNT03-HOW-MANY (cardinality of an object set, 1..20) -----
def _sample_cardinality(rng: random.Random, task: str) -> SampledContent:
    n = rng.randint(1, 20)
    return SampledContent(
        operands={"object_count": n},
        prompt={"stem": "How many objects are there?", "object_count": n, "layout": "scattered", "task": task},
    )


def sample_count_objects(rng: random.Random, grade: int) -> SampledContent:
    return _sample_cardinality(rng, "count_objects")


def sample_how_many(rng: random.Random, grade: int) -> SampledContent:
    return _sample_cardinality(rng, "identify_cardinality")


# ----- B-CNT04-MAKE-SET (produce exactly `target` objects from a larger pool) -----
def sample_make_set(rng: random.Random, grade: int) -> SampledContent:
    target = rng.randint(1, 20)
    pool = target + rng.randint(3, 8)
    return SampledContent(
        operands={"target": target, "pool_size": pool},
        prompt={"stem": f"Select exactly {target} objects.", "target": target, "pool_size": pool},
    )


# ----- B-CNT06-SKIP-COUNT (continue a skip sequence; step in {2,5,10}; totals <= 100) -----
def sample_skip_count(rng: random.Random, grade: int) -> SampledContent:
    step = rng.choice((2, 5, 10))
    max_len = min(6, 100 // step)
    length = rng.randint(2, max(2, max_len - 1))  # >= 2 anchors shown
    max_start = 100 - length * step  # answer = start + length*step must be <= 100
    start = rng.randint(0, max(0, max_start))
    sequence = [start + step * i for i in range(length)]
    stem = ", ".join(str(x) for x in sequence) + ", __"
    return SampledContent(
        operands={"sequence": sequence, "step": step, "start": start, "length": length},
        prompt={"stem": stem, "sequence_shown": sequence, "blank_position": "terminal", "step": step},
    )


SAMPLER = ItemSampler(
    item_template_id="B-CNT01-SEQ-CONTINUE", task_type="continue_count_sequence", skill_id="counting",
    eligible_grades=(2,), response_format="single_integer", sample=sample_counting_sequence,
    guard_ids=("G-GRADE-ELIGIBLE", "G-SEQUENCE-LENGTH", "G-OPERAND-BOUNDS", "G-NO-LEADING-ZERO",
               "G-DISTRACTOR-NE-CORRECT", "G-UNIQUE-DISTRACTORS", "G-NO-DUP-OPTIONS"),
)
_CNT02 = ItemSampler(
    item_template_id="B-CNT02-COUNT-OBJECTS", task_type="count_objects", skill_id="counting",
    eligible_grades=(2,), response_format="single_integer_or_choice", sample=sample_count_objects,
    guard_ids=("G-GRADE-ELIGIBLE", "G-OPERAND-BOUNDS", "G-CARDINALITY", "G-NO-NEGATIVE-RESULT",
               "G-DISTRACTOR-NE-CORRECT", "G-UNIQUE-DISTRACTORS", "G-NO-DUP-OPTIONS"),
)
_CNT03 = ItemSampler(
    item_template_id="B-CNT03-HOW-MANY", task_type="identify_cardinality", skill_id="counting",
    eligible_grades=(2,), response_format="single_integer_or_choice", sample=sample_how_many,
    guard_ids=("G-GRADE-ELIGIBLE", "G-OPERAND-BOUNDS", "G-CARDINALITY", "G-NO-NEGATIVE-RESULT",
               "G-DISTRACTOR-NE-CORRECT", "G-UNIQUE-DISTRACTORS", "G-NO-DUP-OPTIONS"),
)
_CNT04 = ItemSampler(
    item_template_id="B-CNT04-MAKE-SET", task_type="produce_requested_set", skill_id="counting",
    eligible_grades=(2,), response_format="interactive_set_selection", sample=sample_make_set,
    required_distractors=0,  # interactive set production: no multiple-choice option set
    guard_ids=("G-GRADE-ELIGIBLE", "G-OPERAND-BOUNDS", "G-CARDINALITY", "G-NO-NEGATIVE-RESULT",
               "G-DISTRACTOR-NE-CORRECT", "G-UNIQUE-DISTRACTORS", "G-NO-DUP-OPTIONS"),
)
_CNT06 = ItemSampler(
    item_template_id="B-CNT06-SKIP-COUNT", task_type="skip_count_sequence", skill_id="counting",
    eligible_grades=(3,), response_format="single_integer", sample=sample_skip_count,
    guard_ids=("G-GRADE-ELIGIBLE", "G-SKIP-STEP", "G-OPERAND-BOUNDS", "G-NO-LEADING-ZERO",
               "G-DISTRACTOR-NE-CORRECT", "G-UNIQUE-DISTRACTORS", "G-NO-DUP-OPTIONS"),
)

ALL_SAMPLERS = (SAMPLER, _CNT02, _CNT03, _CNT04, _CNT06)
