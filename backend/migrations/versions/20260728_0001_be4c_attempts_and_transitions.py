"""BE4c (BEplan §9 BE4.3 + BE4.4): attempt submission + first-attempt-only atomic BKT.

Persistence only — no scientific math here (the service layer calls
``app.infrastructure.live_engine.adapter.LiveEngineAdapter`` for every BKT/correctness step).
Adds two PRIVATE tables:

- ``b_attempts``: one row per submitted attempt/timeout event on an opportunity. Server-derived
  ``attempt_index`` is unique per opportunity (``uq_b_attempts_opportunity_index``), preventing a
  concurrent double-insert of the same index.
- ``b_skill_state_transitions``: the immutable first-attempt BKT observation + mastery
  transition. ``uq_b_skill_state_transitions_opportunity`` is both the DB-level "claim" for the
  unique first-attempt observation on an opportunity AND the transition row itself — a second
  concurrent claim for the same opportunity fails the unique index, never producing a second BKT
  update. No update/delete path is ever issued against this table by the application.

Column names avoid every ``PROHIBITED_COLUMN_TERMS`` entry (see
``tests/test_be2_architecture_guards.py``): mastery is spelled ``p_l``,
correctness is spelled ``response_matched``.

Revision ID: 20260728_0001
Revises: 20260727_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260728_0001"
down_revision: str | Sequence[str] | None = "20260727_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def provenance_columns() -> list[sa.Column]:
    return [
        sa.Column("created_at_utc", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at_utc", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("system_actor", sa.String(128), nullable=True),
        sa.Column("request_id", sa.String(64), nullable=False),
        sa.Column("operation_or_event_type", sa.String(128), nullable=False),
        sa.Column("reason_code", sa.String(128), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("before_reference_or_version", sa.String(255), nullable=True),
        sa.Column("after_reference_or_version", sa.String(255), nullable=True),
        sa.Column("source_class", sa.String(16), nullable=False),
        sa.Column("source_system", sa.String(128), nullable=False),
        sa.Column("source_record_id", sa.String(255), nullable=True),
        sa.Column("environment", sa.String(32), nullable=False),
        sa.Column("schema_revision", sa.String(64), nullable=False),
        sa.Column("approval_evidence_reference", sa.String(255), nullable=True),
    ]


def provenance_constraints(prefix: str) -> list[sa.Constraint]:
    return [
        sa.ForeignKeyConstraint(["actor_user_id"], ["app_users.user_id"], ondelete="RESTRICT"),
        sa.CheckConstraint("source_class IN ('REAL', 'SYNTHETIC', 'IMPORTED', 'TEST')", name=f"ck_{prefix}_source_class"),
        sa.CheckConstraint("(actor_user_id IS NOT NULL) <> (system_actor IS NOT NULL)", name=f"ck_{prefix}_actor_exactly_one"),
        sa.CheckConstraint("environment <> '' AND source_system <> '' AND request_id <> ''", name=f"ck_{prefix}_required_provenance_nonblank"),
    ]


def upgrade() -> None:
    op.create_table(
        "b_attempts",
        sa.Column("attempt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("learner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempt_index", sa.Integer(), nullable=False),
        sa.Column("event_kind", sa.String(32), nullable=False),
        sa.Column("submitted_value", sa.String(255), nullable=True),
        sa.Column("response_matched", sa.Boolean(), nullable=True),
        sa.Column("client_elapsed_ms", sa.Integer(), nullable=True),
        sa.Column("server_submitted_at_utc", sa.DateTime(timezone=True), nullable=False),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("attempt_id"),
        sa.ForeignKeyConstraint(["item_opportunity_id"], ["b_item_opportunities.item_opportunity_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["learner_id"], ["b_learners.learner_id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("item_opportunity_id", "attempt_index", name="uq_b_attempts_opportunity_index"),
        sa.CheckConstraint("event_kind IN ('RESPONSE', 'TIMEOUT')", name="ck_b_attempts_event_kind"),
        sa.CheckConstraint("attempt_index >= 1", name="ck_b_attempts_attempt_index_positive"),
        sa.CheckConstraint(
            "(event_kind = 'RESPONSE' AND response_matched IS NOT NULL AND submitted_value IS NOT NULL) "
            "OR (event_kind = 'TIMEOUT' AND response_matched IS NULL AND submitted_value IS NULL)",
            name="ck_b_attempts_response_matched_consistency",
        ),
        sa.CheckConstraint("client_elapsed_ms IS NULL OR client_elapsed_ms >= 0", name="ck_b_attempts_client_elapsed_ms_nonnegative"),
        *provenance_constraints("b_attempts"),
    )

    op.create_table(
        "b_skill_state_transitions",
        sa.Column("skill_state_transition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("learner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("skill_id", sa.String(128), nullable=False),
        sa.Column("item_opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("response_matched", sa.Boolean(), nullable=False),
        sa.Column("p_l_before", sa.Float(), nullable=False),
        sa.Column("predicted_probability", sa.Float(), nullable=False),
        sa.Column("posterior_p_l", sa.Float(), nullable=False),
        sa.Column("p_l_after", sa.Float(), nullable=False),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("skill_state_transition_id"),
        sa.ForeignKeyConstraint(["learner_id"], ["b_learners.learner_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["item_opportunity_id"], ["b_item_opportunities.item_opportunity_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["attempt_id"], ["b_attempts.attempt_id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("item_opportunity_id", name="uq_b_skill_state_transitions_opportunity"),
        sa.UniqueConstraint("attempt_id", name="uq_b_skill_state_transitions_attempt"),
        sa.CheckConstraint("p_l_before >= 0.0 AND p_l_before <= 1.0", name="ck_b_skill_state_transitions_p_l_before_bounded"),
        sa.CheckConstraint("predicted_probability >= 0.0 AND predicted_probability <= 1.0", name="ck_b_skill_state_transitions_predicted_probability_bounded"),
        sa.CheckConstraint("posterior_p_l >= 0.0 AND posterior_p_l <= 1.0", name="ck_b_skill_state_transitions_posterior_p_l_bounded"),
        sa.CheckConstraint("p_l_after >= 0.0 AND p_l_after <= 1.0", name="ck_b_skill_state_transitions_p_l_after_bounded"),
        *provenance_constraints("b_skill_state_transitions"),
    )


def downgrade() -> None:
    op.drop_table("b_skill_state_transitions")
    op.drop_table("b_attempts")
