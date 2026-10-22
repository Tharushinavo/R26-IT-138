"""Add limited profile and classroom persistence foundations.

Revision ID: 20260722_0004
Revises: 20260722_0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260722_0004"
down_revision: str | Sequence[str] | None = "20260722_0003"
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
    op.add_column("app_users", sa.Column("profile_type", sa.String(16), nullable=True))
    op.create_check_constraint("ck_app_users_profile_type", "app_users", "profile_type IS NULL OR profile_type IN ('LEARNER', 'TEACHER')")
    op.add_column("b_learners", sa.Column("name", sa.String(255), nullable=True))
    op.create_check_constraint("ck_b_learners_name_nonblank", "b_learners", "name IS NULL OR btrim(name) <> ''")
    op.create_unique_constraint("uq_app_user_learner_links_user", "app_user_learner_links", ["user_id"])
    op.create_unique_constraint("uq_app_user_learner_links_learner", "app_user_learner_links", ["learner_id"])

    op.create_table(
        "teacher_profiles",
        sa.Column("teacher_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("teacher_profile_id"),
        sa.ForeignKeyConstraint(["user_id"], ["app_users.user_id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("user_id", name="uq_teacher_profiles_user"),
        sa.CheckConstraint("btrim(name) <> ''", name="ck_teacher_profiles_name_nonblank"),
        *provenance_constraints("teacher_profiles"),
    )
    op.create_table(
        "classrooms",
        sa.Column("classroom_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("teacher_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("grade", sa.String(16), nullable=False),
        sa.Column("row_version", sa.Integer(), server_default=sa.text("0"), nullable=False),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("classroom_id"),
        sa.ForeignKeyConstraint(["teacher_profile_id"], ["teacher_profiles.teacher_profile_id"], ondelete="RESTRICT"),
        sa.CheckConstraint("grade IN ('GRADE_2', 'GRADE_3')", name="ck_classrooms_grade"),
        sa.CheckConstraint("name IS NULL OR btrim(name) <> ''", name="ck_classrooms_name_nonblank"),
        sa.CheckConstraint("row_version >= 0", name="ck_classrooms_row_version"),
        *provenance_constraints("classrooms"),
    )
    op.create_index("uq_classrooms_teacher_normalized_name", "classrooms", ["teacher_profile_id", sa.text("lower(btrim(name))")], unique=True, postgresql_where=sa.text("name IS NOT NULL"))
    op.create_table(
        "classroom_invites",
        sa.Column("classroom_invite_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("classroom_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("row_version", sa.Integer(), server_default=sa.text("0"), nullable=False),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("classroom_invite_id"),
        sa.ForeignKeyConstraint(["classroom_id"], ["classrooms.classroom_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["app_users.user_id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("token_hash", name="uq_classroom_invites_token_hash"),
        sa.CheckConstraint("token_hash ~ '^[0-9a-f]{64}$'", name="ck_classroom_invites_token_hash"),
        sa.CheckConstraint("row_version >= 0", name="ck_classroom_invites_row_version"),
        *provenance_constraints("classroom_invites"),
    )
    op.create_table(
        "classroom_memberships",
        sa.Column("classroom_membership_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("classroom_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("learner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("classroom_invite_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("requested_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("row_version", sa.Integer(), server_default=sa.text("0"), nullable=False),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("classroom_membership_id"),
        sa.ForeignKeyConstraint(["classroom_id"], ["classrooms.classroom_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["learner_id"], ["b_learners.learner_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["classroom_invite_id"], ["classroom_invites.classroom_invite_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["decided_by_user_id"], ["app_users.user_id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("classroom_id", "learner_id", name="uq_classroom_memberships_pair"),
        sa.CheckConstraint("state IN ('PENDING', 'APPROVED', 'REJECTED')", name="ck_classroom_memberships_state"),
        sa.CheckConstraint("(state = 'PENDING' AND decided_at_utc IS NULL AND decided_by_user_id IS NULL) OR (state IN ('APPROVED', 'REJECTED') AND decided_at_utc IS NOT NULL AND decided_by_user_id IS NOT NULL)", name="ck_classroom_memberships_decision"),
        sa.CheckConstraint("row_version >= 0", name="ck_classroom_memberships_row_version"),
        *provenance_constraints("classroom_memberships"),
    )
    op.execute("""
        CREATE FUNCTION enforce_app_user_profile_type_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.profile_type IS NOT NULL AND NEW.profile_type IS DISTINCT FROM OLD.profile_type THEN
                RAISE EXCEPTION 'profile type is immutable' USING ERRCODE = '23514', CONSTRAINT = 'ck_app_users_profile_type_immutable';
            END IF;
            RETURN NEW;
        END;
        $$
    """)
    op.execute("CREATE TRIGGER trg_app_users_profile_type_immutable BEFORE UPDATE OF profile_type ON app_users FOR EACH ROW EXECUTE FUNCTION enforce_app_user_profile_type_immutable()")


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_app_users_profile_type_immutable ON app_users")
    op.execute("DROP FUNCTION enforce_app_user_profile_type_immutable()")
    op.drop_table("classroom_memberships")
    op.drop_table("classroom_invites")
    op.drop_index("uq_classrooms_teacher_normalized_name", table_name="classrooms")
    op.drop_table("classrooms")
    op.drop_table("teacher_profiles")
    op.drop_constraint("uq_app_user_learner_links_learner", "app_user_learner_links", type_="unique")
    op.drop_constraint("uq_app_user_learner_links_user", "app_user_learner_links", type_="unique")
    op.drop_constraint("ck_b_learners_name_nonblank", "b_learners", type_="check")
    op.drop_column("b_learners", "name")
    op.drop_constraint("ck_app_users_profile_type", "app_users", type_="check")
    op.drop_column("app_users", "profile_type")
