"""Addition samplers (Phase B2A / B2A.2).

Implemented: ADD01 (combine two sets, 0-9), ADD02 (count-on a number line), ADD03 (single-digit
symbolic), ADD04 (two-digit no-regroup), ADD05 (two-digit regroup-required). ADD01/ADD03 share
the same addition semantics but differ in representation (pictorial sets vs symbolic). ADD04
never regroups; ADD05 always regroups.
"""

from __future__ import annotations

import random

from .base import ItemSampler, SampledContent

# ----- shared bounded single-digit addend draw (sum <= 18) -----
def _sample_single_digit_pair(rng: random.Random) -> tuple[int, int]:
    a = rng.randint(0, 9)
    b = rng.randint(0, min(9, 18 - a))
    return a, b


# ----- B-ADD01-COMBINE-SETS (0-9 + 0-9, sum <= 18; pictorial sets) -----
def sample_combine_sets(rng: random.Random, grade: int) -> SampledContent:
    a, b = _sample_single_digit_pair(rng)
    return SampledContent(operands={"a": a, "b": b},
                          prompt={"stem": f"Put the two groups together: {a} and {b}.", "set_a": a, "set_b": b, "operator": "+"})


# ----- B-ADD03-SINGLE-DIGIT (0-9 + 0-9, sum <= 18; symbolic) -----
def sample_single_digit_addition(rng: random.Random, grade: int) -> SampledContent:
    a, b = _sample_single_digit_pair(rng)
    return SampledContent(operands={"a": a, "b": b},
                          prompt={"stem": f"{a} + {b} = ?", "left": a, "right": b, "operator": "+"})


# ----- B-ADD02-COUNT-ON (count on from a start; start 1-50, jumps 1-10) -----
def sample_count_on(rng: random.Random, grade: int) -> SampledContent:
    start = rng.randint(1, 50)
    jumps = rng.randint(1, 10)
    return SampledContent(operands={"start": start, "jumps": jumps},
                          prompt={"stem": f"Start at {start} and count on {jumps}.", "start": start, "jumps": jumps})


# ----- B-ADD04-2D-NO-REGROUP (per-column sums never reach 10) -----
def sample_two_digit_no_regroup(rng: random.Random, grade: int) -> SampledContent:
    tens_a = rng.randint(1, 8)
    tens_b = rng.randint(1, 9 - tens_a)
    ones_a = rng.randint(0, 9)
    ones_b = rng.randint(0, 9 - ones_a)
    a = 10 * tens_a + ones_a
    b = 10 * tens_b + ones_b
    return SampledContent(operands={"a": a, "b": b},
                          prompt={"stem": f"{a} + {b} = ?", "left": a, "right": b, "operator": "+"})


# ----- B-ADD05-REGROUP (ones column carries; total <= 99) -----
def sample_two_digit_regroup(rng: random.Random, grade: int) -> SampledContent:
    # ones_a + ones_b >= 10 (carry required); tens_a + tens_b + 1 <= 9 (no hundreds); total <= 99.
    ones_a = rng.randint(1, 9)
    ones_b = rng.randint(10 - ones_a, 9)  # forces ones_a + ones_b >= 10
    tens_a = rng.randint(1, 7)
    tens_b = rng.randint(1, 8 - tens_a)   # tens_a + tens_b <= 8 => +1 carry <= 9
    a = 10 * tens_a + ones_a
    b = 10 * tens_b + ones_b
    return SampledContent(operands={"a": a, "b": b},
                          prompt={"stem": f"{a} + {b} = ?", "left": a, "right": b, "operator": "+"})


SAMPLER = ItemSampler(
    item_template_id="B-ADD04-2D-NO-REGROUP", task_type="two_digit_addition_no_regroup", skill_id="addition",
    eligible_grades=(3,), response_format="single_integer_or_choice", sample=sample_two_digit_no_regroup,
    guard_ids=("G-GRADE-ELIGIBLE", "G-OPERAND-BOUNDS", "G-NO-REGROUP", "G-NO-NEGATIVE-RESULT",
               "G-NO-LEADING-ZERO", "G-DISTRACTOR-NE-CORRECT", "G-UNIQUE-DISTRACTORS", "G-NO-DUP-OPTIONS"),
)
_ADD01 = ItemSampler(
    item_template_id="B-ADD01-COMBINE-SETS", task_type="combine_two_sets", skill_id="addition",
    eligible_grades=(2,), response_format="single_integer_or_choice", sample=sample_combine_sets,
    guard_ids=("G-GRADE-ELIGIBLE", "G-OPERAND-BOUNDS", "G-NO-NEGATIVE-RESULT",
               "G-DISTRACTOR-NE-CORRECT", "G-UNIQUE-DISTRACTORS", "G-NO-DUP-OPTIONS"),
)
_ADD02 = ItemSampler(
    item_template_id="B-ADD02-COUNT-ON", task_type="count_on_number_line", skill_id="addition",
    eligible_grades=(2, 3), response_format="single_integer_or_choice", sample=sample_count_on,
    guard_ids=("G-GRADE-ELIGIBLE", "G-OPERAND-BOUNDS", "G-NO-NEGATIVE-RESULT",
               "G-DISTRACTOR-NE-CORRECT", "G-UNIQUE-DISTRACTORS", "G-NO-DUP-OPTIONS"),
)
_ADD03 = ItemSampler(
    item_template_id="B-ADD03-SINGLE-DIGIT", task_type="single_digit_addition", skill_id="addition",
    eligible_grades=(2,), response_format="single_integer_or_choice", sample=sample_single_digit_addition,
    guard_ids=("G-GRADE-ELIGIBLE", "G-OPERAND-BOUNDS", "G-NO-NEGATIVE-RESULT",
               "G-DISTRACTOR-NE-CORRECT", "G-UNIQUE-DISTRACTORS", "G-NO-DUP-OPTIONS"),
)
_ADD05 = ItemSampler(
    item_template_id="B-ADD05-REGROUP", task_type="addition_with_regrouping", skill_id="addition",
    eligible_grades=(3,), response_format="single_integer_or_choice", sample=sample_two_digit_regroup,
    guard_ids=("G-GRADE-ELIGIBLE", "G-OPERAND-BOUNDS", "G-REGROUP-REQUIRED", "G-NO-NEGATIVE-RESULT",
               "G-NO-LEADING-ZERO", "G-DISTRACTOR-NE-CORRECT", "G-UNIQUE-DISTRACTORS", "G-NO-DUP-OPTIONS"),
)

ALL_SAMPLERS = (SAMPLER, _ADD01, _ADD02, _ADD03, _ADD05)
