"""Authoritative Component B item-catalogue loader (read-only) — SPEC §6.1, §7.

Loads the machine-readable ``component_b_item_catalogue`` YAML embedded in §11 of the
authoritative Markdown catalogue and validates it, failing closed on any defect. The
free-text ``grade_scope`` is normalized ONCE here into ``eligible_grades`` via an explicit
reviewed mapping (SPEC §7.1); the runtime never parses ``grade_scope``.

This module does not modify or rewrite the catalogue. If the catalogue contains a defect
(e.g. duplicate template id, unknown skill, unmapped grade_scope), loading raises
``CatalogueValidationError`` and stops — it never silently changes authoritative content.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Dict, Tuple

import yaml

from models.contracts import SKILLS as CONTRACT_SKILLS  # single source of truth (7 skills)

from ..models.catalogue import ItemTemplate, LoadedCatalogue

# Repo root = Implementation_v1.0/../  (this file: catalogue/loader.py -> parents[3] == Yass/)
_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CATALOGUE_PATH = (
    _REPO_ROOT / "Component_B_v1.0" / "R26-IT-138_Component_B_Item_and_Task_Set_Catalogue_v1.0.md"
)

SEVEN_SKILLS: Tuple[str, ...] = tuple(CONTRACT_SKILLS)

_REQUIRED_TEMPLATE_KEYS = (
    "item_template_id",
    "set_id",
    "skill_id",
    "curriculum_node_id",
    "node_name",
    "grade_scope",
    "difficulty_level",
    "task_type",
    "representation_type",
    "status",
)

# Explicit, reviewed grade-scope -> normalized grade gate (SPEC §7.1). Keyed by the EXACT
# catalogue ``grade_scope`` strings (en-dash U+2013 preserved). Fails closed on any unmapped
# value so the normalized mapping stays complete and reviewed.
_GRADE_GATE_MAP: Dict[str, Tuple[Tuple[int, ...], str]] = {
    "Grade 2": ((2,), "DERIVED"),
    "Grade 2 foundation": ((2,), "DERIVED"),
    "Grade 2 intervention scope": ((2,), "DERIVED"),
    "Grade 2: 1–50; Grade 3: 1–999": ((2, 3), "DERIVED"),
    "Grade 3": ((3,), "DERIVED"),
    "Grade 3 extension": ((3,), "DERIVED"),
    # Ambiguous Grade-2 range -> Grade 3 only until resolved (SPEC §7.2).
    "Grade 3; Grade 2 range pending": ((3,), "CALIBRATION_PENDING"),
    "Grades 2–3": ((2, 3), "DERIVED"),
    "Grades 2–3 intervention extension": ((2, 3), "DERIVED"),
}


class CatalogueValidationError(ValueError):
    """Raised when the authoritative catalogue fails a load-time invariant."""


def catalogue_file_checksum(path: Path | str | None = None) -> str:
    """Stable SHA-256 hex digest of the authoritative catalogue file bytes (provenance).

    Read-only: never mutates the catalogue. Recorded in the Phase-B2A run manifest so an
    instance batch is traceable to the exact catalogue content it was generated from.
    """
    catalogue_path = Path(path) if path is not None else DEFAULT_CATALOGUE_PATH
    if not catalogue_path.exists():
        raise CatalogueValidationError(f"Catalogue file not found: {catalogue_path}")
    return hashlib.sha256(catalogue_path.read_bytes()).hexdigest()


def _extract_catalogue_yaml_block(markdown_text: str) -> str:
    """Return the fenced ```yaml block whose body defines ``component_b_item_catalogue``."""
    for match in re.finditer(r"```yaml\s*\n(.*?)\n```", markdown_text, re.DOTALL):
        body = match.group(1)
        if body.lstrip().startswith("component_b_item_catalogue:"):
            return body
    raise CatalogueValidationError(
        "Could not find the machine-readable `component_b_item_catalogue:` YAML block (§11)."
    )


def normalize_grade_scope(grade_scope_text: str) -> Tuple[Tuple[int, ...], str]:
    """Map a catalogue ``grade_scope`` string to ``(eligible_grades, grade_gate_status)``."""
    key = str(grade_scope_text).strip()
    if key not in _GRADE_GATE_MAP:
        raise CatalogueValidationError(
            f"grade_scope {grade_scope_text!r} is not in the reviewed normalized grade-gate "
            f"mapping (SPEC §7.1). Add an explicit entry after review before loading."
        )
    return _GRADE_GATE_MAP[key]


def load_catalogue(path: Path | str | None = None) -> LoadedCatalogue:
    """Load + validate the authoritative catalogue, returning immutable template objects."""
    catalogue_path = Path(path) if path is not None else DEFAULT_CATALOGUE_PATH
    if not catalogue_path.exists():
        raise CatalogueValidationError(f"Catalogue file not found: {catalogue_path}")

    block = _extract_catalogue_yaml_block(catalogue_path.read_text(encoding="utf-8"))
    doc = yaml.safe_load(block)
    root = doc.get("component_b_item_catalogue") if isinstance(doc, dict) else None
    if not isinstance(root, dict):
        raise CatalogueValidationError("Top-level `component_b_item_catalogue` mapping missing.")

    # Top-level: the catalogue's declared skill vocabulary must be exactly the 7 frozen skills.
    declared_skills = tuple(root.get("skills") or ())
    if tuple(declared_skills) != SEVEN_SKILLS:
        raise CatalogueValidationError(
            f"Catalogue `skills` must be exactly the 7 frozen skills {SEVEN_SKILLS}, got {declared_skills}"
        )

    item_sets = root.get("item_sets") or []
    if not isinstance(item_sets, list) or not item_sets:
        raise CatalogueValidationError("Catalogue `item_sets` list is empty or malformed.")

    seen_ids: set[str] = set()
    templates = []
    for raw in item_sets:
        if not isinstance(raw, dict):
            raise CatalogueValidationError(f"item_set entry is not a mapping: {raw!r}")
        missing = [k for k in _REQUIRED_TEMPLATE_KEYS if k not in raw or raw[k] in (None, "")]
        if missing:
            raise CatalogueValidationError(
                f"item_set {raw.get('item_template_id', '<?>')} missing required fields: {missing}"
            )

        template_id = str(raw["item_template_id"])
        if template_id in seen_ids:
            raise CatalogueValidationError(f"Duplicate item_template_id: {template_id}")
        seen_ids.add(template_id)

        skill_id = str(raw["skill_id"])
        if skill_id not in SEVEN_SKILLS:
            raise CatalogueValidationError(
                f"Template {template_id} has unrecognized skill_id {skill_id!r} (must be one of the 7 frozen skills)"
            )

        eligible_grades, gate_status = normalize_grade_scope(str(raw["grade_scope"]))
        status_raw = str(raw["status"])
        evidence_status = status_raw.split(";", 1)[0].strip()

        prereq = raw.get("prerequisite_nodes") or []
        prereq_tuple = tuple(str(p) for p in prereq) if isinstance(prereq, list) else ()

        # Additive (Phase B2B.3.1): read-only, optional L1/L2/L3 hint text. Not required at load
        # time (backward-compatible) — fail-closed on missing/blank content happens only when a
        # caller actually requests a hint, in ``behaviour.hints.get_catalogue_hint``.
        hint_level_1 = raw.get("hint_level_1")
        hint_level_2 = raw.get("hint_level_2")
        hint_level_3 = raw.get("hint_level_3")

        templates.append(
            ItemTemplate(
                item_template_id=template_id,
                set_id=str(raw["set_id"]),
                skill_id=skill_id,
                curriculum_node_id=str(raw["curriculum_node_id"]),
                node_name=str(raw["node_name"]),
                difficulty_level=str(raw["difficulty_level"]),
                task_type=str(raw["task_type"]),
                representation_type=str(raw["representation_type"]),
                status_raw=status_raw,
                evidence_status=evidence_status,
                prerequisite_nodes=prereq_tuple,
                eligible_grades=eligible_grades,
                grade_gate_status=gate_status,  # type: ignore[arg-type]
                source_grade_scope_text=str(raw["grade_scope"]),
                hint_level_1=str(hint_level_1) if hint_level_1 is not None else None,
                hint_level_2=str(hint_level_2) if hint_level_2 is not None else None,
                hint_level_3=str(hint_level_3) if hint_level_3 is not None else None,
            )
        )

    # Every one of the 7 skills must be represented by at least one template.
    covered = {t.skill_id for t in templates}
    if covered != set(SEVEN_SKILLS):
        raise CatalogueValidationError(f"Templates do not cover all 7 skills; missing {set(SEVEN_SKILLS) - covered}")

    return LoadedCatalogue(
        catalogue_version=str(root.get("version", "unknown")),
        catalogue_status=str(root.get("status", "unknown")),
        source_path=str(catalogue_path),
        skills=SEVEN_SKILLS,
        templates=tuple(sorted(templates, key=lambda t: t.item_template_id)),
    )
