"""Place-value samplers (Phase B2A / B2A.2).

Implemented: PV01 (identify tens/ones digit, 2-digit), PV02 (decompose 2-digit -> expanded
form), PV03 (identify hundreds/tens/ones digit, 3-digit), PV04 (decompose 3-digit -> expanded
form). PV02/PV04 are *structured-equivalence* templates: the correct answer is the numeral and
the accepted written forms (``20+3``, ``2 tens + 3 ones``) are supplied as equivalents rather
than as distractors. DEFERRED: PV05/PV06 (interactive base-ten regroup/ungroup exchange —
representation not specified as deterministic answerable content).
"""

from __future__ import annotations

import random

from .base import ItemSampler, SampledContent

# ----- B-PV01-IDENTIFY-TENS-ONES (2-digit, distinct digits) -----
PV01_MIN, PV01_MAX = 10, 99


def sample_identify_place(rng: random.Random, grade: int) -> SampledContent:
    n = rng.randint(PV01_MIN, PV01_MAX)
    while (n // 10) % 10 == n % 10:  # v1: no repeated digit
        n = rng.randint(PV01_MIN, PV01_MAX)
    place = rng.choice(["tens", "ones"])
    return SampledContent(operands={"n": n, "place": place},
                          prompt={"stem": f"In {n}, what is the {place} digit?", "n": n, "place": place})


# ----- B-PV02-DECOMPOSE-2D (expanded form of a 2-digit number) -----
def sample_decompose_2d(rng: random.Random, grade: int) -> SampledContent:
    n = rng.randint(10, 99)
    tens, ones = n // 10, n % 10
    return SampledContent(
        operands={"n": n, "tens": tens, "ones": ones},
        prompt={"stem": f"Write {n} in expanded form.", "n": n, "places": ["tens", "ones"]},
    )


# ----- B-PV03-IDENTIFY-HTO (identify a digit in a 3-digit number) -----
def sample_identify_hto(rng: random.Random, grade: int) -> SampledContent:
    n = rng.randint(100, 999)
    place = rng.choice(["hundreds", "tens", "ones"])
    return SampledContent(operands={"n": n, "place": place},
                          prompt={"stem": f"In {n}, what is the {place} digit?", "n": n, "place": place})


# ----- B-PV04-DECOMPOSE-3D (expanded form of a 3-digit number) -----
def sample_decompose_3d(rng: random.Random, grade: int) -> SampledContent:
    n = rng.randint(100, 999)
    hundreds, tens, ones = n // 100, (n // 10) % 10, n % 10
    return SampledContent(
        operands={"n": n, "hundreds": hundreds, "tens": tens, "ones": ones},
        prompt={"stem": f"Write {n} in expanded form.", "n": n, "places": ["hundreds", "tens", "ones"]},
    )


SAMPLER = ItemSampler(
    item_template_id="B-PV01-IDENTIFY-TENS-ONES", task_type="identify_digit_place", skill_id="place_value",
    eligible_grades=(2,), response_format="single_choice_or_integer", sample=sample_identify_place,
    guard_ids=("G-GRADE-ELIGIBLE", "G-OPERAND-BOUNDS", "G-DISTINCT-DIGITS", "G-NO-LEADING-ZERO",
               "G-DISTRACTOR-NE-CORRECT", "G-UNIQUE-DISTRACTORS", "G-NO-DUP-OPTIONS"),
)
_PV02 = ItemSampler(
    item_template_id="B-PV02-DECOMPOSE-2D", task_type="decompose_two_digit_number", skill_id="place_value",
    eligible_grades=(2,), response_format="expanded_form", sample=sample_decompose_2d,
    required_distractors=0, integer_answer=False,
    guard_ids=("G-GRADE-ELIGIBLE", "G-OPERAND-BOUNDS", "G-NO-LEADING-ZERO",
               "G-DECOMP-RECONSTRUCTS", "G-COMPOSE-MATCHES"),
)
_PV03 = ItemSampler(
    item_template_id="B-PV03-IDENTIFY-HTO", task_type="identify_hundreds_tens_ones", skill_id="place_value",
    eligible_grades=(3,), response_format="single_choice_or_integer", sample=sample_identify_hto,
    guard_ids=("G-GRADE-ELIGIBLE", "G-OPERAND-BOUNDS", "G-NO-LEADING-ZERO", "G-COMPOSE-MATCHES",
               "G-DISTRACTOR-NE-CORRECT", "G-UNIQUE-DISTRACTORS", "G-NO-DUP-OPTIONS"),
)
_PV04 = ItemSampler(
    item_template_id="B-PV04-DECOMPOSE-3D", task_type="decompose_three_digit_number", skill_id="place_value",
    eligible_grades=(3,), response_format="expanded_form", sample=sample_decompose_3d,
    required_distractors=0, integer_answer=False,
    guard_ids=("G-GRADE-ELIGIBLE", "G-OPERAND-BOUNDS", "G-NO-LEADING-ZERO",
               "G-DECOMP-RECONSTRUCTS", "G-COMPOSE-MATCHES"),
)

ALL_SAMPLERS = (SAMPLER, _PV02, _PV03, _PV04)
