"""``CSessionRequest`` and its shared-context sub-model (SPEC §6.1, §8).

``CSessionRequest`` is the only place Component B's consumed mastery edge
(``BToCMasteryPayload``, the shared frozen v2.1 contract) enters Component C. Every other
field is either C-local or explicitly restricted to attendance/partial/technical context
(SPEC §8.3; cold-start assessment revision note) -- there is no B-derived readiness field
anywhere on this model, and ``extra="forbid"`` makes that a structural guarantee, not just
a convention: no caller can smuggle an extra B-shaped field onto this request.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from models.contracts import BToCMasteryPayload, CSessionId, InterventionSessionId, StudentId

from .enums import AttendanceStatus, GradeLevel, PolicyMode, SessionMode
from .learner_state import CLocalLearnerState


def _student_prefix(identifier: str) -> str:
    return identifier[:8]


_B_DERIVED_KEY_MARKERS = (
    "mastery_", "b_mastery", "population", "dd_subtype", "observation_count",
    "bkt", "p_l0", "p_t", "p_g", "p_s", "readiness",
)


def _walk_keys(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _walk_keys(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _walk_keys(child)


class SharedObservableContext(BaseModel):
    """Authorized shared-session context: attendance/partial/technical ONLY (SPEC §8.3).

    Deliberately excludes any B-derived signal (e.g. a per-skill readiness/evidence mask
    derived from B's ``observation_count`` -- explicitly withdrawn per the cold-start
    assessment's revision note). ``extra="forbid"`` means no such field can be added
    without a model change, which is itself the boundary-purity guarantee.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    attendance_status: AttendanceStatus
    is_partial: bool
    technical_issue_flag: bool


class CSessionRequest(BaseModel):
    """One Component C session request (SPEC §6.1)."""

    model_config = ConfigDict(extra="forbid")

    student_id: StudentId
    intervention_session_id: InterventionSessionId
    intervention_session_number: Annotated[int, Field(ge=1, le=25)]
    intervention_session_date: date
    c_session_id: CSessionId
    c_session_number: Annotated[int, Field(ge=1)]
    grade_level: GradeLevel
    session_mode: SessionMode
    b_mastery_payload: BToCMasteryPayload | None
    # Opaque pending a C5 session-aggregate model; guarded below for B-shaped leakage.
    prior_complete_c_summary: dict[str, Any] | None
    shared_observable_context: SharedObservableContext
    c_local_state: CLocalLearnerState
    root_seed: int
    policy_mode: PolicyMode

    @model_validator(mode="after")
    def _validate_invariants(self) -> "CSessionRequest":
        for identifier in (self.intervention_session_id, self.c_session_id):
            if _student_prefix(identifier) != self.student_id:
                raise ValueError("ID-05: session identifier prefix must match student_id")

        if self.session_mode == "combined" and self.b_mastery_payload is None:
            raise ValueError("SPEC §6.1: b_mastery_payload is required when session_mode is 'combined'")
        if self.session_mode == "c_only" and self.b_mastery_payload is not None:
            raise ValueError("SPEC §6.1/SF-043: b_mastery_payload is prohibited when session_mode is 'c_only'")

        if self.b_mastery_payload is not None:
            if self.b_mastery_payload.student_id != self.student_id:
                raise ValueError("RI-01: b_mastery_payload.student_id disagrees with the C session request")
            if self.b_mastery_payload.intervention_session_id != self.intervention_session_id:
                raise ValueError("RI-01: b_mastery_payload.intervention_session_id disagrees with the C session request")

        if self.prior_complete_c_summary is not None:
            found = {
                key for key in _walk_keys(self.prior_complete_c_summary)
                if any(marker in key.lower() for marker in _B_DERIVED_KEY_MARKERS)
            }
            if found:
                raise ValueError(
                    f"SF-043/boundary-purity: prior_complete_c_summary must carry no B-derived field: {sorted(found)}"
                )
        return self
