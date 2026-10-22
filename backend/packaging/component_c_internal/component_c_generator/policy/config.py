"""``CPolicyConfig`` (Phase C4.1) -- versioned, no-defaults rule-based-policy thresholds.

SPEC §14.1 names the rule-based baseline as the release policy but does not fix numeric
thresholds; the Component C Parameters do not specify difficulty-adaptation thresholds either.
Every value below is therefore an explicit ``ENGINEERING_ASSUMPTION``, tagged
``parameter_source_status = "TEST_FIXTURE_ONLY"``. The authoritative thresholds remain
``CALIBRATION_PENDING`` (SPEC §14: "Hyperparameters CALIBRATION_PENDING"). Nothing here is
written to any governance document.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

POLICY_CONFIG_VERSION = "c4.1-policy-1.0.0"


class CPolicyConfig(BaseModel):
    """Thresholds for ``rule_based.propose_difficulty_action`` (SPEC §14.1)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    config_version: str
    parameter_source_status: str

    # Propose increase_difficulty only when ALL hold: high recent correctness, low average
    # attempts (little struggle), and strain not already elevated.
    increase_correctness_threshold: Annotated[float, Field(ge=0.0, le=1.0)]
    increase_max_avg_attempts: Annotated[float, Field(ge=1.0)]
    increase_max_strain: Annotated[float, Field(ge=0.0, le=1.0)]

    # Propose decrease_difficulty when ANY holds: low recent correctness, a real error run, or
    # elevated strain.
    decrease_correctness_threshold: Annotated[float, Field(ge=0.0, le=1.0)]
    decrease_error_run_threshold: Annotated[int, Field(ge=1)]
    decrease_min_strain: Annotated[float, Field(ge=0.0, le=1.0)]

    @field_validator("config_version", "parameter_source_status")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not str(v).strip():
            raise ValueError("version / source-status strings must be non-empty")
        return v

    @model_validator(mode="after")
    def _threshold_ordering(self) -> "CPolicyConfig":
        if not (self.decrease_correctness_threshold < self.increase_correctness_threshold):
            raise ValueError("decrease_correctness_threshold must be < increase_correctness_threshold")
        if not (self.increase_max_strain < self.decrease_min_strain):
            raise ValueError("increase_max_strain must be < decrease_min_strain")
        return self


def default_policy_config() -> CPolicyConfig:
    """The Phase C4.1 TEST_FIXTURE_ONLY policy config -- explicit builder, never a silent
    fallback (mirrors every prior Component C config builder)."""
    return CPolicyConfig(
        config_version=POLICY_CONFIG_VERSION,
        parameter_source_status="TEST_FIXTURE_ONLY",
        increase_correctness_threshold=0.80,
        increase_max_avg_attempts=1.30,
        increase_max_strain=0.30,
        decrease_correctness_threshold=0.40,
        decrease_error_run_threshold=3,
        decrease_min_strain=0.60,
    )
