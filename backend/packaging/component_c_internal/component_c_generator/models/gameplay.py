"""``GameplayEvent`` (SPEC §6.4 / C3 §14) and derived ``CTaskOpportunitySummary`` (C3 §15).

Both are strict/frozen: ``extra="forbid"`` is the structural guarantee that no C4/C5 field
(engagement/frustration/learner-state/C->3), no Component 3 field, no Component A field, and no
B-internal field (timing/hints/errors/attempts/BKT) can ever appear on a C3 output -- there is
no runtime scan needed because none is declared, and adding one is a rejected unknown field.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from models.contracts import CSessionId, InterventionSessionId, StudentId

from .enums import ScaffoldLevel
from .seed import CSeedLineage

# SPEC §6.4 (parent SPEC) / C3 §9.1 (Appendix M global event sequence) / C3 §8, §10, §12, §13:
# the approved C3 observable event vocabulary. Terminal events are exactly the three Appendix-M
# terminal types; finer termination causes live on `terminal_reason` (C3 §13.1), not here.
EventType = Literal[
    "game_task_offered",
    "game_task_started",
    "action_performed",
    "answer_submitted",
    "answer_evaluated",
    "retry_started",
    "pause_started",
    "pause_ended",
    "scaffold_requested",
    "scaffold_shown",
    "technical_issue",
    "game_task_completed",
    "game_task_skipped",
    "game_task_quit",
]

TERMINAL_EVENT_TYPES = ("game_task_completed", "game_task_skipped", "game_task_quit")
ATTEMPT_SCOPED_EVENT_TYPES = ("action_performed", "answer_submitted", "answer_evaluated")
SCAFFOLD_EVENT_TYPES = ("scaffold_requested", "scaffold_shown")
ACTION_PAYLOAD_EVENT_TYPES = ("action_performed", "answer_submitted")

# C3 §13.1 -- the complete terminal-reason vocabulary.
TerminalReason = Literal[
    "completed_correct",
    "completed_incorrect",
    "skipped",
    "quit_after_error",
    "quit_without_recent_error",
    "technical_issue",
    "attempt_cap_exhausted",
    "timeout_no_response",
    "safe_session_stop",
]

# C3 §13.3 / §15: which coarse event_type each fine-grained terminal_reason maps to (an explicit
# engineering reconciliation -- Appendix M's global event sequence names only THREE terminal
# event types, while C3 §13.1 names NINE terminal reasons; event_type carries the coarse
# category, terminal_reason the specific cause).
TERMINAL_REASON_EVENT_TYPE: dict[str, str] = {
    "completed_correct": "game_task_completed",
    "completed_incorrect": "game_task_completed",
    "attempt_cap_exhausted": "game_task_completed",
    "skipped": "game_task_skipped",
    "quit_after_error": "game_task_quit",
    "quit_without_recent_error": "game_task_quit",
    "technical_issue": "game_task_quit",
    "timeout_no_response": "game_task_quit",
    "safe_session_stop": "game_task_quit",
}


class GameplayEvent(BaseModel):
    """One canonical observable gameplay event (C3 §14)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str
    event_type: EventType
    event_index: Annotated[int, Field(ge=1)]
    student_id: StudentId
    intervention_session_id: InterventionSessionId
    c_session_id: CSessionId
    game_task_instance_id: str
    task_index: Annotated[int, Field(ge=1)]
    attempt_number: Optional[Annotated[int, Field(ge=1)]] = None
    event_timestamp_relative_ms: Annotated[int, Field(ge=0)]
    action_payload: Optional[dict[str, Any]] = None
    evaluation_payload: Optional[dict[str, Any]] = None
    scaffold_code: Optional[ScaffoldLevel] = None
    technical_flag: bool
    terminal_reason: Optional[TerminalReason] = None
    seed_lineage: CSeedLineage
    generator_version: str
    config_checksum: str

    @model_validator(mode="after")
    def _field_scoping_invariants(self) -> "GameplayEvent":
        if (self.attempt_number is not None) != (self.event_type in ATTEMPT_SCOPED_EVENT_TYPES):
            raise ValueError(
                f"attempt_number must be set iff event_type is one of {ATTEMPT_SCOPED_EVENT_TYPES}, "
                f"got event_type={self.event_type!r} attempt_number={self.attempt_number!r}"
            )
        if (self.terminal_reason is not None) != (self.event_type in TERMINAL_EVENT_TYPES):
            raise ValueError(
                f"terminal_reason must be set iff event_type is one of {TERMINAL_EVENT_TYPES}, "
                f"got event_type={self.event_type!r} terminal_reason={self.terminal_reason!r}"
            )
        if self.terminal_reason is not None and TERMINAL_REASON_EVENT_TYPE[self.terminal_reason] != self.event_type:
            raise ValueError(
                f"terminal_reason {self.terminal_reason!r} must pair with event_type "
                f"{TERMINAL_REASON_EVENT_TYPE[self.terminal_reason]!r}, got {self.event_type!r}"
            )
        if (self.scaffold_code is not None) != (self.event_type in SCAFFOLD_EVENT_TYPES):
            raise ValueError(
                f"scaffold_code must be set iff event_type is one of {SCAFFOLD_EVENT_TYPES}, "
                f"got event_type={self.event_type!r} scaffold_code={self.scaffold_code!r}"
            )
        if self.action_payload is not None and self.event_type not in ACTION_PAYLOAD_EVENT_TYPES:
            raise ValueError(
                f"action_payload is only permitted on {ACTION_PAYLOAD_EVENT_TYPES}, got {self.event_type!r}"
            )
        if self.evaluation_payload is not None and self.event_type != "answer_evaluated":
            raise ValueError(f"evaluation_payload is only permitted on 'answer_evaluated', got {self.event_type!r}")
        return self


class CTaskOpportunitySummary(BaseModel):
    """Derived task-opportunity summary (C3 §15) -- every field derived only from
    ``c_gameplay_events``, never independently sampled. Field names are chosen to match the
    C->3 v3.0 session-aggregate names C5 will roll these up into (C3 §15 closing note)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    student_id: StudentId
    intervention_session_id: InterventionSessionId
    c_session_id: CSessionId
    game_task_instance_id: str
    task_index: Annotated[int, Field(ge=1)]

    task_offered: bool
    task_started: bool
    task_completed: bool
    task_skipped: bool
    task_quit: bool
    technical_issue: bool

    correct_task: Optional[bool] = None
    total_attempts: Annotated[int, Field(ge=0)]
    retry_count: Annotated[int, Field(ge=0)]

    scaffold_requested: bool
    scaffold_count: Annotated[int, Field(ge=0)]
    highest_scaffold_level: Optional[ScaffoldLevel] = None

    c_answer_changes: Annotated[int, Field(ge=0)]

    task_latency_sec: Optional[Annotated[float, Field(gt=0.0, le=90.0)]] = None
    inactive_time_sec: Annotated[float, Field(ge=0.0)]
    inactivity_periods: Annotated[int, Field(ge=0)]

    quit_after_error: bool
    terminal_reason: Optional[TerminalReason] = None

    first_attempt_correct: Optional[bool] = None
    final_attempt_correct: Optional[bool] = None
    consecutive_error_max_within_task: Annotated[int, Field(ge=0)]

    @model_validator(mode="after")
    def _summary_invariants(self) -> "CTaskOpportunitySummary":
        completed_count = sum([self.task_completed, self.task_skipped, self.task_quit])
        if self.task_started and completed_count != 1:
            raise ValueError("exactly one of task_completed/task_skipped/task_quit must hold for a started task")
        if not self.task_started and completed_count != 0:
            raise ValueError("a never-started task cannot be completed/skipped/quit")
        if self.retry_count != max(self.total_attempts - 1, 0):
            raise ValueError("retry_count must equal max(total_attempts - 1, 0)")
        if self.total_attempts == 0 and (self.first_attempt_correct is not None or self.final_attempt_correct is not None):
            raise ValueError("first/final_attempt_correct must be null when total_attempts is 0")
        if self.total_attempts > 0 and self.first_attempt_correct is None:
            raise ValueError("first_attempt_correct must be set when total_attempts > 0")
        if self.total_attempts > 0 and self.final_attempt_correct is None:
            raise ValueError("final_attempt_correct must be set when total_attempts > 0")
        if not self.task_completed and self.correct_task is not None:
            raise ValueError("correct_task must be null unless task_completed is true")
        if self.task_completed and self.correct_task is None:
            raise ValueError("correct_task must be set when task_completed is true")
        if self.quit_after_error and not (self.task_quit and self.terminal_reason == "quit_after_error"):
            raise ValueError("quit_after_error=true requires task_quit and terminal_reason=='quit_after_error'")
        if self.scaffold_count > 0 and self.highest_scaffold_level is None:
            raise ValueError("highest_scaffold_level must be set when scaffold_count > 0")
        if self.scaffold_count == 0 and self.highest_scaffold_level is not None:
            raise ValueError("highest_scaffold_level must be null when scaffold_count == 0")
        return self
