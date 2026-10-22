"""``CLocalLearnerState`` (SPEC §6.2) -- C-owned persistent hidden state.

Internal only (SF-041: Component C owns its own hidden state and equations, never reading
B's beyond the consumed mastery edge). ``extra="forbid"`` plus the deliberate omission of
any ``mastery_*`` / B-shaped field is the structural guarantee that this model **cannot**
carry cached B mastery (SF-043: no cache/carry-forward of the B payload) -- there is no
runtime scan needed because no such field is declared, and any attempt to add one is
rejected as an unknown field.
"""

from __future__ import annotations

from typing import Annotated, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models.contracts import SKILLS, Probability

from .enums import LearnerState

_SEVEN_SKILLS = frozenset(SKILLS)

DifficultyLevel = Annotated[int, Field(ge=1, le=5)]


class CLocalLearnerState(BaseModel):
    """C-local persistent learner state carried session-to-session (SPEC §6.2).

    Latent-trait fields (``c_game_fluency_baseline``, ``c_persistence_tendency``,
    ``c_challenge_tolerance``, ``c_engagement_propensity``) are population-neutral C-local
    roots (SPEC §12.1); their sampled *values* are a later-phase (C4+) concern -- this model
    only carries the typed slot. No numeric default is supplied by this model.
    """

    model_config = ConfigDict(extra="forbid")

    c_game_fluency_baseline: float
    c_persistence_tendency: float
    c_challenge_tolerance: float
    c_engagement_propensity: Probability

    difficulty_by_skill: dict[str, DifficultyLevel]

    recent_template_exposure: Tuple[str, ...] = ()
    recent_family_exposure: Tuple[str, ...] = ()
    recent_representation_exposure: Tuple[str, ...] = ()
    recent_success_window: Tuple[bool, ...] = ()
    recent_strain_window: Tuple[float, ...] = ()

    last_complete_learner_state: LearnerState | None = None
    last_complete_frustration_index: Probability | None = None

    safety_increase_block_counter: Annotated[int, Field(ge=0)] = 0

    seed_version: str
    config_version: str
    catalogue_version: str
    state_checksum: str

    @field_validator("difficulty_by_skill")
    @classmethod
    def _difficulty_by_skill_uses_known_skills(cls, v: dict[str, int]) -> dict[str, int]:
        unknown = set(v.keys()) - _SEVEN_SKILLS
        if unknown:
            raise ValueError(f"difficulty_by_skill keys must be among the seven frozen skills; unknown={sorted(unknown)}")
        return v

    @field_validator("seed_version", "config_version", "catalogue_version", "state_checksum")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not str(v).strip():
            raise ValueError("version / checksum strings must be non-empty")
        return v
