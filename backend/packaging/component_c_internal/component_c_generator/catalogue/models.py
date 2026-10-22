"""Typed catalogue MODELS only (Game-Task Catalogue §2.3, §12).

No loader, no eligibility filtering, no task-instance generation, no evaluator -- those are
Phase C2 (SPEC §5/§4 phase map). These structs are the typed shape the C2 loader will
populate from the authoritative catalogue source; Phase C1 defines the shape only.
"""

from __future__ import annotations

from typing import Annotated, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from models.contracts import SKILLS

from ..models.enums import FunctionalRole, ScaffoldLevel, TemplateStatus

_SEVEN_SKILLS = frozenset(SKILLS)
_GRADES = frozenset({2, 3})


class GameFamily(BaseModel):
    """One reusable interaction mechanic (Game-Task Catalogue §1.4, §2.3, §3).

    Baseline scope is 8 families / 30 templates (Catalogue §1.4); ``template_count`` is a
    structural field the C2 loader populates from the templates it actually loads -- not a
    hardcoded scientific value here.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    game_family_id: str
    family_name: str
    main_skills: Tuple[str, ...]
    template_count: Annotated[int, Field(ge=0)]

    @field_validator("game_family_id", "family_name")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not str(v).strip():
            raise ValueError("game_family_id / family_name must be non-empty")
        return v

    @field_validator("main_skills")
    @classmethod
    def _known_skills(cls, v: Tuple[str, ...]) -> Tuple[str, ...]:
        if not v:
            raise ValueError("main_skills must be non-empty")
        unknown = set(v) - _SEVEN_SKILLS
        if unknown:
            raise ValueError(f"main_skills must be among the seven frozen skills; unknown={sorted(unknown)}")
        return v


class GameTaskTemplate(BaseModel):
    """One reviewed curriculum/mechanic definition (Game-Task Catalogue §12 field groups).

    Field groups mirror the catalogue's own §12.1-§12.5 structure exactly (identity and
    governance; curriculum alignment; mathematical definition; gameplay and adaptation;
    telemetry and accessibility) so this struct needs no re-derivation when the C2 loader is
    built. A ``game_task_template_id`` must never be reused as a generated task-instance id
    (Catalogue §3) -- instance ids are a C2/C3 concern, out of scope here.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # §12.1 Identity and governance
    game_family_id: str
    game_task_template_id: str
    template_version: str
    catalogue_version: str
    template_status: TemplateStatus
    component_owner: str
    title: str
    description: str
    source_references: Tuple[str, ...] = ()
    approval_status: str
    active_flag: bool

    # §12.2 Curriculum alignment
    primary_skill_id: str
    curriculum_node_ids: Tuple[str, ...]
    prerequisite_node_ids: Tuple[str, ...] = ()
    grade_scope: Tuple[int, ...]
    number_range_scope: str
    curriculum_status: str
    calibration_notes: str = ""

    # §12.3 Mathematical definition
    mathematical_construct: str
    input_representation: str
    target_representation: str
    generator_constraints: str
    correctness_function: str
    completion_condition: str
    invalid_case_exclusions: str
    error_signatures: Tuple[str, ...] = ()

    # §12.4 Gameplay and adaptation
    core_mechanic: str
    valid_action_space: str
    retry_policy: str
    skip_policy: str
    pause_policy: str
    feedback_rule: str
    functional_role: FunctionalRole
    difficulty_dimensions: Tuple[str, ...]
    difficulty_level_map: dict[str, str]
    allowed_scaffold_levels: Tuple[ScaffoldLevel, ...]
    recovery_template_or_config: Optional[str] = None
    safety_behavior: str

    # §12.5 Telemetry and accessibility
    telemetry_events: Tuple[str, ...]
    latency_start_event: str
    latency_end_event: str
    motor_error_measure: Optional[str] = None
    technical_failure_rule: str
    drag_alternative: bool
    audio_available: bool
    text_available: bool
    color_independent_encoding: bool
    reduced_motion_support: bool
    timing_adjustable: bool
    target_size_check: bool

    @field_validator("component_owner")
    @classmethod
    def _component_owner_is_c(cls, v: str) -> str:
        if v != "C":
            raise ValueError("component_owner must be 'C' (Catalogue §12.1)")
        return v

    @field_validator("game_family_id", "game_task_template_id")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not str(v).strip():
            raise ValueError("game_family_id / game_task_template_id must be non-empty")
        return v

    @field_validator("primary_skill_id")
    @classmethod
    def _known_primary_skill(cls, v: str) -> str:
        if v not in _SEVEN_SKILLS:
            raise ValueError(f"primary_skill_id must be one of the seven frozen skills, got {v!r}")
        return v

    @field_validator("grade_scope")
    @classmethod
    def _known_grades(cls, v: Tuple[int, ...]) -> Tuple[int, ...]:
        if not v:
            raise ValueError("grade_scope must be non-empty")
        unknown = set(v) - _GRADES
        if unknown:
            raise ValueError(f"grade_scope must be a subset of {{2, 3}}; unknown={sorted(unknown)}")
        return v

    @field_validator("allowed_scaffold_levels")
    @classmethod
    def _non_empty_scaffolds(cls, v: Tuple[str, ...]) -> Tuple[str, ...]:
        if not v:
            raise ValueError("allowed_scaffold_levels must be non-empty (Catalogue §2.4)")
        return v

    @model_validator(mode="after")
    def _fail_closed_lifecycle(self) -> "GameTaskTemplate":
        # Catalogue §2.2/§14.1: RETIRED must never be generated; DEFERRED_EXTENSION is not
        # used in baseline v1 -- both fail closed regardless of a mismatched active_flag.
        if self.template_status in ("RETIRED", "DEFERRED_EXTENSION") and self.active_flag:
            raise ValueError(
                f"Catalogue §2.2: a template with template_status={self.template_status!r} "
                "must have active_flag=False (fail-closed)"
            )
        return self
