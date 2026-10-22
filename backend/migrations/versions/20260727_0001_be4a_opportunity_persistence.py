"""BE4a (BEplan §9 BE4.1): private opportunity/task-instance/presentation-token persistence.

Persistence only — no selection science, no adapter wiring. Adds three PRIVATE tables:
``b_item_opportunities`` (one OPEN opportunity per active session, enforced by a partial unique
index), ``b_task_instances`` (SAFE presentation subset + PRIVATE grading/provenance columns —
schema only, populated by BE4b), and ``b_presentation_tokens`` (opaque short-lived tokens bound
to session/opportunity/learner/runtime-bundle).

Revision ID: 20260727_0001
Revises: 20260723_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260727_0001"
down_revision: str | Sequence[str] | None = "20260723_0001"
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
        "b_item_opportunities",
        sa.Column("item_opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("learner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("skill_id", sa.String(128), nullable=False),
        sa.Column("item_template_id", sa.String(128), nullable=False),
        sa.Column("opportunity_index", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("presented_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timeout_deadline_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("selection_provenance", postgresql.JSONB(), nullable=False),
        sa.Column("row_version", sa.Integer(), server_default=sa.text("0"), nullable=False),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("item_opportunity_id"),
        sa.ForeignKeyConstraint(["session_id"], ["b_sessions.session_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["learner_id"], ["b_learners.learner_id"], ondelete="RESTRICT"),
        sa.CheckConstraint("state IN ('OPEN', 'CLOSED')", name="ck_b_item_opportunities_state"),
        sa.CheckConstraint("row_version >= 0", name="ck_b_item_opportunities_row_version"),
        sa.CheckConstraint("timeout_deadline_utc > created_at_utc", name="ck_b_item_opportunities_timeout_after_created"),
        *provenance_constraints("b_item_opportunities"),
    )
    op.create_index(
        "uq_b_item_opportunities_one_open_per_session",
        "b_item_opportunities",
        ["session_id"],
        unique=True,
        postgresql_where=sa.text("state = 'OPEN'"),
    )

    op.create_table(
        "b_task_instances",
        sa.Column("task_instance_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_template_id", sa.String(128), nullable=False),
        sa.Column("skill_id", sa.String(128), nullable=False),
        sa.Column("grade", sa.SmallInteger(), nullable=False),
        sa.Column("difficulty_level", sa.String(64), nullable=False),
        sa.Column("representation_type", sa.String(64), nullable=False),
        sa.Column("response_format", sa.String(64), nullable=False),
        sa.Column("prompt", postgresql.JSONB(), nullable=False),
        sa.Column("presented_choices", postgresql.JSONB(), nullable=False),
        sa.Column("correct_answer", sa.String(255), nullable=False),
        sa.Column("allowed_equivalent_answers", postgresql.JSONB(), nullable=False),
        sa.Column("distractor_candidates", postgresql.JSONB(), nullable=False),
        sa.Column("distractor_rule_ids", postgresql.JSONB(), nullable=False),
        sa.Column("generated_operands", postgresql.JSONB(), nullable=False),
        sa.Column("generation_seed", sa.BigInteger(), nullable=False),
        sa.Column("applied_guard_ids", postgresql.JSONB(), nullable=False),
        sa.Column("catalogue_version", sa.String(128), nullable=False),
        sa.Column("catalogue_checksum", sa.String(64), nullable=False),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("task_instance_id"),
        sa.ForeignKeyConstraint(["item_opportunity_id"], ["b_item_opportunities.item_opportunity_id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("item_opportunity_id", name="uq_b_task_instances_opportunity"),
        sa.CheckConstraint("grade IN (2, 3)", name="ck_b_task_instances_grade"),
        *provenance_constraints("b_task_instances"),
    )

    op.create_table(
        "b_presentation_tokens",
        sa.Column("presentation_token_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("learner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("runtime_bundle_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("issued_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at_utc", sa.DateTime(timezone=True), nullable=False),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("presentation_token_id"),
        sa.ForeignKeyConstraint(["session_id"], ["b_sessions.session_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["item_opportunity_id"], ["b_item_opportunities.item_opportunity_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["learner_id"], ["b_learners.learner_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["runtime_bundle_record_id"], ["b_runtime_bundle_records.runtime_bundle_record_id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("token_hash", name="uq_b_presentation_tokens_token_hash"),
        sa.CheckConstraint("token_hash ~ '^[0-9a-f]{64}$'", name="ck_b_presentation_tokens_token_hash"),
        sa.CheckConstraint("expires_at_utc > issued_at_utc", name="ck_b_presentation_tokens_expiry"),
        *provenance_constraints("b_presentation_tokens"),
    )


def downgrade() -> None:
    op.drop_table("b_presentation_tokens")
    op.drop_table("b_task_instances")
    op.drop_index("uq_b_item_opportunities_one_open_per_session", table_name="b_item_opportunities")
    op.drop_table("b_item_opportunities")
