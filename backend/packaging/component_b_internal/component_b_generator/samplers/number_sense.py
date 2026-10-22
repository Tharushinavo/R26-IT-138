"""Number-sense samplers (Phase B2A / B2A.2).

Implemented: NS02 (quantity->numeral), NS03 (compare sets), NS04 (compare numerals),
NS05 (order three numbers), NS07 (conservation). DEFERRED: NS01 (number-name rendering
underspecified), NS06 (NS-06 node CALIBRATION_PENDING; number-line tolerance unresolved).
"""

from __future__ import annotations

import random

from .base import ItemSampler, SampledContent

# ----- B-NS04-COMPARE-NUMERALS (symbolic comparison; G3 1..999) -----
NS04_MIN, NS04_MAX, EQUALITY_RATE = 1, 999, 0.15


def sample_compare_numerals(rng: random.Random, grade: int) -> SampledContent:
    if rng.random() < EQUALITY_RATE:
        a = rng.randint(NS04_MIN, NS04_MAX)
        b = a
    else:
        a = rng.randint(NS04_MIN, NS04_MAX)
        b = rng.randint(NS04_MIN, NS04_MAX)
        while b == a:
            b = rng.randint(NS04_MIN, NS04_MAX)
    return SampledContent(operands={"a": a, "b": b},
                          prompt={"stem": f"{a} __ {b}", "left": a, "right": b, "options": ["<", ">", "="]})


# ----- B-NS02-QUANTITY-NUMERAL (numeral equal to object cardinality; 1..20) -----
def sample_quantity_numeral(rng: random.Random, grade: int) -> SampledContent:
    n = rng.randint(1, 20)
    return SampledContent(operands={"object_count": n},
                          prompt={"stem": "Which numeral matches the quantity?", "object_count": n, "options_range": [0, 20]})


# ----- B-NS03-COMPARE-SETS (non-symbolic comparison; sets 1..20, |diff|<=8, equality <=20%) -----
def sample_compare_sets(rng: random.Random, grade: int) -> SampledContent:
    if rng.random() < 0.20:
        a = rng.randint(1, 20)
        b = a
    else:
        a = rng.randint(1, 20)
        diff = rng.randint(1, 8)
        options = [a + diff, a - diff]
        options = [x for x in options if 1 <= x <= 20]
        b = rng.choice(options) if options else a
    return SampledContent(operands={"set_a": a, "set_b": b},
                          prompt={"stem": "Compare the two sets.", "set_a": a, "set_b": b, "options": ["<", ">", "="]})


# ----- B-NS05-ORDER-NUMBERS (order three unique numbers 0..999; asc/desc) -----
def sample_order_numbers(rng: random.Random, grade: int) -> SampledContent:
    nums = rng.sample(range(0, 1000), 3)  # three unique
    direction = rng.choice(("ascending", "descending"))
    return SampledContent(operands={"numbers": nums, "direction": direction},
                          prompt={"stem": f"Order these {direction}.", "numbers": nums, "direction": direction})


# ----- B-NS07-CONSERVATION (same/changed; matched sets 1..15) -----
def sample_conservation(rng: random.Random, grade: int) -> SampledContent:
    n = rng.randint(1, 15)
    transformation = rng.choice(("rearrange", "add", "remove"))
    if transformation == "add":
        delta = rng.randint(1, 3)
    elif transformation == "remove":
        delta = -rng.randint(1, min(3, n))
    else:
        delta = 0
    # `delta` is included in the PROMPT, not only the operands. It is presentation data: it is
    # derived from the objects the learner is shown, and it reveals nothing the before/after visual
    # would not already show them. Without it, a renderer knows the direction of the change but not
    # its magnitude, so it cannot draw the "after" panel — and drawing only the `rearrange` case (the
    # one where delta is 0) would make the presence of a visual a perfect non-mathematical cue for
    # the answer "same".
    return SampledContent(operands={"initial_count": n, "transformation": transformation, "delta": delta},
                          prompt={"stem": "Is the quantity the same or changed?", "initial_count": n,
                                  "transformation": transformation, "delta": delta,
                                  "options": ["same", "changed"]})


SAMPLER = ItemSampler(
    item_template_id="B-NS04-COMPARE-NUMERALS", task_type="compare_written_numbers", skill_id="number_sense",
    eligible_grades=(3,), response_format="relation_choice", sample=sample_compare_numerals,
    required_distractors=2, integer_answer=False,
    guard_ids=("G-GRADE-ELIGIBLE", "G-OPERAND-BOUNDS", "G-NO-LEADING-ZERO", "G-UNIQUE-COMPARISON",
               "G-DISTRACTOR-NE-CORRECT", "G-UNIQUE-DISTRACTORS", "G-NO-DUP-OPTIONS"),
)
_NS02 = ItemSampler(
    item_template_id="B-NS02-QUANTITY-NUMERAL", task_type="match_quantity_to_numeral", skill_id="number_sense",
    eligible_grades=(2,), response_format="single_choice", sample=sample_quantity_numeral,
    guard_ids=("G-GRADE-ELIGIBLE", "G-OPERAND-BOUNDS", "G-CARDINALITY", "G-NO-NEGATIVE-RESULT",
               "G-DISTRACTOR-NE-CORRECT", "G-UNIQUE-DISTRACTORS", "G-NO-DUP-OPTIONS"),
)
_NS03 = ItemSampler(
    item_template_id="B-NS03-COMPARE-SETS", task_type="compare_nonsymbolic_quantities", skill_id="number_sense",
    eligible_grades=(2,), response_format="relation_choice", sample=sample_compare_sets,
    required_distractors=2, integer_answer=False,
    guard_ids=("G-GRADE-ELIGIBLE", "G-OPERAND-BOUNDS", "G-UNIQUE-COMPARISON",
               "G-DISTRACTOR-NE-CORRECT", "G-UNIQUE-DISTRACTORS", "G-NO-DUP-OPTIONS"),
)
_NS05 = ItemSampler(
    item_template_id="B-NS05-ORDER-NUMBERS", task_type="order_three_numbers", skill_id="number_sense",
    eligible_grades=(3,), response_format="ordered_list", sample=sample_order_numbers,
    required_distractors=3, integer_answer=False,
    guard_ids=("G-GRADE-ELIGIBLE", "G-OPERAND-BOUNDS", "G-ORDER-VALID",
               "G-DISTRACTOR-NE-CORRECT", "G-UNIQUE-DISTRACTORS", "G-NO-DUP-OPTIONS"),
)
_NS07 = ItemSampler(
    item_template_id="B-NS07-CONSERVATION", task_type="quantity_conservation", skill_id="number_sense",
    eligible_grades=(2,), response_format="binary_or_choice", sample=sample_conservation,
    required_distractors=1, integer_answer=False,
    guard_ids=("G-GRADE-ELIGIBLE", "G-OPERAND-BOUNDS", "G-CONSERVATION-CONSISTENT",
               "G-DISTRACTOR-NE-CORRECT", "G-UNIQUE-DISTRACTORS", "G-NO-DUP-OPTIONS"),
)

ALL_SAMPLERS = (SAMPLER, _NS02, _NS03, _NS05, _NS07)
