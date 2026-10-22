"""C Template Registry generator (Component C batch after 9b-1, work order
``c-template-registry-work-order.md`` + ``-ADDENDUM.md``).

Derives ``backend/contract/c-template-registry.json`` and its sidecar
``c-template-registry.meta.json`` **live** from the installed
``component_c_generator`` wheel -- never from ``packaging/`` (``.dockerignore``d, absent from
the image) and never from ``os.listdir``. Mirrors the BE5a OpenAPI freeze precedent
(``scripts`` producing an artefact ``tests/test_be5a_contract_freeze.py`` checks against
``app.openapi()``): one artefact, two independent readers (this backend's own drift test, and
the frontend's archetype-table coverage test, out of scope for this batch).

``build_registry()`` is the importable core -- no CLI side effects at import time -- so
``tests/test_c_template_registry_freeze.py`` imports the real builder rather than
re-implementing it (ADDENDUM A0, "approved specifically": script and test must not be able to
drift apart). Writing the artefact/sidecar only happens under ``if __name__ == "__main__"``.

ADDENDUM Ruling 1: the artefact carries **``template_id`` and ``valid_action_space`` only**.
``family_id`` is deliberately never reintroduced here -- see the ruling for why a
template-id-derived family value is worse than no field at all.

ADDENDUM Ruling 3: top-level shape is a **sorted array** of objects, not a keyed object.

Extraction: ``valid_action_space`` is not a static attribute -- it is only reachable by calling
each template's ``generate(rng, difficulty_level, params)`` and reading it off the returned
``GeneratedContent``. This script calls it once per template, at seed 0 / difficulty level 1
(mirrors the ADDENDUM's exact call shape). Failure is loud and per-template: never
catch-and-skip, which would silently yield a partial registry.

Determinism: ``json.dumps(..., indent=2, sort_keys=True, ensure_ascii=True)`` plus an explicit
trailing ``"\\n"``, written as raw bytes (``open(path, "wb")``) so no platform newline
translation can occur. No wall-clock, no observable randomness (the RNG seed is fixed at 0
purely to satisfy ``generate``'s signature -- ``valid_action_space`` is asserted
difficulty/seed-invariant by the drift test's own Ruling-2 guard, not depended on here).

**Do not run this script.** The supervisor runs it in-container and produces the artefact,
exactly as the 9b-0 wheel build was split from its own generator script.
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Any

from component_c_generator.generation_config import default_generation_config
from component_c_generator.tasks.registry import TASKS, supported_template_ids

CONTRACT_DIR = Path(__file__).resolve().parent.parent / "contract"
ARTEFACT_PATH = CONTRACT_DIR / "c-template-registry.json"
META_PATH = CONTRACT_DIR / "c-template-registry.meta.json"

CONTRACT_VERSION = "v1"
WHEEL_VERSION = "0.1.0+c3.09267ab"
SOURCE = (
    "component_c_generator.tasks.registry (installed wheel) via "
    "scripts/generate_c_template_registry.py"
)


def build_registry() -> list[dict[str, Any]]:
    """The live registry: a sorted list of ``{"template_id": ..., "valid_action_space": ...}``,
    one entry per id returned by ``supported_template_ids()`` -- never ``os.listdir`` or any
    other filesystem enumeration. Imported directly by the drift test so the two can never
    disagree about how the registry is built.

    Fails loudly, per template, with the template id in the exception, the moment any single
    template's ``generate`` call raises -- never catches and skips, which would silently yield
    a partial registry.
    """
    config = default_generation_config()
    entries: list[dict[str, Any]] = []
    for template_id in supported_template_ids():
        task = TASKS[template_id]
        try:
            params = config.params_for(template_id)
            generated = task.generate(random.Random(0), 1, params)
        except Exception as exc:  # noqa: BLE001 -- re-raised immediately, template id attached
            raise RuntimeError(
                f"C template registry generation failed for template {template_id!r}: {exc}"
            ) from exc
        entries.append(
            {
                "template_id": template_id,
                "valid_action_space": generated.valid_action_space,
            }
        )
    return sorted(entries, key=lambda entry: entry["template_id"])


def _serialize_registry(registry: list[dict[str, Any]]) -> bytes:
    """Deterministic serialization: sorted keys, stable ``(", ", ": ")`` separators (the
    ``json.dumps`` default under ``indent=2``), ASCII-only escaping, an explicit trailing
    newline, returned as raw bytes so no platform newline translation can occur regardless of
    how the caller writes them."""
    text = json.dumps(registry, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    return text.encode("utf-8")


def _serialize_meta(checksum_sha256: str) -> bytes:
    meta = {
        "checksum_sha256": checksum_sha256,
        "contract_version": CONTRACT_VERSION,
        "wheel_version": WHEEL_VERSION,
        "source": SOURCE,
    }
    text = json.dumps(meta, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    return text.encode("utf-8")


def main() -> None:
    """CLI entry point. Deliberately isolated behind ``__main__`` so importing this module (as
    the drift test does, for ``build_registry``) has no side effect -- nothing is written to
    disk merely by importing."""
    registry = build_registry()
    registry_bytes = _serialize_registry(registry)
    checksum = hashlib.sha256(registry_bytes).hexdigest()
    meta_bytes = _serialize_meta(checksum)

    CONTRACT_DIR.mkdir(parents=True, exist_ok=True)
    with open(ARTEFACT_PATH, "wb") as artefact_file:
        artefact_file.write(registry_bytes)
    with open(META_PATH, "wb") as meta_file:
        meta_file.write(meta_bytes)


if __name__ == "__main__":
    main()
