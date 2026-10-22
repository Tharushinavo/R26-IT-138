"""BE-C2 Part A: numeric ordering of ``presented_choices``, and the two-derivation parity test.

The defect: choices were ``sorted({correct, *distractors})`` on *strings*, so a child could be shown
``60, 61, 62, 7``. Measured against the real generator, 14% of Grade 2 and 24% of Grade 3 numeric
items were displayed out of numeric order. For a dyscalculia cohort that works directly against the
skill being assessed, so it is a correctness problem rather than a cosmetic one.

The parity test at the bottom is the other half of this batch. Two places derived this list, and the
only thing keeping them in step was a docstring in ``opportunity_persistence._safe_presented_choices``
claiming it "mirrors ``project_to_public``'s presented-choices derivation exactly". Nothing enforced
that. They now share one function, and this file asserts the shared behaviour from both entry points.
"""

import pytest

from app.application.opportunity_persistence import _safe_presented_choices
from app.domain.live_engine.presentation import derive_presented_choices


# --- numeric ordering ---------------------------------------------------------------------------


def test_numeric_choices_are_ordered_by_magnitude_not_lexicographically() -> None:
    # The exact regression: lexicographic sorting put "7" last, after "62".
    assert derive_presented_choices("7", ["60", "61", "62"]) == ("7", "60", "61", "62")


def test_numeric_ordering_across_digit_lengths() -> None:
    assert derive_presented_choices("9", ["10", "3", "100"]) == ("3", "9", "10", "100")
    assert derive_presented_choices("123", ["45", "6", "1000"]) == ("6", "45", "123", "1000")


def test_already_ordered_numeric_choices_are_unchanged() -> None:
    assert derive_presented_choices("47", ["48", "49", "50"]) == ("47", "48", "49", "50")


def test_negative_integers_order_numerically() -> None:
    # int() accepts a leading "-" where str.isdigit() does not; the predicate and the sort key are
    # the same call, so these sort by magnitude rather than by string.
    assert derive_presented_choices("-3", ["-10", "2"]) == ("-10", "-3", "2")


# --- the lexicographic fallback, which must stay ---------------------------------------------------


def test_relation_symbols_keep_lexicographic_ordering() -> None:
    # No numeric magnitude exists for these; they must keep the ordering they have always had.
    assert derive_presented_choices("<", [">", "="]) == ("<", "=", ">")


def test_conservation_words_keep_lexicographic_ordering() -> None:
    assert derive_presented_choices("same", ["changed"]) == ("changed", "same")


def test_comma_joined_orderings_keep_lexicographic_ordering() -> None:
    # ordered_list choices are comma-joined server-side and are not integers.
    assert derive_presented_choices("12,45,300", ["300,45,12", "45,12,300"]) == (
        "12,45,300",
        "300,45,12",
        "45,12,300",
    )


def test_a_single_non_integer_choice_forces_the_lexicographic_fallback() -> None:
    # Mixed input: one unparseable member means the whole list falls back, rather than some
    # half-numeric ordering nobody specified.
    assert derive_presented_choices("10", ["9", "none of these"]) == ("10", "9", "none of these")


def test_unicode_digit_forms_do_not_slip_through_as_numeric() -> None:
    # "²".isdigit() is True but int("²") raises — which is exactly why the predicate is int(), not
    # isdigit(). This must take the lexicographic path and must not raise.
    choices = derive_presented_choices("2", ["²"])
    assert set(choices) == {"2", "²"}


# --- deduplication is unchanged --------------------------------------------------------------------


def test_deduplication_still_happens_before_ordering() -> None:
    assert derive_presented_choices("7", ["7", "8", "8", "9"]) == ("7", "8", "9")


def test_no_distractors_yields_no_choices() -> None:
    # Free-entry and count-selection formats: unchanged, still an empty list.
    assert derive_presented_choices("123", []) == ()


def test_distinct_strings_denoting_the_same_number_are_both_kept_deterministically() -> None:
    # Set semantics cannot collapse "07" and "7" (different strings), so the string is the
    # tie-break and the result must be stable rather than arbitrary.
    assert derive_presented_choices("7", ["07"]) == ("07", "7")
    assert derive_presented_choices("7", ["07"]) == derive_presented_choices("07", ["7"])


# --- the parity test that was missing ----------------------------------------------------------------


@pytest.mark.parametrize(
    "correct,distractors",
    [
        ("7", ["60", "61", "62"]),
        ("9", ["10", "3", "100"]),
        ("47", ["48", "49", "50"]),
        ("-3", ["-10", "2"]),
        ("<", [">", "="]),
        ("same", ["changed"]),
        ("12,45,300", ["300,45,12", "45,12,300"]),
        ("10", ["9", "none of these"]),
        ("7", ["7", "8", "8", "9"]),
        ("123", []),
        ("0", ["1", "2", "3"]),
    ],
)
def test_both_derivations_agree_exactly(correct: str, distractors: list[str]) -> None:
    """``project_to_public``'s derivation and ``_safe_presented_choices`` must be identical.

    They are now the same function, so this is cheap to keep green — and it is the assertion whose
    absence let a docstring stand in for enforcement. It covers integer, symbol and mixed cases.
    """
    assert _safe_presented_choices(correct, distractors) == list(
        derive_presented_choices(correct, distractors)
    )
