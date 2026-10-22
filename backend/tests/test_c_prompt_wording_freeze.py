"""C Prompt Wording drift test (Component C batch BE-prompt-text, third member of the artefact
family after the template registry and the prompt exemplars).

**CANDIDATE WORDING, NOT OWNER-REVIEWED.** This module tests that the wording MACHINERY works --
coverage, variant resolution, determinism, banned-term/length/no-digit bounds, and that every
guard actually fires. It proves nothing about whether the wording's CONTENT is good child-facing
text; that is the owner's review, not this suite's job. See
``app/domain/live_engine_c/prompt_wording.py``'s own docstring for the full disclosure, including
the instruction-versus-answer rule that decides which templates carry variants.

Mirrors ``test_c_template_registry_freeze.py`` / ``test_c_prompt_exemplars_freeze.py``'s
discipline: imports ``build_wording`` from the script rather than re-implementing the extraction,
so script and test cannot drift apart.

WHY THE BANNED-TERM AND LENGTH CHECKS SCAN ``PROMPT_TEXT_BY_TEMPLATE`` VALUES -- RUNTIME STRING
VALUES -- AND NEVER THE MODULE'S SOURCE TEXT. The caution carried from the frontend side: a guard
first written as a bare substring match over raw SOURCE text failed on its own explanatory
comments, because "the module's source" includes its docstring, which necessarily discusses the
very terms the guard bans. Scanning the frozen artefact's ``prompt_text`` values (the actual
content, already derived) rather than ``Path(...).read_text()`` (the file's raw bytes, docstring
included) makes that failure mode structurally impossible here: the docstring is never examined
by these checks at all, not filtered out of an examination that would otherwise catch it.
``test_banned_term_scan_would_have_caught_the_source_scan_mistake`` demonstrates this concretely:
it shows the source-scan approach WOULD flag this very file's own docstring, and the value-scan
approach does not.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from app.domain.live_engine_c.errors import PromptWordingUnavailableError
from app.domain.live_engine_c.prompt_wording import PROMPT_TEXT_BY_TEMPLATE, prompt_text_for
from scripts.generate_c_prompt_wording import _serialize_wording, build_wording

CONTRACT_DIR = Path(__file__).parent.parent / "contract"
FROZEN_PATH = CONTRACT_DIR / "c-prompt-wording.json"
META_PATH = CONTRACT_DIR / "c-prompt-wording.meta.json"
REGISTRY_PATH = CONTRACT_DIR / "c-template-registry.json"
EXEMPLARS_PATH = CONTRACT_DIR / "c-prompt-exemplars.json"
SOURCE_MODULE_PATH = (
    Path(__file__).parent.parent / "app" / "domain" / "live_engine_c" / "prompt_wording.py"
)

ALLOWED_ENTRY_KEYS = frozenset(
    {"game_task_template_id", "variant_key", "variant_value", "prompt_text"}
)

VARIANT_TEMPLATE_IDS = frozenset({"C-EG-02", "C-NP-04"})

# BUILDER JUDGMENT -- UNRATIFIED. Not a governance threshold or a member of the seven gated
# parameter families (c_task.py's docstring makes this distinction explicitly) -- a content
# vocabulary for keeping internal/technical jargon out of child-facing text, in the same spirit
# as (but a different list from, and a different PURPOSE than) B's PROHIBITED_COLUMN_TERMS, which
# guards database-column/API-field names, not prose read by a child. Never applied to the module
# docstring or comments -- see module docstring above.
#
# DELIBERATELY EXCLUDES "correct"/"answer" -- a category error caught while drafting, recorded
# rather than silently avoided (mirrors the exemplars script's own "SUPERVISOR CORRECTION" for
# the same class of mistake). Both are ordinary instructional English ("write the answer",
# "choose the correct number") legitimately used in child-facing math questions; they are banned
# from FIELD NAMES elsewhere in this codebase (FORBIDDEN_FIELD_TERMS, PROHIBITED_COLUMN_TERMS)
# because there they signal a private concept leaking into a schema, not because the words
# themselves are unsafe in prose. Applying that field-name vocabulary to prose flagged two of
# this batch's own real, correct entries (C-SF-03, C-TC-03) before this list was corrected --
# the same "vocabulary borrowed from the wrong layer" mistake the exemplars script's own
# docstring already documents once. Answer-leakage is guarded separately, by the no-digits rule
# and by never naming which option in a labelled-choice set is correct -- not by banning the word
# "answer" from a question.
BANNED_TECHNICAL_TERMS = frozenset(
    {
        "difficulty", "scaffold", "template", "seed", "mastery", "bkt", "payload",
        "algorithm", "parameter", "generator", "vector",
        "evaluat", "config", "session", "instance", "catalogue", "calibrat",
    }
)

# BUILDER JUDGMENT -- UNRATIFIED. A generous upper bound for a short, Grade-2-appropriate
# question, not a readability formula -- see the length test's own docstring for the stated
# blind spot: this cannot detect a short but confusing sentence.
MAX_WORDING_LENGTH_CHARS = 120


def _frozen_wording() -> dict:
    return json.loads(FROZEN_PATH.read_text(encoding="utf-8"))


def _frozen_entries() -> list[dict]:
    return _frozen_wording()["entries"]


def _frozen_exemplar_entries() -> list[dict]:
    return json.loads(EXEMPLARS_PATH.read_text(encoding="utf-8"))["entries"]


def test_live_wording_matches_frozen_artefact() -> None:
    """Any unreviewed change to ``PROMPT_TEXT_BY_TEMPLATE`` fails this test -- the property that
    makes the artefact self-checking rather than a snapshot nobody re-derives. Compares
    SERIALIZED BYTES, mirroring the registry/exemplars precedent, since "regenerating produces
    this exact file" is a statement about bytes."""
    assert _serialize_wording(build_wording()) == FROZEN_PATH.read_bytes()


def test_frozen_artefact_checksum_matches_meta() -> None:
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    digest = hashlib.sha256(FROZEN_PATH.read_bytes()).hexdigest()
    assert digest == meta["checksum_sha256"]
    assert meta["contract_version"] == "v1"


def test_top_level_label_is_test_fixture_only() -> None:
    assert _frozen_wording()["label"] == "TEST_FIXTURE_ONLY"


def test_wording_covers_exactly_the_registry_template_set_no_gaps_no_extras() -> None:
    """ACCEPTANCE CRITERION 4: a missing template fails the suite rather than rendering blank.
    Cross-checked against ``c-template-registry.json`` (not a live wheel call, unlike the
    registry/exemplars scripts themselves) so this test has no wheel dependency of its own --
    wording is authored content, and its coverage claim is checked against the frozen list of
    templates the generator supports, not re-derived from the wheel a second time here.

    The template id SET is still exactly the registry's 30, even though the entry COUNT is now
    32 (two templates contribute two entries each) -- see
    ``test_entry_count_is_32_with_exactly_two_variant_templates``."""
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    registry_ids = {entry["template_id"] for entry in registry}

    wording_ids = {entry["game_task_template_id"] for entry in _frozen_entries()}

    assert len(registry_ids) == 30
    assert wording_ids == registry_ids


def test_entry_count_is_32_with_exactly_two_variant_templates() -> None:
    """ACCEPTANCE CRITERION 3: 32 entries total (28 non-variant templates + 2 templates x 2
    variants each), and exactly two template ids carry variants."""
    entries = _frozen_entries()
    assert len(entries) == 32

    variant_ids = {
        entry["game_task_template_id"] for entry in entries if entry["variant_key"] is not None
    }
    assert variant_ids == VARIANT_TEMPLATE_IDS

    by_template: dict[str, int] = {}
    for entry in entries:
        by_template[entry["game_task_template_id"]] = by_template.get(
            entry["game_task_template_id"], 0
        ) + 1
    assert set(by_template) == (
        {entry["template_id"] for entry in json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))}
    )
    for template_id, count in by_template.items():
        expected = 2 if template_id in VARIANT_TEMPLATE_IDS else 1
        assert count == expected, (template_id, count)


def test_every_entry_key_set_equals_allow_list_exactly() -> None:
    for entry in _frozen_entries():
        assert set(entry) == ALLOWED_ENTRY_KEYS, entry.get("game_task_template_id", "<missing>")


def test_allow_list_negative_control_fails_on_a_third_key() -> None:
    """Demonstrates, with REAL output, that the key-set assertion FAILS when a fifth key is added
    -- proving the guard can actually fire, per this project's standing discipline (X-10)."""
    real_entry = _frozen_entries()[0]
    tampered_entry = dict(real_entry, internal_note="not part of the allow-list")

    assert set(real_entry) == ALLOWED_ENTRY_KEYS
    assert set(tampered_entry) != ALLOWED_ENTRY_KEYS


def test_variant_key_and_variant_value_are_both_null_or_both_non_null() -> None:
    """Never one of each -- a lone ``variant_key`` with a null ``variant_value`` (or vice versa)
    would be a malformed row that ``prompt_text_for`` could not resolve correctly."""
    for entry in _frozen_entries():
        has_key = entry["variant_key"] is not None
        has_value = entry["variant_value"] is not None
        assert has_key == has_value, entry


def test_variant_negative_control_fires_on_mismatched_nullness() -> None:
    """RED direction: a row with a variant_key but no variant_value must be caught."""
    tampered_entry = {
        "game_task_template_id": "C-EG-02",
        "variant_key": "direction",
        "variant_value": None,
        "prompt_text": "Build the array shown.",
    }
    has_key = tampered_entry["variant_key"] is not None
    has_value = tampered_entry["variant_value"] is not None
    assert has_key != has_value


def test_variant_values_agree_with_exemplars_in_both_directions() -> None:
    """ACCEPTANCE CRITERION 5: every variant value in the wording table actually occurs in
    ``c-prompt-exemplars.json`` for that template, and every value occurring there has a wording
    entry. Catches a generator change introducing a third direction in either artefact."""
    exemplar_entries = _frozen_exemplar_entries()

    for template_id in VARIANT_TEMPLATE_IDS:
        wording_rows = [
            entry for entry in _frozen_entries() if entry["game_task_template_id"] == template_id
        ]
        variant_key = wording_rows[0]["variant_key"]
        wording_values = {row["variant_value"] for row in wording_rows}

        exemplar_values = {
            entry["prompt_payload"][variant_key]
            for entry in exemplar_entries
            if entry["game_task_template_id"] == template_id
        }

        assert wording_values == exemplar_values, (template_id, wording_values, exemplar_values)


def test_c_cc_04_names_both_trial_types_neutrally_and_names_neither_as_correct() -> None:
    """ACCEPTANCE CRITERION 6: C-CC-04's string is not variant-keyed (one entry, no variant), is
    true on both trial types, and never states which is correct -- checked by asserting it does
    not literally contain either trial_type value or a same/changed verdict word."""
    entries = [
        entry for entry in _frozen_entries() if entry["game_task_template_id"] == "C-CC-04"
    ]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["variant_key"] is None
    assert entry["variant_value"] is None

    text_lower = entry["prompt_text"].lower()
    for banned in ("add_remove", "rearrange_only", "moved around"):
        assert banned not in text_lower, entry["prompt_text"]


def _variant_text(template_id: str, variant_value: str) -> str:
    """The authored string for one variant, read from the table itself.

    These two tests are about the RESOLVER -- that it reads the variant key out of the payload,
    and that it ignores the payload for a template with no variants. Asserting against literal
    wording made them fail whenever the wording was edited (the 2026-09-28 ESL rewrite), which is
    a content review pretending to be a mechanism test. The content has its own guards: coverage,
    banned terms, length, no digits, and the frozen artefact's checksum.
    """
    for variant in PROMPT_TEXT_BY_TEMPLATE[template_id]:
        if variant.variant_value == variant_value:
            return variant.prompt_text
    raise AssertionError(f"no {variant_value!r} variant for {template_id}")


def test_prompt_text_for_resolves_variant_from_payload() -> None:
    """ACCEPTANCE CRITERION 1: the resolver takes a payload and resolves variants from it,
    server-side."""
    for template_id, values in (("C-EG-02", ("build", "read")), ("C-NP-04", ("ascending", "descending"))):
        resolved = {
            value: prompt_text_for(template_id, {"direction": value}) for value in values
        }
        for value in values:
            assert resolved[value] == _variant_text(template_id, value)
        # The variants must actually differ, or "resolution" would be indistinguishable from
        # returning the same string twice.
        assert len(set(resolved.values())) == len(values), resolved


def test_prompt_text_for_ignores_payload_for_non_variant_template() -> None:
    only = PROMPT_TEXT_BY_TEMPLATE["C-BT-01"]
    assert len(only) == 1
    expected = only[0].prompt_text
    assert prompt_text_for("C-BT-01", {}) == expected
    assert prompt_text_for("C-BT-01", {"anything": "irrelevant"}) == expected
    assert prompt_text_for("C-BT-01", {"direction": "build"}) == expected


# --- ESL register (2026-09-28) ------------------------------------------------------------------
#
# BANNED_TECHNICAL_TERMS above keeps SYSTEM vocabulary off a child's screen. This is a different
# axis: school-register English that a Grade 2 reader whose first language is Sinhala should not
# have to decode before the mathematics starts. Mirrors the list Component B's wording is held to
# (app/domain/live_engine/prompt_wording.py), so the two components cannot drift into two different
# registers for the same learner.
#
# Real maths vocabulary a Grade 2 class is taught -- "tens", "ones", "hundreds", "groups", "rows",
# "equally", "half" -- is deliberately NOT here. Removing that would teach the wrong thing rather
# than simplify.
ESL_BANNED_WORDS = (
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
    "subtract",
    "trade",
)


def test_no_wording_uses_school_register_english() -> None:
    offenders = {
        entry["game_task_template_id"]: entry["prompt_text"]
        for entry in _frozen_entries()
        for word in ESL_BANNED_WORDS
        if word in entry["prompt_text"].lower()
    }
    assert offenders == {}, offenders


def test_esl_scan_would_catch_a_regression() -> None:
    """Negative control, in this file's own idiom: the scan must actually fire on the wording these
    strings replaced, or it proves nothing."""
    replaced = "Build the array shown."
    assert any(word in replaced.lower() for word in ESL_BANNED_WORDS)


def test_wording_stays_short_enough_to_read_aloud() -> None:
    """MAX_WORDING_LENGTH_CHARS is a generous outer bound on the whole string. This is the tighter,
    per-sentence one Component B is held to: one idea per sentence, few words. It catches a future
    addition written as prose, not this batch's phrasing."""
    for entry in _frozen_entries():
        for sentence in (part for part in re.split(r"[.?]", entry["prompt_text"]) if part.strip()):
            words = sentence.split()
            assert len(words) <= 9, (entry["game_task_template_id"], sentence.strip(), len(words))


def test_prompt_text_for_raises_on_unknown_template() -> None:
    with pytest.raises(PromptWordingUnavailableError):
        prompt_text_for("C-NOT-A-REAL-TEMPLATE", {})


def test_prompt_text_for_raises_on_unknown_variant_value() -> None:
    """ACCEPTANCE CRITERION 2: an unknown variant value RAISES -- it does not fall back to a
    default string, does not pick the first entry, and does not return a placeholder."""
    with pytest.raises(PromptWordingUnavailableError):
        prompt_text_for("C-EG-02", {"direction": "sideways"})


def test_prompt_text_for_raises_on_missing_discriminator_key() -> None:
    """A payload that omits the discriminator entirely (``prompt_payload.get`` returns ``None``)
    must also raise, not silently match a variant whose value happens to be ``None``."""
    with pytest.raises(PromptWordingUnavailableError):
        prompt_text_for("C-EG-02", {})


def test_unknown_variant_negative_control_proves_the_raise_path_not_a_return() -> None:
    """Positive proof the unknown-variant guard actually raises rather than merely being callable
    without error: calling with a genuinely unsupported value must be the ONLY way to observe the
    exception -- a known value must NOT raise."""
    with pytest.raises(PromptWordingUnavailableError):
        prompt_text_for("C-NP-04", {"direction": "sideways"})

    # silent direction: the same call shape with a real value does not raise
    prompt_text_for("C-NP-04", {"direction": "ascending"})


def test_no_ascii_digit_in_any_wording() -> None:
    """ACCEPTANCE CRITERION 7, the no-digits rule (taken, per the batch's planning turn):
    structurally impossible to leak a numeric answer, and forces count-agnostic phrasing for the
    three templates whose blank count varies by level rather than leaving that to author
    discipline."""
    offenders = {
        entry["game_task_template_id"]: entry["prompt_text"]
        for entry in _frozen_entries()
        if any(ch.isdigit() for ch in entry["prompt_text"])
    }
    assert not offenders, offenders


def test_no_digits_negative_control_fires_on_a_real_entry() -> None:
    """POSITIVE PROOF the digit scan does real work: tampers one real entry with a digit and
    shows the same predicate catches it."""
    real_entry = _frozen_entries()[0]
    tampered_text = real_entry["prompt_text"] + " (level 3)"

    assert not any(ch.isdigit() for ch in real_entry["prompt_text"])
    assert any(ch.isdigit() for ch in tampered_text)


def test_no_banned_technical_term_in_any_wording_value() -> None:
    """ACCEPTANCE CRITERION 4 (readability): scans ``prompt_text`` VALUES only -- see module
    docstring for why this is scoped to content, never to the source file (which necessarily
    discusses these terms in its own docstring/comments)."""
    offenders = {
        entry["game_task_template_id"]: entry["prompt_text"]
        for entry in _frozen_entries()
        if any(term in entry["prompt_text"].lower() for term in BANNED_TECHNICAL_TERMS)
    }
    assert not offenders, offenders


def test_banned_term_negative_control_fires_on_a_real_violation() -> None:
    """RED direction: a synthetic entry that genuinely contains a banned term must be caught."""
    violating_text = "Use the scaffold to find the correct answer."
    assert any(term in violating_text.lower() for term in BANNED_TECHNICAL_TERMS)


def test_banned_term_scan_would_have_caught_the_source_scan_mistake() -> None:
    """SILENT direction, and the specific caution this batch was told to carry forward: a bare
    substring match over the module's raw SOURCE TEXT would flag this very file's own docstring
    (which discusses "difficulty", "scaffold", "template", "mastery", etc. at length, explaining
    why the wording avoids them) -- demonstrating the naive approach breaks exactly the way the
    frontend's guard once did. The actual check (scanning the frozen artefact's ``prompt_text``
    values) does not examine source text at all, so it cannot repeat that failure -- shown here by
    contrast, not asserted about a check that was never built."""
    source_text = SOURCE_MODULE_PATH.read_text(encoding="utf-8").lower()
    naive_source_scan_hits = {term for term in BANNED_TECHNICAL_TERMS if term in source_text}
    assert naive_source_scan_hits, (
        "expected the module's own docstring to mention several banned terms while explaining "
        "the rule -- if this is empty, the demonstration below is vacuous"
    )

    value_scan_hits = {
        term
        for term in BANNED_TECHNICAL_TERMS
        for entry in _frozen_entries()
        if term in entry["prompt_text"].lower()
    }
    assert not value_scan_hits, value_scan_hits


def test_wording_length_within_bound() -> None:
    """ACCEPTANCE CRITERION 4 (length/readability bound). STATED BLIND SPOT: a character-count
    ceiling is a proxy for brevity, not for Grade-2 comprehensibility -- it cannot detect a short
    but confusing sentence, and passing it is not evidence the wording is well-written."""
    offenders = {
        entry["game_task_template_id"]: len(entry["prompt_text"])
        for entry in _frozen_entries()
        if len(entry["prompt_text"]) > MAX_WORDING_LENGTH_CHARS
    }
    assert not offenders, offenders


def test_length_negative_control_fires_on_an_overlong_entry() -> None:
    overlong_text = "x" * (MAX_WORDING_LENGTH_CHARS + 1)
    assert len(overlong_text) > MAX_WORDING_LENGTH_CHARS

    real_entry = _frozen_entries()[0]
    assert len(real_entry["prompt_text"]) <= MAX_WORDING_LENGTH_CHARS


def test_entries_sorted_by_template_then_variant_value_nulls_first() -> None:
    entries = _frozen_entries()
    keys = [(entry["game_task_template_id"], entry["variant_value"] or "") for entry in entries]
    assert keys == sorted(keys)
