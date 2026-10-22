"""Immutable per-skill BKT mastery state (Phase B3.0).

``BBKTSkillState`` is the estimator-side mastery record: it is always an *estimate*, never the
hidden simulation truth, and carries no population axis.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models.contracts import SKILLS

_SEVEN_SKILLS = frozenset(SKILLS)


class BBKTSkillState(BaseModel):
    """One learner's current BKT mastery estimate for one skill.

    ``p_l`` is the current posterior mastery estimate ``p(L)`` in ``[0, 1]`` — an estimate, never
    the hidden simulation truth. ``observation_count`` is the number of first-attempt
    observations folded into this estimate so far.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    student_id: str
    skill_id: str
    p_l: Annotated[float, Field(ge=0.0, le=1.0)]
    observation_count: Annotated[int, Field(ge=0)]

    @field_validator("skill_id")
    @classmethod
    def _valid_skill(cls, v: str) -> str:
        if v not in _SEVEN_SKILLS:
            raise ValueError(f"skill_id must be one of the seven frozen skills {tuple(SKILLS)}, got {v!r}")
        return v
