"""``CSelectionConfig`` (Phase C4.0) -- versioned, no-defaults selection configuration.

The cold-start assessment's familiarization window ``W`` is explicitly
``ENGINEERING_ASSUMPTION + CALIBRATION_PENDING`` (assessment §5.5), subject to the feasibility
constraint ``W * min_guaranteed_bootstrap_opportunities_per_eligible_combined_session >= K *
grade_valid_skill_count`` (K=2 first-attempt observations per skill). The assessment's own
worked example resolves this to **grade-specific** provisional values: Grade 2 (5 skills):
``ceil(10/6) = 2``; Grade 3 (7 skills): ``ceil(14/6) = 3``. Those two integers
(``familiarization_window_by_grade = {2: 2, 3: 3}``) are the ONLY values transcribed here from
the assessment's own worked arithmetic -- not newly invented. Every value in this module is
tagged ``parameter_source_status = "TEST_FIXTURE_ONLY"``; the authoritative K, minimum
bootstrap-opportunity count, and therefore the final W remain CALIBRATION_PENDING pending the
B-side bootstrap coverage override (assessment §5.4, a separate B-internal patch) and Component
C Parameters sign-off. Nothing here is written to any governance document.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SELECTION_CONFIG_VERSION = "c4.0-selection-1.0.0"


class CSelectionConfig(BaseModel):
    """Versioned, no-defaults Phase C4.0 selection configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    config_version: str
    parameter_source_status: str

    # Cold-start assessment §5.3/§5.5: grade -> W (eligible combined handoffs before the
    # transition to mastery-driven selection). Keys MUST be exactly {2, 3}.
    familiarization_window_by_grade: dict[int, Annotated[int, Field(ge=1)]]

    # SPEC §8.2 fallback / §5.3: familiarization and C-only fallback both start at difficulty 1.
    familiarization_difficulty_level: Annotated[int, Field(ge=1, le=5)]
    fallback_difficulty_level: Annotated[int, Field(ge=1, le=5)]

    # SPEC §8.2 bullet 6 / §10: "permit only levels 1-2" caps for familiarization and C-only
    # fallback (exposed as provenance for the C4.1 adaptation policy; C4.0 does not enforce
    # these beyond the initial pick, which is already within cap).
    familiarization_session_difficulty_cap: Annotated[int, Field(ge=1, le=5)]
    fallback_difficulty_cap: Annotated[int, Field(ge=1, le=5)]

    @field_validator("config_version", "parameter_source_status")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not str(v).strip():
            raise ValueError("version / source-status strings must be non-empty")
        return v

    @field_validator("familiarization_window_by_grade")
    @classmethod
    def _exactly_grades_2_and_3(cls, v: dict[int, int]) -> dict[int, int]:
        if set(v.keys()) != {2, 3}:
            raise ValueError(f"familiarization_window_by_grade must have exactly keys {{2, 3}}, got {sorted(v)}")
        return v

    @model_validator(mode="after")
    def _cap_consistency(self) -> "CSelectionConfig":
        if self.familiarization_difficulty_level > self.familiarization_session_difficulty_cap:
            raise ValueError("familiarization_difficulty_level must not exceed its own session cap")
        if self.fallback_difficulty_level > self.fallback_difficulty_cap:
            raise ValueError("fallback_difficulty_level must not exceed fallback_difficulty_cap")
        return self

    def window_for_grade(self, grade: int) -> int:
        if grade not in self.familiarization_window_by_grade:
            raise ValueError(f"no familiarization window configured for grade {grade}")
        return self.familiarization_window_by_grade[grade]


def default_selection_config() -> CSelectionConfig:
    """The Phase C4.0 TEST_FIXTURE_ONLY selection config (assessment §5.5 worked values) --
    explicit builder, never a silent fallback."""
    return CSelectionConfig(
        config_version=SELECTION_CONFIG_VERSION,
        parameter_source_status="TEST_FIXTURE_ONLY",
        familiarization_window_by_grade={2: 2, 3: 3},  # assessment §5.5 worked example
        familiarization_difficulty_level=1,
        fallback_difficulty_level=1,
        familiarization_session_difficulty_cap=2,
        fallback_difficulty_cap=2,
    )
