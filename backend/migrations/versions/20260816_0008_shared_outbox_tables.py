"""Component C batch 9c-1a (Master Build Plan v3.0 Section 11 Phase 9; 9b_9c plan Track 9c,
"9c-1 -- the tables and the routing"): the two shared outbox tables Phase 9's own text already
authorizes -- ``outbox_events`` and ``contract_deliveries``. Deliberately unprefixed (no ``b_``/
``c_``) because they are shared infrastructure, not shared ownership (Component B owner's
condition 1). Mirrors ``app.infrastructure.persistence_models``'s new ``OutboxEventRecord`` and
``ContractDeliveryRecord`` models exactly; see those classes' own docstrings for the full
ownership mechanism (condition 2), the reason ``contract_name`` is not enumerated (condition 2
again), and the reason neither table carries a learner identifier (condition 3 / 9c-0). No
trigger, no seed data, no third table -- see ``backend/buildLog1.md``'s 9c-1a entry for the full
verification trace.

Revision ID: 20260816_0008
Revises: 20260816_0007
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260816_0008"
down_revision: str | Sequence[str] | None = "20260816_0007"
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
        "outbox_events",
        sa.Column("outbox_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owning_component", sa.String(1), nullable=False),
        sa.Column("contract_name", sa.String(32), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("outbox_event_id"),
        sa.CheckConstraint("owning_component IN ('B', 'C')", name="ck_outbox_events_owning_component"),
        sa.CheckConstraint("contract_name <> ''", name="ck_outbox_events_contract_name_nonblank"),
        *provenance_constraints("outbox_events"),
    )
    op.create_table(
        "contract_deliveries",
        sa.Column("contract_delivery_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("outbox_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("delivery_detail", sa.String(500), nullable=True),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("contract_delivery_id"),
        sa.ForeignKeyConstraint(["outbox_event_id"], ["outbox_events.outbox_event_id"], ondelete="RESTRICT"),
        sa.CheckConstraint("outcome <> ''", name="ck_contract_deliveries_outcome_nonblank"),
        sa.CheckConstraint(
            "delivery_detail IS NULL OR delivery_detail <> ''",
            name="ck_contract_deliveries_delivery_detail_nonblank_or_null",
        ),
        *provenance_constraints("contract_deliveries"),
    )


def downgrade() -> None:
    op.drop_table("contract_deliveries")
    op.drop_table("outbox_events")
