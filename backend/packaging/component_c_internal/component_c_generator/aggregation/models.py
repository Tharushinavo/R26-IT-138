"""``CSessionAggregate`` -- the §18 DERIVED VALUES container (Phase C5.0).

This is C5.0's own internal handoff type, not the C→3 payload (the payload adapter is C5.1).
Field names deliberately match the C→3 v3.0 names verbatim (SPEC §18 closing note: "Field names
are chosen to match the C->3 v3.0 session-aggregate names") so C5.1 can map them across with no
renaming, and so the CRITICAL ORACLE TEST can assemble a real ``CToComponent3Payload`` directly
from this model's fields.
"""

from __future__ import annotations

from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

DifficultyTrend = Literal["increasing", "stable", "decreasing"]


class CSessionAggregate(BaseModel):
    """§18 derived session aggregate. ``inactive_time_available`` records whether
    ``inactive_time_sec`` was genuinely derivable from telemetry (Params §9/§10
    "C-COMP-v1-fallback-periods ... only when inactive_time_sec genuinely unavailable") --
    ``inactive_time_sec`` itself stays a required numeric field (matching the committed,
    non-nullable oracle field of the same name), but composite computation must consult this
    flag, not just the number, to decide which formula version applies (see
    ``composites.engagement_frustration``)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    task_opportunity_count: Annotated[int, Field(ge=0)]
    completed_task_count: Annotated[int, Field(ge=0)]
    correct_task_count: Annotated[int, Field(ge=0)]
    total_attempt_count: Annotated[int, Field(ge=0)]
    accuracy_rate: Optional[Annotated[float, Field(ge=0.0, le=1.0)]]
    avg_attempts_per_task: Optional[Annotated[float, Field(ge=1.0)]]
    task_completion_rate: Annotated[float, Field(ge=0.0, le=1.0)]

    inactivity_periods: Annotated[int, Field(ge=0)]
    inactive_time_sec: Annotated[float, Field(ge=0.0)]
    inactive_time_available: bool
    session_duration_sec: Annotated[float, Field(gt=0.0)]
    time_in_target_band_sec: Annotated[float, Field(ge=0.0)]

    consecutive_error_max: Annotated[int, Field(ge=0)]
    difficulty_floor_hits: Annotated[int, Field(ge=0)]
    quit_after_error: bool
    safety_override_count: Annotated[int, Field(ge=0)]

    c_mean_game_task_latency_sec: Optional[Annotated[float, Field(gt=0.0, le=90.0)]]
    c_median_game_task_latency_sec: Optional[Annotated[float, Field(gt=0.0, le=90.0)]]

    current_difficulty_level: Annotated[int, Field(ge=1, le=5)]
    difficulty_trend: DifficultyTrend

    session_technical_issue_flag: bool
