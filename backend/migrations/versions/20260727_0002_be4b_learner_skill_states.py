"""BE4b (BEplan §9 BE4.2): per-learner, per-skill BKT state (P(L) + observation count).

Persistence only — no scientific math here. Adds one PRIVATE table, ``b_learner_skill_states``:
one row per (learner, skill), holding the current P(L) mastery estimate and an observation
count. BE4b READS this table and INITIALIZES missing rows from the pinned bundle's TEST-fixture
P(L0) priors; it never updates an existing row. BKT updates (BE4c) will own writes to ``p_l`` /
``observation_count`` after the first real attempt. No cross-skill transfer: each row is
independent, keyed by (learner_id, skill_id).

Revision ID: 20260727_0002
Revises: 20260727_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260727_0002"
down_revision: str | Sequence[str] | None = "20260727_0001"
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
        "b_learner_skill_states",
        sa.Column("learner_skill_state_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("learner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("skill_id", sa.String(128), nullable=False),
        sa.Column("p_l", sa.Float(), nullable=False),
        sa.Column("observation_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("learner_skill_state_id"),
        sa.ForeignKeyConstraint(["learner_id"], ["b_learners.learner_id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("learner_id", "skill_id", name="uq_b_learner_skill_states_pair"),
        sa.CheckConstraint("p_l >= 0.0 AND p_l <= 1.0", name="ck_b_learner_skill_states_p_l_bounded"),
        sa.CheckConstraint("observation_count >= 0", name="ck_b_learner_skill_states_observation_count"),
        *provenance_constraints("b_learner_skill_states"),
    )


def downgrade() -> None:
    op.drop_table("b_learner_skill_states")
