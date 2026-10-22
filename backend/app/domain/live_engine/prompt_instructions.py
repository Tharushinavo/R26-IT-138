"""Child-facing instruction sentences for the Component B item templates whose ``stem`` is not
already a self-contained question (2026-09-27).

**CANDIDATE WORDING -- NOT OWNER-REVIEWED.** The three strings below were authored this batch to
close a real gap found in the running app: ``B-CNT01-SEQ-CONTINUE`` reaches a child as the bare
text ``"2, 3, 4, 5, __"``, with nothing anywhere on the screen saying what to do with it. Writing
the wording and approving the wording are two different steps; nothing here should be read as
approval of the content, only of the mechanism.

WHY THIS IS AUTHORED HERE AND NOT FIXED IN THE GENERATOR. The stem is built inside the vendored
research wheel (``component_b_generator/samplers/counting.py``'s
``stem = ", ".join(...) + ", __"``), which is Yass's, hash-pinned in ``requirements.lock``, and
carries a per-file SHA manifest. ``packaging/component_b_internal/IMPORT_POLICY.md`` draws the
boundary: Upadya owns real learners and presentation, Yass owns the generator, and Upadya may not
rewrite its content. So the instruction is Upadya's own authored text, resolved in Upadya's own
layer, exactly as Component C already does it -- see ``app/domain/live_engine_c/prompt_wording.py``,
whose ``PROMPT_TEXT_BY_TEMPLATE`` is likewise "authored content, not the installed wheel".

WHY SERVER-SIDE AND NOT IN THE APP. Component B's stem architecture is backend-owned and
server-supplied; the frontend relays it verbatim and never composes or rewrites item text (that
same C module states the rule). A client that assembled its own instruction would be inventing
item content, and would have to do it from payload keys whose semantics are per-template. Keying
off ``item_template_id`` -- which stays PRIVATE, never reaching the wire -- is the honest version.

WHY ONLY THREE ENTRIES. Every other template's stem already states its own task ("In 16, what is
the ones digit?", "Put the two groups together: 6 and 1.", "Order these ascending."), and the
arithmetic templates read as questions in their own right ("6 + 1 = ?"). Adding a sentence to
those would be noise on a screen built for a seven-year-old. A template absent from this mapping
gets no instruction, which is the correct default, not an oversight.
"""

from __future__ import annotations

from typing import Mapping

from app.domain.live_engine.locales import DEFAULT_LOCALE, Locale


INSTRUCTION_BY_TEMPLATE: Mapping[str, str] = {
    # "2, 3, 4, 5, __" -- a sequence with a terminal blank and no instruction of any kind.
    # "What number comes next?" rather than "Guess the next number": the child is working it out,
    # not guessing, and "comes next" is the commoner phrase for a Sinhala-first reader.
    "B-CNT01-SEQ-CONTINUE": "What number comes next?",
    # "0, 5, 10, __" -- the same shape, skip-counting; same gap, same fix.
    "B-CNT06-SKIP-COUNT": "What number comes next?",
    # "7 __ 9", answered by choosing <, > or =. The blank is an operator, not a number, so
    # anything about "the next number" would be actively wrong here. Worded identically to
    # B-NS03-COMPARE-SETS in prompt_wording.py, since it is the same question.
    "B-NS04-COMPARE-NUMERALS": "Tap the correct sign.",
}

# ** NOT REVIEWED. NOT ENABLED BY DEFAULT. ** First-draft Sinhala, same standing as the table in
# prompt_wording.py: written to prove the path, to be corrected by a Sinhala-speaking primary
# teacher before any child sees it. English is what serves until then.
INSTRUCTION_BY_TEMPLATE_SI: Mapping[str, str] = {
    "B-CNT01-SEQ-CONTINUE": "ඊළඟට එන අංකය කුමක්ද?",
    "B-CNT06-SKIP-COUNT": "ඊළඟට එන අංකය කුමක්ද?",
    # Worded identically to B-NS03-COMPARE-SETS in prompt_wording.py, as in English.
    "B-NS04-COMPARE-NUMERALS": "නිවැරදි ලකුණ තෝරන්න.",
}

INSTRUCTIONS_BY_LOCALE: Mapping[Locale, Mapping[str, str]] = {
    "en": INSTRUCTION_BY_TEMPLATE,
    "si": INSTRUCTION_BY_TEMPLATE_SI,
}

# The key the instruction is published under inside the open ``prompt`` payload. The frontend
# reads exactly this and renders it above the stem.
INSTRUCTION_PROMPT_KEY = "instruction"


def instruction_for(item_template_id: str, locale: Locale = DEFAULT_LOCALE) -> str | None:
    """The authored instruction for a template, or ``None`` when its stem already stands alone.

    Falls back per string to English, exactly as ``simplified_stem_for`` does, so a partially
    translated table is safe to ship.
    """
    for candidate in (locale, DEFAULT_LOCALE):
        instruction = INSTRUCTIONS_BY_LOCALE.get(candidate, {}).get(item_template_id)
        if instruction is not None:
            return instruction
    return None
