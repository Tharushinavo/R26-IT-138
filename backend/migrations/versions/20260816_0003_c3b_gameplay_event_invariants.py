"""Component C Phase 3b: at-most-one-terminal-event, event_index/timestamp ordering, and the
attempt_number/event_type structural rule (Phase 3b work order, R-J/R-K/R-L/R-O).

Creates NO table -- Phase 3a's ten tables already exist. Adds:
  - a partial UNIQUE index expressing AT MOST ONE terminal event per task (I1's at-most-one
    half only; "at least one" is explicitly DEFERRED per R-K, not built here or anywhere in this
    migration -- see the persistence_models.py docstring and buildLog1.md for its named home);
  - two triggers (I2, I3), mirroring 20260722_0003_bundle_integrity_guards.py's structure
    exactly: named CREATE FUNCTION, named CREATE TRIGGER, downgrade drops trigger then function
    in reverse order. Both lock the c_task_instances row identified by the event's
    game_task_instance_id (the event's true immediate parent) via SELECT ... FOR UPDATE, to
    serialize concurrent writers to the same task's event stream -- the same row-locking pattern
    B's own trigger already uses for the same reason (R-J's binding condition);
  - a structural CHECK (I4's sub-rule, R-L): attempt_number may only be set on the three
    attempt-scoped event types, sourced live from the installed C engine wheel's own
    attempt-scoped-event-type constant (see persistence_models.py for the exact source path).
    This is NOT "attempt counts bounded" and must never be described as satisfying I4 -- I4's
    numeric bound is BLOCKED, ESCALATED TO THE OWNER (R-L) and is not built in any form here.

Revision ID: 20260816_0003
Revises: 20260816_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260816_0003"
down_revision: str | Sequence[str] | None = "20260816_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


EVENT_INDEX_CONSECUTIVE_FUNCTION = """
CREATE FUNCTION enforce_c_gameplay_event_index_consecutive()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    previous_max_event_index integer;
BEGIN
    -- Lock the task instance row (the event's true immediate parent) to serialize concurrent
    -- writers appending to the same task's event stream -- same pattern as
    -- enforce_b_session_active_bundle_eligibility's SELECT ... FOR UPDATE.
    PERFORM 1 FROM c_task_instances WHERE c_task_instance_id = NEW.game_task_instance_id FOR UPDATE;

    SELECT MAX(event_index) INTO previous_max_event_index
      FROM c_gameplay_events
     WHERE game_task_instance_id = NEW.game_task_instance_id;

    IF previous_max_event_index IS NULL THEN
        IF NEW.event_index <> 1 THEN
            RAISE EXCEPTION 'first gameplay event for a task must have event_index = 1'
                USING ERRCODE = '23514', CONSTRAINT = 'ck_c_gameplay_events_index_consecutive';
        END IF;
    ELSIF NEW.event_index <> previous_max_event_index + 1 THEN
        RAISE EXCEPTION 'gameplay event_index must be consecutive from 1 within a task'
            USING ERRCODE = '23514', CONSTRAINT = 'ck_c_gameplay_events_index_consecutive';
    END IF;

    RETURN NEW;
END;
$$
"""


EVENT_TIMESTAMP_NON_DECREASING_FUNCTION = """
CREATE FUNCTION enforce_c_gameplay_event_timestamp_non_decreasing()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    previous_max_timestamp integer;
BEGIN
    PERFORM 1 FROM c_task_instances WHERE c_task_instance_id = NEW.game_task_instance_id FOR UPDATE;

    SELECT MAX(event_timestamp_relative_ms) INTO previous_max_timestamp
      FROM c_gameplay_events
     WHERE game_task_instance_id = NEW.game_task_instance_id;

    IF previous_max_timestamp IS NOT NULL AND NEW.event_timestamp_relative_ms < previous_max_timestamp THEN
        RAISE EXCEPTION 'gameplay event_timestamp_relative_ms must be non-decreasing within a task'
            USING ERRCODE = '23514', CONSTRAINT = 'ck_c_gameplay_events_timestamp_non_decreasing';
    END IF;

    RETURN NEW;
END;
$$
"""


def upgrade() -> None:
    op.create_index(
        "uq_c_gameplay_events_at_most_one_terminal_per_instance",
        "c_gameplay_events",
        ["game_task_instance_id"],
        unique=True,
        postgresql_where=sa.text("event_type IN ('game_task_completed', 'game_task_skipped', 'game_task_quit')"),
    )
    op.create_check_constraint(
        "ck_c_gameplay_events_attempt_number_scope",
        "c_gameplay_events",
        "attempt_number IS NULL OR event_type IN ('action_performed', 'answer_submitted', 'answer_evaluated')",
    )
    op.execute(EVENT_INDEX_CONSECUTIVE_FUNCTION)
    op.execute(
        """
        CREATE TRIGGER trg_c_gameplay_events_index_consecutive
        BEFORE INSERT
        ON c_gameplay_events
        FOR EACH ROW
        EXECUTE FUNCTION enforce_c_gameplay_event_index_consecutive()
        """
    )
    op.execute(EVENT_TIMESTAMP_NON_DECREASING_FUNCTION)
    op.execute(
        """
        CREATE TRIGGER trg_c_gameplay_events_timestamp_non_decreasing
        BEFORE INSERT
        ON c_gameplay_events
        FOR EACH ROW
        EXECUTE FUNCTION enforce_c_gameplay_event_timestamp_non_decreasing()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_c_gameplay_events_timestamp_non_decreasing ON c_gameplay_events")
    op.execute("DROP FUNCTION enforce_c_gameplay_event_timestamp_non_decreasing()")
    op.execute("DROP TRIGGER trg_c_gameplay_events_index_consecutive ON c_gameplay_events")
    op.execute("DROP FUNCTION enforce_c_gameplay_event_index_consecutive()")
    op.drop_constraint(
        "ck_c_gameplay_events_attempt_number_scope",
        "c_gameplay_events",
        type_="check",
    )
    op.drop_index("uq_c_gameplay_events_at_most_one_terminal_per_instance", table_name="c_gameplay_events")
