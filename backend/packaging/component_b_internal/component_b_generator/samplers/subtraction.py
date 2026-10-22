"""Subtraction samplers (Phase B2A / B2A.2).

Implemented: SUB01 (take away objects, within 9), SUB03 (single-digit symbolic, within 9),
SUB04 (two-digit no-borrow), SUB05 (two-digit borrow-required). SUB04 never borrows; SUB05
always borrows. DEFERRED: SUB02 (find-difference, CALIBRATION_PENDING).
"""

from __future__ import annotations

import random

from .base import ItemSampler, SampledContent


# ----- B-SUB01-TAKE-AWAY (remove objects; minuend 1-9, subtrahend 0..minuend) -----
def sample_take_away(rng: random.Random, grade: int) -> SampledContent:
    a = rng.randint(1, 9)
    b = rng.randint(0, a)
    return SampledContent(operands={"a": a, "b": b},
                          prompt={"stem": f"There are {a}. Take away {b}.", "total": a, "removed": b, "operator": "-"})


# ----- B-SUB03-WITHIN-9 (single-digit symbolic; 0 <= b <= a <= 9) -----
def sample_within_9(rng: random.Random, grade: int) -> SampledContent:
    a = rng.randint(0, 9)
    b = rng.randint(0, a)
    return SampledContent(operands={"a": a, "b": b},
                          prompt={"stem": f"{a} - {b} = ?", "left": a, "right": b, "operator": "-"})


# ----- B-SUB04-2D-NO-BORROW (each minuend digit >= subtrahend digit) -----
def sample_two_digit_no_borrow(rng: random.Random, grade: int) -> SampledContent:
    tens_a = rng.randint(1, 9)
    tens_b = rng.randint(1, tens_a)
    ones_a = rng.randint(0, 9)
    ones_b = rng.randint(0, ones_a)
    a = 10 * tens_a + ones_a
    b = 10 * tens_b + ones_b
    return SampledContent(operands={"a": a, "b": b},
                          prompt={"stem": f"{a} - {b} = ?", "left": a, "right": b, "operator": "-"})


# ----- B-SUB05-BORROW (ones column borrows; result >= 0) -----
def sample_two_digit_borrow(rng: random.Random, grade: int) -> SampledContent:
    # ones(a) < ones(b) forces a borrow; tens(a) > tens(b) keeps the overall result non-negative.
    ones_a = rng.randint(0, 8)
    ones_b = rng.randint(ones_a + 1, 9)   # ones_a < ones_b => borrow required
    tens_b = rng.randint(1, 8)
    tens_a = rng.randint(tens_b + 1, 9)   # tens_a > tens_b => a > b even after the borrow
    a = 10 * tens_a + ones_a
    b = 10 * tens_b + ones_b
    return SampledContent(operands={"a": a, "b": b},
                          prompt={"stem": f"{a} - {b} = ?", "left": a, "right": b, "operator": "-"})


SAMPLER = ItemSampler(
    item_template_id="B-SUB04-2D-NO-BORROW", task_type="two_digit_subtraction_no_borrow", skill_id="subtraction",
    eligible_grades=(3,), response_format="single_integer_or_choice", sample=sample_two_digit_no_borrow,
    guard_ids=("G-GRADE-ELIGIBLE", "G-OPERAND-BOUNDS", "G-NO-BORROW", "G-NO-NEGATIVE-RESULT",
               "G-NO-LEADING-ZERO", "G-DISTRACTOR-NE-CORRECT", "G-UNIQUE-DISTRACTORS", "G-NO-DUP-OPTIONS"),
)
_SUB01 = ItemSampler(
    item_template_id="B-SUB01-TAKE-AWAY", task_type="remove_objects", skill_id="subtraction",
    eligible_grades=(2,), response_format="single_integer_or_choice", sample=sample_take_away,
    guard_ids=("G-GRADE-ELIGIBLE", "G-OPERAND-BOUNDS", "G-NO-NEGATIVE-RESULT",
               "G-DISTRACTOR-NE-CORRECT", "G-UNIQUE-DISTRACTORS", "G-NO-DUP-OPTIONS"),
)
_SUB03 = ItemSampler(
    item_template_id="B-SUB03-WITHIN-9", task_type="single_digit_subtraction", skill_id="subtraction",
    eligible_grades=(2,), response_format="single_integer_or_choice", sample=sample_within_9,
    guard_ids=("G-GRADE-ELIGIBLE", "G-OPERAND-BOUNDS", "G-NO-NEGATIVE-RESULT",
               "G-DISTRACTOR-NE-CORRECT", "G-UNIQUE-DISTRACTORS", "G-NO-DUP-OPTIONS"),
)
_SUB05 = ItemSampler(
    item_template_id="B-SUB05-BORROW", task_type="subtraction_with_borrowing", skill_id="subtraction",
    eligible_grades=(3,), response_format="single_integer_or_choice", sample=sample_two_digit_borrow,
    guard_ids=("G-GRADE-ELIGIBLE", "G-OPERAND-BOUNDS", "G-BORROW-REQUIRED", "G-NO-NEGATIVE-RESULT",
               "G-NO-LEADING-ZERO", "G-DISTRACTOR-NE-CORRECT", "G-UNIQUE-DISTRACTORS", "G-NO-DUP-OPTIONS"),
)

ALL_SAMPLERS = (SAMPLER, _SUB01, _SUB03, _SUB05)
