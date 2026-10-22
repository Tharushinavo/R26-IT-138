"""C Prompt Exemplars drift test (Component C batch after the template registry, work order
``c-prompt-exemplars-work-order.md`` + ``Component_C_Prompt_Exemplar_Artefact_Request.md``).

Freezes ``backend/contract/c-prompt-exemplars.json`` (``{"label": "TEST_FIXTURE_ONLY", "entries":
[...]}, one entry per ``(game_task_template_id, difficulty_level)`` for all 30 templates x levels
1..5, 150 total) and enforces that the live artefact -- recomputed from the installed
``component_c_generator`` wheel via the imported
``scripts.generate_c_prompt_exemplars.build_exemplars()`` -- never silently drifts from it.
Mirrors ``test_c_template_registry_freeze.py``'s discipline: imports ``build_exemplars`` from the
script rather than re-implementing the extraction, and imports ``PROHIBITED_COLUMN_TERMS`` from
``tests.test_be2_architecture_guards`` rather than copying it -- both so script/test and the two
prohibited-term lists can never drift apart from each other.

THE ALLOW-LIST TEST (work order §3, D3 item 4) is a KEY-SET assertion, not a value scan -- see
the work order's own finding: a value scan (does any answer value appear in any prompt value)
fails on CORRECT output for at least four templates that legitimately share a key between
``prompt_payload`` and ``correct_answer_payload`` (e.g. C-MCL-04's shared ``target_position``).
The key-set assertion below, plus its negative control, is the formulation the work order
requires instead.

SUPERVISOR CORRECTION -- ``test_live_exemplars_match_frozen_artefact`` compares SERIALIZED BYTES,
not parsed structures. Some ``prompt_payload`` values are Python tuples in the generator's return
value; JSON has no tuple type, so the frozen file round-trips them to lists, and a parsed-structure
comparison (``build_exemplars() == json.loads(...)``) sees a type mismatch on 10 of 150 entries
even though every value is identical. "Regenerating produces this exact file" is a statement about
bytes, which is also what the checksum/byte-identity guarantees already rest on -- so the byte
comparison is the more correct assertion, not a workaround. ``build_exemplars()`` itself is left
untouched: it still returns whatever the generator returned, tuples included: the "verbatim"
guarantee does not get quietly redefined to "verbatim, except containers we normalised."

SUPERVISOR CORRECTION -- the nested prompt-payload key scan was removed from
``test_no_prohibited_field_name_in_frozen_artefact``. ``PROHIBITED_COLUMN_TERMS`` is Component B's
database-column vocabulary; ``shown_sequence`` (C-NP-01/02/03's rendering content -- the literal
sequence of numbers shown to the child) is legitimate content that trips its ``sequenc`` term.
Applying a DB-column vocabulary to generator prompt-payload content keys was a category error.
Keeping the scan would require a per-key exemption list, which is tuning away the measurement --
the exact practice this project forbids. The test now asserts the five-field TOP-LEVEL allow-list
only, which is the strong guarantee: ``correct_answer_payload``/``difficulty_vector`` are proven
never read (see ``test_every_entry_key_set_equals_allow_list_exactly`` and its negative control).

RESIDUAL, named rather than papered over: if a generator template ever placed answer-bearing data
*inside* ``prompt_payload`` itself, this artefact would carry it and nothing in this test module
would catch it. That is a generator-side property, not one this artefact's own tests can assert.
"""

from __future__ import annotations

import hashlib
import json
from itertools import product
from pathlib import Path
from random import Random

import pytest

from component_c_generator.generation_config import default_generation_config
from component_c_generator.tasks.registry import TASKS

from app.domain.live_engine_c.generation_mode_guard import (
    GenerationConfigNotPermittedError,
    assert_generation_config_permitted,
)
from scripts.generate_c_prompt_exemplars import (
    DIFFICULTY_LEVELS,
    MASTER_SEED,
    _entry_seed,
    _serialize_exemplars,
    build_exemplars,
)
from tests.test_be2_architecture_guards import PROHIBITED_COLUMN_TERMS

CONTRACT_DIR = Path(__file__).parent.parent / "contract"
FROZEN_PATH = CONTRACT_DIR / "c-prompt-exemplars.json"
META_PATH = CONTRACT_DIR / "c-prompt-exemplars.meta.json"
REGISTRY_PATH = CONTRACT_DIR / "c-template-registry.json"

ALLOWED_ENTRY_KEYS = frozenset(
    {
        "game_task_template_id", "difficulty_level", "prompt_payload", "interactive_assets",
        "valid_action_space", "blanks", "prompt_text",
    }
)

# Mirrors task_service._BLANKS_TEMPLATE_IDS exactly -- BE-prompt-text batch.
_BLANKS_TEMPLATE_IDS = frozenset({"C-NP-01", "C-NP-02", "C-NP-03"})


def _frozen_exemplars() -> dict:
    return json.loads(FROZEN_PATH.read_text(encoding="utf-8"))


def _frozen_entries() -> list[dict]:
    return _frozen_exemplars()["entries"]


def test_live_exemplars_match_frozen_artefact() -> None:
    """Any unreviewed change to the installed wheel's template set, any template's
    ``prompt_payload``/``interactive_assets``/``valid_action_space``, or the seed derivation
    fails this test -- the property that makes the artefact self-checking rather than a snapshot
    nobody re-derives (work order D3 item 1).

    Compares SERIALIZED BYTES, not parsed structures (see module docstring, "SUPERVISOR
    CORRECTION"): some prompt_payload values are Python tuples, which JSON has no type for, so a
    parsed-structure comparison sees tuple-vs-list mismatches on entries whose content is
    otherwise identical. "Regenerating produces this exact file" is a statement about bytes."""
    assert _serialize_exemplars(build_exemplars()) == FROZEN_PATH.read_bytes()


def test_frozen_artefact_checksum_matches_meta() -> None:
    """D3 item 2. Fails on a hand-edited artefact or a stale checksum."""
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    digest = hashlib.sha256(FROZEN_PATH.read_bytes()).hexdigest()
    assert digest == meta["checksum_sha256"]
    assert meta["contract_version"] == "v1"


def test_top_level_label_is_test_fixture_only() -> None:
    assert _frozen_exemplars()["label"] == "TEST_FIXTURE_ONLY"


def test_exemplar_completeness_150_entries_30_times_5_no_gaps_no_extras() -> None:
    """D3 item 3: exact equality against the full (template_id, difficulty_level) product set --
    not a subset or count-only check, so a missing pair, an extra pair, or a duplicate collapsing
    the set comparison all fail this test individually (the explicit length checks catch the
    duplicate case, which a bare set-equality check alone would hide)."""
    entries = _frozen_entries()
    config = default_generation_config()
    template_ids = tuple(sorted(config.per_template))

    pairs = [(entry["game_task_template_id"], entry["difficulty_level"]) for entry in entries]
    expected_pairs = set(product(template_ids, DIFFICULTY_LEVELS))

    assert len(entries) == 150
    assert len(pairs) == len(set(pairs)), "frozen artefact has a duplicate (template_id, difficulty_level) pair"
    assert set(pairs) == expected_pairs
    assert len(pairs) == len(expected_pairs)
    assert len(template_ids) == 30


def test_every_entry_key_set_equals_allow_list_exactly() -> None:
    """D3 item 4, first half: every entry's key set equals the seven-field allow-list exactly --
    no eighth key, no missing key. (Five fields through the exemplars batch; BE-prompt-text adds
    ``blanks`` and ``prompt_text`` as the sixth and seventh.)"""
    for entry in _frozen_entries():
        assert set(entry) == ALLOWED_ENTRY_KEYS, entry["game_task_template_id"]


def test_allow_list_negative_control_fails_on_an_eighth_key() -> None:
    """D3 item 4, second half (work order acceptance criterion 1): demonstrates, with REAL
    output, that the same key-set assertion FAILS when an eighth key is added to a real entry --
    proving the guard can actually fire, unlike a value-scan exemption list that only ever grows."""
    real_entry = _frozen_entries()[0]
    tampered_entry = dict(real_entry, correct_answer_payload={"leaked": True})

    assert set(real_entry) == ALLOWED_ENTRY_KEYS
    assert set(tampered_entry) != ALLOWED_ENTRY_KEYS


def test_blanks_non_null_for_exactly_the_three_np_templates() -> None:
    """ACCEPTANCE CRITERION 1: ``blanks`` non-null for exactly C-NP-01/02/03 (all 5 levels each),
    null for the other 27 templates (all 5 levels each) -- asserted as a SET, so a future template
    silently acquiring or losing the field fails loudly rather than by coincidence of which
    templates happened to be checked."""
    non_null_template_ids = {
        entry["game_task_template_id"] for entry in _frozen_entries() if entry["blanks"] is not None
    }
    null_template_ids = {
        entry["game_task_template_id"] for entry in _frozen_entries() if entry["blanks"] is None
    }
    assert non_null_template_ids == _BLANKS_TEMPLATE_IDS
    assert null_template_ids == {
        entry["game_task_template_id"] for entry in _frozen_entries()
    } - _BLANKS_TEMPLATE_IDS
    for entry in _frozen_entries():
        if entry["game_task_template_id"] in _BLANKS_TEMPLATE_IDS:
            assert isinstance(entry["blanks"], int) and not isinstance(entry["blanks"], bool)


def test_blanks_cross_check_against_generated_difficulty_vector() -> None:
    """THE BEST CHECK IN THIS BATCH (planning-turn framing, kept here verbatim because it names
    exactly what this test is for): this project now derives ``blanks`` two different ways in two
    different places, for two different structural reasons --
    ``task_service._blanks`` (production, ``app/``) reads ``record.difficulty_vector["blanks"]``
    because calling ``default_generation_config()`` is forbidden anywhere under ``app/``;
    ``generate_c_prompt_exemplars.build_exemplars`` (this script, NOT under ``app/``) reads
    ``params.count_b_by_level[difficulty_level - 1]`` because reading
    ``generated.difficulty_vector`` here would breach this module's own "never referenced"
    guarantee for that field. Both routes are claimed to always produce the identical number,
    by construction of the pinned generator's own source (``number_path.py`` writes
    ``blanks = params.count_b_by_level[difficulty_level - 1]`` into ``difficulty_vector``
    verbatim) -- this test is the one assertion that would catch the two derivation paths
    silently diverging, by generating fresh (independently of ``build_exemplars``, which never
    reads ``difficulty_vector``) and comparing ``generated.difficulty_vector["blanks"]`` against
    the frozen artefact's ``blanks`` value for the three affected templates, at all five levels."""
    config = default_generation_config()
    for template_id in _BLANKS_TEMPLATE_IDS:
        task = TASKS[template_id]
        params = config.params_for(template_id)
        for difficulty_level in DIFFICULTY_LEVELS:
            seed = _entry_seed(MASTER_SEED, template_id, difficulty_level)
            generated = task.generate(Random(seed), difficulty_level, params)
            frozen_entry = next(
                entry
                for entry in _frozen_entries()
                if entry["game_task_template_id"] == template_id
                and entry["difficulty_level"] == difficulty_level
            )
            assert generated.difficulty_vector["blanks"] == frozen_entry["blanks"], (
                template_id,
                difficulty_level,
            )


def test_interactive_assets_empty_for_all_150() -> None:
    """D3 item 5. Would fail the moment any template starts populating interactive_assets --
    turning a silent no-op into a loud, specific failure (request doc §3.2)."""
    for entry in _frozen_entries():
        assert entry["interactive_assets"] == {}, entry["game_task_template_id"]


def test_valid_action_space_agrees_with_template_registry() -> None:
    """D3 item 6: a cheap cross-check between two independently generated artefacts. Fails if
    either artefact is regenerated inconsistently with the other."""
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    registry_by_id = {entry["template_id"]: entry["valid_action_space"] for entry in registry}

    for entry in _frozen_entries():
        template_id = entry["game_task_template_id"]
        assert template_id in registry_by_id, template_id
        assert entry["valid_action_space"] == registry_by_id[template_id], template_id


def test_no_prohibited_field_name_in_frozen_artefact() -> None:
    """D3 item 7: imports PROHIBITED_COLUMN_TERMS rather than copying it, so this list and the
    DB-column guard's list can never drift apart. Scans TOP-LEVEL entry keys only (see module
    docstring, "SUPERVISOR CORRECTION" -- the nested prompt_payload/valid_action_space key scan
    was removed as a category error: PROHIBITED_COLUMN_TERMS is Component B's database-column
    vocabulary, and legitimate rendering content such as C-NP-01's shown_sequence trips its
    sequenc term)."""
    offenders: set[tuple[str, str]] = set()
    for entry in _frozen_entries():
        template_id = entry.get("game_task_template_id", "<missing>")
        for key in entry:
            if any(term in key.lower() for term in PROHIBITED_COLUMN_TERMS):
                offenders.add((template_id, key))
    assert not offenders, offenders


def test_generation_config_refused_outside_smoke_mode() -> None:
    """Supervisor ruling 1: recording "the gate was called with smoke_mode=True and passed" only
    proves a boolean was passed. This test proves the gate is NOT inert for this content -- the
    exact same config the generator script uses is REFUSED under smoke_mode=False, which is what
    makes "produced under the smoke gate" a genuine claim rather than a stale provenance line.
    Would FAIL (silently passing where it should raise) the moment a future change made
    parameter_source_status something permissive while the sidecar's provenance string still
    claimed smoke-only content."""
    config = default_generation_config()
    assert config.parameter_source_status == "TEST_FIXTURE_ONLY"

    # The gate permits it under smoke_mode=True (what the generator script actually calls).
    assert_generation_config_permitted(config, smoke_mode=True)

    # The gate refuses the identical config under smoke_mode=False.
    with pytest.raises(GenerationConfigNotPermittedError):
        assert_generation_config_permitted(config, smoke_mode=False)
