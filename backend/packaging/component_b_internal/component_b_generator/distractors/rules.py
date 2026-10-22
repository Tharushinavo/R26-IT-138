"""Per-template distractor-candidate rules + bounds predicates (Phase B2A / B2A.2).

Each rule is a pure function of ``(operands, correct_raw)`` returning ordered
``(candidate_value, rule_id)`` pairs. The registry layer normalizes, range-checks, excludes the
correct answer and its accepted equivalents, de-duplicates, and (when a required count is
requested) tops up integer templates with generic off-by-k fillers — so these rules only need to
*propose* mathematically motivated candidates. No ``eval``; no RNG (reproducible from operands).

Distractors are mathematical candidates only. They are never assigned to a learner and never
classified as a learner misconception (that is out of scope until B2B).
"""

from __future__ import annotations

from typing import Callable, List, Tuple

from ..answers.rules import RELATIONS

Candidate = Tuple[object, str]  # (raw value, rule_id)


def _digits(n: int) -> Tuple[int, int]:
    return (n // 10) % 10, n % 10  # (tens, ones)


# --------------------------------------------------------------------------------------
# Distractor proposal rules
# --------------------------------------------------------------------------------------


def counting_distractors(operands: dict, correct: int) -> List[Candidate]:
    last = int(operands["sequence"][-1])
    return [
        (correct - 1, "D-OFF-BY-ONE-MINUS"),
        (correct + 1, "D-OFF-BY-ONE-PLUS"),
        (correct - 2, "D-OFF-BY-TWO-MINUS"),
        (correct + 2, "D-OFF-BY-TWO-PLUS"),
        (last, "D-REPEAT-LAST"),
    ]


def skip_count_distractors(operands: dict, correct: int) -> List[Candidate]:
    last = int(operands["sequence"][-1])
    step = int(operands["step"])
    return [
        (last, "D-REPEAT-LAST"),
        (correct + step, "D-EXTRA-STEP"),
        (correct - step, "D-MISSED-STEP"),
        (correct + 1, "D-OFF-BY-ONE-PLUS"),
        (correct - 1, "D-OFF-BY-ONE-MINUS"),
    ]


def cardinality_distractors(operands: dict, correct: int) -> List[Candidate]:
    return [
        (correct - 1, "D-MISCOUNT-MINUS-ONE"),
        (correct + 1, "D-MISCOUNT-PLUS-ONE"),
        (correct - 2, "D-MISCOUNT-MINUS-TWO"),
        (correct + 2, "D-MISCOUNT-PLUS-TWO"),
    ]


def make_set_distractors(operands: dict, correct: int) -> List[Candidate]:
    # Interactive set production: no fixed multiple-choice option set.
    return []


def number_sense_distractors(operands: dict, correct: str) -> List[Candidate]:
    return [(r, "D-OTHER-RELATION") for r in RELATIONS if r != correct]


def compare_sets_distractors(operands: dict, correct: str) -> List[Candidate]:
    return [(r, "D-OTHER-RELATION") for r in RELATIONS if r != correct]


def order_numbers_distractors(operands: dict, correct) -> List[Candidate]:
    c = tuple(int(x) for x in correct)
    reverse = tuple(reversed(c))
    swap_first = (c[1], c[0], c[2])
    swap_last = (c[0], c[2], c[1])
    return [
        (reverse, "D-REVERSED-ORDER"),
        (swap_first, "D-ADJACENT-SWAP-FIRST"),
        (swap_last, "D-ADJACENT-SWAP-LAST"),
    ]


def conservation_distractors(operands: dict, correct: str) -> List[Candidate]:
    other = "changed" if correct == "same" else "same"
    return [(other, "D-OPPOSITE-JUDGEMENT")]


def place_value_distractors(operands: dict, correct: int) -> List[Candidate]:
    n = int(operands["n"])
    place = str(operands["place"])
    tens, ones = _digits(n)
    other_digit = ones if place == "tens" else tens
    return [
        (other_digit, "D-OTHER-DIGIT"),
        (correct - 1, "D-NEARBY-MINUS"),
        (correct + 1, "D-NEARBY-PLUS"),
    ]


def place_value_digit3_distractors(operands: dict, correct: int) -> List[Candidate]:
    n = int(operands["n"])
    place = str(operands["place"])
    hundreds, tens, ones = (n // 100) % 10, (n // 10) % 10, n % 10
    others = {"hundreds": (tens, ones), "tens": (hundreds, ones), "ones": (hundreds, tens)}[place]
    return [
        (others[0], "D-OTHER-PLACE-DIGIT-A"),
        (others[1], "D-OTHER-PLACE-DIGIT-B"),
        (correct - 1, "D-NEARBY-MINUS"),
        (correct + 1, "D-NEARBY-PLUS"),
    ]


def structured_no_distractors(operands: dict, correct) -> List[Candidate]:
    # Decomposition templates use accepted equivalent written forms, not distractors.
    return []


def addition_distractors(operands: dict, correct: int) -> List[Candidate]:
    a, b = int(operands["a"]), int(operands["b"])
    _, ones_a = _digits(a)
    _, ones_b = _digits(b)
    return [
        (correct - 1, "D-OFF-BY-ONE-MINUS"),
        (correct + 1, "D-OFF-BY-ONE-PLUS"),
        (abs(a - b), "D-OPERATOR-CONFUSION-DIFF"),
        (a, "D-ONE-ADDEND"),
        (ones_a + ones_b, "D-ONES-ONLY-SUM"),
    ]


def count_on_distractors(operands: dict, correct: int) -> List[Candidate]:
    start, jumps = int(operands["start"]), int(operands["jumps"])
    return [
        (correct - 1, "D-OFF-BY-ONE-MINUS"),
        (correct + 1, "D-OFF-BY-ONE-PLUS"),
        (start, "D-MISSED-ALL-JUMPS"),
        (start - jumps, "D-COUNTED-BACK"),
        (jumps, "D-JUMPS-ONLY"),
    ]


def subtraction_distractors(operands: dict, correct: int) -> List[Candidate]:
    a, b = int(operands["a"]), int(operands["b"])
    return [
        (correct - 1, "D-OFF-BY-ONE-MINUS"),
        (correct + 1, "D-OFF-BY-ONE-PLUS"),
        (a + b, "D-OPERATOR-CONFUSION-SUM"),
        (b, "D-SUBTRAHEND"),
    ]


def multiplication_distractors(operands: dict, correct: int) -> List[Candidate]:
    a, b = int(operands["a"]), int(operands["b"])
    return [
        (a * (b - 1), "D-ADJACENT-FACT-MINUS"),
        (a * (b + 1), "D-ADJACENT-FACT-PLUS"),
        (a + b, "D-OPERATOR-CONFUSION-SUM"),
        (correct - a, "D-PRODUCT-MINUS-FACTOR"),
        (correct + a, "D-PRODUCT-PLUS-FACTOR"),
    ]


def division_distractors(operands: dict, correct: int) -> List[Candidate]:
    dividend = int(operands["dividend"])
    return [
        (correct - 1, "D-OFF-BY-ONE-MINUS"),
        (correct + 1, "D-OFF-BY-ONE-PLUS"),
        (dividend - 2, "D-DIVIDEND-MINUS-DIVISOR"),
        (dividend, "D-INVERSE-DOUBLE"),
    ]


def equal_groups_distractors(operands: dict, correct: int) -> List[Candidate]:
    groups, size = int(operands["groups"]), int(operands["size"])
    return [
        (groups + size, "D-OPERATOR-CONFUSION-SUM"),
        (correct - size, "D-ONE-FEWER-GROUP"),
        (correct + size, "D-ONE-EXTRA-GROUP"),
        (groups, "D-GROUP-COUNT-ONLY"),
        (size, "D-GROUP-SIZE-ONLY"),
    ]


def array_distractors(operands: dict, correct: int) -> List[Candidate]:
    rows, cols = int(operands["rows"]), int(operands["cols"])
    return [
        (rows + cols, "D-OPERATOR-CONFUSION-SUM"),
        (correct - rows, "D-ONE-FEWER-COLUMN"),
        (correct + rows, "D-ONE-EXTRA-COLUMN"),
        (correct - cols, "D-ONE-FEWER-ROW"),
        (correct + cols, "D-ONE-EXTRA-ROW"),
    ]


def sharing_distractors(operands: dict, correct: int) -> List[Candidate]:
    total, recipients = int(operands["total"]), int(operands["recipients"])
    return [
        (correct - 1, "D-OFF-BY-ONE-MINUS"),
        (correct + 1, "D-OFF-BY-ONE-PLUS"),
        (total - recipients, "D-SUBTRACT-RECIPIENTS"),
        (recipients, "D-RECIPIENTS-ONLY"),
        (total, "D-TOTAL-UNSHARED"),
    ]


def grouping_distractors(operands: dict, correct: int) -> List[Candidate]:
    total, group_size = int(operands["total"]), int(operands["group_size"])
    return [
        (correct - 1, "D-OFF-BY-ONE-MINUS"),
        (correct + 1, "D-OFF-BY-ONE-PLUS"),
        (total - group_size, "D-SUBTRACT-GROUP-SIZE"),
        (group_size, "D-GROUP-SIZE-ONLY"),
        (total, "D-TOTAL-UNGROUPED"),
    ]


# --------------------------------------------------------------------------------------
# Per-template bounds predicates (a candidate is kept only if it obeys these).
# --------------------------------------------------------------------------------------


def _nonneg_int_max(hi: int) -> Callable[[object], bool]:
    def pred(v: object) -> bool:
        return isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= hi
    return pred


def _relation_bounds(v: object) -> bool:
    return isinstance(v, str) and v in RELATIONS


def _binary_bounds(v: object) -> bool:
    return isinstance(v, str) and v in ("same", "changed")


def _order_bounds(v: object) -> bool:
    if not isinstance(v, (tuple, list)) or len(v) != 3:
        return False
    if any(not isinstance(x, int) or isinstance(x, bool) or not (0 <= x <= 999) for x in v):
        return False
    return len(set(v)) == 3  # three distinct numbers


COUNTING_BOUNDS = _nonneg_int_max(50)
SKIP_BOUNDS = _nonneg_int_max(100)
CARDINALITY_BOUNDS = _nonneg_int_max(20)
PLACE_VALUE_BOUNDS = _nonneg_int_max(9)
ADDITION_BOUNDS = _nonneg_int_max(99)
ADD_SINGLE_BOUNDS = _nonneg_int_max(18)
ADD_COUNTON_BOUNDS = _nonneg_int_max(60)
SUBTRACTION_BOUNDS = _nonneg_int_max(99)
SUB_SINGLE_BOUNDS = _nonneg_int_max(9)
MULTIPLICATION_BOUNDS = _nonneg_int_max(120)
MUL_SMALL_BOUNDS = _nonneg_int_max(100)
DIVISION_BOUNDS = _nonneg_int_max(98)
DIV_SMALL_BOUNDS = _nonneg_int_max(20)
NUMBER_SENSE_BOUNDS = _relation_bounds
BINARY_BOUNDS = _binary_bounds
ORDER_BOUNDS = _order_bounds
