"""Component D (Component D authorization, owner decision D-011 A1, 2026-10-21): the three
cognitive-profiling tables -- ``d_learner_state``, ``d_interactions`` and
``d_cognitive_profiles``.

Mirrors ``app.infrastructure.persistence_models``'s ``DLearnerStateRecord``,
``DInteractionRecord`` and ``DCognitiveProfileRecord`` exactly; those classes' docstrings carry
the reasoning this file does not repeat -- why the recommendation text is NOT stored, why
``session_id`` is globally unique, and why ``features`` is JSONB.

NAMES. ``response_matched`` and ``assist_used`` are the host's own names for these concepts
(``b_attempts.response_matched``; ``b_hint_events.assist_*``), adopted under D-011 A4 in place of
compD's ``is_correct`` and ``hint_used``. **No column exemption was asked for or granted** --
``AUTHORIZED_D_COLUMN_EXCEPTIONS`` deliberately does not exist, because with the host's own names
there is nothing left to exempt.

The provenance helpers below are copied from ``20260816_0008_shared_outbox_tables.py`` rather than
imported from it: a migration must keep describing the schema as it was at ITS revision, so a
later edit to 0008 can never retroactively change what 0010 creates.

Revision ID: 20261021_0010
Revises: 20260914_0009
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20261021_0010"
down_revision: str | Sequence[str] | None = "20260914_0009"
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
        sa.CheckConstraint(
            "source_class IN ('REAL', 'SYNTHETIC', 'IMPORTED', 'TEST')", name=f"ck_{prefix}_source_class"
        ),
        sa.CheckConstraint(
            "(actor_user_id IS NOT NULL) <> (system_actor IS NOT NULL)", name=f"ck_{prefix}_actor_exactly_one"
        ),
        sa.CheckConstraint(
            "environment <> '' AND source_system <> '' AND request_id <> ''",
            name=f"ck_{prefix}_required_provenance_nonblank",
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "d_learner_state",
        sa.Column("learner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("intro_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("language", sa.String(2), nullable=False),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("learner_id"),
        sa.ForeignKeyConstraint(["learner_id"], ["b_learners.learner_id"], ondelete="RESTRICT"),
        sa.CheckConstraint("language IN ('en', 'si')", name="ck_d_learner_state_language"),
        *provenance_constraints("d_learner_state"),
    )

    op.create_table(
        "d_interactions",
        sa.Column("d_interaction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("learner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_id", sa.String(128), nullable=False),
        sa.Column("topic", sa.String(16), nullable=False),
        sa.Column("difficulty", sa.String(8), nullable=False),
        sa.Column("response_time_sec", sa.Float(), nullable=False),
        sa.Column("attempts", sa.SmallInteger(), nullable=False),
        sa.Column("response_matched", sa.Boolean(), nullable=False),
        sa.Column("assist_used", sa.Boolean(), nullable=False),
        sa.Column("click_count", sa.Integer(), nullable=False),
        sa.Column("session_time_sec", sa.Float(), nullable=False),
        sa.Column("time_between_actions", sa.Float(), nullable=False),
        sa.Column("error_type", sa.String(16), nullable=False),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("d_interaction_id"),
        sa.ForeignKeyConstraint(["learner_id"], ["b_learners.learner_id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("session_id", "question_id", name="uq_d_interactions_session_question"),
        sa.CheckConstraint(
            "topic IN ('Counting', 'Addition', 'Subtraction', 'Division')", name="ck_d_interactions_topic"
        ),
        sa.CheckConstraint("difficulty IN ('Easy', 'Medium', 'Hard')", name="ck_d_interactions_difficulty"),
        sa.CheckConstraint(
            "error_type IN ('none', 'calculation', 'conceptual', 'careless', 'unknown')",
            name="ck_d_interactions_error_type",
        ),
        sa.CheckConstraint("response_time_sec >= 0", name="ck_d_interactions_response_time_sec_nonnegative"),
        sa.CheckConstraint("session_time_sec >= 0", name="ck_d_interactions_session_time_sec_nonnegative"),
        sa.CheckConstraint(
            "time_between_actions >= 0", name="ck_d_interactions_time_between_actions_nonnegative"
        ),
        sa.CheckConstraint("click_count >= 0", name="ck_d_interactions_click_count_nonnegative"),
        sa.CheckConstraint("attempts >= 1", name="ck_d_interactions_attempts_at_least_one"),
        sa.CheckConstraint("question_id <> ''", name="ck_d_interactions_question_id_nonblank"),
        *provenance_constraints("d_interactions"),
    )

    op.create_table(
        "d_cognitive_profiles",
        sa.Column("d_cognitive_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("learner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("memory_level", sa.String(16), nullable=False),
        sa.Column("attention_level", sa.String(16), nullable=False),
        sa.Column("number_sense_level", sa.String(16), nullable=False),
        sa.Column("processing_speed_level", sa.String(16), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("model_version", sa.String(64), nullable=False),
        sa.Column("features", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("d_cognitive_profile_id"),
        sa.ForeignKeyConstraint(["learner_id"], ["b_learners.learner_id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("session_id", name="uq_d_cognitive_profiles_session"),
        sa.CheckConstraint(
            "memory_level IN ('low', 'medium', 'high')", name="ck_d_cognitive_profiles_memory_level"
        ),
        sa.CheckConstraint(
            "attention_level IN ('low', 'medium', 'high')", name="ck_d_cognitive_profiles_attention_level"
        ),
        sa.CheckConstraint(
            "number_sense_level IN ('low', 'medium', 'high')",
            name="ck_d_cognitive_profiles_number_sense_level",
        ),
        sa.CheckConstraint(
            "processing_speed_level IN ('Slow', 'Moderate', 'Fast')",
            name="ck_d_cognitive_profiles_processing_speed_level",
        ),
        sa.CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 1",
            name="ck_d_cognitive_profiles_confidence_score_unit_interval",
        ),
        sa.CheckConstraint("model_version <> ''", name="ck_d_cognitive_profiles_model_version_nonblank"),
        *provenance_constraints("d_cognitive_profiles"),
    )
    # Created separately rather than inline: the index is DESC on generated_at, which
    # `op.create_table` cannot express.
    op.create_index(
        "ix_d_cognitive_profiles_learner_generated_at",
        "d_cognitive_profiles",
        ["learner_id", sa.text("generated_at DESC")],
    )


def downgrade() -> None:
    # Reverse creation order: d_interactions and d_cognitive_profiles both reference b_learners,
    # and nothing references these three, so the only ordering that matters is dropping the index
    # with its table.
    op.drop_index("ix_d_cognitive_profiles_learner_generated_at", table_name="d_cognitive_profiles")
    op.drop_table("d_cognitive_profiles")
    op.drop_table("d_interactions")
    op.drop_table("d_learner_state")
