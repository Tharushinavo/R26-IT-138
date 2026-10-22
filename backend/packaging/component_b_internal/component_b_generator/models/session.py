"""Scheduled-session context and seed lineage (SPEC §5, §8)."""

from __future__ import annotations

from typing import Tuple

from pydantic import BaseModel, ConfigDict, field_validator

from .enums import Grade


class SeedLineage(BaseModel):
    """Traceable record of the deterministic seed derivation for one unit of work.

    ``path`` is the ordered chain of (level, key) components that produced ``seed`` from
    the global seed, e.g. ``(("global", "20260716"), ("learner", "STU-0001"),
    ("scheduled_session", "3"), ("component_b_session", "3"), ("item_opportunity", "2"))``.
    Same path + global seed => same ``seed`` (order-independent; no unordered iteration).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    global_seed: int
    path: Tuple[Tuple[str, str], ...]
    seed: int


class ScheduledSessionContext(BaseModel):
    """One of the learner's 25 scheduled intervention-session opportunities (SF-040).

    Phase B1 assumes the session is B-attended (``b_scheduled=True``); the attendance /
    calendar / attrition model is a later shared-simulation concern (SF-040) and is not
    implemented here. A fully-missed slot would produce no B-session (SPEC §8 / SF-043).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    student_id: str
    grade: Grade
    scheduled_session_number: int  # 1..N (N = configured scheduled session count; <=25)
    b_scheduled: bool
    scheduled_session_seed: int
    component_b_session_seed: int

    @field_validator("scheduled_session_number")
    @classmethod
    def _positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("scheduled_session_number must be >= 1")
        return v
