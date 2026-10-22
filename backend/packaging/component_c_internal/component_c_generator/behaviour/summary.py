"""Derive ``CTaskOpportunitySummary`` from ``c_gameplay_events`` (C3 §15).

Every field is computed by re-parsing the ordered event stream -- nothing is threaded through
from the attempt-loop's internal state. This is what makes ``quit_after_error`` genuinely
event-derived (C3 §13.2: "event-derived, never independently sampled as a stored label") rather
than a loop-tracked boolean that merely happens to agree with the events.
"""

from __future__ import annotations

from typing import Optional, Sequence

from ..models.gameplay import GameplayEvent, TERMINAL_EVENT_TYPES


def derive_task_opportunity_summary(events: Sequence[GameplayEvent]) -> "CTaskOpportunitySummary":
    from ..models.gameplay import CTaskOpportunitySummary  # local import avoids a cycle at module load

    if not events:
        raise ValueError("cannot derive a summary from an empty event stream")

    first = events[0]
    student_id = first.student_id
    intervention_session_id = first.intervention_session_id
    c_session_id = first.c_session_id
    game_task_instance_id = first.game_task_instance_id
    task_index = first.task_index

    task_offered = any(e.event_type == "game_task_offered" for e in events)
    task_started = any(e.event_type == "game_task_started" for e in events)

    terminal_events = [e for e in events if e.event_type in TERMINAL_EVENT_TYPES]
    if len(terminal_events) != 1:
        raise ValueError(f"expected exactly one terminal event, found {len(terminal_events)}")
    terminal = terminal_events[0]
    terminal_reason = terminal.terminal_reason

    task_completed = terminal.event_type == "game_task_completed"
    task_skipped = terminal.event_type == "game_task_skipped"
    task_quit = terminal.event_type == "game_task_quit"
    technical_issue = bool(terminal.technical_flag) or any(e.event_type == "technical_issue" for e in events)

    submitted_events = [e for e in events if e.event_type == "answer_submitted"]
    evaluated_events = [e for e in events if e.event_type == "answer_evaluated"]
    total_attempts = len(submitted_events)
    retry_count = max(total_attempts - 1, 0)

    evaluated_results = [bool(e.evaluation_payload["is_correct"]) for e in evaluated_events]
    first_attempt_correct = evaluated_results[0] if evaluated_results else None
    final_attempt_correct = evaluated_results[-1] if evaluated_results else None

    correct_task: Optional[bool] = None
    if task_completed:
        correct_task = final_attempt_correct if final_attempt_correct is not None else False

    consecutive_error_max = 0
    running = 0
    for is_correct in evaluated_results:
        if is_correct:
            running = 0
        else:
            running += 1
            consecutive_error_max = max(consecutive_error_max, running)

    scaffold_requested_events = [e for e in events if e.event_type == "scaffold_requested"]
    scaffold_shown_events = [e for e in events if e.event_type == "scaffold_shown"]
    scaffold_requested = len(scaffold_requested_events) > 0
    scaffold_count = len(scaffold_shown_events)
    highest_scaffold_level = None
    if scaffold_shown_events:
        # C0 < C1 < ... < C4 -- lexicographic order on "C<digit>" matches numeric order.
        highest_scaffold_level = max(e.scaffold_code for e in scaffold_shown_events)

    c_answer_changes = 0
    submitted_payloads = [e.action_payload for e in submitted_events]
    for prev, cur in zip(submitted_payloads, submitted_payloads[1:]):
        if prev != cur:
            c_answer_changes += 1

    task_latency_sec: Optional[float] = None
    if evaluated_events:
        # C3 §9: task latency derives from the valid submitted/completed action's latency --
        # the elapsed clock time between the corresponding submission and the attempt before it.
        last_submit = submitted_events[-1]
        idx = events.index(last_submit)
        preceding_ts = 0
        for e in events[:idx][::-1]:
            if e.event_type in ("game_task_started", "answer_evaluated", "retry_started", "pause_ended"):
                preceding_ts = e.event_timestamp_relative_ms
                break
        elapsed_ms = last_submit.event_timestamp_relative_ms - preceding_ts
        if elapsed_ms > 0:
            task_latency_sec = round(elapsed_ms / 1000.0, 6)

    inactive_time_sec = 0.0
    inactivity_periods = 0
    pause_starts = [e for e in events if e.event_type == "pause_started"]
    pause_ends = [e for e in events if e.event_type == "pause_ended"]
    if len(pause_starts) != len(pause_ends):
        raise ValueError("unpaired pause_started/pause_ended events")
    for start, end in zip(pause_starts, pause_ends):
        if end.event_timestamp_relative_ms < start.event_timestamp_relative_ms:
            raise ValueError("pause_ended precedes its pause_started")
        if start.technical_flag:
            continue  # SPEC §10: technical pause time must not increase learner inactivity burden
        inactive_time_sec += (end.event_timestamp_relative_ms - start.event_timestamp_relative_ms) / 1000.0
        inactivity_periods += 1

    # C3 §13.2: quit_after_error is true only when the terminal reason is quit_after_error AND
    # the immediately preceding evaluable (answer_evaluated) event was incorrect AND no
    # successful action followed it -- re-derived here from the event order, not trusted from
    # the loop.
    quit_after_error = False
    if terminal_reason == "quit_after_error" and evaluated_results:
        quit_after_error = evaluated_results[-1] is False

    return CTaskOpportunitySummary(
        student_id=student_id,
        intervention_session_id=intervention_session_id,
        c_session_id=c_session_id,
        game_task_instance_id=game_task_instance_id,
        task_index=task_index,
        task_offered=task_offered,
        task_started=task_started,
        task_completed=task_completed,
        task_skipped=task_skipped,
        task_quit=task_quit,
        technical_issue=technical_issue,
        correct_task=correct_task,
        total_attempts=total_attempts,
        retry_count=retry_count,
        scaffold_requested=scaffold_requested,
        scaffold_count=scaffold_count,
        highest_scaffold_level=highest_scaffold_level,
        c_answer_changes=c_answer_changes,
        task_latency_sec=task_latency_sec,
        inactive_time_sec=round(inactive_time_sec, 6),
        inactivity_periods=inactivity_periods,
        quit_after_error=quit_after_error,
        terminal_reason=terminal_reason,
        first_attempt_correct=first_attempt_correct,
        final_attempt_correct=final_attempt_correct,
        consecutive_error_max_within_task=consecutive_error_max,
    )
