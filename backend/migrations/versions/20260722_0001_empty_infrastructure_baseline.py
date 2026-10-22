"""Empty BE1 infrastructure baseline.

Revision ID: 20260722_0001
Revises: None
"""

from collections.abc import Sequence


revision: str = "20260722_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create no business tables."""


def downgrade() -> None:
    """Remove no business tables."""
