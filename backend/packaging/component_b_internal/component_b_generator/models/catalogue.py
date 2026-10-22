"""Immutable item-catalogue template reference + normalized grade gate (SPEC §6.1, §7)."""

from __future__ import annotations

from typing import Optional, Tuple

from pydantic import BaseModel, ConfigDict

from .enums import CalibrationStatus, Grade


class ItemTemplate(BaseModel):
    """One immutable Component B item template, loaded read-only from the authoritative
    §11 catalogue YAML. Field subset used by Phase B1 plus provenance.

    ``eligible_grades`` is the **normalized** grade gate derived once at load time from the
    catalogue's free-text ``grade_scope`` (SPEC §7.1); the runtime never parses
    ``grade_scope`` (kept only as ``source_grade_scope_text`` provenance).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    item_template_id: str
    set_id: str
    skill_id: str
    curriculum_node_id: str
    node_name: str
    difficulty_level: str
    task_type: str
    representation_type: str
    # The B catalogue's per-template status is a free-text evidence+calibration string
    # (e.g. "OFFICIAL_CURRICULUM; catalogue thresholds/ranges: PROJECT_PROPOSAL + ...").
    # Stored verbatim as provenance; ``evidence_status`` is the leading tag.
    status_raw: str
    evidence_status: str
    prerequisite_nodes: Tuple[str, ...] = ()

    # Normalized grade gate (derived at load; SPEC §7.1)
    eligible_grades: Tuple[int, ...]
    grade_gate_status: CalibrationStatus
    source_grade_scope_text: str  # provenance only, never parsed at runtime

    # Additive (Phase B2B.3.1): catalogue-authored L1/L2/L3 hint text, parsed read-only from the
    # same §11 item_set entry. Optional so existing callers/fixtures that construct an
    # ``ItemTemplate`` without hint content remain valid (backward-compatible). Fail-closed
    # behaviour on missing/blank content lives in ``behaviour.hints.get_catalogue_hint``, not here.
    hint_level_1: Optional[str] = None
    hint_level_2: Optional[str] = None
    hint_level_3: Optional[str] = None

    def is_eligible_for_grade(self, grade: Grade) -> bool:
        return grade in self.eligible_grades

    def is_active(self) -> bool:
        # Activation is decided from the authoritative *leading* status tag (``evidence_status``,
        # the segment before the first ';' — see catalogue/loader.py), NOT from a substring scan of
        # the whole free-text status. A template is inactive only when its leading lifecycle tag is
        # a retired/deferred marker. This is exact/leading-anchored so descriptive tail prose (e.g.
        # B-DIV01's "recipients 5 and 10 deferred …") can never falsely deactivate a live template.
        tag = self.evidence_status.strip().upper()
        return not (tag.startswith("RETIRED") or tag.startswith("DEFERRED"))


class LoadedCatalogue(BaseModel):
    """Result of loading + validating the authoritative catalogue (read-only)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    catalogue_version: str
    catalogue_status: str
    source_path: str
    skills: Tuple[str, ...]
    templates: Tuple[ItemTemplate, ...]

    def by_id(self, template_id: str) -> Optional[ItemTemplate]:
        for t in self.templates:
            if t.item_template_id == template_id:
                return t
        return None

    def eligible_for(self, grade: Grade, skill_id: Optional[str] = None) -> Tuple[ItemTemplate, ...]:
        """Grade-gated candidate set (the ONLY hard eligibility filter, SPEC §7.2).

        Deterministic order (sorted by template id) so selection never depends on unordered
        iteration. Optionally narrowed to one ``skill_id``.
        """
        out = [
            t
            for t in self.templates
            if t.is_active() and t.is_eligible_for_grade(grade) and (skill_id is None or t.skill_id == skill_id)
        ]
        return tuple(sorted(out, key=lambda t: t.item_template_id))
