"""Reviewed structured place-value expression parser (Phase B2A.2).

Parses a *narrowly approved* set of place-value written forms into an integer so that
equivalent decompositions of the same numeral can be recognized:

    "123"                       -> 123
    "100 + 20 + 3"              -> 123
    "1 hundred + 2 tens + 3 ones"  -> 123   (singular/plural unit words accepted)

This is a hand-written, deterministic parser. It intentionally supports **only** the two
approved grammars below and rejects everything else. There is **no** ``eval``/``exec``, no
variables, no parentheses, no general arithmetic, no unrestricted natural language, and no
execution of catalogue text. Malformed input raises :class:`StructuredParseError`.

Grammar A (bare numeral):    DIGITS                       (no leading zero unless it is "0")
Grammar B (additive):        TERM ( "+" TERM )*           where each TERM is either
                               - a plain non-negative integer (a place value like "100"), or
                               - "<digit> <unit>" with unit in {hundred(s), ten(s), one(s)}.
Grammar B forbids repeating the same place-value unit twice.
"""

from __future__ import annotations

import re

# Unit word -> its place multiplier. Singular and plural are both accepted.
_UNIT_MULTIPLIER = {
    "hundred": 100, "hundreds": 100,
    "ten": 10, "tens": 10,
    "one": 1, "ones": 1,
}
_UNIT_CANONICAL = {"hundred": "hundreds", "hundreds": "hundreds",
                   "ten": "tens", "tens": "tens", "one": "ones", "ones": "ones"}

_INT_RE = re.compile(r"^[0-9]+$")
_UNIT_TERM_RE = re.compile(r"^([0-9]+)\s+([a-z]+)$")


class StructuredParseError(ValueError):
    """Raised when a string is not one of the approved place-value forms."""


def _parse_integer_token(token: str) -> int:
    """A plain non-negative integer token; leading zeros rejected (except the single '0')."""
    if not _INT_RE.match(token):
        raise StructuredParseError(f"not an integer token: {token!r}")
    if len(token) > 1 and token[0] == "0":
        raise StructuredParseError(f"leading zero not allowed: {token!r}")
    return int(token)


def parse_place_value_expression(text: str) -> int:
    """Parse an approved place-value form into its integer value (deterministic, no eval)."""
    if not isinstance(text, str):
        raise StructuredParseError("input must be a string")
    raw = text.strip().lower()
    if not raw:
        raise StructuredParseError("empty expression")

    # Grammar A: a bare numeral.
    if "+" not in raw and " " not in raw:
        return _parse_integer_token(raw)

    # Grammar B: additive terms separated by '+'.
    terms = raw.split("+")
    if any(t.strip() == "" for t in terms):
        raise StructuredParseError(f"empty term in expression: {text!r}")

    total = 0
    seen_units: set[str] = set()
    for term in terms:
        tok = term.strip()
        unit_match = _UNIT_TERM_RE.match(tok)
        if unit_match:
            count_str, unit = unit_match.group(1), unit_match.group(2)
            if unit not in _UNIT_MULTIPLIER:
                raise StructuredParseError(f"unknown place-value unit: {unit!r}")
            canonical = _UNIT_CANONICAL[unit]
            if canonical in seen_units:
                raise StructuredParseError(f"place-value unit repeated: {canonical}")
            seen_units.add(canonical)
            count = _parse_integer_token(count_str)
            total += count * _UNIT_MULTIPLIER[unit]
        elif _INT_RE.match(tok):
            total += _parse_integer_token(tok)
        else:
            raise StructuredParseError(f"malformed term: {term!r}")
    return total


def structured_equivalent_forms(n: int) -> tuple[str, ...]:
    """Deterministic accepted written forms of ``n`` besides the bare numeral.

    Only place values with a non-zero digit contribute a term (so 205 -> "200 + 5", never
    "200 + 0 + 5"). Returns both the numeric-expanded form and the unit-word form.
    """
    if not isinstance(n, int) or isinstance(n, bool) or n < 0:
        raise StructuredParseError("n must be a non-negative integer")
    hundreds, tens, ones = (n // 100) % 10, (n // 10) % 10, n % 10
    numeric_terms: list[str] = []
    word_terms: list[str] = []
    for digit, place_value, singular, plural in (
        (hundreds, 100, "hundred", "hundreds"),
        (tens, 10, "ten", "tens"),
        (ones, 1, "one", "ones"),
    ):
        if digit != 0:
            numeric_terms.append(str(digit * place_value))
            word_terms.append(f"{digit} {singular if digit == 1 else plural}")
    if not numeric_terms:  # n == 0
        return ()
    return (" + ".join(numeric_terms), " + ".join(word_terms))


def structured_forms_equivalent(a: str, b: str) -> bool:
    """True iff two approved place-value forms denote the same integer (deterministic)."""
    return parse_place_value_expression(a) == parse_place_value_expression(b)
