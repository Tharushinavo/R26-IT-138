"""Authoritative Component C game-task catalogue loader (read-only) -- SPEC §7.

Loads the machine-readable ``component_c_game_task_catalogue`` YAML embedded in Appendix M
of the authoritative Markdown catalogue (Phase C2.0) and validates it, failing closed on any
defect. The free-text ``grade_scope_text`` is normalized ONCE here into ``eligible_grades``
via an explicit reviewed mapping (mirrors ``component_b_generator.catalogue.loader``'s SPEC
§7.1 pattern); the runtime never re-parses ``grade_scope_text``.

This module does not modify or rewrite the catalogue. If the catalogue contains a defect
(e.g. duplicate template id, unknown skill, unmapped grade_scope), loading raises
``CatalogueValidationError`` and stops -- it never silently changes authoritative content.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Dict, Tuple

import yaml

from models.contracts import SKILLS as CONTRACT_SKILLS  # single source of truth (7 skills)

from .loaded_models import LoadedCatalogue, LoadedGameFamily, LoadedGameTaskTemplate

# Repo root = Implementation_v1.0/../  (this file: catalogue/loader.py -> parents[3] == Yass/)
_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CATALOGUE_PATH = (
    _REPO_ROOT / "Component_C_v1.0" / "R26-IT-138_Component_C_Game_Task_Catalogue_v1.0.md"
)

SEVEN_SKILLS: Tuple[str, ...] = tuple(CONTRACT_SKILLS)

EXPECTED_FAMILY_IDS: Tuple[str, ...] = tuple(f"C-GF-0{i}" for i in range(1, 9))
EXPECTED_TEMPLATE_COUNT_BY_FAMILY: Dict[str, int] = {
    "C-GF-01": 4, "C-GF-02": 4, "C-GF-03": 4, "C-GF-04": 4,
    "C-GF-05": 4, "C-GF-06": 4, "C-GF-07": 3, "C-GF-08": 3,
}
EXPECTED_TEMPLATE_COUNT = 30

_STATUS_VOCAB = ("BASELINE_ACTIVE", "BASELINE_CONDITIONAL", "DEFERRED_EXTENSION", "RETIRED")
_ROLE_VOCAB = ("MAIN", "SUPPORT", "MAIN_SUPPORT", "RECOVERY_ONLY")

_REQUIRED_TEMPLATE_KEYS = (
    "game_family_id", "family_name", "game_task_template_id", "template_title",
    "primary_skill_ids", "curriculum_node_ids", "grade_scope_text", "status", "status_note",
    "functional_role", "representations", "representations_note", "learner_action",
    "correctness", "error_signatures", "main_difficulty_levers", "recovery",
)

# Explicit, reviewed grade-scope -> normalized grade gate. Keyed by the EXACT Appendix M
# ``grade_scope_text`` strings (en-dash U+2013 preserved). Fails closed on any unmapped value
# so the normalized mapping stays complete and reviewed (mirrors B's SPEC §7.1 pattern).
#
# Interpretation rule applied uniformly (per the C2.1 build brief): wherever ONE grade's
# clause carries a hedge word ("review", "proposal", "pending", "after ... review"), that
# grade is treated as NOT YET eligible (CALIBRATION_PENDING) and excluded from
# ``eligible_grades``; the grade stated without a hedge (a bare number, "baseline",
# "foundation", "minimum", "approved ranges", "intervention scope/extension", "only") is
# eligible now (DERIVED). Where NEITHER grade carries a hedge word, both are eligible
# (DERIVED). This generalizes B's own precedent ("Grade 3; Grade 2 range pending" -> Grade-3
# only, CALIBRATION_PENDING) symmetrically to whichever grade is hedged in the C text.
_GRADE_GATE_MAP: Dict[str, Tuple[Tuple[int, ...], str]] = {
    "Grade 2 baseline; Grade 3 review": ((2,), "CALIBRATION_PENDING"),
    "Grade 2": ((2,), "DERIVED"),
    "Grade 2 foundation; Grade 3 review": ((2,), "CALIBRATION_PENDING"),
    "Grades 2–3": ((2, 3), "DERIVED"),
    "Grade 3": ((3,), "DERIVED"),
    "Grade 3; Grade 2 only after range review": ((3,), "CALIBRATION_PENDING"),
    "Grade 2 1–50 minimum; Grade 3 through approved ranges": ((2, 3), "DERIVED"),
    "Grade 2 intervention scope; Grade 3 review": ((2,), "CALIBRATION_PENDING"),
    "Grade 3 below 1000; Grade 2 small-range proposal": ((3,), "CALIBRATION_PENDING"),
    "Grades 2–3 intervention extension": ((2, 3), "DERIVED"),
    "Grade 3 only": ((3,), "DERIVED"),
}


class CatalogueValidationError(ValueError):
    """Raised when the authoritative catalogue fails a load-time invariant."""


def catalogue_file_checksum(path: Path | str | None = None) -> str:
    """Stable SHA-256 hex digest of the authoritative catalogue file bytes (provenance)."""
    catalogue_path = Path(path) if path is not None else DEFAULT_CATALOGUE_PATH
    if not catalogue_path.exists():
        raise CatalogueValidationError(f"Catalogue file not found: {catalogue_path}")
    return hashlib.sha256(catalogue_path.read_bytes()).hexdigest()


def _extract_catalogue_yaml_block(markdown_text: str) -> str:
    """Return the fenced ```yaml block whose body defines ``component_c_game_task_catalogue``."""
    for match in re.finditer(r"```yaml\s*\n(.*?)\n```", markdown_text, re.DOTALL):
        body = match.group(1)
        if body.lstrip().startswith("component_c_game_task_catalogue:"):
            return body
    raise CatalogueValidationError(
        "Could not find the machine-readable `component_c_game_task_catalogue:` YAML block (Appendix M)."
    )


def normalize_grade_scope(grade_scope_text: str) -> Tuple[Tuple[int, ...], str]:
    """Map an Appendix M ``grade_scope_text`` string to ``(eligible_grades, grade_gate_status)``."""
    key = str(grade_scope_text).strip()
    if key not in _GRADE_GATE_MAP:
        raise CatalogueValidationError(
            f"grade_scope_text {grade_scope_text!r} is not in the reviewed normalized "
            f"grade-gate mapping (SPEC §7.1 pattern). Add an explicit entry after review "
            f"before loading."
        )
    return _GRADE_GATE_MAP[key]


def load_catalogue(path: Path | str | None = None) -> LoadedCatalogue:
    """Load + validate the authoritative catalogue, returning immutable template objects."""
    catalogue_path = Path(path) if path is not None else DEFAULT_CATALOGUE_PATH
    if not catalogue_path.exists():
        raise CatalogueValidationError(f"Catalogue file not found: {catalogue_path}")

    block = _extract_catalogue_yaml_block(catalogue_path.read_text(encoding="utf-8"))
    doc = yaml.safe_load(block)
    root = doc.get("component_c_game_task_catalogue") if isinstance(doc, dict) else None
    if not isinstance(root, dict):
        raise CatalogueValidationError("Top-level `component_c_game_task_catalogue` mapping missing.")

    declared_skills = tuple(root.get("skills") or ())
    if declared_skills != SEVEN_SKILLS:
        raise CatalogueValidationError(
            f"Catalogue `skills` must be exactly the 7 frozen skills {SEVEN_SKILLS}, got {declared_skills}"
        )

    raw_families = root.get("family_id_mapping") or []
    if not isinstance(raw_families, list) or len(raw_families) != 8:
        raise CatalogueValidationError(
            f"Catalogue `family_id_mapping` must list exactly 8 families, got {len(raw_families) if isinstance(raw_families, list) else 'non-list'}"
        )
    families = []
    seen_family_ids: set[str] = set()
    for raw in raw_families:
        family_id = str(raw["game_family_id"])
        if family_id in seen_family_ids:
            raise CatalogueValidationError(f"Duplicate game_family_id in family_id_mapping: {family_id}")
        seen_family_ids.add(family_id)
        families.append(
            LoadedGameFamily(
                game_family_id=family_id,
                family_name=str(raw["family_name"]),
                template_id_prefix=str(raw["template_id_prefix"]),
            )
        )
    if seen_family_ids != set(EXPECTED_FAMILY_IDS):
        raise CatalogueValidationError(
            f"family_id_mapping must be exactly {sorted(EXPECTED_FAMILY_IDS)}, got {sorted(seen_family_ids)}"
        )
    prefix_by_family = {f.game_family_id: f.template_id_prefix for f in families}

    raw_templates = root.get("templates") or []
    if not isinstance(raw_templates, list) or not raw_templates:
        raise CatalogueValidationError("Catalogue `templates` list is empty or malformed.")

    seen_ids: set[str] = set()
    templates = []
    for raw in raw_templates:
        if not isinstance(raw, dict):
            raise CatalogueValidationError(f"template entry is not a mapping: {raw!r}")
        missing = [k for k in _REQUIRED_TEMPLATE_KEYS if k not in raw]
        if missing:
            raise CatalogueValidationError(
                f"template {raw.get('game_task_template_id', '<?>')} missing required fields: {missing}"
            )
        extra = set(raw.keys()) - set(_REQUIRED_TEMPLATE_KEYS)
        if extra:
            raise CatalogueValidationError(
                f"template {raw.get('game_task_template_id', '<?>')} has unrecognized fields: {sorted(extra)}"
            )

        template_id = str(raw["game_task_template_id"])
        if template_id in seen_ids:
            raise CatalogueValidationError(f"Duplicate game_task_template_id: {template_id}")
        seen_ids.add(template_id)

        family_id = str(raw["game_family_id"])
        if family_id not in prefix_by_family:
            raise CatalogueValidationError(f"Template {template_id} references unknown game_family_id {family_id!r}")
        expected_prefix = prefix_by_family[family_id]
        if not template_id.startswith(f"{expected_prefix}-"):
            raise CatalogueValidationError(
                f"Template {template_id} does not match its family's template_id_prefix {expected_prefix!r}"
            )

        primary_skill_ids = tuple(str(s) for s in raw["primary_skill_ids"])
        if not primary_skill_ids:
            raise CatalogueValidationError(f"Template {template_id} has no primary_skill_ids")
        unknown_skills = set(primary_skill_ids) - set(SEVEN_SKILLS)
        if unknown_skills:
            raise CatalogueValidationError(
                f"Template {template_id} has unrecognized skill(s) {sorted(unknown_skills)} "
                f"(must be a subset of the 7 frozen skills)"
            )

        status = str(raw["status"])
        if status not in _STATUS_VOCAB:
            raise CatalogueValidationError(f"Template {template_id} has unrecognized status {status!r}")

        role = str(raw["functional_role"])
        if role not in _ROLE_VOCAB:
            raise CatalogueValidationError(f"Template {template_id} has unrecognized functional_role {role!r}")

        representations = tuple(str(r) for r in raw["representations"])
        if not representations:
            raise CatalogueValidationError(f"Template {template_id} has no representations")
        if len(set(representations)) != len(representations):
            raise CatalogueValidationError(f"Template {template_id} has duplicate representations: {representations}")

        curriculum_node_ids = tuple(str(n) for n in raw["curriculum_node_ids"])
        if not curriculum_node_ids:
            raise CatalogueValidationError(f"Template {template_id} has no curriculum_node_ids")

        error_signatures = raw.get("error_signatures")
        error_signatures_tuple = tuple(str(e) for e in error_signatures) if error_signatures is not None else None

        eligible_grades, gate_status = normalize_grade_scope(str(raw["grade_scope_text"]))

        templates.append(
            LoadedGameTaskTemplate(
                game_family_id=family_id,
                family_name=str(raw["family_name"]),
                game_task_template_id=template_id,
                template_title=str(raw["template_title"]),
                primary_skill_ids=primary_skill_ids,
                curriculum_node_ids=curriculum_node_ids,
                grade_scope_text=str(raw["grade_scope_text"]),
                status=status,  # type: ignore[arg-type]
                status_note=raw.get("status_note"),
                functional_role=role,  # type: ignore[arg-type]
                representations=representations,
                representations_note=raw.get("representations_note"),
                learner_action=str(raw["learner_action"]),
                correctness=str(raw["correctness"]),
                error_signatures=error_signatures_tuple,
                main_difficulty_levers=str(raw["main_difficulty_levers"]),
                recovery=str(raw["recovery"]),
                eligible_grades=eligible_grades,
                grade_gate_status=gate_status,
            )
        )

    if len(templates) != EXPECTED_TEMPLATE_COUNT:
        raise CatalogueValidationError(
            f"Catalogue must declare exactly {EXPECTED_TEMPLATE_COUNT} templates, got {len(templates)}"
        )
    counts: Dict[str, int] = {}
    for t in templates:
        counts[t.game_family_id] = counts.get(t.game_family_id, 0) + 1
    if counts != EXPECTED_TEMPLATE_COUNT_BY_FAMILY:
        raise CatalogueValidationError(
            f"Per-family template counts must be {EXPECTED_TEMPLATE_COUNT_BY_FAMILY}, got {counts}"
        )

    # Every one of the 7 skills must be represented by at least one template (mirrors B).
    covered = {s for t in templates for s in t.primary_skill_ids}
    if covered != set(SEVEN_SKILLS):
        raise CatalogueValidationError(f"Templates do not cover all 7 skills; missing {set(SEVEN_SKILLS) - covered}")

    return LoadedCatalogue(
        catalogue_version=str(root.get("version", "unknown")),
        catalogue_status=str(root.get("status", "unknown")),
        source_path=str(catalogue_path),
        skills=SEVEN_SKILLS,
        families=tuple(sorted(families, key=lambda f: f.game_family_id)),
        templates=tuple(sorted(templates, key=lambda t: t.game_task_template_id)),
    )
