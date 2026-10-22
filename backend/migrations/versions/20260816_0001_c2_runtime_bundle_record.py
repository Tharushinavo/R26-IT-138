"""Component C Phase 2: c_runtime_bundle_records only.

Mirrors ``20260722_0003``-adjacent ``b_runtime_bundle_records`` (see
``app.infrastructure.persistence_models.RuntimeBundleRecord``) column set and constraint style
exactly, for Component C's own runtime-bundle manifests
(``prabathi-component-c-live-engine``). No relationship to any B table. No other table is
created by this migration -- the other nine Phase 3 tables are out of scope for Phase 2.

Revision ID: 20260816_0001
Revises: 20260801_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260816_0001"
down_revision: str | Sequence[str] | None = "20260801_0001"
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
        "c_runtime_bundle_records",
        sa.Column("c_runtime_bundle_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bundle_version", sa.String(128), nullable=False),
        sa.Column("manifest_checksum", sa.String(64), nullable=False),
        sa.Column("publication_state", sa.String(16), nullable=False),
        sa.Column("approval_status", sa.String(64), nullable=False),
        sa.Column("immutable_after_publication", sa.Boolean(), server_default=sa.false(), nullable=False),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("c_runtime_bundle_record_id"),
        sa.UniqueConstraint("bundle_version", name="uq_c_runtime_bundle_records_version"),
        sa.UniqueConstraint("manifest_checksum", name="uq_c_runtime_bundle_records_checksum"),
        sa.CheckConstraint("manifest_checksum ~ '^[0-9a-f]{64}$'", name="ck_c_runtime_bundle_records_checksum"),
        sa.CheckConstraint(
            "publication_state IN ('DRAFT', 'PUBLISHED', 'RETIRED')",
            name="ck_c_runtime_bundle_records_publication_state",
        ),
        sa.CheckConstraint(
            "publication_state <> 'PUBLISHED' OR immutable_after_publication",
            name="ck_c_runtime_bundle_records_published_immutable",
        ),
        *provenance_constraints("c_runtime_bundle_records"),
    )


def downgrade() -> None:
    op.drop_table("c_runtime_bundle_records")
