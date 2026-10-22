"""Hard mathematical + catalogue-constraint guards (Phase B2A).

Each guard is a pure check over a :class:`GuardContext`. On success it returns its stable
guard id; on violation it raises :class:`TaskInstanceValidationError`. Guards are the
authority on validity: even though samplers only ever draw valid operands, every instance is
re-verified independently (defense in depth), and the guards are exercised directly with
deliberately-invalid operands in the tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Tuple

from .errors import TaskInstanceValidationError

# Bumped for the B2A.2 coverage expansion (new mathematical guards + operand bounds).
GUARD_REGISTRY_VERSION = "b2a2-1.0.0"


@dataclass(frozen=True)
class GuardContext:
    item_template_id: str
    task_type: str
    skill_id: str
    grade: int
    eligible_grades: Tuple[int, ...]
    operands: dict
    correct_raw: object
    correct_norm: str
    distractors: Tuple[str, ...] = field(default_factory=tuple)


def _fail(guard_id: str, message: str) -> None:
    raise TaskInstanceValidationError(f"{guard_id}: {message}")


def _digits2(n: int) -> Tuple[int, int]:
    return (n // 10) % 10, n % 10


def _digits3(n: int) -> Tuple[int, int, int]:
    return (n // 100) % 10, (n // 10) % 10, n % 10  # (hundreds, tens, ones)


# --------------------------------------------------------------------------------------
# Per-template operand-bounds checks (translated from catalogue number/operand envelopes).
# --------------------------------------------------------------------------------------


def _bounds_counting(o: dict) -> None:
    seq = list(o.get("sequence", []))
    step = int(o.get("step", 0))
    if step != 1:
        _fail("G-OPERAND-BOUNDS", "counting step must be 1 (ascending 1-step)")
    if not (3 <= len(seq) <= 6):
        _fail("G-OPERAND-BOUNDS", "counting sequence length must be 3..6")
    if any(not (1 <= int(x) <= 50) for x in seq):
        _fail("G-OPERAND-BOUNDS", "counting terms must be within 1..50")
    if any(int(seq[i + 1]) - int(seq[i]) != 1 for i in range(len(seq) - 1)):
        _fail("G-OPERAND-BOUNDS", "counting sequence must be consecutive ascending")
    if not (int(seq[-1]) + step <= 50):
        _fail("G-OPERAND-BOUNDS", "counting answer must stay within 1..50")


def _bounds_number_sense(o: dict) -> None:
    for k in ("a", "b"):
        if not (1 <= int(o[k]) <= 999):
            _fail("G-OPERAND-BOUNDS", "compare operands must be within 1..999")


def _bounds_place_value(o: dict) -> None:
    if not (10 <= int(o["n"]) <= 99):
        _fail("G-OPERAND-BOUNDS", "place-value number must be a two-digit 10..99")
    if str(o["place"]) not in ("tens", "ones"):
        _fail("G-OPERAND-BOUNDS", "place must be 'tens' or 'ones'")


def _bounds_addition(o: dict) -> None:
    a, b = int(o["a"]), int(o["b"])
    if not (10 <= a <= 99 and 10 <= b <= 99):
        _fail("G-OPERAND-BOUNDS", "addition operands must be two-digit 10..99")
    if a + b > 99:
        _fail("G-OPERAND-BOUNDS", "addition total must be <= 99")


def _bounds_subtraction(o: dict) -> None:
    a, b = int(o["a"]), int(o["b"])
    if not (10 <= a <= 99 and 10 <= b <= 99):
        _fail("G-OPERAND-BOUNDS", "subtraction operands must be two-digit 10..99")


def _bounds_multiplication(o: dict) -> None:
    a, b = int(o["a"]), int(o["b"])
    if a not in (2, 5, 10):
        _fail("G-OPERAND-BOUNDS", "multiplication factor must be one of 2, 5, 10")
    if not (0 <= b <= 10):
        _fail("G-OPERAND-BOUNDS", "multiplicand must be within 0..10")
    if a * b > 100:
        _fail("G-OPERAND-BOUNDS", "product must be <= 100")


def _bounds_division(o: dict) -> None:
    d, v = int(o["dividend"]), int(o["divisor"])
    if v != 2:
        _fail("G-OPERAND-BOUNDS", "divisor must be 2")
    if not (2 <= d <= 98):
        _fail("G-OPERAND-BOUNDS", "dividend must be within 2..98")


# ----- Phase B2A.2 operand-bounds checks -----


def _bounds_cardinality(o: dict) -> None:
    if not (1 <= int(o["object_count"]) <= 20):
        _fail("G-OPERAND-BOUNDS", "object count must be within 1..20")


def _bounds_make_set(o: dict) -> None:
    target, pool = int(o["target"]), int(o["pool_size"])
    if not (1 <= target <= 20):
        _fail("G-OPERAND-BOUNDS", "make-set target must be within 1..20")
    if not (target < pool <= target + 8):
        _fail("G-OPERAND-BOUNDS", "make-set pool must be larger than target by 1..8")


def _bounds_skip_count(o: dict) -> None:
    seq = [int(x) for x in o.get("sequence", [])]
    step = int(o.get("step", 0))
    if step not in (2, 5, 10):
        _fail("G-OPERAND-BOUNDS", "skip step must be one of 2, 5, 10")
    if len(seq) < 2:
        _fail("G-OPERAND-BOUNDS", "skip sequence must show at least 2 anchors")
    if any(x < 0 for x in seq):
        _fail("G-OPERAND-BOUNDS", "skip terms must be non-negative")
    if any(seq[i + 1] - seq[i] != step for i in range(len(seq) - 1)):
        _fail("G-OPERAND-BOUNDS", "skip sequence must advance by the given step")
    if seq[-1] + step > 100:
        _fail("G-OPERAND-BOUNDS", "skip answer must stay within 100")


def _bounds_compare_sets(o: dict) -> None:
    a, b = int(o["set_a"]), int(o["set_b"])
    if not (1 <= a <= 20 and 1 <= b <= 20):
        _fail("G-OPERAND-BOUNDS", "set sizes must be within 1..20")
    if abs(a - b) > 8:
        _fail("G-OPERAND-BOUNDS", "set-size difference must be at most 8")


def _bounds_order_numbers(o: dict) -> None:
    nums = [int(x) for x in o["numbers"]]
    if len(nums) != 3:
        _fail("G-OPERAND-BOUNDS", "order task must have exactly 3 numbers")
    if any(not (0 <= x <= 999) for x in nums):
        _fail("G-OPERAND-BOUNDS", "order numbers must be within 0..999")
    if len(set(nums)) != 3:
        _fail("G-OPERAND-BOUNDS", "order numbers must be distinct")
    if str(o["direction"]) not in ("ascending", "descending"):
        _fail("G-OPERAND-BOUNDS", "order direction must be ascending or descending")


def _bounds_conservation(o: dict) -> None:
    n = int(o["initial_count"])
    if not (1 <= n <= 15):
        _fail("G-OPERAND-BOUNDS", "conservation initial count must be within 1..15")
    if str(o["transformation"]) not in ("rearrange", "add", "remove"):
        _fail("G-OPERAND-BOUNDS", "conservation transformation is not recognized")


def _bounds_decompose_2d(o: dict) -> None:
    n = int(o["n"])
    if not (10 <= n <= 99):
        _fail("G-OPERAND-BOUNDS", "decompose-2D number must be within 10..99")


def _bounds_identify_hto(o: dict) -> None:
    if not (100 <= int(o["n"]) <= 999):
        _fail("G-OPERAND-BOUNDS", "3-digit number must be within 100..999")
    if str(o["place"]) not in ("hundreds", "tens", "ones"):
        _fail("G-OPERAND-BOUNDS", "place must be hundreds, tens, or ones")


def _bounds_decompose_3d(o: dict) -> None:
    if not (100 <= int(o["n"]) <= 999):
        _fail("G-OPERAND-BOUNDS", "decompose-3D number must be within 100..999")


def _bounds_add_single(o: dict) -> None:
    a, b = int(o["a"]), int(o["b"])
    if not (0 <= a <= 9 and 0 <= b <= 9):
        _fail("G-OPERAND-BOUNDS", "single-digit addends must be within 0..9")
    if a + b > 18:
        _fail("G-OPERAND-BOUNDS", "single-digit sum must be <= 18")


def _bounds_count_on(o: dict) -> None:
    start, jumps = int(o["start"]), int(o["jumps"])
    if not (1 <= start <= 50):
        _fail("G-OPERAND-BOUNDS", "count-on start must be within 1..50")
    if not (1 <= jumps <= 10):
        _fail("G-OPERAND-BOUNDS", "count-on jumps must be within 1..10")


def _bounds_add_regroup(o: dict) -> None:
    a, b = int(o["a"]), int(o["b"])
    if not (10 <= a <= 99 and 10 <= b <= 99):
        _fail("G-OPERAND-BOUNDS", "regroup addends must be two-digit 10..99")
    if a + b > 99:
        _fail("G-OPERAND-BOUNDS", "regroup total must be <= 99 (no hundreds)")


def _bounds_take_away(o: dict) -> None:
    a, b = int(o["a"]), int(o["b"])
    if not (1 <= a <= 9):
        _fail("G-OPERAND-BOUNDS", "take-away total must be within 1..9")
    if not (0 <= b <= a):
        _fail("G-OPERAND-BOUNDS", "take-away removed must be within 0..total")


def _bounds_sub_within9(o: dict) -> None:
    a, b = int(o["a"]), int(o["b"])
    if not (0 <= a <= 9):
        _fail("G-OPERAND-BOUNDS", "single-digit minuend must be within 0..9")
    if not (0 <= b <= a):
        _fail("G-OPERAND-BOUNDS", "single-digit subtrahend must be within 0..minuend")


def _bounds_sub_borrow(o: dict) -> None:
    a, b = int(o["a"]), int(o["b"])
    if not (10 <= a <= 99 and 10 <= b <= 99):
        _fail("G-OPERAND-BOUNDS", "borrow operands must be two-digit 10..99")
    if a < b:
        _fail("G-OPERAND-BOUNDS", "borrow result must be non-negative")


def _bounds_equal_groups(o: dict) -> None:
    groups, size = int(o["groups"]), int(o["size"])
    if groups not in (2, 5, 10):
        _fail("G-OPERAND-BOUNDS", "group count must be one of 2, 5, 10")
    if not (1 <= size <= 10):
        _fail("G-OPERAND-BOUNDS", "group size must be within 1..10")
    if groups * size > 100:
        _fail("G-OPERAND-BOUNDS", "product must be <= 100")


def _bounds_array(o: dict) -> None:
    rows, cols = int(o["rows"]), int(o["cols"])
    if not (2 <= rows <= 10 and 2 <= cols <= 10):
        _fail("G-OPERAND-BOUNDS", "array rows/cols must be within 2..10")
    if rows * cols > 100:
        _fail("G-OPERAND-BOUNDS", "array product must be <= 100")


def _bounds_sharing(o: dict) -> None:
    total, recipients = int(o["total"]), int(o["recipients"])
    if recipients != 2:
        _fail("G-OPERAND-BOUNDS", "sharing recipients must be 2")
    if not (2 <= total <= 40):
        _fail("G-OPERAND-BOUNDS", "sharing total must be within 2..40")


def _bounds_grouping(o: dict) -> None:
    total, group_size = int(o["total"]), int(o["group_size"])
    if group_size not in (2, 5, 10):
        _fail("G-OPERAND-BOUNDS", "group size must be one of 2, 5, 10")
    if not (2 <= total <= 40):
        _fail("G-OPERAND-BOUNDS", "grouping total must be within 2..40")


_OPERAND_BOUNDS: Dict[str, Callable[[dict], None]] = {
    # --- Phase B2A representatives (7) ---
    "B-CNT01-SEQ-CONTINUE": _bounds_counting,
    "B-NS04-COMPARE-NUMERALS": _bounds_number_sense,
    "B-PV01-IDENTIFY-TENS-ONES": _bounds_place_value,
    "B-ADD04-2D-NO-REGROUP": _bounds_addition,
    "B-SUB04-2D-NO-BORROW": _bounds_subtraction,
    "B-MUL03-FACTS-2-5-10": _bounds_multiplication,
    "B-DIV03-DIVIDE-BY-2": _bounds_division,
    # --- Phase B2A.2 additions (22) ---
    "B-CNT02-COUNT-OBJECTS": _bounds_cardinality,
    "B-CNT03-HOW-MANY": _bounds_cardinality,
    "B-CNT04-MAKE-SET": _bounds_make_set,
    "B-CNT06-SKIP-COUNT": _bounds_skip_count,
    "B-NS02-QUANTITY-NUMERAL": _bounds_cardinality,
    "B-NS03-COMPARE-SETS": _bounds_compare_sets,
    "B-NS05-ORDER-NUMBERS": _bounds_order_numbers,
    "B-NS07-CONSERVATION": _bounds_conservation,
    "B-PV02-DECOMPOSE-2D": _bounds_decompose_2d,
    "B-PV03-IDENTIFY-HTO": _bounds_identify_hto,
    "B-PV04-DECOMPOSE-3D": _bounds_decompose_3d,
    "B-ADD01-COMBINE-SETS": _bounds_add_single,
    "B-ADD02-COUNT-ON": _bounds_count_on,
    "B-ADD03-SINGLE-DIGIT": _bounds_add_single,
    "B-ADD05-REGROUP": _bounds_add_regroup,
    "B-SUB01-TAKE-AWAY": _bounds_take_away,
    "B-SUB03-WITHIN-9": _bounds_sub_within9,
    "B-SUB05-BORROW": _bounds_sub_borrow,
    "B-MUL01-EQUAL-GROUPS": _bounds_equal_groups,
    "B-MUL02-ARRAY-TOTAL": _bounds_array,
    "B-DIV01-EQUAL-SHARING": _bounds_sharing,
    "B-DIV02-EQUAL-GROUPING": _bounds_grouping,
}


# --------------------------------------------------------------------------------------
# Guards
# --------------------------------------------------------------------------------------


def guard_grade_eligible(ctx: GuardContext) -> str:
    if ctx.grade not in ctx.eligible_grades:
        _fail("G-GRADE-ELIGIBLE", f"grade {ctx.grade} not in eligible grades {ctx.eligible_grades}")
    return "G-GRADE-ELIGIBLE"


def guard_operand_bounds(ctx: GuardContext) -> str:
    check = _OPERAND_BOUNDS.get(ctx.item_template_id)
    if check is None:
        _fail("G-OPERAND-BOUNDS", f"no operand-bounds check for {ctx.item_template_id}")
    check(ctx.operands)
    return "G-OPERAND-BOUNDS"


def guard_no_negative_result(ctx: GuardContext) -> str:
    if isinstance(ctx.correct_raw, int) and ctx.correct_raw < 0:
        _fail("G-NO-NEGATIVE-RESULT", f"result {ctx.correct_raw} is negative")
    return "G-NO-NEGATIVE-RESULT"


def guard_no_div_zero(ctx: GuardContext) -> str:
    if int(ctx.operands.get("divisor", 1)) == 0:
        _fail("G-NO-DIV-ZERO", "divisor is zero")
    return "G-NO-DIV-ZERO"


def guard_exact_divisibility(ctx: GuardContext) -> str:
    d, v = int(ctx.operands["dividend"]), int(ctx.operands["divisor"])
    if v == 0 or d % v != 0:
        _fail("G-EXACT-DIVISIBILITY", f"{d}/{v} is not exact (remainder present)")
    return "G-EXACT-DIVISIBILITY"


def guard_no_regroup(ctx: GuardContext) -> str:
    a, b = int(ctx.operands["a"]), int(ctx.operands["b"])
    ta, oa = _digits2(a)
    tb, ob = _digits2(b)
    if oa + ob > 9 or ta + tb > 9 or a + b > 99:
        _fail("G-NO-REGROUP", f"{a}+{b} requires regrouping (forbidden for a no-regroup template)")
    return "G-NO-REGROUP"


def guard_no_borrow(ctx: GuardContext) -> str:
    a, b = int(ctx.operands["a"]), int(ctx.operands["b"])
    ta, oa = _digits2(a)
    tb, ob = _digits2(b)
    if oa < ob or ta < tb:
        _fail("G-NO-BORROW", f"{a}-{b} requires borrowing (forbidden for a no-borrow template)")
    return "G-NO-BORROW"


def guard_distinct_digits(ctx: GuardContext) -> str:
    n = int(ctx.operands["n"])
    t, o = _digits2(n)
    if t == o:
        _fail("G-DISTINCT-DIGITS", f"{n} has repeated digits (forbidden in v1)")
    return "G-DISTINCT-DIGITS"


def guard_sequence_length(ctx: GuardContext) -> str:
    seq = list(ctx.operands.get("sequence", []))
    if not (3 <= len(seq) <= 6):
        _fail("G-SEQUENCE-LENGTH", f"sequence length {len(seq)} outside 3..6")
    return "G-SEQUENCE-LENGTH"


# Template -> ((operand_key, minimum_value), ...). A multi-digit display slot must hold a value
# >= its minimum (e.g. a two-digit slot is >= 10) so it is not a shorter number padded with a
# leading zero into a wider position.
_LEADING_ZERO_SLOTS = {
    "B-PV01-IDENTIFY-TENS-ONES": (("n", 10),),
    "B-ADD04-2D-NO-REGROUP": (("a", 10), ("b", 10)),
    "B-SUB04-2D-NO-BORROW": (("a", 10), ("b", 10)),
    "B-ADD05-REGROUP": (("a", 10), ("b", 10)),
    "B-SUB05-BORROW": (("a", 10), ("b", 10)),
    "B-PV02-DECOMPOSE-2D": (("n", 10),),
    "B-PV03-IDENTIFY-HTO": (("n", 100),),
    "B-PV04-DECOMPOSE-3D": (("n", 100),),
}


def guard_no_leading_zero(ctx: GuardContext) -> str:
    # Displayed numerals must never render with a leading zero. Integer operands render
    # canonically; for multi-digit-template slots the value must be >= the slot minimum.
    for key, minimum in _LEADING_ZERO_SLOTS.get(ctx.item_template_id, ()):
        v = int(ctx.operands[key])
        if v < minimum or (len(str(v)) > 1 and str(v)[0] == "0"):
            _fail("G-NO-LEADING-ZERO", f"operand {key}={v} would render with a leading zero")
    for x in ctx.operands.get("sequence", []) or []:
        s = str(int(x))
        if len(s) > 1 and s[0] == "0":
            _fail("G-NO-LEADING-ZERO", f"sequence term {x} renders with a leading zero")
    return "G-NO-LEADING-ZERO"


# --------------------------------------------------------------------------------------
# Phase B2A.2 mathematical guards
# --------------------------------------------------------------------------------------


def guard_cardinality(ctx: GuardContext) -> str:
    # The recomputed answer must equal the shown quantity (object_count) or requested set size.
    if "object_count" in ctx.operands:
        n = int(ctx.operands["object_count"])
        if int(ctx.correct_raw) != n:
            _fail("G-CARDINALITY", f"answer {ctx.correct_raw} != shown cardinality {n}")
    elif "target" in ctx.operands:
        t = int(ctx.operands["target"])
        if int(ctx.correct_raw) != t:
            _fail("G-CARDINALITY", f"answer {ctx.correct_raw} != requested set size {t}")
    else:
        _fail("G-CARDINALITY", "no cardinality operand present")
    return "G-CARDINALITY"


def guard_skip_step(ctx: GuardContext) -> str:
    seq = [int(x) for x in ctx.operands.get("sequence", [])]
    step = int(ctx.operands.get("step", 0))
    if step not in (2, 5, 10):
        _fail("G-SKIP-STEP", f"skip step {step} is not one of 2, 5, 10")
    if len(seq) < 2 or any(seq[i + 1] - seq[i] != step for i in range(len(seq) - 1)):
        _fail("G-SKIP-STEP", "skip sequence is not a consistent arithmetic progression")
    if int(ctx.correct_raw) != seq[-1] + step:
        _fail("G-SKIP-STEP", "skip answer must be the last term plus the step")
    return "G-SKIP-STEP"


def guard_regroup_required(ctx: GuardContext) -> str:
    a, b = int(ctx.operands["a"]), int(ctx.operands["b"])
    _, oa = _digits2(a)
    _, ob = _digits2(b)
    if oa + ob < 10:
        _fail("G-REGROUP-REQUIRED", f"{a}+{b} does not require regrouping (ones sum < 10)")
    return "G-REGROUP-REQUIRED"


def guard_borrow_required(ctx: GuardContext) -> str:
    a, b = int(ctx.operands["a"]), int(ctx.operands["b"])
    _, oa = _digits2(a)
    _, ob = _digits2(b)
    if oa >= ob:
        _fail("G-BORROW-REQUIRED", f"{a}-{b} does not require borrowing (ones digit sufficient)")
    if a - b < 0:
        _fail("G-BORROW-REQUIRED", f"{a}-{b} is negative")
    return "G-BORROW-REQUIRED"


def guard_equal_groups(ctx: GuardContext) -> str:
    groups, size = int(ctx.operands["groups"]), int(ctx.operands["size"])
    if groups <= 0 or size <= 0:
        _fail("G-EQUAL-GROUPS", "group count and size must be positive")
    if int(ctx.correct_raw) != groups * size:
        _fail("G-EQUAL-GROUPS", "answer must equal groups * size")
    return "G-EQUAL-GROUPS"


def guard_array_valid(ctx: GuardContext) -> str:
    rows, cols = int(ctx.operands["rows"]), int(ctx.operands["cols"])
    if rows <= 0 or cols <= 0:
        _fail("G-ARRAY-VALID", "rows and cols must be positive")
    if int(ctx.correct_raw) != rows * cols:
        _fail("G-ARRAY-VALID", "answer must equal rows * cols")
    return "G-ARRAY-VALID"


def guard_sharing_exact(ctx: GuardContext) -> str:
    total, recipients = int(ctx.operands["total"]), int(ctx.operands["recipients"])
    if recipients <= 0 or total % recipients != 0:
        _fail("G-SHARING-EXACT", f"{total} does not share exactly among {recipients}")
    if int(ctx.correct_raw) != total // recipients:
        _fail("G-SHARING-EXACT", "answer must equal total // recipients")
    return "G-SHARING-EXACT"


def guard_grouping_exact(ctx: GuardContext) -> str:
    total, group_size = int(ctx.operands["total"]), int(ctx.operands["group_size"])
    if group_size <= 0 or total % group_size != 0:
        _fail("G-GROUPING-EXACT", f"{total} does not group exactly into {group_size}s")
    if int(ctx.correct_raw) != total // group_size:
        _fail("G-GROUPING-EXACT", "answer must equal total // group_size")
    return "G-GROUPING-EXACT"


def guard_order_valid(ctx: GuardContext) -> str:
    nums = [int(x) for x in ctx.operands["numbers"]]
    direction = str(ctx.operands["direction"])
    if len(set(nums)) != len(nums):
        _fail("G-ORDER-VALID", "order numbers must be distinct (unique ordering)")
    expected = sorted(nums, reverse=(direction == "descending"))
    answer = [int(x) for x in ctx.correct_raw]  # type: ignore[union-attr]
    if answer != expected:
        _fail("G-ORDER-VALID", "answer must be the numbers sorted in the requested direction")
    return "G-ORDER-VALID"


def guard_unique_comparison(ctx: GuardContext) -> str:
    if "a" in ctx.operands and "b" in ctx.operands:
        a, b = int(ctx.operands["a"]), int(ctx.operands["b"])
    else:
        a, b = int(ctx.operands["set_a"]), int(ctx.operands["set_b"])
    expected = "=" if a == b else (">" if a > b else "<")
    if ctx.correct_norm != expected:
        _fail("G-UNIQUE-COMPARISON", f"comparison answer {ctx.correct_norm!r} != unique relation {expected!r}")
    return "G-UNIQUE-COMPARISON"


def guard_conservation_consistent(ctx: GuardContext) -> str:
    delta = int(ctx.operands["delta"])
    expected = "same" if delta == 0 else "changed"
    if ctx.correct_norm != expected:
        _fail("G-CONSERVATION-CONSISTENT", f"conservation answer {ctx.correct_norm!r} inconsistent with delta {delta}")
    return "G-CONSERVATION-CONSISTENT"


def guard_decomp_reconstructs(ctx: GuardContext) -> str:
    n = int(ctx.operands["n"])
    if "hundreds" in ctx.operands:
        h, t, o = int(ctx.operands["hundreds"]), int(ctx.operands["tens"]), int(ctx.operands["ones"])
        if 100 * h + 10 * t + o != n:
            _fail("G-DECOMP-RECONSTRUCTS", f"{h}h {t}t {o}o does not reconstruct {n}")
    else:
        t, o = int(ctx.operands["tens"]), int(ctx.operands["ones"])
        if 10 * t + o != n:
            _fail("G-DECOMP-RECONSTRUCTS", f"{t}t {o}o does not reconstruct {n}")
    return "G-DECOMP-RECONSTRUCTS"


def guard_compose_matches(ctx: GuardContext) -> str:
    # The recomputed answer must be consistent with the numeral's digit composition.
    n = int(ctx.operands["n"])
    if "place" in ctx.operands:  # identify-digit templates
        h, t, o = _digits3(n)
        place = str(ctx.operands["place"])
        expected = {"hundreds": h, "tens": t, "ones": o}.get(place)
        if expected is None:
            _fail("G-COMPOSE-MATCHES", f"unknown place {place!r}")
        if int(ctx.correct_raw) != expected:
            _fail("G-COMPOSE-MATCHES", f"digit answer {ctx.correct_raw} != composed {place} digit {expected}")
    else:  # decomposition templates: the numeral itself is the composed value
        if int(ctx.correct_raw) != n:
            _fail("G-COMPOSE-MATCHES", f"composed value {ctx.correct_raw} != numeral {n}")
    return "G-COMPOSE-MATCHES"


def guard_unique_distractors(ctx: GuardContext) -> str:
    if len(set(ctx.distractors)) != len(ctx.distractors):
        _fail("G-UNIQUE-DISTRACTORS", "duplicate distractor candidates")
    return "G-UNIQUE-DISTRACTORS"


def guard_distractor_ne_correct(ctx: GuardContext) -> str:
    if ctx.correct_norm in ctx.distractors:
        _fail("G-DISTRACTOR-NE-CORRECT", "a distractor equals the correct answer")
    return "G-DISTRACTOR-NE-CORRECT"


def guard_no_dup_options(ctx: GuardContext) -> str:
    options = (ctx.correct_norm,) + tuple(ctx.distractors)
    if len(set(options)) != len(options):
        _fail("G-NO-DUP-OPTIONS", "duplicate answer options (correct + distractors)")
    return "G-NO-DUP-OPTIONS"


GUARD_FUNCS: Dict[str, Callable[[GuardContext], str]] = {
    "G-GRADE-ELIGIBLE": guard_grade_eligible,
    "G-OPERAND-BOUNDS": guard_operand_bounds,
    "G-NO-NEGATIVE-RESULT": guard_no_negative_result,
    "G-NO-DIV-ZERO": guard_no_div_zero,
    "G-EXACT-DIVISIBILITY": guard_exact_divisibility,
    "G-NO-REGROUP": guard_no_regroup,
    "G-NO-BORROW": guard_no_borrow,
    "G-DISTINCT-DIGITS": guard_distinct_digits,
    "G-SEQUENCE-LENGTH": guard_sequence_length,
    "G-NO-LEADING-ZERO": guard_no_leading_zero,
    "G-UNIQUE-DISTRACTORS": guard_unique_distractors,
    "G-DISTRACTOR-NE-CORRECT": guard_distractor_ne_correct,
    "G-NO-DUP-OPTIONS": guard_no_dup_options,
    # --- Phase B2A.2 guards ---
    "G-CARDINALITY": guard_cardinality,
    "G-SKIP-STEP": guard_skip_step,
    "G-REGROUP-REQUIRED": guard_regroup_required,
    "G-BORROW-REQUIRED": guard_borrow_required,
    "G-EQUAL-GROUPS": guard_equal_groups,
    "G-ARRAY-VALID": guard_array_valid,
    "G-SHARING-EXACT": guard_sharing_exact,
    "G-GROUPING-EXACT": guard_grouping_exact,
    "G-ORDER-VALID": guard_order_valid,
    "G-UNIQUE-COMPARISON": guard_unique_comparison,
    "G-CONSERVATION-CONSISTENT": guard_conservation_consistent,
    "G-DECOMP-RECONSTRUCTS": guard_decomp_reconstructs,
    "G-COMPOSE-MATCHES": guard_compose_matches,
}


def run_guards(guard_ids: Tuple[str, ...], ctx: GuardContext) -> Tuple[str, ...]:
    """Run the named guards in order; raise on the first violation. Returns applied ids."""
    applied = []
    for gid in guard_ids:
        fn = GUARD_FUNCS.get(gid)
        if fn is None:
            raise TaskInstanceValidationError(f"unknown guard id {gid!r}")
        applied.append(fn(ctx))
    return tuple(applied)
