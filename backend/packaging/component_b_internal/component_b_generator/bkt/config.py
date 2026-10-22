"""Population-neutral BKT configuration (Phase B3.0, SPEC §C.3).

``BBKTConfig`` holds **skill-keyed** ``P(L0)/P(T)/P(G)/P(S)`` for all seven frozen skills, a
global ``theta_B`` certification threshold, and floor policy for the Guess-Guard (B3.3). There is
no population axis anywhere: the config is keyed by skill only, and any ``population`` /
``dd_subtype`` / ``item_difficulty`` / sequencing / Component-C/3 field is rejected
(ownership-scoped ``extra="forbid"``, SPEC §F row "B3"). No numeric value has a production
default — every scientific value is supplied explicitly by the caller (tests may use
``TEST_FIXTURE_ONLY``; production callers record ``CALIBRATION_PENDING`` until sign-off).
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from models.contracts import SKILLS

B3_VERSION = "b3-1.0.0"

Probability = Annotated[float, Field(ge=0.0, le=1.0)]

_SEVEN_SKILLS = frozenset(SKILLS)


class SkillBKTParams(BaseModel):
    """One skill's BKT parameters: ``P(L0)``, ``P(T)``, ``P(G)``, ``P(S)``.

    Structural constraints (FROZEN, SPEC §5.7/§C.3): ``P(G) + P(S) < 1`` and ``P(G) <= 0.5``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    p_l0: Probability
    p_t: Probability
    p_g: Probability
    p_s: Probability

    @model_validator(mode="after")
    def _structural_constraints(self) -> "SkillBKTParams":
        if not (self.p_g + self.p_s < 1.0):
            raise ValueError("FROZEN constraint violated: P(G) + P(S) must be < 1")
        if not (self.p_g <= 0.5):
            raise ValueError("FROZEN constraint violated: P(G) must be <= 0.5")
        return self


class BBKTConfig(BaseModel):
    """Population-neutral BKT configuration (Phase B3.0).

    Skill-keyed BKT parameters for all seven frozen skills, plus the global certification
    threshold ``theta_B`` and Guess-Guard floor policy. ``extra="forbid"`` rejects any field
    outside B3's ownership, including ``population``, ``dd_subtype``, ``item_difficulty``, and
    any sequencing / Component-C / Component-3 field.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    skill_params: dict[str, SkillBKTParams]

    theta_B: Annotated[float, Field(gt=0.0, lt=1.0)]

    floor_quantile: Annotated[float, Field(gt=0.0, lt=1.0)]
    floor_min_obs: Annotated[int, Field(ge=1)]

    config_version: str
    parameter_source_status: str  # e.g. "CALIBRATION_PENDING" or a clearly-named test fixture tag

    @field_validator("config_version", "parameter_source_status")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not str(v).strip():
            raise ValueError("version / source-status strings must be non-empty")
        return v

    @field_validator("skill_params")
    @classmethod
    def _exactly_seven_skills(cls, v: dict[str, SkillBKTParams]) -> dict[str, SkillBKTParams]:
        keys = set(v.keys())
        if keys != _SEVEN_SKILLS:
            missing = _SEVEN_SKILLS - keys
            extra = keys - _SEVEN_SKILLS
            raise ValueError(
                f"skill_params must contain exactly the seven frozen skills {tuple(SKILLS)}; "
                f"missing={sorted(missing)} extra={sorted(extra)}"
            )
        return v
