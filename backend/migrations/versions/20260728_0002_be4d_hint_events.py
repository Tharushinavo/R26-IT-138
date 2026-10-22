"""BE4d (BEplan §9 BE4.5): governed L1/L2/L3 hint events.

Persistence only — no scientific math here (the service layer calls
``app.infrastructure.live_engine.adapter.LiveEngineAdapter.get_hint`` for the actual catalogue
lookup). Adds one PRIVATE table:

- ``b_hint_events``: one row per governed assist request on an opportunity, SEPARATE from
  ``b_attempts``/``b_skill_state_transitions`` — a hint request is never a mastery/BKT
  observation. ``uq_b_hint_events_opportunity_level`` prevents a duplicate row at the same
  escalation level for the same opportunity.

Column names avoid every ``PROHIBITED_COLUMN_TERMS`` entry (see
``tests/test_be2_architecture_guards.py``): the governed hint level is spelled ``assist_level``,
not ``hint_level``. Only the catalogue reconstruction key (``content_id`` + ``catalogue_version``
+ ``catalogue_checksum``) is persisted — never the hint text itself.

Revision ID: 20260728_0002
Revises: 20260728_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260728_0002"
down_revision: str | Sequence[str] | None = "20260728_0001"
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
        "b_hint_events",
        sa.Column("assist_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("learner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assist_level", sa.SmallInteger(), nullable=False),
        sa.Column("content_id", sa.String(255), nullable=False),
        sa.Column("catalogue_version", sa.String(128), nullable=False),
        sa.Column("catalogue_checksum", sa.String(64), nullable=False),
        sa.Column("requested_at_utc", sa.DateTime(timezone=True), nullable=False),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("assist_event_id"),
        sa.ForeignKeyConstraint(["item_opportunity_id"], ["b_item_opportunities.item_opportunity_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["learner_id"], ["b_learners.learner_id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("item_opportunity_id", "assist_level", name="uq_b_hint_events_opportunity_level"),
        sa.CheckConstraint("assist_level >= 1 AND assist_level <= 3", name="ck_b_hint_events_assist_level_bounded"),
        *provenance_constraints("b_hint_events"),
    )


def downgrade() -> None:
    op.drop_table("b_hint_events")
