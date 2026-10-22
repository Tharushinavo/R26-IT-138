"""Typed records for the LOADED Appendix M catalogue (Phase C2.1).

These are distinct from ``component_c_generator.catalogue.models.GameFamily`` /
``GameTaskTemplate`` (Phase C1): those model the richer, aspirational Section 12 field
groups the catalogue *document* describes narratively but does not actually populate
per-template. Appendix M (Phase C2.0) transcribes only the fields genuinely present in the
Section 5 tables. Rather than force-fit the loader's real output into C1's richer shape
(which would require inventing ~25 field values that do not exist in the source -- exactly
what this phase must not do), this module defines a loader-native ``LoadedGameTaskTemplate``
/ ``LoadedCatalogue`` pair that matches Appendix M's actual schema, mirroring
``component_b_generator.models.catalogue.ItemTemplate`` / ``LoadedCatalogue``. C1's
``catalogue/models.py`` is left untouched and unused by this loader; reconciling the two
shapes (or retiring the unused one) is an owner decision flagged in the Phase C2.1 build
report, not silently resolved here.
"""

from __future__ import annotations

from typing import Optional, Tuple

from pydantic import BaseModel, ConfigDict

from models.contracts import SKILLS

from ..models.enums import FunctionalRole, TemplateStatus

SEVEN_SKILLS = frozenset(SKILLS)


class LoadedGameTaskTemplate(BaseModel):
    """One template exactly as transcribed in Appendix M (Phase C2.0) -- read-only.

    ``eligible_grades`` / ``grade_gate_status`` are the NORMALIZED grade gate, derived once
    at load time from ``grade_scope_text`` via the reviewed ``_GRADE_GATE_MAP`` (mirrors B's
    SPEC §7.1 pattern); the runtime never re-parses ``grade_scope_text``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    game_family_id: str
    family_name: str
    game_task_template_id: str
    template_title: str
    primary_skill_ids: Tuple[str, ...]
    curriculum_node_ids: Tuple[str, ...]
    grade_scope_text: str
    status: TemplateStatus
    status_note: Optional[str]
    functional_role: FunctionalRole
    representations: Tuple[str, ...]
    representations_note: Optional[str]
    learner_action: str
    correctness: str
    error_signatures: Optional[Tuple[str, ...]]
    main_difficulty_levers: str
    recovery: str

    # Normalized grade gate (derived at load; mirrors B SPEC §7.1)
    eligible_grades: Tuple[int, ...]
    grade_gate_status: str  # "DERIVED" or "CALIBRATION_PENDING"

    def is_eligible_for_grade(self, grade: int) -> bool:
        return grade in self.eligible_grades

    def is_active(self) -> bool:
        # Fail-closed lifecycle (Catalogue §2.2/§14.1): only BASELINE_ACTIVE and
        # BASELINE_CONDITIONAL templates are ever runtime-eligible; DEFERRED_EXTENSION and
        # RETIRED are never generated regardless of grade eligibility.
        return self.status in ("BASELINE_ACTIVE", "BASELINE_CONDITIONAL")


class LoadedGameFamily(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    game_family_id: str
    family_name: str
    template_id_prefix: str


class LoadedCatalogue(BaseModel):
    """Result of loading + validating Appendix M (read-only)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    catalogue_version: str
    catalogue_status: str
    source_path: str
    skills: Tuple[str, ...]
    families: Tuple[LoadedGameFamily, ...]
    templates: Tuple[LoadedGameTaskTemplate, ...]

    def by_id(self, template_id: str) -> Optional[LoadedGameTaskTemplate]:
        for t in self.templates:
            if t.game_task_template_id == template_id:
                return t
        return None

    def eligible_for(self, grade: int, skill_id: Optional[str] = None) -> Tuple[LoadedGameTaskTemplate, ...]:
        """Grade-gated candidate set (the ONLY hard eligibility filter, mirrors B SPEC §7.2).

        Deterministic order (sorted by template id) so selection never depends on unordered
        iteration. Optionally narrowed to one ``skill_id``.
        """
        out = [
            t
            for t in self.templates
            if t.is_active()
            and t.is_eligible_for_grade(grade)
            and (skill_id is None or skill_id in t.primary_skill_ids)
        ]
        return tuple(sorted(out, key=lambda t: t.game_task_template_id))
