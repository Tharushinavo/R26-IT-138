"""BE2 Limited Batch 1 neutral persistence foundations.

Revision ID: 20260722_0002
Revises: 20260722_0001
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260722_0002"
down_revision: str | Sequence[str] | None = "20260722_0001"
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


def provenance_constraints(table: str) -> list[sa.Constraint]:
    return [
        sa.ForeignKeyConstraint(["actor_user_id"], ["app_users.user_id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "source_class IN ('REAL', 'SYNTHETIC', 'IMPORTED', 'TEST')",
            name=f"ck_{table}_source_class",
        ),
        sa.CheckConstraint(
            "(actor_user_id IS NOT NULL) <> (system_actor IS NOT NULL)",
            name=f"ck_{table}_actor_exactly_one",
        ),
        sa.CheckConstraint(
            "environment <> '' AND source_system <> '' AND request_id <> ''",
            name=f"ck_{table}_required_provenance_nonblank",
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "app_users",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supabase_subject", sa.String(255), nullable=False),
        sa.Column("status", sa.String(64), nullable=False),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("supabase_subject", name="uq_app_users_supabase_subject"),
        sa.CheckConstraint("supabase_subject <> ''", name="ck_app_users_subject_nonblank"),
        sa.CheckConstraint("status <> ''", name="ck_app_users_status_nonblank"),
        *provenance_constraints("app_users"),
    )
    op.create_table(
        "b_learners",
        sa.Column("learner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("grade", sa.SmallInteger(), nullable=True),
        sa.Column("status", sa.String(64), nullable=False),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("learner_id"),
        sa.CheckConstraint("grade IS NULL OR grade IN (2, 3)", name="ck_b_learners_grade"),
        sa.CheckConstraint("status <> ''", name="ck_b_learners_status_nonblank"),
        *provenance_constraints("b_learners"),
    )
    op.create_table(
        "app_user_learner_links",
        sa.Column("link_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("learner_id", postgresql.UUID(as_uuid=True), nullable=False),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("link_id"),
        sa.ForeignKeyConstraint(["user_id"], ["app_users.user_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["learner_id"], ["b_learners.learner_id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("user_id", "learner_id", name="uq_app_user_learner_links_pair"),
        *provenance_constraints("app_user_learner_links"),
    )
    op.create_table(
        "b_runtime_bundle_records",
        sa.Column("runtime_bundle_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bundle_version", sa.String(128), nullable=False),
        sa.Column("manifest_checksum", sa.String(64), nullable=False),
        sa.Column("publication_state", sa.String(16), nullable=False),
        sa.Column("approval_status", sa.String(64), nullable=False),
        sa.Column("immutable_after_publication", sa.Boolean(), server_default=sa.false(), nullable=False),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("runtime_bundle_record_id"),
        sa.UniqueConstraint("bundle_version", name="uq_b_runtime_bundle_records_version"),
        sa.UniqueConstraint("manifest_checksum", name="uq_b_runtime_bundle_records_checksum"),
        sa.CheckConstraint("manifest_checksum ~ '^[0-9a-f]{64}$'", name="ck_b_runtime_bundle_records_checksum"),
        sa.CheckConstraint(
            "publication_state IN ('DRAFT', 'PUBLISHED', 'RETIRED')",
            name="ck_b_runtime_bundle_records_publication_state",
        ),
        sa.CheckConstraint(
            "publication_state <> 'PUBLISHED' OR immutable_after_publication",
            name="ck_b_runtime_bundle_records_published_immutable",
        ),
        *provenance_constraints("b_runtime_bundle_records"),
    )
    op.create_table(
        "b_sessions",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("learner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("runtime_bundle_record_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("expires_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("row_version", sa.Integer(), server_default=sa.text("0"), nullable=False),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("session_id"),
        sa.ForeignKeyConstraint(["learner_id"], ["b_learners.learner_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["runtime_bundle_record_id"],
            ["b_runtime_bundle_records.runtime_bundle_record_id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "state IN ('starting', 'active', 'completing', 'completed', 'abandoned', 'expired', 'technical_failed')",
            name="ck_b_sessions_state",
        ),
        sa.CheckConstraint("row_version >= 0", name="ck_b_sessions_row_version"),
        sa.CheckConstraint(
            "state <> 'active' OR runtime_bundle_record_id IS NOT NULL",
            name="ck_b_sessions_active_bundle_required",
        ),
        *provenance_constraints("b_sessions"),
    )
    op.create_index(
        "uq_b_sessions_one_starting_or_active_per_learner",
        "b_sessions",
        ["learner_id"],
        unique=True,
        postgresql_where=sa.text("state IN ('starting', 'active')"),
    )
    op.create_table(
        "b_session_events",
        sa.Column("session_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("session_event_id"),
        sa.ForeignKeyConstraint(["session_id"], ["b_sessions.session_id"], ondelete="RESTRICT"),
        *provenance_constraints("b_session_events"),
    )
    op.create_table(
        "b_idempotency_records",
        sa.Column("idempotency_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("http_method", sa.String(16), nullable=False),
        sa.Column("operation_identifier", sa.String(255), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("processing_status", sa.String(32), nullable=False),
        sa.Column("canonical_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("response_status", sa.SmallInteger(), nullable=True),
        sa.Column("expires_at_utc", sa.DateTime(timezone=True), nullable=False),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("idempotency_record_id"),
        sa.UniqueConstraint(
            "actor_user_id", "http_method", "operation_identifier", "idempotency_key",
            name="uq_b_idempotency_records_scope",
        ),
        sa.CheckConstraint("actor_user_id IS NOT NULL", name="ck_b_idempotency_records_actor_required"),
        sa.CheckConstraint("processing_status <> ''", name="ck_b_idempotency_records_status_nonblank"),
        sa.CheckConstraint("request_fingerprint ~ '^[0-9a-f]{64}$'", name="ck_b_idempotency_records_fingerprint"),
        sa.CheckConstraint("expires_at_utc > created_at_utc", name="ck_b_idempotency_records_expiry"),
        *provenance_constraints("b_idempotency_records"),
    )
    op.create_table(
        "b_audit_events",
        sa.Column("audit_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("audit_event_id"),
        *provenance_constraints("b_audit_events"),
    )


def downgrade() -> None:
    op.drop_table("b_audit_events")
    op.drop_table("b_idempotency_records")
    op.drop_table("b_session_events")
    op.drop_index("uq_b_sessions_one_starting_or_active_per_learner", table_name="b_sessions")
    op.drop_table("b_sessions")
    op.drop_table("b_runtime_bundle_records")
    op.drop_table("app_user_learner_links")
    op.drop_table("b_learners")
    op.drop_table("app_users")
