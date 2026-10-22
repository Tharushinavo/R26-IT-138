"""``GameTaskInstance`` (SPEC §6.3) and ``EvaluationResult`` (Phase C2.1).

``GameTaskInstance`` carries the mathematical truth of one generated task; learner behaviour
must never alter it (SPEC §6.3 header note). Fields not yet owned by this phase (scaffolding,
recovery routing, technical-status transitions beyond generation itself) carry the documented
C2.1 baseline value -- they are C4/C3 concerns, not invented content.
"""

from __future__ import annotations

import re
from typing import Any, Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict, field_validator

from models.contracts import CSessionId, StudentId

from .enums import FunctionalRole, ScaffoldLevel
from .seed import CSeedLineage

# game_task_instance_id: <c_session_id>-T<task_index>-X001  (one instance per task opportunity in v1)
GAME_TASK_INSTANCE_ID_RE = re.compile(r"^STU-[0-9]{4}-C-[0-9]{3}-T[0-9]{3}-X[0-9]{3}$")

GradeScope = Literal[2, 3]
TechnicalStatus = Literal["OK", "FAILED"]


class GameTaskInstance(BaseModel):
    """One deterministic, playable Component C task instance (SPEC §6.3)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    # --- catalogue linkage ---
    game_family_id: str
    game_task_template_id: str
    game_task_instance_id: str
    template_version: str
    catalogue_version: str
    generator_version: str
    seed_lineage: CSeedLineage

    # --- identity ---
    student_id: StudentId
    c_session_id: CSessionId
    task_index: int

    # --- curriculum linkage ---
    skill_id: str
    curriculum_node_id: str
    grade_scope: GradeScope
    difficulty_level: int
    difficulty_vector: dict[str, Any]
    functional_role: FunctionalRole
    representation_mode: str

    # --- generated mathematical content ---
    prompt_payload: dict[str, Any]
    interactive_assets: dict[str, Any]
    correct_answer_payload: dict[str, Any]
    correctness_function_id: str
    valid_action_space: dict[str, Any]
    completion_condition: str
    failure_condition: str

    # --- C4/C3 state, baseline-only in C2.1 ---
    scaffold_state: ScaffoldLevel
    recovery_parent_instance_id: Optional[str] = None
    technical_status: TechnicalStatus

    @field_validator("game_task_instance_id")
    @classmethod
    def _id_format(cls, v: str) -> str:
        if not GAME_TASK_INSTANCE_ID_RE.match(v):
            raise ValueError(f"game_task_instance_id must match {GAME_TASK_INSTANCE_ID_RE.pattern}, got {v!r}")
        return v

    @field_validator("task_index")
    @classmethod
    def _task_index_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("task_index must be >= 1")
        return v

    @field_validator("difficulty_level")
    @classmethod
    def _difficulty_level_range(cls, v: int) -> int:
        if not (1 <= v <= 5):
            raise ValueError("difficulty_level must be in 1..5 (Catalogue §6)")
        return v


class EvaluationResult(BaseModel):
    """Pure output of ``evaluation.evaluate`` (Phase C2.1, SPEC §11).

    Carries only what was actually evaluated: the instance/template identity, the learner
    action as submitted, and the correctness verdict. No population, mastery, latent state,
    policy, or future information is ever read to produce this -- see ``evaluation.evaluate``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    game_task_instance_id: str
    game_task_template_id: str
    correctness_function_id: str
    learner_action: dict[str, Any]
    is_correct: bool
    details: dict[str, Any] = {}
