"""Versioned, no-defaults configuration for §18 session aggregation (Phase C5.0).

The §18 count/rate/timing identities themselves are ``FROZEN`` (C→3 v3.0 §4.3) and carry no
tunable numeric value -- they are exact ratios/sums transcribed verbatim, not calibratable. The
one genuinely provisional number this package needs is the Params §14 "minimum evidence before
adaptation" gate (``>= 3 completed tasks``), reused here to decide ``difficulty_trend`` (Params
§14: "insufficient evidence -> hold; difficulty_trend='stable'"). Params §14's own header marks
*all* of its RL/adaptation values -- including this one -- as provisional v1 defaults
(``ENGINEERING_ASSUMPTION`` · ``CALIBRATION_PENDING``), so it is versioned here rather than
hardcoded as a bare literal.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

AGGREGATION_CONFIG_VERSION = "c5.0-aggregation-1.0.0"


class CAggregationConfig(BaseModel):
    """§18 session-aggregation configuration (Phase C5.0)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    config_version: str
    parameter_source_status: str

    # Params §14: "Minimum evidence before adaptation: >= 3 completed tasks in the current
    # C-session." Reused here (not re-derived) to gate difficulty_trend computation -- below
    # this many completed tasks, difficulty_trend is forced "stable" regardless of the realized
    # AdaptationDecision trajectory (Params §14 fallback behaviour).
    min_completed_tasks_for_difficulty_trend: Annotated[int, Field(ge=1)]

    @field_validator("config_version", "parameter_source_status")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not str(v).strip():
            raise ValueError("version / source-status strings must be non-empty")
        return v


def default_aggregation_config() -> CAggregationConfig:
    return CAggregationConfig(
        config_version=AGGREGATION_CONFIG_VERSION,
        parameter_source_status="TEST_FIXTURE_ONLY",
        min_completed_tasks_for_difficulty_trend=3,
    )
