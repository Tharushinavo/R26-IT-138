"""Locale resolution and the per-string fallback that makes a partial translation safe to ship.

The learners this app targets speak Sinhala first, and until 2026-09-28 the product had no
localisation of any kind. These pin the two properties that let Sinhala wording land one reviewed
item at a time: English stays the default, and a missing translation serves English rather than a
gap.
"""

import random

import pytest
from component_b_generator.samplers.registry import SAMPLERS

from app.domain.live_engine.locales import DEFAULT_LOCALE, SUPPORTED_LOCALES, resolve_locale
from app.domain.live_engine.prompt_instructions import (
    INSTRUCTION_BY_TEMPLATE,
    INSTRUCTION_BY_TEMPLATE_SI,
    instruction_for,
)
from app.domain.live_engine.prompt_wording import (
    STEM_BUILDER_BY_TEMPLATE,
    STEM_BUILDER_BY_TEMPLATE_SI,
    simplified_stem_for,
)


def sample_prompt(template_id: str, seed: int = 7) -> dict:
    sampler = SAMPLERS[template_id]
    return dict(sampler.sample(random.Random(seed), sampler.eligible_grades[0]).prompt)


# --- resolution ----------------------------------------------------------------------------

def test_english_is_the_default_so_unreviewed_sinhala_cannot_reach_a_child_by_accident() -> None:
    assert DEFAULT_LOCALE == "en"
    assert resolve_locale(None) == "en"
    assert resolve_locale("") == "en"


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("si", "si"),
        ("si-LK", "si"),
        ("SI-lk", "si"),
        ("  si  ", "si"),
        # A real Accept-Language, quality values and all: the first supported tag offered wins.
        ("si-LK,si;q=0.9,en-US;q=0.8", "si"),
        ("en-GB,en;q=0.9", "en"),
        # Unsupported languages fall back rather than failing the request -- a learner must always
        # get a readable question.
        ("ta-LK", "en"),
        ("fr", "en"),
        ("not a language tag", "en"),
        ("*", "en"),
    ],
)
def test_resolve_locale_reads_real_accept_language_values(header: str, expected: str) -> None:
    assert resolve_locale(header) == expected


def test_a_preferred_unsupported_language_falls_through_to_one_we_have() -> None:
    """Tamil first, Sinhala second: the learner gets Sinhala, not English."""
    assert resolve_locale("ta-LK,si;q=0.8") == "si"


# --- per-string fallback -------------------------------------------------------------------

def test_a_template_without_sinhala_serves_english_not_a_gap() -> None:
    """This is what lets translations land one at a time. B-PV02 has English wording and no
    Sinhala; asking in Sinhala must still produce the English sentence."""
    assert "B-PV02-DECOMPOSE-2D" in STEM_BUILDER_BY_TEMPLATE
    assert "B-PV02-DECOMPOSE-2D" not in STEM_BUILDER_BY_TEMPLATE_SI
    prompt = sample_prompt("B-PV02-DECOMPOSE-2D")
    assert simplified_stem_for("B-PV02-DECOMPOSE-2D", prompt, "si") == simplified_stem_for(
        "B-PV02-DECOMPOSE-2D", prompt, "en"
    )


def test_a_translated_template_serves_sinhala() -> None:
    prompt = sample_prompt("B-CNT02-COUNT-OBJECTS")
    english = simplified_stem_for("B-CNT02-COUNT-OBJECTS", prompt, "en")
    sinhala = simplified_stem_for("B-CNT02-COUNT-OBJECTS", prompt, "si")
    assert sinhala != english
    assert sinhala == "ඔබ කීයක් දකිනවාද?"


def test_instructions_fall_back_the_same_way() -> None:
    assert instruction_for("B-CNT01-SEQ-CONTINUE", "si") == INSTRUCTION_BY_TEMPLATE_SI["B-CNT01-SEQ-CONTINUE"]
    # A template with no instruction in either language stays None rather than inventing one.
    assert instruction_for("B-ADD03-SINGLE-DIGIT", "si") is None
    assert instruction_for("B-ADD03-SINGLE-DIGIT", "en") is None


def test_no_locale_ever_yields_a_half_rendered_sentence() -> None:
    """A builder that cannot fill its placeholders returns None and falls back, rather than
    emitting a sentence with a hole or a stray "None" in it -- in either language."""
    for locale in SUPPORTED_LOCALES:
        for template_id in sorted(SAMPLERS):
            for seed in range(6):
                stem = simplified_stem_for(template_id, sample_prompt(template_id, seed), locale)
                if stem is None:
                    continue
                assert "{" not in stem and "}" not in stem, (locale, template_id, stem)
                assert "None" not in stem, (locale, template_id, stem)
                assert stem.strip() == stem and stem


def test_every_sinhala_entry_is_for_a_template_that_actually_exists() -> None:
    """A stale key would silently never be served. Catch it here rather than in a classroom."""
    for table in (STEM_BUILDER_BY_TEMPLATE_SI, INSTRUCTION_BY_TEMPLATE_SI):
        assert set(table) <= set(SAMPLERS), sorted(set(table) - set(SAMPLERS))


def test_sinhala_tables_are_a_subset_of_what_english_covers() -> None:
    """Sinhala translates wording English already has. A Sinhala-only entry would mean an item
    whose English readers get the raw generator stem while Sinhala readers get authored text."""
    assert set(STEM_BUILDER_BY_TEMPLATE_SI) <= set(STEM_BUILDER_BY_TEMPLATE)
    assert set(INSTRUCTION_BY_TEMPLATE_SI) <= set(INSTRUCTION_BY_TEMPLATE)


def test_sinhala_strings_are_actually_sinhala_and_keep_digits_as_digits() -> None:
    """Sinhala script is U+0D80..U+0DFF. Numbers stay as numerals: a child reading a maths
    question needs the digit, not a spelled-out word."""
    for template_id, builder in STEM_BUILDER_BY_TEMPLATE_SI.items():
        stem = builder(sample_prompt(template_id))
        if stem is None:
            continue
        assert any("඀" <= ch <= "෿" for ch in stem), (template_id, stem)
    for template_id, text in INSTRUCTION_BY_TEMPLATE_SI.items():
        assert any("඀" <= ch <= "෿" for ch in text), (template_id, text)

    with_number = STEM_BUILDER_BY_TEMPLATE_SI["B-CNT04-MAKE-SET"](sample_prompt("B-CNT04-MAKE-SET"))
    assert any(ch.isdigit() for ch in with_number), with_number
