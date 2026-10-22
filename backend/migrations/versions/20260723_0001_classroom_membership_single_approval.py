"""Enforce at most one APPROVED classroom membership per learner.

Revision ID: 20260723_0001
Revises: 20260722_0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260723_0001"
down_revision: str | Sequence[str] | None = "20260722_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_classroom_memberships_one_approved_per_learner",
        "classroom_memberships",
        ["learner_id"],
        unique=True,
        postgresql_where=sa.text("state = 'APPROVED'"),
    )


def downgrade() -> None:
    op.drop_index("uq_classroom_memberships_one_approved_per_learner", table_name="classroom_memberships")
