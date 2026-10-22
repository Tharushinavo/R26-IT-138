"""Child-facing wording for Component B's items, written for learners whose first language is
Sinhala (2026-09-27 owner instruction).

**CANDIDATE WORDING -- NOT OWNER-REVIEWED, NOT LINGUIST-REVIEWED.** Every string below was authored
in one batch to build the mechanism and to make the questions readable. Writing the wording and
approving it are different steps done by different people; nothing here should be read as approval
of its content. The same caveat Component C's ``prompt_wording.py`` carries applies in full.

WHAT PROBLEM THIS SOLVES. The generator's stems are written in fluent, school-register English:
"Which numeral matches the quantity?", "Write 51 in expanded form.", "An array has 7 rows and 4
columns. How many?". For a Grade 2 child reading English as a second language, the mathematics is
not the hard part of those sentences -- the English is. A child who can add 5 and 2 should not lose
the item because "numeral", "expanded form" or "array" is unfamiliar.

THE RULES THESE STRINGS FOLLOW, so a later addition matches rather than drifts:
  1. Short. One idea per sentence, and as few words as carry it.
  2. Everyday words. No "numeral", "quantity", "expanded form", "array", "column", "digit",
     "select", "exactly", "ascending"/"descending". Real maths vocabulary a Grade 2 class is
     actually taught -- "tens", "ones", "hundreds", "groups", "equally" -- is KEPT: replacing it
     would be teaching the wrong thing, not simplifying. A word is only removed when it is
     REGISTER; a word that carries the mathematics stays even when it is long.
  3. Same shape for the same idea, so the pattern is learned once. "How many do you see?" is the
     counting question everywhere it applies; "Pick the right sign." is the comparison question
     everywhere it applies.
  4. Ask a question the answer format actually answers. A child choosing between < > and = is not
     being asked "which group has more" -- they are being asked for a sign.

WHAT IS DELIBERATELY LEFT ALONE. The bare arithmetic stems -- "5 + 2 = ?", "85 - 77 = ?",
"5 x 2 = ?", "42 / 2 = ?" -- get nothing. Notation is already language-free, and it is the one form
that costs a Sinhala-first child nothing to read. Wrapping it in an English sentence would ADD the
barrier this module exists to remove. A template absent from the mapping keeps the generator's own
stem, which is the correct default rather than an oversight.

WHERE THIS SITS, and why not in the generator. The stems are built inside the vendored research
wheel (``component_b_generator/samplers/``), which is Yass's, hash-pinned in ``requirements.lock``
and carries a per-file SHA manifest; ``packaging/component_b_internal/IMPORT_POLICY.md`` draws the
boundary -- Upadya owns presentation, Yass owns the generator, and Upadya does not rewrite its
content. So this is Upadya's own authored text, applied at projection time.

THE RESEARCH RECORD IS UNCHANGED. Only the DTO the child is shown carries this wording. The
generator's original stem stays exactly as generated in ``b_task_instances.prompt``, so every
persisted row still says what the item actually was, and nothing here is retroactive.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping

from app.domain.live_engine.locales import DEFAULT_LOCALE, Locale


# --- helpers ---------------------------------------------------------------------------------

def _get(prompt: Mapping[str, Any], key: str) -> Any:
    return prompt.get(key)


def _all_present(prompt: Mapping[str, Any], *keys: str) -> bool:
    return all(prompt.get(key) is not None for key in keys)


# --- per-template builders -------------------------------------------------------------------
#
# Each returns the child-facing stem, or None to fall back to the generator's own. Returning None
# on a missing key is what makes this fail SAFE: a payload shaped differently than expected shows
# the original English rather than a sentence with a hole in it.

def _count_objects(prompt: Mapping[str, Any]) -> str | None:
    return "How many do you see?"


def _make_set(prompt: Mapping[str, Any]) -> str | None:
    if not _all_present(prompt, "target"):
        return None
    return f"Tap {_get(prompt, 'target')} things."


def _quantity_numeral(prompt: Mapping[str, Any]) -> str | None:
    return "How many are there? Tap the number."


def _compare(prompt: Mapping[str, Any]) -> str | None:
    return "Tap the correct sign."


def _order_numbers(prompt: Mapping[str, Any]) -> str | None:
    direction = _get(prompt, "direction")
    if direction == "ascending":
        return "Put these in order. Small to big."
    if direction == "descending":
        return "Put these in order. Big to small."
    return None


def _conservation(prompt: Mapping[str, Any]) -> str | None:
    return "Is the number the same or different?"


def _identify_place(prompt: Mapping[str, Any]) -> str | None:
    if not _all_present(prompt, "n", "place"):
        return None
    return f"What number is in the {_get(prompt, 'place')} box?"


def _decompose_2d(prompt: Mapping[str, Any]) -> str | None:
    if not _all_present(prompt, "n"):
        return None
    return "How many tens and how many ones?"


def _decompose_3d(prompt: Mapping[str, Any]) -> str | None:
    if not _all_present(prompt, "n"):
        return None
    return "How many hundreds, tens and ones?"


def _combine_sets(prompt: Mapping[str, Any]) -> str | None:
    if not _all_present(prompt, "set_a", "set_b"):
        return None
    return "How many are there in both groups?"


def _count_on(prompt: Mapping[str, Any]) -> str | None:
    if not _all_present(prompt, "start", "jumps"):
        return None
    return (
        f"Start at {_get(prompt, 'start')}. Count on {_get(prompt, 'jumps')} more. "
        "What number do you stop at?"
    )


def _take_away(prompt: Mapping[str, Any]) -> str | None:
    if not _all_present(prompt, "total", "removed"):
        return None
    return "Some are crossed out. How many are not crossed out?"


def _equal_groups(prompt: Mapping[str, Any]) -> str | None:
    if not _all_present(prompt, "groups", "size"):
        return None
    return f"{_get(prompt, 'groups')} groups. {_get(prompt, 'size')} in each group. How many in all?"


def _array_total(prompt: Mapping[str, Any]) -> str | None:
    if not _all_present(prompt, "rows", "cols"):
        return None
    return f"{_get(prompt, 'rows')} rows. {_get(prompt, 'cols')} in each row. How many in all?"


def _equal_sharing(prompt: Mapping[str, Any]) -> str | None:
    if not _all_present(prompt, "total", "recipients"):
        return None
    # "equally" is KEPT, and was wrongly dropped in the first pass of this module. Equal sharing is
    # the mathematical content of the item: without the word, "share 22 between 2" permits 21 and 1
    # and the question stops being the question. It belongs with "tens", "ones" and "groups" in
    # rule 2's kept vocabulary, not with the register words this module strips.
    return f"Share {_get(prompt, 'total')} equally between {_get(prompt, 'recipients')}. How many does each get?"


def _equal_grouping(prompt: Mapping[str, Any]) -> str | None:
    if not _all_present(prompt, "total", "group_size"):
        return None
    return f"Put {_get(prompt, 'total')} into groups of {_get(prompt, 'group_size')}. How many groups?"


STEM_BUILDER_BY_TEMPLATE: Mapping[str, Callable[[Mapping[str, Any]], "str | None"]] = {
    # Counting
    "B-CNT02-COUNT-OBJECTS": _count_objects,
    "B-CNT03-HOW-MANY": _count_objects,
    "B-CNT04-MAKE-SET": _make_set,
    # Number sense
    "B-NS02-QUANTITY-NUMERAL": _quantity_numeral,
    "B-NS03-COMPARE-SETS": _compare,
    "B-NS05-ORDER-NUMBERS": _order_numbers,
    "B-NS07-CONSERVATION": _conservation,
    # Place value
    "B-PV01-IDENTIFY-TENS-ONES": _identify_place,
    "B-PV02-DECOMPOSE-2D": _decompose_2d,
    "B-PV03-IDENTIFY-HTO": _identify_place,
    "B-PV04-DECOMPOSE-3D": _decompose_3d,
    # Addition
    "B-ADD01-COMBINE-SETS": _combine_sets,
    "B-ADD02-COUNT-ON": _count_on,
    # Subtraction
    "B-SUB01-TAKE-AWAY": _take_away,
    # Multiplication
    "B-MUL01-EQUAL-GROUPS": _equal_groups,
    "B-MUL02-ARRAY-TOTAL": _array_total,
    # Division
    "B-DIV01-EQUAL-SHARING": _equal_sharing,
    "B-DIV02-EQUAL-GROUPING": _equal_grouping,
    # Deliberately absent: B-ADD03/04/05, B-SUB03/04/05, B-MUL03, B-DIV03 (bare notation), and
    # B-CNT01/B-CNT06/B-NS04, whose stem IS the material to work on and which carry an
    # `instruction` sentence instead -- see prompt_instructions.py.
}


# --- Sinhala -----------------------------------------------------------------------------------
#
# ** NOT REVIEWED. NOT ENABLED BY DEFAULT. ** These are a first draft written to prove the
# localisation path end to end, by someone who is not a Sinhala-speaking primary teacher. They must
# be checked -- and corrected -- by one before any child sees them. The resolver defaults to
# English (``locales.DEFAULT_LOCALE``), so nothing here reaches a learner until a caller explicitly
# asks for ``si``.
#
# The table is deliberately PARTIAL, and that is safe: ``simplified_stem_for`` falls back per
# string, so a template absent here serves its English wording rather than a gap. Translations can
# therefore land one reviewed item at a time instead of all 29 at once.
#
# Numbers stay as digits. Sinhala uses the same digits, and a child reading a maths question needs
# the numeral, not a spelled-out word.

def _si_count_objects(prompt: Mapping[str, Any]) -> str | None:
    return "ඔබ කීයක් දකිනවාද?"


def _si_make_set(prompt: Mapping[str, Any]) -> str | None:
    if not _all_present(prompt, "target"):
        return None
    return f"දේවල් {_get(prompt, 'target')}ක් තට්ටු කරන්න."


def _si_quantity_numeral(prompt: Mapping[str, Any]) -> str | None:
    return "කීයද කියා පෙන්වන අංකය තෝරන්න."


def _si_compare(prompt: Mapping[str, Any]) -> str | None:
    return "නිවැරදි ලකුණ තෝරන්න."


def _si_order_numbers(prompt: Mapping[str, Any]) -> str | None:
    direction = _get(prompt, "direction")
    if direction == "ascending":
        return "මේවා පිළිවෙලට තබන්න. කුඩාම සිට විශාලම දක්වා."
    if direction == "descending":
        return "මේවා පිළිවෙලට තබන්න. විශාලම සිට කුඩාම දක්වා."
    return None


STEM_BUILDER_BY_TEMPLATE_SI: Mapping[str, Callable[[Mapping[str, Any]], "str | None"]] = {
    "B-CNT02-COUNT-OBJECTS": _si_count_objects,
    "B-CNT03-HOW-MANY": _si_count_objects,
    "B-CNT04-MAKE-SET": _si_make_set,
    "B-NS02-QUANTITY-NUMERAL": _si_quantity_numeral,
    "B-NS03-COMPARE-SETS": _si_compare,
    "B-NS05-ORDER-NUMBERS": _si_order_numbers,
}

#: Every locale's builder table. English is the only COMPLETE one, by design -- see above.
STEM_BUILDERS_BY_LOCALE: Mapping[Locale, Mapping[str, Callable[[Mapping[str, Any]], "str | None"]]] = {
    "en": STEM_BUILDER_BY_TEMPLATE,
    "si": STEM_BUILDER_BY_TEMPLATE_SI,
}


def simplified_stem_for(
    item_template_id: str,
    prompt: Mapping[str, Any],
    locale: Locale = DEFAULT_LOCALE,
) -> str | None:
    """The child-facing stem for a template, or ``None`` to keep the generator's own.

    Falls back PER STRING: a template with no wording in ``locale`` serves the English wording, and
    only a template with neither returns ``None``. A builder that returns ``None`` because the
    payload lacked a key falls back the same way, so an unexpected payload shape can never produce
    a half-rendered sentence in either language.
    """
    for candidate in (locale, DEFAULT_LOCALE):
        builder = STEM_BUILDERS_BY_LOCALE.get(candidate, {}).get(item_template_id)
        if builder is None:
            continue
        stem = builder(prompt)
        if stem is not None:
            return stem
    return None
