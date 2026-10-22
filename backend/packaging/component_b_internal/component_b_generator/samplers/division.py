"""Division samplers (Phase B2A / B2A.2).

Implemented: DIV01 (equal sharing between 2 recipients), DIV02 (equal grouping, group size
2/5/10), DIV03 (divide-by-2 facts). All divisions are exact (no remainder). Sharing (how many
each recipient gets) and grouping (how many groups form) are kept as distinct semantics.
DEFERRED: DIV04 (multiplication/division fact family, CALIBRATION_PENDING). DIV01 recipients 5
and 10 are deferred per catalogue (PROJECT_PROPOSAL); only sharing between 2 is implemented.
"""

from __future__ import annotations

import random

from .base import ItemSampler, SampledContent


# ----- B-DIV03-DIVIDE-BY-2 (even dividend 2-98, divisor 2) -----
def sample_divide_by_two(rng: random.Random, grade: int) -> SampledContent:
    dividend = 2 * rng.randint(1, 49)
    return SampledContent(operands={"dividend": dividend, "divisor": 2},
                          prompt={"stem": f"{dividend} / 2 = ?", "dividend": dividend, "divisor": 2})


# ----- B-DIV01-EQUAL-SHARING (even total 2-40 shared between 2 recipients) -----
def sample_equal_sharing(rng: random.Random, grade: int) -> SampledContent:
    total = 2 * rng.randint(1, 20)  # even, 2..40
    recipients = 2
    return SampledContent(operands={"total": total, "recipients": recipients},
                          prompt={"stem": f"Share {total} equally between {recipients}. How many each?",
                                  "total": total, "recipients": recipients})


# ----- B-DIV02-EQUAL-GROUPING (total 2-40 divided into groups of 2/5/10) -----
def sample_equal_grouping(rng: random.Random, grade: int) -> SampledContent:
    group_size = rng.choice((2, 5, 10))
    max_groups = 40 // group_size
    groups = rng.randint(1, max_groups)
    total = group_size * groups
    return SampledContent(operands={"total": total, "group_size": group_size},
                          prompt={"stem": f"Put {total} into groups of {group_size}. How many groups?",
                                  "total": total, "group_size": group_size})


SAMPLER = ItemSampler(
    item_template_id="B-DIV03-DIVIDE-BY-2", task_type="division_fact_by_two", skill_id="division",
    eligible_grades=(3,), response_format="single_integer_or_choice", sample=sample_divide_by_two,
    guard_ids=("G-GRADE-ELIGIBLE", "G-NO-DIV-ZERO", "G-EXACT-DIVISIBILITY", "G-OPERAND-BOUNDS",
               "G-NO-NEGATIVE-RESULT", "G-DISTRACTOR-NE-CORRECT", "G-UNIQUE-DISTRACTORS", "G-NO-DUP-OPTIONS"),
)
_DIV01 = ItemSampler(
    item_template_id="B-DIV01-EQUAL-SHARING", task_type="share_equally", skill_id="division",
    eligible_grades=(3,), response_format="single_integer_or_choice", sample=sample_equal_sharing,
    guard_ids=("G-GRADE-ELIGIBLE", "G-OPERAND-BOUNDS", "G-SHARING-EXACT", "G-NO-NEGATIVE-RESULT",
               "G-DISTRACTOR-NE-CORRECT", "G-UNIQUE-DISTRACTORS", "G-NO-DUP-OPTIONS"),
)
_DIV02 = ItemSampler(
    item_template_id="B-DIV02-EQUAL-GROUPING", task_type="form_equal_groups", skill_id="division",
    eligible_grades=(3,), response_format="single_integer_or_choice", sample=sample_equal_grouping,
    guard_ids=("G-GRADE-ELIGIBLE", "G-OPERAND-BOUNDS", "G-GROUPING-EXACT", "G-NO-NEGATIVE-RESULT",
               "G-DISTRACTOR-NE-CORRECT", "G-UNIQUE-DISTRACTORS", "G-NO-DUP-OPTIONS"),
)

ALL_SAMPLERS = (SAMPLER, _DIV01, _DIV02)
