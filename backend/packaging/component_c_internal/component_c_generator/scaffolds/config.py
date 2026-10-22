"""Versioned, no-defaults configuration for the scaffold ladder + recovery-task builder
(Phase C4.2). SPEC §15 names the C0-C4 ladder and its meanings but fixes no numeric
escalation threshold; every value below is therefore an explicit ``ENGINEERING_ASSUMPTION``,
tagged ``parameter_source_status = "TEST_FIXTURE_ONLY"``. Authoritative thresholds remain
``CALIBRATION_PENDING``. Nothing here is written to any governance document.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCAFFOLD_CONFIG_VERSION = "c4.2-scaffold-1.0.0"
RECOVERY_CONFIG_VERSION = "c4.2-recovery-1.0.0"


class CScaffoldConfig(BaseModel):
    """Ordinary (non-safety-forced) scaffold-escalation thresholds, keyed on consecutive
    incorrect attempts on the CURRENT task opportunity (SPEC §15). Strictly increasing --
    each level requires strictly more consecutive misses than the one below it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    config_version: str
    parameter_source_status: str

    level_c1_min_consecutive_incorrect: Annotated[int, Field(ge=1)]
    level_c2_min_consecutive_incorrect: Annotated[int, Field(ge=1)]
    level_c3_min_consecutive_incorrect: Annotated[int, Field(ge=1)]
    level_c4_min_consecutive_incorrect: Annotated[int, Field(ge=1)]

    @field_validator("config_version", "parameter_source_status")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not str(v).strip():
            raise ValueError("version / source-status strings must be non-empty")
        return v

    @model_validator(mode="after")
    def _strictly_increasing(self) -> "CScaffoldConfig":
        levels = (
            self.level_c1_min_consecutive_incorrect,
            self.level_c2_min_consecutive_incorrect,
            self.level_c3_min_consecutive_incorrect,
            self.level_c4_min_consecutive_incorrect,
        )
        if not all(a < b for a, b in zip(levels, levels[1:])):
            raise ValueError(f"scaffold level thresholds must be strictly increasing C1<C2<C3<C4, got {levels}")
        return self


def default_scaffold_config() -> CScaffoldConfig:
    return CScaffoldConfig(
        config_version=SCAFFOLD_CONFIG_VERSION,
        parameter_source_status="TEST_FIXTURE_ONLY",
        level_c1_min_consecutive_incorrect=1,
        level_c2_min_consecutive_incorrect=2,
        level_c3_min_consecutive_incorrect=3,
        level_c4_min_consecutive_incorrect=4,
    )


class CRecoveryConfig(BaseModel):
    """Recovery-task realization constants (SPEC §10/§15): recovery is always level 1, always
    scaffold C4, and always has time pressure removed -- these three are FROZEN structural
    facts of what "recovery" means, not tunable numbers, so they are not configurable fields
    here (hardcoding them is not a "silent default": they are the definition of a recovery
    task, cited directly from SPEC §10/§15). This config only carries the one genuinely
    tunable value: how many eligible-template candidates may be considered before giving up
    (a bound, not a science value)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    config_version: str
    parameter_source_status: str

    @field_validator("config_version", "parameter_source_status")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not str(v).strip():
            raise ValueError("version / source-status strings must be non-empty")
        return v


def default_recovery_config() -> CRecoveryConfig:
    return CRecoveryConfig(config_version=RECOVERY_CONFIG_VERSION, parameter_source_status="TEST_FIXTURE_ONLY")
