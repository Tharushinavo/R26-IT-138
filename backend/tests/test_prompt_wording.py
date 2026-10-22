"""The child-facing wording, checked against what the generator actually produces.

Written for learners whose first language is Sinhala (2026-09-27 owner instruction). These tests
drive the REAL samplers rather than hand-written payloads, so a wording string that reads a key the
generator does not emit fails here instead of reaching a child as a sentence with a hole in it.
"""

import random
import re

from component_b_generator.samplers.registry import SAMPLERS

from app.domain.live_engine.prompt_instructions import INSTRUCTION_BY_TEMPLATE
from app.domain.live_engine.prompt_wording import STEM_BUILDER_BY_TEMPLATE, simplified_stem_for


# Words the generator uses that a Grade 2 reader of English-as-a-second-language should not have to
# get past to answer a maths question. Real maths vocabulary a Grade 2 class is taught -- "tens",
# "ones", "hundreds", "groups" -- is deliberately NOT here: replacing that would teach the wrong
# thing rather than simplify.
BANNED_WORDS = (
    "numeral",
    "quantity",
    "expanded form",
    "array",
    "column",
    "digit",
    "select",
    "exactly",
    "ascending",
    "descending",
)

# Templates left with the generator's own stem on purpose: bare notation, which is language-free
# and the one form that costs a Sinhala-first child nothing to read.
NOTATION_ONLY = {
    "B-ADD03-SINGLE-DIGIT",
    "B-ADD04-2D-NO-REGROUP",
    "B-ADD05-REGROUP",
    "B-SUB03-WITHIN-9",
    "B-SUB04-2D-NO-BORROW",
    "B-SUB05-BORROW",
    "B-MUL03-FACTS-2-5-10",
    "B-DIV03-DIVIDE-BY-2",
}

# Templates whose stem IS the material to work on, so they keep it and gain an instruction instead.
MATERIAL_STEM = {"B-CNT01-SEQ-CONTINUE", "B-CNT06-SKIP-COUNT", "B-NS04-COMPARE-NUMERALS"}


def sample_prompt(template_id: str, seed: int) -> dict:
    sampler = SAMPLERS[template_id]
    return dict(sampler.sample(random.Random(seed), sampler.eligible_grades[0]).prompt)


def child_facing_text(template_id: str, prompt: dict) -> str:
    """Everything the child reads for this item: the stem they get, plus any instruction."""
    stem = simplified_stem_for(template_id, prompt) or prompt["stem"]
    instruction = INSTRUCTION_BY_TEMPLATE.get(template_id, "")
    return f"{instruction} {stem}".strip()


def test_every_template_is_accounted_for() -> None:
    """No template may be silently forgotten: each is simplified, given an instruction, or
    explicitly listed as notation that is better left alone."""
    handled = set(STEM_BUILDER_BY_TEMPLATE) | MATERIAL_STEM | NOTATION_ONLY
    assert set(SAMPLERS) == handled, {
        "missing": sorted(set(SAMPLERS) - handled),
        "stale": sorted(handled - set(SAMPLERS)),
    }


def test_no_child_facing_text_uses_a_banned_word() -> None:
    """The point of the whole module, checked over real generator output."""
    for template_id in sorted(SAMPLERS):
        for seed in range(12):
            text = child_facing_text(template_id, sample_prompt(template_id, seed)).lower()
            for word in BANNED_WORDS:
                assert word not in text, f"{template_id}: {word!r} in {text!r}"


def test_every_simplified_stem_renders_fully_from_real_payloads() -> None:
    """A builder reading a key the generator does not emit would return None (fail-safe) and the
    original English would silently come back. That must never be the case for a real payload."""
    for template_id in sorted(STEM_BUILDER_BY_TEMPLATE):
        for seed in range(12):
            prompt = sample_prompt(template_id, seed)
            stem = simplified_stem_for(template_id, prompt)
            assert stem is not None, f"{template_id} fell back to the generator stem"
            assert stem.strip() == stem and stem
            # No unsubstituted placeholder and no stray "None" from a missing key.
            assert "{" not in stem and "}" not in stem, f"{template_id}: {stem!r}"
            assert not re.search(r"\bNone\b", stem), f"{template_id}: {stem!r}"


def test_a_missing_key_falls_back_instead_of_rendering_a_hole() -> None:
    """Fail-safe: an unexpected payload shape shows the generator's English, not a broken sentence."""
    for template_id, prompt in (
        ("B-PV01-IDENTIFY-TENS-ONES", {"stem": "x", "n": 51}),          # no 'place'
        ("B-ADD01-COMBINE-SETS", {"stem": "x", "set_a": 5}),            # no 'set_b'
        ("B-DIV01-EQUAL-SHARING", {"stem": "x"}),                       # neither key
        ("B-NS05-ORDER-NUMBERS", {"stem": "x", "direction": "sideways"}),  # unknown direction
    ):
        assert simplified_stem_for(template_id, prompt) is None, template_id


def test_notation_items_are_left_exactly_as_generated() -> None:
    """Wrapping "5 + 2 = ?" in an English sentence would ADD the barrier this removes."""
    for template_id in sorted(NOTATION_ONLY):
        prompt = sample_prompt(template_id, 3)
        assert simplified_stem_for(template_id, prompt) is None
        assert template_id not in INSTRUCTION_BY_TEMPLATE
        # Still recognisably an equation, i.e. we did not quietly stop covering these.
        assert "=" in prompt["stem"]


def test_child_facing_sentences_stay_short() -> None:
    """One idea per sentence, few words. The cap is generous on purpose -- it catches a future
    addition written in school-register prose, not this batch's own phrasing."""
    for template_id in sorted(SAMPLERS):
        prompt = sample_prompt(template_id, 5)
        text = child_facing_text(template_id, prompt)
        for sentence in (part for part in re.split(r"[.?]", text) if part.strip()):
            words = sentence.split()
            assert len(words) <= 8, f"{template_id}: {len(words)} words in {sentence.strip()!r}"


def test_the_same_question_is_asked_the_same_way_everywhere() -> None:
    """Rule 3: one shape per idea, so the pattern is learned once rather than re-read each time."""
    counting = {
        simplified_stem_for(t, sample_prompt(t, 1)) for t in ("B-CNT02-COUNT-OBJECTS", "B-CNT03-HOW-MANY")
    }
    assert counting == {"How many do you see?"}

    comparison = {
        simplified_stem_for("B-NS03-COMPARE-SETS", sample_prompt("B-NS03-COMPARE-SETS", 1)),
        INSTRUCTION_BY_TEMPLATE["B-NS04-COMPARE-NUMERALS"],
    }
    # "Tap the correct sign." since 2026-10-20. "right" was read as the DIRECTION -- these screens
    # have left/right layouts -- and the Sinhala table already said නිවැරදි ("correct"), so the
    # English was the locale out of step. The ASSERTION is unchanged: both comparison templates
    # must still ask the SAME question, whichever words it uses.
    assert comparison == {"Tap the correct sign."}

    next_number = {INSTRUCTION_BY_TEMPLATE[t] for t in ("B-CNT01-SEQ-CONTINUE", "B-CNT06-SKIP-COUNT")}
    assert next_number == {"What number comes next?"}


def test_real_maths_vocabulary_is_kept_rather_than_simplified_away() -> None:
    """Place value and grouping language is what the child is being taught; dropping it would be
    teaching the wrong thing, not making the English easier."""
    assert "tens" in simplified_stem_for("B-PV02-DECOMPOSE-2D", sample_prompt("B-PV02-DECOMPOSE-2D", 1))
    hto = simplified_stem_for("B-PV04-DECOMPOSE-3D", sample_prompt("B-PV04-DECOMPOSE-3D", 1))
    assert "hundreds" in hto and "tens" in hto and "ones" in hto
    assert "groups" in simplified_stem_for("B-DIV02-EQUAL-GROUPING", sample_prompt("B-DIV02-EQUAL-GROUPING", 1))
