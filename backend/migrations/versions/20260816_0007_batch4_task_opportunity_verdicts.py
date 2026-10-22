"""Component C backend remediation, batch 4 (Amendment A-1): the ONE new table this amendment
authorizes -- ``c_task_opportunity_verdicts``. Mirrors ``app.infrastructure.persistence_models``'s
new ``CTaskOpportunityVerdictRecord`` model exactly; see that class's own docstring for the full
K3/K4 register trace, both rulings, and both owner conditions this table and its two CHECK
constraints satisfy. No trigger, no seed data, no second table -- see
``backend/buildLog1.md``'s batch 4 entry for the full R0 trace of what this migration does and
does not do.

Revision ID: 20260816_0007
Revises: 20260816_0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260816_0007"
down_revision: str | Sequence[str] | None = "20260816_0006"
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
        "c_task_opportunity_verdicts",
        sa.Column("c_task_opportunity_verdict_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("c_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_task_instance_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_index", sa.Integer(), nullable=False),
        sa.Column("validator_check", sa.String(64), nullable=False),
        sa.Column("verdict_detail", sa.String(500), nullable=False),
        sa.Column("supersedes_verdict_id", postgresql.UUID(as_uuid=True), nullable=True),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("c_task_opportunity_verdict_id"),
        sa.ForeignKeyConstraint(["c_session_id"], ["c_sessions.c_session_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["game_task_instance_id"], ["c_task_instances.c_task_instance_id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_verdict_id"],
            ["c_task_opportunity_verdicts.c_task_opportunity_verdict_id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "validator_check <> ''", name="ck_c_task_opportunity_verdicts_validator_check_nonblank"
        ),
        sa.CheckConstraint(
            "supersedes_verdict_id IS DISTINCT FROM c_task_opportunity_verdict_id",
            name="ck_c_task_opportunity_verdicts_not_self_superseding",
        ),
        *provenance_constraints("c_task_opportunity_verdicts"),
    )


def downgrade() -> None:
    op.drop_table("c_task_opportunity_verdicts")
