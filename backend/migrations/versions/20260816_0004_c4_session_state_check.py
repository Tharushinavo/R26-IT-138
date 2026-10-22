"""Component C Phase 4: c_sessions.state CHECK constraint (SUPERVISOR RULING (lead), Phase 4
work order, c_sessions.state section). Reuses SESSION_STATES exactly, unchanged, all seven
values -- couples C's lifecycle vocabulary to the same constant B's ck_b_sessions_state uses. The
only migration authorized this batch.

Revision ID: 20260816_0004
Revises: 20260816_0003
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260816_0004"
down_revision: str | Sequence[str] | None = "20260816_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_c_sessions_state",
        "c_sessions",
        "state IN ('starting', 'active', 'completing', 'completed', 'abandoned', 'expired', 'technical_failed')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_c_sessions_state", "c_sessions", type_="check")
