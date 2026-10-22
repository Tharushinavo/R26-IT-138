"""Multiplication samplers (Phase B2A / B2A.2).

Implemented: MUL01 (count equal groups), MUL02 (interpret an array), MUL03 (2/5/10 facts).
Products are bounded to <= 100 (MUL01/MUL02) / official fact families (MUL03).
"""

from __future__ import annotations

import random

from .base import ItemSampler, SampledContent

FACTORS = (2, 5, 10)


# ----- B-MUL03-FACTS-2-5-10 -----
def sample_fact_2_5_10(rng: random.Random, grade: int) -> SampledContent:
    a = rng.choice(FACTORS)
    b = rng.randint(0, 10)
    return SampledContent(operands={"a": a, "b": b},
                          prompt={"stem": f"{a} x {b} = ?", "left": a, "right": b, "operator": "x"})


# ----- B-MUL01-EQUAL-GROUPS (groups in {2,5,10}, size 1-10, product <= 100) -----
def sample_equal_groups(rng: random.Random, grade: int) -> SampledContent:
    groups = rng.choice(FACTORS)
    max_size = min(10, 100 // groups)
    size = rng.randint(1, max_size)
    return SampledContent(operands={"groups": groups, "size": size},
                          prompt={"stem": f"{groups} groups of {size}. How many in all?", "groups": groups, "size": size})


# ----- B-MUL02-ARRAY-TOTAL (rows 2-10, cols 2-10, product <= 100) -----
def sample_array_total(rng: random.Random, grade: int) -> SampledContent:
    rows = rng.randint(2, 10)
    max_cols = min(10, 100 // rows)
    cols = rng.randint(2, max(2, max_cols))
    return SampledContent(operands={"rows": rows, "cols": cols},
                          prompt={"stem": f"An array has {rows} rows and {cols} columns. How many?", "rows": rows, "cols": cols})


SAMPLER = ItemSampler(
    item_template_id="B-MUL03-FACTS-2-5-10", task_type="multiplication_fact", skill_id="multiplication",
    eligible_grades=(3,), response_format="single_integer_or_choice", sample=sample_fact_2_5_10,
    guard_ids=("G-GRADE-ELIGIBLE", "G-OPERAND-BOUNDS", "G-NO-NEGATIVE-RESULT",
               "G-DISTRACTOR-NE-CORRECT", "G-UNIQUE-DISTRACTORS", "G-NO-DUP-OPTIONS"),
)
_MUL01 = ItemSampler(
    item_template_id="B-MUL01-EQUAL-GROUPS", task_type="count_equal_groups", skill_id="multiplication",
    eligible_grades=(3,), response_format="single_integer_or_choice", sample=sample_equal_groups,
    guard_ids=("G-GRADE-ELIGIBLE", "G-OPERAND-BOUNDS", "G-EQUAL-GROUPS", "G-NO-NEGATIVE-RESULT",
               "G-DISTRACTOR-NE-CORRECT", "G-UNIQUE-DISTRACTORS", "G-NO-DUP-OPTIONS"),
)
_MUL02 = ItemSampler(
    item_template_id="B-MUL02-ARRAY-TOTAL", task_type="interpret_array", skill_id="multiplication",
    eligible_grades=(3,), response_format="single_integer_or_choice", sample=sample_array_total,
    guard_ids=("G-GRADE-ELIGIBLE", "G-OPERAND-BOUNDS", "G-ARRAY-VALID", "G-NO-NEGATIVE-RESULT",
               "G-DISTRACTOR-NE-CORRECT", "G-UNIQUE-DISTRACTORS", "G-NO-DUP-OPTIONS"),
)

ALL_SAMPLERS = (SAMPLER, _MUL01, _MUL02)
