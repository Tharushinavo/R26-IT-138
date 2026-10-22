"""``CSafetyConfig`` (Phase C4.1) -- versioned, no-defaults hard-safety-controller thresholds.

The familiarization/fallback session difficulty caps are NOT redeclared here -- they are
imported from the already-committed ``component_c_generator.selection.config.CSelectionConfig``
(Phase C4.0) so there is exactly one source of truth for those two numbers. This module owns
only the NEW safety-specific thresholds SPEC §17/§10.2 introduce: the severe consecutive-error
and rolling-strain safety triggers, the increase-block window length, the SPEC §10.2
"prior overloaded/disengaged complete state -> <=2" cap, and the safe-session-termination
threshold. Every value is an explicit ``ENGINEERING_ASSUMPTION``, tagged
``parameter_source_status = "TEST_FIXTURE_ONLY"``; the authoritative thresholds remain
``CALIBRATION_PENDING``. Nothing here is written to any governance document.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SAFETY_CONFIG_VERSION = "c4.1-safety-1.0.0"


class CSafetyConfig(BaseModel):
    """Hard-safety-controller thresholds (SPEC §17, §10.2)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    config_version: str
    parameter_source_status: str

    # Severe safety triggers -- deliberately set at or above the rule-based policy's own
    # decrease_error_run_threshold/decrease_min_strain (CPolicyConfig). By the time a trigger
    # here fires, the ordinary policy has typically already independently proposed a decrease;
    # this layer's job is defense-in-depth -- it ALSO flags recovery, arms the increase-block
    # window, and unconditionally vetoes hold/increase should the policy ever propose one
    # anyway (e.g. from stale or inconsistent evidence), rather than being the primary
    # everyday drift-catcher.
    consecutive_error_trigger: Annotated[int, Field(ge=1)]
    strain_trigger: Annotated[float, Field(ge=0.0, le=1.0)]

    # Bounded window (in subsequent decisions) during which increase_difficulty stays vetoed
    # after a severe trigger fires (SPEC §17 "block future increases for a bounded window").
    increase_block_window: Annotated[int, Field(ge=1)]

    # SPEC §10.2: "prior overloaded/disengaged complete state -> <=2".
    prior_overloaded_disengaged_cap: Annotated[int, Field(ge=1, le=5)]

    # An even more severe threshold than consecutive_error_trigger, for requesting a full safe
    # session stop (SPEC §17 "request safe session termination").
    safe_termination_error_threshold: Annotated[int, Field(ge=1)]

    # Rolling-strain bucket cut points (low < moderate < high < severe), for the
    # AdaptationDecision.rolling_strain_bucket audit field. severe aligns with strain_trigger.
    strain_bucket_low_max: Annotated[float, Field(ge=0.0, le=1.0)]
    strain_bucket_moderate_max: Annotated[float, Field(ge=0.0, le=1.0)]
    strain_bucket_high_max: Annotated[float, Field(ge=0.0, le=1.0)]

    @field_validator("config_version", "parameter_source_status")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not str(v).strip():
            raise ValueError("version / source-status strings must be non-empty")
        return v

    @model_validator(mode="after")
    def _ordering(self) -> "CSafetyConfig":
        if self.safe_termination_error_threshold <= self.consecutive_error_trigger:
            raise ValueError("safe_termination_error_threshold must be > consecutive_error_trigger")
        if not (self.strain_bucket_low_max < self.strain_bucket_moderate_max < self.strain_bucket_high_max):
            raise ValueError("strain bucket cut points must be strictly increasing")
        if self.strain_bucket_high_max > self.strain_trigger:
            raise ValueError("strain_bucket_high_max must be <= strain_trigger (severe starts at the trigger)")
        return self

    def bucket_strain(self, score: float) -> str:
        if score < self.strain_bucket_low_max:
            return "low"
        if score < self.strain_bucket_moderate_max:
            return "moderate"
        if score < self.strain_bucket_high_max:
            return "high"
        return "severe"


def default_safety_config() -> CSafetyConfig:
    """The Phase C4.1 TEST_FIXTURE_ONLY safety config -- explicit builder, never a silent
    fallback."""
    return CSafetyConfig(
        config_version=SAFETY_CONFIG_VERSION,
        parameter_source_status="TEST_FIXTURE_ONLY",
        consecutive_error_trigger=5,
        strain_trigger=0.85,
        increase_block_window=3,
        prior_overloaded_disengaged_cap=2,
        safe_termination_error_threshold=7,
        strain_bucket_low_max=0.25,
        strain_bucket_moderate_max=0.50,
        strain_bucket_high_max=0.85,
    )
