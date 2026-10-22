"""C Prompt Exemplars generator (Component C batch after the template registry, work order
``c-prompt-exemplars-work-order.md`` + ``Component_C_Prompt_Exemplar_Artefact_Request.md``).

Derives ``backend/contract/c-prompt-exemplars.json`` and its sidecar
``c-prompt-exemplars.meta.json`` **live** from the installed ``component_c_generator`` wheel --
never from ``packaging/`` (``.dockerignore``d, absent from the image) and never from
``os.listdir``. Mirrors ``scripts/generate_c_template_registry.py``'s established shape exactly:
one importable ``build_exemplars()`` with no CLI side effects at import time, so
``tests/test_c_prompt_exemplars_freeze.py`` imports the real builder rather than
re-implementing it -- script and test cannot drift apart. Writing the artefact/sidecar only
happens under ``if __name__ == "__main__"``.

WHY 150 ENTRIES, NOT 30 (request doc §3.1): ``valid_action_space`` does not vary by difficulty
(the registry batch's own guard proved this); ``prompt_payload`` does, for 29 of the 30
templates -- verified against the installed wheel, not re-derived here. One entry per
``(game_task_template_id, difficulty_level)``, all 30 templates x levels 1..5. The one template
whose ``prompt_payload`` happens to be identical across all five levels (fully structural
generation, no per-level config value) still produces five distinct entries here, one per level
-- this is expected, not a duplication bug, and is required by the frontend's motor-constancy
tests, which render every template at every level.

THE ALLOW-LIST (work order §3 / request doc §2): each entry is built from named fields only --
``generated.prompt_payload``, ``generated.interactive_assets``, ``generated.valid_action_space``
-- read directly off the ``GeneratedContent`` the template's own ``generate()`` returns.
``generated.correct_answer_payload`` and ``generated.difficulty_vector`` are never referenced
anywhere in this module: not read, not filtered, not in scope. This is the discipline
``app/domain/c_task.py`` documents for itself (X-4, "allow-list construction -- named fields
only") extended to this artefact. There is no step at which the excluded fields could leak,
because there is no step at which they are ever bound to a name.

BE-PROMPT-TEXT BATCH: two more allow-listed fields, ``blanks`` and ``prompt_text`` (work order
§5, "carry the two new fields in c-prompt-exemplars.json too, so the frontend's development
fixture can serve a task with real wording"). Neither breaks the paragraph above.

``blanks`` is derived from ``params.count_b_by_level[difficulty_level - 1]`` -- the SAME
``params`` object this function already reads for generation, already legitimately obtained via
``default_generation_config()`` in an offline script (never permitted in ``app/``; see
``app/domain/c_task.py``'s docstring for the full reasoning) -- gated by the identical
three-template allow-list ``task_service._blanks`` uses in production
(``{"C-NP-01", "C-NP-02", "C-NP-03"}``), ``None`` otherwise. Deliberately NOT read from
``generated.difficulty_vector["blanks"]``, even though that key exists and would give the
identical number (verified: ``number_path.py`` writes
``blanks = params.count_b_by_level[difficulty_level - 1]`` into ``difficulty_vector`` verbatim)
-- reading it here would breach the paragraph above's "never referenced" guarantee for
``difficulty_vector``, which this script has held since the previous batch and this one leaves
intact. ``tests/test_c_prompt_exemplars_freeze.py`` independently cross-checks that this script's
``count_b_by_level``-derived value and the record's ``difficulty_vector``-derived value (the
production path) never disagree, so the two derivation routes this project now has for the same
field cannot silently diverge.

``prompt_text`` is read via ``app.domain.live_engine_c.prompt_wording.prompt_text_for`` -- the
SAME function ``task_service._task_fields`` calls in production -- never a second copy of the
wording table, so the exemplar fixture and the live serving path can never disagree about what a
template's question text is.

THE SMOKE GATE (work order §5): ``assert_generation_config_permitted`` lives app-side
(``app/domain/live_engine_c/generation_mode_guard.py``) and is never on the path a script calling
``TASKS[tid].generate(...)`` directly would traverse. This script calls it explicitly, once,
with ``smoke_mode=True``, before generating anything, so the artefact's provenance says the
content was produced UNDER the gate, not around it. If that call raises, the batch stops --
never caught, never skipped. The sidecar additionally records (supervisor ruling 1) that the
exact same config is REFUSED by the gate under ``smoke_mode=False`` -- proving the gate is not
inert for this content, not merely that a boolean was passed. That second call is asserted by
``tests/test_c_prompt_exemplars_freeze.py``, not by this script (this script's own call is the
``smoke_mode=True`` one only; re-deriving the refusal here would duplicate what the test proves
and risk the two silently diverging).

SEED DESIGN: ``generate()`` takes a seeded RNG. A single ``MASTER_SEED`` is recorded in the
sidecar; every per-entry seed is deterministically derived from it via ``_entry_seed`` below --
reproducible from the recorded master seed alone. The derivation is keyed directly by
``(template_id, difficulty_level)``, never by a running counter or list position, so it is stable
regardless of what order entries happen to be generated in, and regardless of whether only a
subset is ever generated. ``hashlib.sha256`` is used rather than Python's built-in ``hash()``,
which is per-process salted for strings and would not reproduce across runs.

Determinism: ``json.dumps(..., indent=2, sort_keys=True, ensure_ascii=True)`` plus an explicit
trailing ``"\\n"``, written as raw bytes (``open(path, "wb")``) so no platform newline
translation can occur -- same convention as the registry script.

INVOCATION: ``python -m scripts.generate_c_prompt_exemplars`` from the repository root -- NOT
``python scripts/generate_c_prompt_exemplars.py``. Unlike the registry script, this one imports
from ``app.`` for the smoke-gate assertion, and the file-path form puts only ``scripts/`` on
``sys.path[0]`` rather than the repository root, so ``app`` is not importable that way; the
module form puts the working directory on the path, which resolves it. (Do not "fix" this by
adding a ``sys.path`` shim here, and do not drop the ``app.`` import to make the file-path form
work -- that import is the smoke-gate call this artefact's provenance depends on.)

**Do not run this script.** The supervisor runs it in-container and produces the artefact.
"""

from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path
from random import Random
from typing import Any

from component_c_generator.generation_config import default_generation_config
from component_c_generator.tasks.registry import TASKS, supported_template_ids

from app.domain.live_engine_c.generation_mode_guard import assert_generation_config_permitted
from app.domain.live_engine_c.prompt_wording import prompt_text_for

CONTRACT_DIR = Path(__file__).resolve().parent.parent / "contract"
ARTEFACT_PATH = CONTRACT_DIR / "c-prompt-exemplars.json"
META_PATH = CONTRACT_DIR / "c-prompt-exemplars.meta.json"

CONTRACT_VERSION = "v1"
WHEEL_VERSION = "0.1.0+c3.09267ab"
SOURCE = (
    "component_c_generator.tasks.registry (installed wheel) via "
    "scripts/generate_c_prompt_exemplars.py"
)

TEST_FIXTURE_LABEL = "TEST_FIXTURE_ONLY"
DIFFICULTY_LEVELS: tuple[int, ...] = (1, 2, 3, 4, 5)

# BE-prompt-text batch: identical set to task_service._BLANKS_TEMPLATE_IDS -- see module
# docstring, "BE-PROMPT-TEXT BATCH", for why this script derives the value from count_b_by_level
# rather than from generated.difficulty_vector even though both give the same number.
_BLANKS_TEMPLATE_IDS = frozenset({"C-NP-01", "C-NP-02", "C-NP-03"})

# The one recorded value the whole artefact's randomness is reproducible from (see module
# docstring, "SEED DESIGN"). Mirrors the registry script's seed-0 convention.
MASTER_SEED = 0

# Provenance string recorded in the sidecar (supervisor ruling 1): states BOTH that the
# smoke_mode=True call this script makes was permitted, AND that the identical config is refused
# under smoke_mode=False -- proving the gate is not a no-op for this content. The second half is
# asserted by tests/test_c_prompt_exemplars_freeze.py::test_generation_config_refused_outside_smoke_mode,
# not executed here.
GENERATION_CONFIG_SMOKE_GATE_PROVENANCE = (
    "assert_generation_config_permitted(config, smoke_mode=True) called once before generation "
    "and passed; the identical config is asserted (by the drift test, not this script) to raise "
    "GenerationConfigNotPermittedError under smoke_mode=False, proving parameter_source_status "
    "is genuinely disallowed outside smoke mode for this content, not merely that a boolean was "
    "passed"
)


def _entry_seed(master_seed: int, template_id: str, difficulty_level: int) -> int:
    """Deterministic per-entry seed derived from the one recorded master seed, the template id,
    and the difficulty level -- via sha256 (stable across processes/runs/platforms, unlike
    Python's per-process-salted ``hash()``), keyed directly by ``(template_id,
    difficulty_level)`` rather than by generation order, so it is invariant to the order entries
    happen to be generated in and to whether only a subset is ever generated."""
    digest = hashlib.sha256(
        f"{master_seed}:{template_id}:{difficulty_level}".encode("ascii")
    ).hexdigest()
    return int(digest[:16], 16)


def build_exemplars() -> dict[str, Any]:
    """The live exemplar artefact: ``{"label": "TEST_FIXTURE_ONLY", "entries": [...]}``, one
    entry per ``(template_id, difficulty_level)`` for all 30 templates x levels 1..5 (150 total),
    sorted by ``(game_task_template_id, difficulty_level)``. Imported directly by the drift test
    so the two can never disagree about how the artefact is built.

    Calls the smoke gate explicitly, once, before any generation (work order §5). Fails loudly,
    per template AND difficulty level, with both attached in the exception, the moment any single
    ``generate`` call raises -- never catches and skips, which would silently yield a partial
    artefact.
    """
    config = default_generation_config()
    assert_generation_config_permitted(config, smoke_mode=True)

    entries: list[dict[str, Any]] = []
    for template_id in supported_template_ids():
        task = TASKS[template_id]
        params = config.params_for(template_id)
        for difficulty_level in DIFFICULTY_LEVELS:
            seed = _entry_seed(MASTER_SEED, template_id, difficulty_level)
            try:
                generated = task.generate(Random(seed), difficulty_level, params)
            except Exception as exc:  # noqa: BLE001 -- re-raised immediately, id+level attached
                raise RuntimeError(
                    "C prompt exemplar generation failed for template "
                    f"{template_id!r} at difficulty_level={difficulty_level}: {exc}"
                ) from exc
            # Allow-list construction (work order §3): named fields only. generated.
            # correct_answer_payload and generated.difficulty_vector are never referenced --
            # not here, not anywhere else in this module. ``blanks`` comes from ``params``
            # (count_b_by_level), NOT from generated.difficulty_vector -- see module docstring.
            blanks = params.count_b_by_level[difficulty_level - 1] if template_id in _BLANKS_TEMPLATE_IDS else None
            entries.append(
                {
                    "game_task_template_id": template_id,
                    "difficulty_level": difficulty_level,
                    "prompt_payload": generated.prompt_payload,
                    "interactive_assets": generated.interactive_assets,
                    "valid_action_space": generated.valid_action_space,
                    "blanks": blanks,
                    "prompt_text": prompt_text_for(template_id, generated.prompt_payload),
                }
            )

    entries.sort(key=lambda entry: (entry["game_task_template_id"], entry["difficulty_level"]))
    assert len(entries) == len(supported_template_ids()) * len(DIFFICULTY_LEVELS)
    return {"label": TEST_FIXTURE_LABEL, "entries": entries}


def _serialize_exemplars(exemplars: dict[str, Any]) -> bytes:
    """Deterministic serialization: sorted keys, stable ``(", ", ": ")`` separators (the
    ``json.dumps`` default under ``indent=2``), ASCII-only escaping, an explicit trailing
    newline, returned as raw bytes so no platform newline translation can occur regardless of
    how the caller writes them -- identical convention to the registry script."""
    text = json.dumps(exemplars, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    return text.encode("utf-8")


def _serialize_meta(checksum_sha256: str) -> bytes:
    meta = {
        "checksum_sha256": checksum_sha256,
        "contract_version": CONTRACT_VERSION,
        "wheel_version": WHEEL_VERSION,
        "source": SOURCE,
        "master_seed": MASTER_SEED,
        "generation_config_smoke_gate": GENERATION_CONFIG_SMOKE_GATE_PROVENANCE,
    }
    text = json.dumps(meta, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    return text.encode("utf-8")


def main() -> None:
    """CLI entry point. Deliberately isolated behind ``__main__`` so importing this module (as
    the drift test does, for ``build_exemplars``) has no side effect -- nothing is written to
    disk merely by importing."""
    exemplars = build_exemplars()
    exemplars_bytes = _serialize_exemplars(exemplars)
    checksum = hashlib.sha256(exemplars_bytes).hexdigest()
    meta_bytes = _serialize_meta(checksum)

    CONTRACT_DIR.mkdir(parents=True, exist_ok=True)
    with open(ARTEFACT_PATH, "wb") as artefact_file:
        artefact_file.write(exemplars_bytes)
    with open(META_PATH, "wb") as meta_file:
        meta_file.write(meta_bytes)


if __name__ == "__main__":
    main()
