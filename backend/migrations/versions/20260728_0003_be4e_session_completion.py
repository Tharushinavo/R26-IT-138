"""BE4e (BEplan §9 BE4.6): private session-completion aggregate/certification result tables.

Persistence only — no scientific math here (the service layer calls
``app.infrastructure.live_engine.adapter.LiveEngineAdapter.aggregate_session``/
``plausibility_floor``/``evaluate``/``certify_skill`` for the actual computation). Adds two
PRIVATE, immutable tables:

- ``b_session_aggregate_results``: one row per completed session — session-level aggregate
  statistics (first-attempt match rate, completion counts, retries, assisted-opportunity count,
  response-time stats, outcome-pattern distribution).
- ``b_skill_certification_results``: one row per (session, skill) roll-up — the TEST-fixture
  plausibility-check status and certification decision.

Column names avoid every ``PROHIBITED_COLUMN_TERMS`` entry (see
``tests/test_be2_architecture_guards.py``): ``outcome_pattern_distribution`` not
``error_class_distribution``, ``assisted_opportunity_count`` not ``hint_bearing_opportunities``,
``skill_estimate`` not ``mastery``/``p_l``, ``threshold_met_flag`` not ``certified_flag``,
``plausibility_status`` not ``guess_guard_status``, ``first_attempt_match_count``/``_rate`` not
``first_attempt_correct_count``/``_rate``.

Revision ID: 20260728_0003
Revises: 20260728_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260728_0003"
down_revision: str | Sequence[str] | None = "20260728_0002"
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
        "b_session_aggregate_results",
        sa.Column("session_aggregate_result_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("learner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("opportunity_count", sa.Integer(), nullable=False),
        sa.Column("first_attempt_match_rate", sa.Float(), nullable=True),
        sa.Column("completion_count", sa.Integer(), nullable=False),
        sa.Column("completion_rate", sa.Float(), nullable=True),
        sa.Column("total_retry_count", sa.Integer(), nullable=False),
        sa.Column("assisted_opportunity_count", sa.Integer(), nullable=False),
        sa.Column("response_time_mean_ms", sa.Float(), nullable=True),
        sa.Column("response_time_median_ms", sa.Float(), nullable=True),
        sa.Column("response_time_std_ms", sa.Float(), nullable=True),
        sa.Column("outcome_pattern_distribution", postgresql.JSONB(), nullable=False),
        sa.Column("skill_ids_practiced", postgresql.JSONB(), nullable=False),
        sa.Column("completion_policy_version", sa.String(64), nullable=False),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("session_aggregate_result_id"),
        sa.ForeignKeyConstraint(["session_id"], ["b_sessions.session_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["learner_id"], ["b_learners.learner_id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("session_id", name="uq_b_session_aggregate_results_session"),
        sa.CheckConstraint(
            "first_attempt_match_rate IS NULL OR (first_attempt_match_rate >= 0.0 AND first_attempt_match_rate <= 1.0)",
            name="ck_b_session_aggregate_results_match_rate_bounded",
        ),
        sa.CheckConstraint(
            "completion_rate IS NULL OR (completion_rate >= 0.0 AND completion_rate <= 1.0)",
            name="ck_b_session_aggregate_results_completion_rate_bounded",
        ),
        *provenance_constraints("b_session_aggregate_results"),
    )

    op.create_table(
        "b_skill_certification_results",
        sa.Column("skill_result_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("learner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("skill_id", sa.String(128), nullable=False),
        sa.Column("opportunity_count", sa.Integer(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("first_attempt_match_count", sa.Integer(), nullable=False),
        sa.Column("skill_estimate", sa.Float(), nullable=True),
        sa.Column("plausibility_status", sa.String(32), nullable=True),
        sa.Column("threshold_met_flag", sa.Boolean(), nullable=True),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("skill_result_id"),
        sa.ForeignKeyConstraint(["session_id"], ["b_sessions.session_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["learner_id"], ["b_learners.learner_id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("session_id", "skill_id", name="uq_b_skill_certification_results_session_skill"),
        sa.CheckConstraint(
            "skill_estimate IS NULL OR (skill_estimate >= 0.0 AND skill_estimate <= 1.0)",
            name="ck_b_skill_certification_results_skill_estimate_bounded",
        ),
        sa.CheckConstraint(
            "plausibility_status IS NULL OR plausibility_status IN "
            "('NOT_TRIGGERED', 'TRIGGERED', 'INSUFFICIENT_EVIDENCE')",
            name="ck_b_skill_certification_results_plausibility_status",
        ),
        *provenance_constraints("b_skill_certification_results"),
    )


def downgrade() -> None:
    op.drop_table("b_skill_certification_results")
    op.drop_table("b_session_aggregate_results")
