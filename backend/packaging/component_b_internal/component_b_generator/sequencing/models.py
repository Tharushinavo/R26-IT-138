"""Adaptive-sequencing candidate model (Phase B4.0).

``SequencingCandidate`` is the shape of one eligible node/template candidate considered by later
sequencing slices (B4.1 eligibility, B4.2 features, B4.3 scoring/selection). This slice defines
the shape only — no eligibility, feature, or scoring logic.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from models.contracts import SKILLS

_SEVEN_SKILLS = frozenset(SKILLS)


class SequencingCandidate(BaseModel):
    """One eligible sequencing candidate: a template within a skill, with a sequencing-only
    difficulty/ordering hint.

    ``difficulty_band`` is a sequencing/ordering-only concept (in-skill band or rank) — it is
    never a correctness parent and never influences item-response probability. Carries no
    ``population``/``dd_subtype``, no correctness fields, and no Component-C/Component-3 field
    (``extra="forbid"``).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    skill_id: str
    item_template_id: str
    difficulty_band: int

    @field_validator("skill_id")
    @classmethod
    def _valid_skill(cls, v: str) -> str:
        if v not in _SEVEN_SKILLS:
            raise ValueError(f"skill_id must be one of the seven frozen skills {tuple(SKILLS)}, got {v!r}")
        return v

    @field_validator("item_template_id")
    @classmethod
    def _non_empty_template_id(cls, v: str) -> str:
        if not str(v).strip():
            raise ValueError("item_template_id must be non-empty")
        return v
