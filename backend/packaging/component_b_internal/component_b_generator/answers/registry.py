"""Correct-answer rule registry, keyed by ``item_template_id`` (Phase B2A / B2A.2)."""

from __future__ import annotations

from typing import Any, Callable, Dict, Tuple

from . import rules
from .structured import structured_equivalent_forms

# Bumped for the B2A.2 coverage expansion (7 -> 29 answer rules; ordered + structured answers).
ANSWER_REGISTRY_VERSION = "b2a2-1.0.0"

# item_template_id -> pure correct-answer function(operands) -> raw answer value
ANSWER_RULES: Dict[str, Callable[[dict], Any]] = {
    # --- Phase B2A representatives (7) ---
    "B-CNT01-SEQ-CONTINUE": rules.counting_next_in_sequence,
    "B-NS04-COMPARE-NUMERALS": rules.number_sense_compare,
    "B-PV01-IDENTIFY-TENS-ONES": rules.place_value_digit,
    "B-ADD04-2D-NO-REGROUP": rules.addition_sum,
    "B-SUB04-2D-NO-BORROW": rules.subtraction_difference,
    "B-MUL03-FACTS-2-5-10": rules.multiplication_product,
    "B-DIV03-DIVIDE-BY-2": rules.division_quotient,
    # --- Phase B2A.2 additions (22) ---
    "B-CNT02-COUNT-OBJECTS": rules.cardinality_count,
    "B-CNT03-HOW-MANY": rules.cardinality_count,
    "B-CNT04-MAKE-SET": rules.make_set_target,
    "B-CNT06-SKIP-COUNT": rules.counting_next_in_sequence,
    "B-NS02-QUANTITY-NUMERAL": rules.cardinality_count,
    "B-NS03-COMPARE-SETS": rules.number_sense_compare_sets,
    "B-NS05-ORDER-NUMBERS": rules.order_numbers,
    "B-NS07-CONSERVATION": rules.conservation_answer,
    "B-PV02-DECOMPOSE-2D": rules.place_value_numeral,
    "B-PV03-IDENTIFY-HTO": rules.place_value_digit3,
    "B-PV04-DECOMPOSE-3D": rules.place_value_numeral,
    "B-ADD01-COMBINE-SETS": rules.addition_sum,
    "B-ADD02-COUNT-ON": rules.addition_count_on,
    "B-ADD03-SINGLE-DIGIT": rules.addition_sum,
    "B-ADD05-REGROUP": rules.addition_sum,
    "B-SUB01-TAKE-AWAY": rules.subtraction_difference,
    "B-SUB03-WITHIN-9": rules.subtraction_difference,
    "B-SUB05-BORROW": rules.subtraction_difference,
    "B-MUL01-EQUAL-GROUPS": rules.multiplication_equal_groups,
    "B-MUL02-ARRAY-TOTAL": rules.multiplication_array,
    "B-DIV01-EQUAL-SHARING": rules.division_sharing,
    "B-DIV02-EQUAL-GROUPING": rules.division_grouping,
}

# Templates whose catalogue response format admits equivalent written place-value forms.
_STRUCTURED_EQUIVALENCE_TEMPLATES = frozenset({"B-PV02-DECOMPOSE-2D", "B-PV04-DECOMPOSE-3D"})


def correct_answer_raw(item_template_id: str, operands: dict) -> Any:
    """Recompute the raw (un-normalized) correct answer for a template + operands."""
    fn = ANSWER_RULES.get(item_template_id)
    if fn is None:
        raise KeyError(f"no answer rule registered for template {item_template_id!r}")
    return fn(operands)


def allowed_equivalent_answers(item_template_id: str, operands: dict) -> Tuple[str, ...]:
    """Accepted alternative canonical forms beyond the single correct answer.

    For most templates the accepted set is exactly the canonical form (whitespace / leading-zero
    variants are already handled by :func:`answers.rules.answers_equivalent`), so this is empty.
    The structured place-value decomposition templates additionally accept reviewed expanded and
    unit-word forms (e.g. ``123`` also accepts ``100 + 20 + 3`` and ``1 hundreds + 2 tens +
    3 ones``), generated deterministically by the reviewed parser (no eval).
    """
    if item_template_id in _STRUCTURED_EQUIVALENCE_TEMPLATES:
        return structured_equivalent_forms(int(operands["n"]))
    return ()


def supported_answer_template_ids() -> Tuple[str, ...]:
    return tuple(sorted(ANSWER_RULES))
