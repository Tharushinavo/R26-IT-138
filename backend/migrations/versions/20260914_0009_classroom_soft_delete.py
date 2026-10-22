"""Teacher-initiated classroom deletion, as a SOFT delete (2026-09-14).

A teacher deletes a classroom from the Component 3 dashboard. Nothing is erased:

* ``classrooms`` gains ``deleted_at_utc`` / ``deleted_by_user_id``. A deleted classroom stops
  being listed, fetched, invited to or decided on, but its row -- and every foreign key that
  points at it with ON DELETE RESTRICT -- stays intact.
* ``classroom_memberships.state`` gains ``REMOVED``: every PENDING or APPROVED membership of
  the deleted classroom becomes REMOVED. That frees the learner from the one-APPROVED-per-
  learner partial unique index, so they can join another classroom with a new code. The
  learner's own data (profile, B/C sessions, attempts) is keyed by ``learner_id`` and is not
  touched. ``REMOVED`` carries a decision time and decider like APPROVED/REJECTED.
* The per-teacher unique classroom name ignores deleted classrooms, so "2A" can be created
  again after "2A" was deleted.

Revision ID: 20260914_0009
Revises: 20260816_0008
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260914_0009"
down_revision: str | Sequence[str] | None = "20260816_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("classrooms", sa.Column("deleted_at_utc", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "classrooms",
        sa.Column(
            "deleted_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("app_users.user_id", ondelete="RESTRICT", name="fk_classrooms_deleted_by_user_id_app_users"),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        "ck_classrooms_deletion_pair",
        "classrooms",
        "(deleted_at_utc IS NULL) = (deleted_by_user_id IS NULL)",
    )

    op.drop_index("uq_classrooms_teacher_normalized_name", table_name="classrooms")
    op.create_index(
        "uq_classrooms_teacher_normalized_name",
        "classrooms",
        ["teacher_profile_id", sa.text("lower(btrim(name))")],
        unique=True,
        postgresql_where=sa.text("name IS NOT NULL AND deleted_at_utc IS NULL"),
    )

    op.drop_constraint("ck_classroom_memberships_state", "classroom_memberships", type_="check")
    op.create_check_constraint(
        "ck_classroom_memberships_state",
        "classroom_memberships",
        "state IN ('PENDING', 'APPROVED', 'REJECTED', 'REMOVED')",
    )
    op.drop_constraint("ck_classroom_memberships_decision", "classroom_memberships", type_="check")
    op.create_check_constraint(
        "ck_classroom_memberships_decision",
        "classroom_memberships",
        "(state = 'PENDING' AND decided_at_utc IS NULL AND decided_by_user_id IS NULL) OR "
        "(state IN ('APPROVED', 'REJECTED', 'REMOVED') AND decided_at_utc IS NOT NULL AND decided_by_user_id IS NOT NULL)",
    )


def downgrade() -> None:
    # Pre-0009 has no way to say "deleted". The suite's migration-reversibility tests downgrade
    # a shared test database that holds deleted classrooms, so refusing here would break them
    # permanently. Instead: a REMOVED membership becomes REJECTED (decided, not counted), and a
    # deleted classroom loses its name -- its join code is already revoked and it has no
    # counted members, so it is inert, and a NULL name keeps it out of the name index where it
    # could otherwise collide with a live classroom of the same name.
    op.execute("UPDATE classroom_memberships SET state = 'REJECTED' WHERE state = 'REMOVED'")
    op.execute("UPDATE classrooms SET name = NULL WHERE deleted_at_utc IS NOT NULL")
    op.drop_constraint("ck_classroom_memberships_decision", "classroom_memberships", type_="check")
    op.create_check_constraint(
        "ck_classroom_memberships_decision",
        "classroom_memberships",
        "(state = 'PENDING' AND decided_at_utc IS NULL AND decided_by_user_id IS NULL) OR "
        "(state IN ('APPROVED', 'REJECTED') AND decided_at_utc IS NOT NULL AND decided_by_user_id IS NOT NULL)",
    )
    op.drop_constraint("ck_classroom_memberships_state", "classroom_memberships", type_="check")
    op.create_check_constraint(
        "ck_classroom_memberships_state",
        "classroom_memberships",
        "state IN ('PENDING', 'APPROVED', 'REJECTED')",
    )
    op.drop_index("uq_classrooms_teacher_normalized_name", table_name="classrooms")
    op.create_index(
        "uq_classrooms_teacher_normalized_name",
        "classrooms",
        ["teacher_profile_id", sa.text("lower(btrim(name))")],
        unique=True,
        postgresql_where=sa.text("name IS NOT NULL"),
    )
    op.drop_constraint("ck_classrooms_deletion_pair", "classrooms", type_="check")
    op.drop_column("classrooms", "deleted_by_user_id")
    op.drop_column("classrooms", "deleted_at_utc")
