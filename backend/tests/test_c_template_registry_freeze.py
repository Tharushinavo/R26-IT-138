"""C Template Registry drift test (Component C batch after 9b-1; work order
``c-template-registry-work-order.md`` + ``-ADDENDUM.md``, ADDENDUM A0/D3).

Freezes ``backend/contract/c-template-registry.json`` (a sorted array of
``{"template_id", "valid_action_space"}``, ADDENDUM Ruling 3) and enforces that the live
registry -- recomputed from the installed ``component_c_generator`` wheel via the imported
``scripts.generate_c_template_registry.build_registry()`` -- never silently drifts from it.
Mirrors ``test_be5a_contract_freeze.py``'s four assertions (live-matches-frozen, checksum,
exact id-set equality, no prohibited field name), plus a fifth: the ADDENDUM Ruling 2
difficulty-invariance guard.

Deliberately imports ``build_registry`` from the script rather than re-implementing the
extraction here, and imports ``PROHIBITED_COLUMN_TERMS`` from
``tests.test_be2_architecture_guards`` rather than copying the list -- both per ADDENDUM A0,
so script/test and the two prohibited-term lists can never drift apart from each other.
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

from component_c_generator.generation_config import default_generation_config
from component_c_generator.tasks.registry import TASKS, supported_template_ids

from scripts.generate_c_template_registry import build_registry
from tests.test_be2_architecture_guards import PROHIBITED_COLUMN_TERMS

CONTRACT_DIR = Path(__file__).parent.parent / "contract"
FROZEN_PATH = CONTRACT_DIR / "c-template-registry.json"
META_PATH = CONTRACT_DIR / "c-template-registry.meta.json"


def _frozen_registry() -> list[dict]:
    return json.loads(FROZEN_PATH.read_text(encoding="utf-8"))


def test_live_registry_matches_frozen_artefact() -> None:
    """Any unreviewed change to the installed wheel's template set or any template's
    valid_action_space fails this test -- the property that makes the artefact self-checking
    rather than a snapshot nobody re-derives (work order acceptance criterion / D3 item 1)."""
    assert build_registry() == _frozen_registry()


def test_frozen_artefact_checksum_matches_meta() -> None:
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    digest = hashlib.sha256(FROZEN_PATH.read_bytes()).hexdigest()
    assert digest == meta["checksum_sha256"]
    assert meta["contract_version"] == "v1"


def test_frozen_template_id_set_matches_supported_template_ids_exactly() -> None:
    """Exact equality, not a subset (work order acceptance criterion 3: a subset check would
    pass while missing a removed template) -- plus a length check to catch a duplicate entry
    that would otherwise hide behind a coincidentally-correct set (D3 item 3)."""
    frozen = _frozen_registry()
    frozen_ids = [entry["template_id"] for entry in frozen]
    live_ids = supported_template_ids()

    assert len(frozen_ids) == len(set(frozen_ids)), "frozen artefact has a duplicate template_id"
    assert set(frozen_ids) == set(live_ids)
    assert len(frozen_ids) == len(live_ids)


def test_no_prohibited_field_name_in_frozen_artefact() -> None:
    """No private/scientific term (D3 item 4) appears in either the artefact's top-level field
    names or any ``valid_action_space`` key, using the SAME ``PROHIBITED_COLUMN_TERMS`` the
    DB-column guard uses -- imported, never copied, so the two lists cannot drift apart."""
    offenders: set[tuple[str, str]] = set()
    for entry in _frozen_registry():
        template_id = entry.get("template_id", "<missing>")
        for key in entry:
            if any(term in key.lower() for term in PROHIBITED_COLUMN_TERMS):
                offenders.add((template_id, key))
        for action_key in entry.get("valid_action_space", {}):
            if any(term in action_key.lower() for term in PROHIBITED_COLUMN_TERMS):
                offenders.add((template_id, action_key))
    assert not offenders, offenders


def test_valid_action_space_is_difficulty_invariant_across_all_five_levels() -> None:
    """ADDENDUM Ruling 2: extracting ``valid_action_space`` by calling ``generate()`` at ONE
    difficulty level (as ``build_registry`` does, at level 1) embeds an assumption -- that the
    action space is difficulty-invariant -- that is true today but enforced by nothing in the
    generator itself, and the archetype model this artefact ultimately feeds rests on that
    invariance. This test makes it a CHECKED property: for every template, generate at each
    difficulty level 1..5 and assert ``valid_action_space`` is IDENTICAL across all five. A red
    result here is a genuine finding that the archetype grouping is unsound, not merely that
    the artefact needs regenerating -- fails per template, with the id in the message."""
    config = default_generation_config()
    for template_id in supported_template_ids():
        task = TASKS[template_id]
        params = config.params_for(template_id)
        action_spaces_by_level = {
            level: task.generate(random.Random(0), level, params).valid_action_space
            for level in (1, 2, 3, 4, 5)
        }
        baseline = action_spaces_by_level[1]
        assert all(space == baseline for space in action_spaces_by_level.values()), (
            f"template {template_id!r}: valid_action_space is NOT difficulty-invariant across "
            f"levels 1..5 -- got {action_spaces_by_level}"
        )
