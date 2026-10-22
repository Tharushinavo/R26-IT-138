"""Pure correct-answer rules + deterministic normalization (Phase B2A).

Every function is a pure function of the sampled ``operands`` mapping produced by the matching
sampler. No I/O, no RNG, no ``eval`` — reviewed catalogue ``correct_answer_rule`` text is
translated into explicit Python here.
"""

from __future__ import annotations

from typing import Any

RELATIONS = ("<", ">", "=")


class AnswerRuleError(ValueError):
    """Raised when operands are structurally unfit for a correct-answer rule."""


def normalize_answer(value: Any) -> str:
    """Deterministic canonical string form of an answer.

    - integers / integer-valued strings -> base-10 with no leading zero (``"07" -> "7"``,
      ``"-0" -> "0"``); surrounding whitespace ignored;
    - relation symbols and other strings -> stripped text.

    This is the single normalization used for the stored ``correct_answer``, for equivalence
    checks, and for distractor de-duplication, so all three agree.
    """
    if isinstance(value, bool):  # guard: bool is an int subclass; not a valid answer here
        raise AnswerRuleError("boolean is not a valid answer value")
    if isinstance(value, int):
        return str(value)
    # Ordered answers (e.g. B-NS05 order-three-numbers) canonicalize element-wise, comma-joined,
    # so a list and an equivalent tuple share one canonical form and can be de-duplicated.
    if isinstance(value, (tuple, list)):
        return ",".join(normalize_answer(v) for v in value)
    text = str(value).strip()
    # Canonicalize integer-like text (handles leading zeros / '+' sign deterministically).
    body = text[1:] if text[:1] in "+-" else text
    if body.isdigit():
        return str(int(text))
    return text


def answers_equivalent(a: Any, b: Any) -> bool:
    """True iff two answers share the same canonical normalized form (deterministic)."""
    return normalize_answer(a) == normalize_answer(b)


# --------------------------------------------------------------------------------------
# Per-template correct-answer rules (one representative template per skill in B2A).
# --------------------------------------------------------------------------------------


def counting_next_in_sequence(operands: dict) -> int:
    """B-CNT01-SEQ-CONTINUE: next integer after the final shown numeral (1-step ascending)."""
    seq = list(operands["sequence"])
    step = int(operands["step"])
    if len(seq) < 1:
        raise AnswerRuleError("counting sequence must be non-empty")
    return int(seq[-1]) + step


def number_sense_compare(operands: dict) -> str:
    """B-NS04-COMPARE-NUMERALS: relation of a to b (one of '<', '>', '=')."""
    a, b = int(operands["a"]), int(operands["b"])
    if a < b:
        return "<"
    if a > b:
        return ">"
    return "="


def place_value_digit(operands: dict) -> int:
    """B-PV01-IDENTIFY-TENS-ONES: the digit at the requested place of a two-digit number."""
    n = int(operands["n"])
    place = str(operands["place"])
    if place == "tens":
        return (n // 10) % 10
    if place == "ones":
        return n % 10
    raise AnswerRuleError(f"unsupported place {place!r} (expected 'tens' or 'ones')")


def addition_sum(operands: dict) -> int:
    """B-ADD04-2D-NO-REGROUP: a + b."""
    return int(operands["a"]) + int(operands["b"])


def subtraction_difference(operands: dict) -> int:
    """B-SUB04-2D-NO-BORROW: a - b."""
    return int(operands["a"]) - int(operands["b"])


def multiplication_product(operands: dict) -> int:
    """B-MUL03-FACTS-2-5-10: a * b (a is the 2/5/10 factor)."""
    return int(operands["a"]) * int(operands["b"])


def division_quotient(operands: dict) -> int:
    """B-DIV03-DIVIDE-BY-2: dividend / divisor (exact integer division)."""
    dividend = int(operands["dividend"])
    divisor = int(operands["divisor"])
    if divisor == 0:
        raise AnswerRuleError("division by zero")
    if dividend % divisor != 0:
        raise AnswerRuleError("non-exact division has a remainder")
    return dividend // divisor


# --------------------------------------------------------------------------------------
# Phase B2A.2 correct-answer rules (22 additional templates).
# --------------------------------------------------------------------------------------


def cardinality_count(operands: dict) -> int:
    """B-CNT02 / B-CNT03 / B-NS02: the cardinality of the shown object set."""
    return int(operands["object_count"])


def make_set_target(operands: dict) -> int:
    """B-CNT04: the requested set size (number of objects to produce)."""
    return int(operands["target"])


def number_sense_compare_sets(operands: dict) -> str:
    """B-NS03: relation of set_a to set_b (non-symbolic comparison)."""
    a, b = int(operands["set_a"]), int(operands["set_b"])
    if a < b:
        return "<"
    if a > b:
        return ">"
    return "="


def order_numbers(operands: dict) -> tuple:
    """B-NS05: the three numbers sorted per the requested direction (ascending/descending)."""
    nums = [int(x) for x in operands["numbers"]]
    direction = str(operands["direction"])
    if direction == "ascending":
        return tuple(sorted(nums))
    if direction == "descending":
        return tuple(sorted(nums, reverse=True))
    raise AnswerRuleError(f"unsupported order direction {direction!r}")


def conservation_answer(operands: dict) -> str:
    """B-NS07: 'same' when the transformation preserves quantity (delta==0), else 'changed'."""
    return "same" if int(operands["delta"]) == 0 else "changed"


def place_value_numeral(operands: dict) -> int:
    """B-PV02 / B-PV04: the numeral being decomposed (the expanded form recomposes to this)."""
    return int(operands["n"])


def place_value_digit3(operands: dict) -> int:
    """B-PV03: the digit at the requested place of a three-digit number."""
    n = int(operands["n"])
    place = str(operands["place"])
    if place == "hundreds":
        return (n // 100) % 10
    if place == "tens":
        return (n // 10) % 10
    if place == "ones":
        return n % 10
    raise AnswerRuleError(f"unsupported place {place!r} (expected hundreds/tens/ones)")


def addition_count_on(operands: dict) -> int:
    """B-ADD02: start + jumps (count-on)."""
    return int(operands["start"]) + int(operands["jumps"])


def multiplication_equal_groups(operands: dict) -> int:
    """B-MUL01: groups * size."""
    return int(operands["groups"]) * int(operands["size"])


def multiplication_array(operands: dict) -> int:
    """B-MUL02: rows * cols."""
    return int(operands["rows"]) * int(operands["cols"])


def division_sharing(operands: dict) -> int:
    """B-DIV01: how many each recipient gets (total / recipients, exact)."""
    total, recipients = int(operands["total"]), int(operands["recipients"])
    if recipients == 0:
        raise AnswerRuleError("sharing among zero recipients")
    if total % recipients != 0:
        raise AnswerRuleError("non-exact sharing has a remainder")
    return total // recipients


def division_grouping(operands: dict) -> int:
    """B-DIV02: how many groups form (total / group_size, exact)."""
    total, group_size = int(operands["total"]), int(operands["group_size"])
    if group_size == 0:
        raise AnswerRuleError("grouping with zero group size")
    if total % group_size != 0:
        raise AnswerRuleError("non-exact grouping has a remainder")
    return total // group_size
