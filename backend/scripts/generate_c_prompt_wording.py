"""C Prompt Wording generator (Component C batch BE-prompt-text, third member of the artefact
family after the template registry and the prompt exemplars).

**CANDIDATE WORDING, NOT OWNER-REVIEWED.** This script derives a frozen, checksummed snapshot of
``app.domain.live_engine_c.prompt_wording.PROMPT_TEXT_BY_TEMPLATE`` -- drafted this batch to prove
the machinery, not approved as final child-facing text. See that module's own docstring for the
full disclosure.

WHY THIS ARTEFACT IS NOT A PEER OF THE OTHER TWO IN ONE RESPECT: the template registry and the
prompt exemplars are read by NOTHING under ``app/`` -- they exist for the frontend's development
fixture and for this backend's own drift tests, and ``tests/test_be2_architecture_guards.py``
mechanically proves no app module reads the exemplars artefact by its literal filename.
``prompt_text`` is different: it must reach a real ``CNextTaskResponse``, so something under
``app/`` has to read wording. This script therefore does NOT source the artefact from a live
wheel call (there is no wheel call for authored content) -- it sources it from the same Python
module ``app.application.live_engine_c.task_service`` reads at request time
(``app.domain.live_engine_c.prompt_wording.PROMPT_TEXT_BY_TEMPLATE``), so the runtime source and
this frozen snapshot can never silently diverge. Runtime code reads the Python module, never this
JSON file -- this file is a derived, checksummed proof of what the module currently contains, not
an alternate source app code should ever open directly (see
``tests/test_be2_architecture_guards.py`` for the guard that keeps it that way).

``build_wording()`` is the importable core -- no CLI side effects at import time -- so
``tests/test_c_prompt_wording_freeze.py`` imports the real builder rather than re-implementing
it, mirroring the registry/exemplars precedent exactly: script and test cannot drift apart.
Writing the artefact/sidecar only happens under ``if __name__ == "__main__"``.

NO SMOKE GATE, UNLIKE THE EXEMPLARS SCRIPT -- deliberately. ``assert_generation_config_permitted``
guards GENERATION parameters (``GenerationConfig``, every value ``TEST_FIXTURE_ONLY``/
``SMOKE_ONLY``). Wording is authored content, not a generation parameter, and calling that guard
here would misrepresent what it protects.

INVOCATION -- THE SAME TRAP AS THE EXEMPLARS SCRIPT, VERIFIED BY RUNNING BOTH FORMS, NOT ASSUMED.
This script imports ``app.domain.live_engine_c.prompt_wording`` (the authoritative source), so it
inherits the exemplars script's invocation trap exactly:
``python -m scripts.generate_c_prompt_wording`` from the repository root -- NOT
``python scripts/generate_c_prompt_wording.py``. The file-path form puts only ``scripts/`` on
``sys.path[0]`` rather than the repository root, so ``app`` is not importable that way
(confirmed: ``ModuleNotFoundError: No module named 'app'``); the module form puts the working
directory on the path, which resolves it (confirmed: produces the artefact). Do not "fix" this
with a ``sys.path`` shim, and do not drop the ``app.`` import to make the file-path form work --
that import is what keeps this script reading the SAME source ``task_service`` reads at request
time, so the runtime module and this frozen snapshot can never silently diverge. The registry
script remains the one family member without this trap (no ``app.`` import at all); the
asymmetry is real, per-script, and worth re-checking rather than assuming for any future member.

Determinism: ``json.dumps(..., indent=2, sort_keys=True, ensure_ascii=True)`` plus an explicit
trailing ``"\\n"``, written as raw bytes (``open(path, "wb")``) so no platform newline translation
can occur -- identical convention to the registry and exemplars scripts. No RNG, no wall-clock, no
seed: the source is a static dict, so byte-identity across independent runs is guaranteed by
construction, not merely tested.

**Do not run this script.** The supervisor runs it and produces the artefact, exactly as the
registry and exemplars batches were split.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.domain.live_engine_c.prompt_wording import PROMPT_TEXT_BY_TEMPLATE, TEST_FIXTURE_LABEL

CONTRACT_DIR = Path(__file__).resolve().parent.parent / "contract"
ARTEFACT_PATH = CONTRACT_DIR / "c-prompt-wording.json"
META_PATH = CONTRACT_DIR / "c-prompt-wording.meta.json"

CONTRACT_VERSION = "v1"
SOURCE = (
    "app.domain.live_engine_c.prompt_wording.PROMPT_TEXT_BY_TEMPLATE (authored content, not the "
    "installed wheel) via scripts/generate_c_prompt_wording.py"
)


def build_wording() -> dict[str, Any]:
    """The live wording artefact: ``{"label": "TEST_FIXTURE_ONLY", "entries": [...]}``, one entry
    per ``(template_id, variant)`` pair in ``PROMPT_TEXT_BY_TEMPLATE`` -- 28 templates contribute
    one entry each, C-EG-02 and C-NP-04 contribute two each (one per ``direction`` value), for 32
    entries total. Sorted by ``(game_task_template_id, variant_value)``, with a non-variant
    template's single ``None`` variant_value sorting first for that template id (via the ``or ""``
    substitution below -- ``None`` and ``str`` are not otherwise orderable). Imported directly by
    the drift test so the two can never disagree about how the artefact is built.

    Every entry is built from named fields only: ``game_task_template_id``, ``variant_key``,
    ``variant_value``, ``prompt_text``. No other field from any other source is ever referenced
    here."""
    entries = [
        {
            "game_task_template_id": template_id,
            "variant_key": variant.variant_key,
            "variant_value": variant.variant_value,
            "prompt_text": variant.prompt_text,
        }
        for template_id, variants in PROMPT_TEXT_BY_TEMPLATE.items()
        for variant in variants
    ]
    entries.sort(key=lambda entry: (entry["game_task_template_id"], entry["variant_value"] or ""))
    return {"label": TEST_FIXTURE_LABEL, "entries": entries}


def _serialize_wording(wording: dict[str, Any]) -> bytes:
    """Deterministic serialization: sorted keys, stable ``(", ", ": ")`` separators (the
    ``json.dumps`` default under ``indent=2``), ASCII-only escaping, an explicit trailing newline,
    returned as raw bytes so no platform newline translation can occur -- identical convention to
    the registry and exemplars scripts."""
    text = json.dumps(wording, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    return text.encode("utf-8")


def _serialize_meta(checksum_sha256: str) -> bytes:
    meta = {
        "checksum_sha256": checksum_sha256,
        "contract_version": CONTRACT_VERSION,
        "source": SOURCE,
    }
    text = json.dumps(meta, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    return text.encode("utf-8")


def main() -> None:
    """CLI entry point. Deliberately isolated behind ``__main__`` so importing this module (as
    the drift test does, for ``build_wording``) has no side effect -- nothing is written to disk
    merely by importing."""
    wording = build_wording()
    wording_bytes = _serialize_wording(wording)
    checksum = hashlib.sha256(wording_bytes).hexdigest()
    meta_bytes = _serialize_meta(checksum)

    CONTRACT_DIR.mkdir(parents=True, exist_ok=True)
    with open(ARTEFACT_PATH, "wb") as artefact_file:
        artefact_file.write(wording_bytes)
    with open(META_PATH, "wb") as meta_file:
        meta_file.write(meta_bytes)


if __name__ == "__main__":
    main()
