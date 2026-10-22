"""Distractor registry + deterministic assembly (Phase B2A / B2A.2), keyed by ``item_template_id``.

Assembly is a pure function of the operands (no RNG). It normalizes candidates, excludes the
correct answer and its accepted equivalent forms, de-duplicates, range-checks, and preserves
deterministic order. When a ``required`` count is requested, integer-answer templates are topped
up with generic off-by-k fillers (nearest-first, bounds-respecting); if the required count still
cannot be met, :class:`DistractorGenerationError` is raised — the engine never silently returns
fewer distractors than required.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

from ..answers.registry import allowed_equivalent_answers
from ..answers.rules import normalize_answer
from ..generation.errors import DistractorGenerationError
from . import rules

# Bumped for the B2A.2 coverage expansion (required-count policy + off-by-k fillers).
DISTRACTOR_REGISTRY_VERSION = "b2a2-1.0.0"

# item_template_id -> (proposal rule, bounds predicate, integer-filler support)
_DISTRACTOR_RULES: Dict[str, Tuple[Callable[[dict, object], List[rules.Candidate]], Callable[[object], bool], bool]] = {
    # --- Phase B2A representatives (7) ---
    "B-CNT01-SEQ-CONTINUE": (rules.counting_distractors, rules.COUNTING_BOUNDS, True),
    "B-NS04-COMPARE-NUMERALS": (rules.number_sense_distractors, rules.NUMBER_SENSE_BOUNDS, False),
    "B-PV01-IDENTIFY-TENS-ONES": (rules.place_value_distractors, rules.PLACE_VALUE_BOUNDS, True),
    "B-ADD04-2D-NO-REGROUP": (rules.addition_distractors, rules.ADDITION_BOUNDS, True),
    "B-SUB04-2D-NO-BORROW": (rules.subtraction_distractors, rules.SUBTRACTION_BOUNDS, True),
    "B-MUL03-FACTS-2-5-10": (rules.multiplication_distractors, rules.MULTIPLICATION_BOUNDS, True),
    "B-DIV03-DIVIDE-BY-2": (rules.division_distractors, rules.DIVISION_BOUNDS, True),
    # --- Phase B2A.2 additions (22) ---
    "B-CNT02-COUNT-OBJECTS": (rules.cardinality_distractors, rules.CARDINALITY_BOUNDS, True),
    "B-CNT03-HOW-MANY": (rules.cardinality_distractors, rules.CARDINALITY_BOUNDS, True),
    "B-CNT04-MAKE-SET": (rules.make_set_distractors, rules.CARDINALITY_BOUNDS, False),
    "B-CNT06-SKIP-COUNT": (rules.skip_count_distractors, rules.SKIP_BOUNDS, True),
    "B-NS02-QUANTITY-NUMERAL": (rules.cardinality_distractors, rules.CARDINALITY_BOUNDS, True),
    "B-NS03-COMPARE-SETS": (rules.compare_sets_distractors, rules.NUMBER_SENSE_BOUNDS, False),
    "B-NS05-ORDER-NUMBERS": (rules.order_numbers_distractors, rules.ORDER_BOUNDS, False),
    "B-NS07-CONSERVATION": (rules.conservation_distractors, rules.BINARY_BOUNDS, False),
    "B-PV02-DECOMPOSE-2D": (rules.structured_no_distractors, rules.PLACE_VALUE_BOUNDS, False),
    "B-PV03-IDENTIFY-HTO": (rules.place_value_digit3_distractors, rules.PLACE_VALUE_BOUNDS, True),
    "B-PV04-DECOMPOSE-3D": (rules.structured_no_distractors, rules.PLACE_VALUE_BOUNDS, False),
    "B-ADD01-COMBINE-SETS": (rules.addition_distractors, rules.ADD_SINGLE_BOUNDS, True),
    "B-ADD02-COUNT-ON": (rules.count_on_distractors, rules.ADD_COUNTON_BOUNDS, True),
    "B-ADD03-SINGLE-DIGIT": (rules.addition_distractors, rules.ADD_SINGLE_BOUNDS, True),
    "B-ADD05-REGROUP": (rules.addition_distractors, rules.ADDITION_BOUNDS, True),
    "B-SUB01-TAKE-AWAY": (rules.subtraction_distractors, rules.SUB_SINGLE_BOUNDS, True),
    "B-SUB03-WITHIN-9": (rules.subtraction_distractors, rules.SUB_SINGLE_BOUNDS, True),
    "B-SUB05-BORROW": (rules.subtraction_distractors, rules.SUBTRACTION_BOUNDS, True),
    "B-MUL01-EQUAL-GROUPS": (rules.equal_groups_distractors, rules.MUL_SMALL_BOUNDS, True),
    "B-MUL02-ARRAY-TOTAL": (rules.array_distractors, rules.MUL_SMALL_BOUNDS, True),
    "B-DIV01-EQUAL-SHARING": (rules.sharing_distractors, rules.DIV_SMALL_BOUNDS, True),
    "B-DIV02-EQUAL-GROUPING": (rules.grouping_distractors, rules.DIV_SMALL_BOUNDS, True),
}

# Bounded search for off-by-k fillers (k up to this magnitude); ample for all catalogue ranges.
_MAX_FILLER_K = 400


def _int_fillers(correct_raw: object) -> List[rules.Candidate]:
    """Deterministic nearest-first off-by-k integer candidates: -1, +1, -2, +2, ..."""
    if not isinstance(correct_raw, int) or isinstance(correct_raw, bool):
        return []
    out: List[rules.Candidate] = []
    for k in range(1, _MAX_FILLER_K + 1):
        out.append((correct_raw - k, f"D-INT-FILLER-MINUS-{k}"))
        out.append((correct_raw + k, f"D-INT-FILLER-PLUS-{k}"))
    return out


def generate_distractors(
    item_template_id: str,
    operands: dict,
    correct_raw: object,
    required: Optional[int] = None,
) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    """Reproducible distractor candidates for a template + operands.

    Returns ``(candidate_strings, rule_ids)`` aligned by index: bounds-checked, correct-answer
    and accepted-equivalent excluded, de-duplicated (first proposal wins), deterministic order.

    ``required`` is the exact number of distinct distractors the response format needs. When
    given and the template-specific rules fall short, integer-answer templates are topped up with
    generic off-by-k fillers; if the requirement still cannot be met, ``DistractorGenerationError``
    is raised. ``required=None`` (or ``0``) disables enforcement and returns all valid candidates.
    """
    entry = _DISTRACTOR_RULES.get(item_template_id)
    if entry is None:
        raise KeyError(f"no distractor rule registered for template {item_template_id!r}")
    propose, in_bounds, supports_fillers = entry

    correct_norm = normalize_answer(correct_raw)
    # Exclude the correct answer and any accepted equivalent written form (e.g. expanded place
    # value), so a distractor can never be silently equivalent to the correct answer.
    seen = {correct_norm}
    for eq in allowed_equivalent_answers(item_template_id, operands):
        seen.add(normalize_answer(eq))

    values: List[str] = []
    rule_ids: List[str] = []

    def _consume(candidates: List[rules.Candidate], stop_at: Optional[int]) -> None:
        for raw_value, rule_id in candidates:
            if stop_at is not None and len(values) >= stop_at:
                return
            if not in_bounds(raw_value):
                continue
            norm = normalize_answer(raw_value)
            if norm in seen:  # excludes correct answer, equivalents, and earlier duplicates
                continue
            seen.add(norm)
            values.append(norm)
            rule_ids.append(rule_id)

    want = required if (required is not None and required > 0) else None
    _consume(list(propose(operands, correct_raw)), want)
    if want is not None and len(values) < want and supports_fillers:
        _consume(_int_fillers(correct_raw), want)

    if want is not None and len(values) < want:
        raise DistractorGenerationError(
            f"template {item_template_id!r} needs {want} distinct distractors but only "
            f"{len(values)} valid candidate(s) could be generated for operands {operands!r}"
        )

    return tuple(values), tuple(rule_ids)


def required_distractor_count(item_template_id: str) -> int:
    """The configured required distractor count for a template (from its sampler)."""
    from ..samplers.registry import get_sampler

    sampler = get_sampler(item_template_id)
    if sampler is None:
        raise KeyError(f"no sampler registered for template {item_template_id!r}")
    return sampler.required_distractors


def supported_distractor_template_ids() -> Tuple[str, ...]:
    return tuple(sorted(_DISTRACTOR_RULES))
