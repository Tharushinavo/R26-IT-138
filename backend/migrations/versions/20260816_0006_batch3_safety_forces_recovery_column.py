"""Component C backend remediation, batch 3 (F-2): adds `safety_forces_recovery` to
`c_policy_decisions`, mirroring the existing sibling column on `c_scaffold_events` exactly
(Boolean, NOT NULL, no default at the ORM level). A temporary server_default is applied for the
ADD COLUMN step only (the table may not be empty in every environment this runs against) and
dropped immediately after, so the column's final shape matches the ORM model -- NOT NULL, no
default -- exactly.

This is the column half of F-2 only. The write (decide_and_persist_adaptation persisting
decide_adaptation_with_safety_flags's activate_recovery_flag into this column) and the read
(task_service.py's incorrect-answer branch reading it back) are application-code changes, not
migration content -- see backend/buildLog1.md for this batch's full R0 trace.

Revision ID: 20260816_0006
Revises: 20260816_0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260816_0006"
down_revision: str | Sequence[str] | None = "20260816_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "c_policy_decisions",
        sa.Column("safety_forces_recovery", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("c_policy_decisions", "safety_forces_recovery", server_default=None)


def downgrade() -> None:
    op.drop_column("c_policy_decisions", "safety_forces_recovery")
