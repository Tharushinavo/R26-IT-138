"""Which language a learner reads the questions in (2026-09-28).

WHY THIS EXISTS. The learners this app is built for speak Sinhala first. Until now every string in
the product was hard-coded English -- there was no localisation of any kind, front or back -- so
the simplified English in ``prompt_wording`` is a MITIGATION, not a solution: even "How many do you
see?" is five English words a Grade 2 child in a Sinhala-medium school has to decode before any
mathematics begins. For a study that means to measure mathematical ability, that is a validity
problem as much as a usability one: a wrong answer cannot be read as "could not do the maths" when
it may mean "could not read the question".

This module is the seam that makes a Sinhala question possible. It is deliberately NOT a
translation framework: it is one resolved locale, one fallback rule, and a place for translated
text to live once a human has written and checked it.

THE FALLBACK RULE IS PER STRING, NOT PER LOCALE. A learner set to Sinhala who meets an item with no
Sinhala wording gets the ENGLISH wording for that item, not a missing string, not a placeholder,
and not a crash. That is what makes it safe to add translations one at a time instead of needing
all 29 before any can ship.

ENGLISH REMAINS THE DEFAULT until a human has reviewed the Sinhala. ``DEFAULT_LOCALE`` is ``en``
and the resolver only returns ``si`` when a caller explicitly asks for it, so nothing unreviewed
can reach a child by accident.
"""

from __future__ import annotations

from typing import Literal, Mapping, TypeVar


Locale = Literal["en", "si"]

SUPPORTED_LOCALES: tuple[Locale, ...] = ("en", "si")

#: English, until the Sinhala wording has been written and checked by someone who teaches these
#: children. See this module's docstring: the default is a safety property, not a preference.
DEFAULT_LOCALE: Locale = "en"

_T = TypeVar("_T")


def resolve_locale(requested: str | None) -> Locale:
    """The locale to serve, from whatever a caller asked for.

    Accepts a bare tag (``si``) or a regional one (``si-LK``), case-insensitively, and ignores any
    ``Accept-Language`` quality suffix. Anything unrecognised -- including ``None`` -- resolves to
    ``DEFAULT_LOCALE`` rather than raising: a learner must always get a readable question, and an
    unfamiliar language tag is not a reason to fail a request.
    """
    if not requested:
        return DEFAULT_LOCALE
    # "si-LK,si;q=0.9,en;q=0.8" -> the first tag that is one of ours, in the order offered.
    for part in requested.split(","):
        tag = part.split(";")[0].strip().lower()
        if not tag:
            continue
        primary = tag.split("-")[0]
        if primary in SUPPORTED_LOCALES:
            return primary  # type: ignore[return-value]
    return DEFAULT_LOCALE


def pick_localized(by_locale: Mapping[Locale, _T], locale: Locale) -> _T | None:
    """The entry for ``locale``, falling back to English, then to nothing.

    Returning ``None`` rather than raising is what lets a partially translated table ship: the
    caller treats a missing entry exactly as it already treats a template it has no wording for.
    """
    if locale in by_locale:
        return by_locale[locale]
    return by_locale.get(DEFAULT_LOCALE)
