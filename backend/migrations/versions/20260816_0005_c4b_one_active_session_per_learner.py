"""Component C Phase 4b: partial unique index enforcing at most one starting/active c_sessions
row per learner. Mirrors uq_b_sessions_one_starting_or_active_per_learner exactly (same predicate
shape, state IN ('starting', 'active')). The ONE migration authorized this batch.

Revision ID: 20260816_0005
Revises: 20260816_0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260816_0005"
down_revision: str | Sequence[str] | None = "20260816_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_c_sessions_one_starting_or_active_per_learner",
        "c_sessions",
        ["student_id"],
        unique=True,
        postgresql_where=sa.text("state IN ('starting', 'active')"),
    )


def downgrade() -> None:
    op.drop_index("uq_c_sessions_one_starting_or_active_per_learner", table_name="c_sessions")
