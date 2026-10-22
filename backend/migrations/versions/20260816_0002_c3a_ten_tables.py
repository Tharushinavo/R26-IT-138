"""Component C Phase 3a: the ten tables (Component_C_Master_Build_Plan_v3.0.md Section 11
Phase 3) -- c_sessions, c_task_opportunities, c_task_instances, c_gameplay_events,
c_task_opportunity_summaries, c_session_aggregate_results, c_learner_local_state,
c_policy_decisions, c_safety_events, c_scaffold_events.

Tables only: no cross-row invariant (terminal-event uniqueness, event_index continuity,
timestamp monotonicity, attempt-count bounds) is created here -- that is Phase 3b. Mirrors
app.infrastructure.persistence_models's ten new model classes exactly; see that file for the
per-column allow-list / CHECK-source commentary.

Revision ID: 20260816_0002
Revises: 20260816_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260816_0002"
down_revision: str | Sequence[str] | None = "20260816_0001"
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
        "c_sessions",
        sa.Column("c_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("intervention_session_id", sa.String(128), nullable=True),
        sa.Column("session_mode", sa.String(16), nullable=False),
        sa.Column("session_phase", sa.String(32), nullable=False),
        sa.Column("mastery_context_mode", sa.String(32), nullable=False),
        sa.Column("catalogue_version", sa.String(128), nullable=False),
        sa.Column("catalogue_checksum", sa.String(64), nullable=False),
        sa.Column("c_runtime_bundle_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("grade", sa.SmallInteger(), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("global_seed", sa.BigInteger(), nullable=False),
        sa.Column("started_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("row_version", sa.Integer(), server_default=sa.text("0"), nullable=False),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("c_session_id"),
        sa.ForeignKeyConstraint(["student_id"], ["b_learners.learner_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["c_runtime_bundle_record_id"], ["c_runtime_bundle_records.c_runtime_bundle_record_id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint(
            "student_id", "intervention_session_id", name="uq_c_sessions_student_intervention_session"
        ),
        sa.CheckConstraint("session_mode IN ('combined', 'c_only')", name="ck_c_sessions_session_mode"),
        sa.CheckConstraint(
            "session_phase IN ('familiarization', 'mastery_driven', 'c_only')", name="ck_c_sessions_session_phase"
        ),
        sa.CheckConstraint(
            "mastery_context_mode IN ('same_session_fresh', 'unavailable_fallback')",
            name="ck_c_sessions_mastery_context_mode",
        ),
        sa.CheckConstraint("grade IN (2, 3)", name="ck_c_sessions_grade"),
        *provenance_constraints("c_sessions"),
    )

    op.create_table(
        "c_task_opportunities",
        sa.Column("c_task_opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("c_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_index", sa.Integer(), nullable=False),
        sa.Column("selected_skill_id", sa.String(128), nullable=False),
        sa.Column("selected_template_id", sa.String(128), nullable=False),
        sa.Column("initial_difficulty_level", sa.Integer(), nullable=False),
        sa.Column("mastery_context_mode", sa.String(32), nullable=False),
        sa.Column("mastery_selected_skill", sa.Float(), nullable=True),
        sa.Column("session_phase", sa.String(32), nullable=False),
        sa.Column("terminal_reason", sa.String(64), nullable=True),
        sa.Column("task_offered_at_utc", sa.DateTime(timezone=True), nullable=False),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("c_task_opportunity_id"),
        sa.ForeignKeyConstraint(["c_session_id"], ["c_sessions.c_session_id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "session_phase IN ('familiarization', 'mastery_driven', 'c_only')",
            name="ck_c_task_opportunities_session_phase",
        ),
        sa.CheckConstraint(
            "mastery_context_mode IN ('same_session_fresh', 'unavailable_fallback')",
            name="ck_c_task_opportunities_mastery_context_mode",
        ),
        *provenance_constraints("c_task_opportunities"),
    )

    op.create_table(
        "c_task_instances",
        sa.Column("c_task_instance_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("c_task_opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_family_id", sa.String(32), nullable=False),
        sa.Column("game_task_template_id", sa.String(64), nullable=False),
        sa.Column("template_version", sa.String(64), nullable=False),
        sa.Column("catalogue_version", sa.String(128), nullable=False),
        sa.Column("generator_version", sa.String(64), nullable=False),
        sa.Column("task_index", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.String(128), nullable=False),
        sa.Column("curriculum_node_id", sa.String(128), nullable=False),
        sa.Column("grade_scope", sa.SmallInteger(), nullable=False),
        sa.Column("difficulty_level", sa.Integer(), nullable=False),
        sa.Column("difficulty_vector", postgresql.JSONB(), nullable=False),
        sa.Column("functional_role", sa.String(32), nullable=False),
        sa.Column("representation_mode", sa.String(64), nullable=False),
        sa.Column("prompt_payload", postgresql.JSONB(), nullable=False),
        sa.Column("interactive_assets", postgresql.JSONB(), nullable=False),
        sa.Column("correct_answer_payload", postgresql.JSONB(), nullable=False),
        sa.Column("correctness_function_id", sa.String(64), nullable=False),
        sa.Column("valid_action_space", postgresql.JSONB(), nullable=False),
        sa.Column("completion_condition", sa.String(255), nullable=False),
        sa.Column("failure_condition", sa.String(255), nullable=False),
        sa.Column("scaffold_state", sa.String(8), nullable=False),
        sa.Column("recovery_parent_instance_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("technical_status", sa.String(16), nullable=False),
        sa.Column("seed_lineage_global_seed", sa.BigInteger(), nullable=False),
        sa.Column("seed_lineage_path", postgresql.JSONB(), nullable=False),
        sa.Column("seed_lineage_seed", sa.BigInteger(), nullable=False),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("c_task_instance_id"),
        sa.ForeignKeyConstraint(
            ["c_task_opportunity_id"], ["c_task_opportunities.c_task_opportunity_id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["recovery_parent_instance_id"], ["c_task_instances.c_task_instance_id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("c_task_opportunity_id", name="uq_c_task_instances_opportunity"),
        sa.CheckConstraint("grade_scope IN (2, 3)", name="ck_c_task_instances_grade_scope"),
        sa.CheckConstraint(
            "scaffold_state IN ('C0', 'C1', 'C2', 'C3', 'C4')", name="ck_c_task_instances_scaffold_state"
        ),
        sa.CheckConstraint("technical_status IN ('OK', 'FAILED')", name="ck_c_task_instances_technical_status"),
        *provenance_constraints("c_task_instances"),
    )

    op.create_table(
        "c_gameplay_events",
        sa.Column("c_gameplay_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("c_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_task_instance_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_index", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("event_index", sa.Integer(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=True),
        sa.Column("event_timestamp_relative_ms", sa.Integer(), nullable=False),
        sa.Column("action_payload", postgresql.JSONB(), nullable=True),
        sa.Column("evaluation_payload", postgresql.JSONB(), nullable=True),
        sa.Column("scaffold_code", sa.String(8), nullable=True),
        sa.Column("technical_flag", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("terminal_reason", sa.String(64), nullable=True),
        sa.Column("seed_lineage_global_seed", sa.BigInteger(), nullable=False),
        sa.Column("seed_lineage_path", postgresql.JSONB(), nullable=False),
        sa.Column("seed_lineage_seed", sa.BigInteger(), nullable=False),
        sa.Column("generator_version", sa.String(64), nullable=False),
        sa.Column("config_checksum", sa.String(64), nullable=False),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("c_gameplay_event_id"),
        sa.ForeignKeyConstraint(["c_session_id"], ["c_sessions.c_session_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["game_task_instance_id"], ["c_task_instances.c_task_instance_id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            "event_type IN ("
            "'game_task_offered', 'game_task_started', 'action_performed', 'answer_submitted', "
            "'answer_evaluated', 'retry_started', 'pause_started', 'pause_ended', "
            "'scaffold_requested', 'scaffold_shown', 'technical_issue', 'game_task_completed', "
            "'game_task_skipped', 'game_task_quit')",
            name="ck_c_gameplay_events_event_type",
        ),
        sa.CheckConstraint("event_timestamp_relative_ms >= 0", name="ck_c_gameplay_events_timestamp_non_negative"),
        sa.CheckConstraint(
            "scaffold_code IS NULL OR scaffold_code IN ('C0', 'C1', 'C2', 'C3', 'C4')",
            name="ck_c_gameplay_events_scaffold_code",
        ),
        sa.CheckConstraint(
            "terminal_reason IS NULL OR terminal_reason IN ("
            "'completed_correct', 'completed_incorrect', 'skipped', 'quit_after_error', "
            "'quit_without_recent_error', 'technical_issue', 'attempt_cap_exhausted', "
            "'timeout_no_response', 'safe_session_stop')",
            name="ck_c_gameplay_events_terminal_reason",
        ),
        *provenance_constraints("c_gameplay_events"),
    )

    op.create_table(
        "c_task_opportunity_summaries",
        sa.Column("c_task_opportunity_summary_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("c_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_task_instance_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_index", sa.Integer(), nullable=False),
        sa.Column("task_offered", sa.Boolean(), nullable=False),
        sa.Column("task_started", sa.Boolean(), nullable=False),
        sa.Column("task_completed", sa.Boolean(), nullable=False),
        sa.Column("task_skipped", sa.Boolean(), nullable=False),
        sa.Column("task_quit", sa.Boolean(), nullable=False),
        sa.Column("technical_issue", sa.Boolean(), nullable=False),
        sa.Column("correct_task", sa.Boolean(), nullable=True),
        sa.Column("total_attempts", sa.Integer(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("scaffold_requested", sa.Boolean(), nullable=False),
        sa.Column("scaffold_count", sa.Integer(), nullable=False),
        sa.Column("highest_scaffold_level", sa.String(8), nullable=True),
        sa.Column("c_answer_changes", sa.Integer(), nullable=False),
        sa.Column("task_latency_sec", sa.Float(), nullable=True),
        sa.Column("inactive_time_sec", sa.Float(), nullable=False),
        sa.Column("inactivity_periods", sa.Integer(), nullable=False),
        sa.Column("quit_after_error", sa.Boolean(), nullable=False),
        sa.Column("terminal_reason", sa.String(64), nullable=True),
        sa.Column("first_attempt_correct", sa.Boolean(), nullable=True),
        sa.Column("final_attempt_correct", sa.Boolean(), nullable=True),
        sa.Column("consecutive_error_max_within_task", sa.Integer(), nullable=False),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("c_task_opportunity_summary_id"),
        sa.ForeignKeyConstraint(["c_session_id"], ["c_sessions.c_session_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["game_task_instance_id"], ["c_task_instances.c_task_instance_id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("game_task_instance_id", name="uq_c_task_opportunity_summaries_instance"),
        sa.CheckConstraint(
            "highest_scaffold_level IS NULL OR highest_scaffold_level IN ('C0', 'C1', 'C2', 'C3', 'C4')",
            name="ck_c_task_opportunity_summaries_highest_scaffold_level",
        ),
        sa.CheckConstraint(
            "terminal_reason IS NULL OR terminal_reason IN ("
            "'completed_correct', 'completed_incorrect', 'skipped', 'quit_after_error', "
            "'quit_without_recent_error', 'technical_issue', 'attempt_cap_exhausted', "
            "'timeout_no_response', 'safe_session_stop')",
            name="ck_c_task_opportunity_summaries_terminal_reason",
        ),
        *provenance_constraints("c_task_opportunity_summaries"),
    )

    op.create_table(
        "c_session_aggregate_results",
        sa.Column("c_session_aggregate_result_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("c_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_opportunity_count", sa.Integer(), nullable=False),
        sa.Column("completed_task_count", sa.Integer(), nullable=False),
        sa.Column("correct_task_count", sa.Integer(), nullable=False),
        sa.Column("total_attempt_count", sa.Integer(), nullable=False),
        sa.Column("accuracy_rate", sa.Float(), nullable=True),
        sa.Column("avg_attempts_per_task", sa.Float(), nullable=True),
        sa.Column("task_completion_rate", sa.Float(), nullable=False),
        sa.Column("inactivity_periods", sa.Integer(), nullable=False),
        sa.Column("inactive_time_sec", sa.Float(), nullable=False),
        sa.Column("inactive_time_available", sa.Boolean(), nullable=False),
        sa.Column("session_duration_sec", sa.Float(), nullable=False),
        sa.Column("time_in_target_band_sec", sa.Float(), nullable=False),
        sa.Column("consecutive_error_max", sa.Integer(), nullable=False),
        sa.Column("difficulty_floor_hits", sa.Integer(), nullable=False),
        sa.Column("quit_after_error", sa.Boolean(), nullable=False),
        sa.Column("safety_override_count", sa.Integer(), nullable=False),
        sa.Column("c_mean_game_task_latency_sec", sa.Float(), nullable=True),
        sa.Column("c_median_game_task_latency_sec", sa.Float(), nullable=True),
        sa.Column("current_difficulty_level", sa.Integer(), nullable=False),
        sa.Column("difficulty_trend", sa.String(16), nullable=False),
        sa.Column("session_technical_issue_flag", sa.Boolean(), nullable=False),
        sa.Column("engagement_score", sa.Float(), nullable=True),
        sa.Column("engagement_completion_component", sa.Float(), nullable=True),
        sa.Column("engagement_activity_component", sa.Float(), nullable=True),
        sa.Column("engagement_target_band_component", sa.Float(), nullable=True),
        sa.Column("engagement_accuracy_component", sa.Float(), nullable=True),
        sa.Column("frustration_index", sa.Float(), nullable=True),
        sa.Column("frustration_error_run_component", sa.Float(), nullable=True),
        sa.Column("frustration_excess_attempt_component", sa.Float(), nullable=True),
        sa.Column("frustration_inactivity_burden_component", sa.Float(), nullable=True),
        sa.Column("frustration_floor_hit_component", sa.Float(), nullable=True),
        sa.Column("frustration_quit_after_error_component", sa.Float(), nullable=True),
        sa.Column("frustration_safety_override_component", sa.Float(), nullable=True),
        sa.Column("telemetry_quality_status", sa.String(32), nullable=True),
        sa.Column("learner_state", sa.String(32), nullable=True),
        sa.Column("state_reason", sa.String(64), nullable=True),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("c_session_aggregate_result_id"),
        sa.ForeignKeyConstraint(["c_session_id"], ["c_sessions.c_session_id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("c_session_id", name="uq_c_session_aggregate_results_session"),
        sa.CheckConstraint(
            "difficulty_trend IN ('increasing', 'stable', 'decreasing')",
            name="ck_c_session_aggregate_results_difficulty_trend",
        ),
        sa.CheckConstraint(
            "telemetry_quality_status IS NULL OR telemetry_quality_status IN "
            "('complete', 'insufficient_evidence', 'technical_issue')",
            name="ck_c_session_aggregate_results_telemetry_quality_status",
        ),
        sa.CheckConstraint(
            "learner_state IS NULL OR learner_state IN "
            "('engaged', 'productive_struggle', 'overloaded', 'disengaged')",
            name="ck_c_session_aggregate_results_learner_state",
        ),
        sa.CheckConstraint(
            "state_reason IS NULL OR state_reason IN ("
            "'technical_issue', 'insufficient_session_evidence', 'safety_override_with_error_burst', "
            "'quit_after_error', 'repeated_floor_hits_with_low_completion', 'high_behavioral_friction', "
            "'low_engagement_score', 'inactivity_with_low_completion', 'high_engagement_low_friction', "
            "'sustained_participation_under_challenge', 'insufficient_sustained_participation')",
            name="ck_c_session_aggregate_results_state_reason",
        ),
        *provenance_constraints("c_session_aggregate_results"),
    )

    op.create_table(
        "c_learner_local_state",
        sa.Column("c_learner_local_state_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("eligible_combined_handoffs_completed", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "sessions_since_last_practice", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("prior_session_end_state", sa.String(32), nullable=True),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("c_learner_local_state_id"),
        sa.ForeignKeyConstraint(["student_id"], ["b_learners.learner_id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("student_id", name="uq_c_learner_local_state_student"),
        sa.CheckConstraint(
            "prior_session_end_state IS NULL OR prior_session_end_state IN "
            "('engaged', 'productive_struggle', 'overloaded', 'disengaged')",
            name="ck_c_learner_local_state_prior_session_end_state",
        ),
        *provenance_constraints("c_learner_local_state"),
    )

    op.create_table(
        "c_policy_decisions",
        sa.Column("c_policy_decision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("c_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("c_task_opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_mode", sa.String(32), nullable=False),
        sa.Column("policy_version", sa.String(64), nullable=False),
        sa.Column("rl_state", postgresql.JSONB(), nullable=True),
        sa.Column("selected_action", sa.String(32), nullable=False),
        sa.Column("applied_action", sa.String(32), nullable=False),
        sa.Column("action_overridden", sa.Boolean(), nullable=False),
        sa.Column("safety_reason", sa.String(128), nullable=True),
        sa.Column("difficulty_before", sa.Integer(), nullable=False),
        sa.Column("difficulty_after", sa.Integer(), nullable=False),
        sa.Column("rolling_strain_bucket", sa.String(16), nullable=False),
        sa.Column("session_start_state_bucket", sa.String(32), nullable=True),
        sa.Column("increase_block_remaining", sa.Integer(), nullable=False),
        sa.Column("internal_reward", sa.Float(), nullable=True),
        sa.Column("seed_lineage_global_seed", sa.BigInteger(), nullable=False),
        sa.Column("seed_lineage_path", postgresql.JSONB(), nullable=False),
        sa.Column("seed_lineage_seed", sa.BigInteger(), nullable=False),
        sa.Column("evidence_snapshot", postgresql.JSONB(), nullable=False),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("c_policy_decision_id"),
        sa.ForeignKeyConstraint(["c_session_id"], ["c_sessions.c_session_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["c_task_opportunity_id"], ["c_task_opportunities.c_task_opportunity_id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            "policy_mode IN ('rule_based_baseline', 'q_learning_offline', 'frozen_q_evaluation')",
            name="ck_c_policy_decisions_policy_mode",
        ),
        sa.CheckConstraint(
            "selected_action IN ('decrease_difficulty', 'hold', 'increase_difficulty')",
            name="ck_c_policy_decisions_selected_action",
        ),
        sa.CheckConstraint(
            "applied_action IN ('decrease_difficulty', 'hold', 'increase_difficulty')",
            name="ck_c_policy_decisions_applied_action",
        ),
        sa.CheckConstraint(
            "rolling_strain_bucket IN ('low', 'moderate', 'high', 'severe')",
            name="ck_c_policy_decisions_rolling_strain_bucket",
        ),
        sa.CheckConstraint(
            "session_start_state_bucket IS NULL OR session_start_state_bucket IN "
            "('engaged', 'productive_struggle', 'overloaded', 'disengaged')",
            name="ck_c_policy_decisions_session_start_state_bucket",
        ),
        *provenance_constraints("c_policy_decisions"),
    )

    op.create_table(
        "c_safety_events",
        sa.Column("c_safety_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("c_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("c_policy_decision_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("trigger_reason", sa.String(128), nullable=False),
        sa.Column("action_taken", sa.String(64), nullable=False),
        sa.Column("difficulty_before", sa.Integer(), nullable=True),
        sa.Column("difficulty_after", sa.Integer(), nullable=True),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("c_safety_event_id"),
        sa.ForeignKeyConstraint(["c_session_id"], ["c_sessions.c_session_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["c_policy_decision_id"], ["c_policy_decisions.c_policy_decision_id"], ondelete="RESTRICT"
        ),
        *provenance_constraints("c_safety_events"),
    )

    op.create_table(
        "c_scaffold_events",
        sa.Column("c_scaffold_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("c_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("c_task_opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(16), nullable=False),
        sa.Column("scaffold_level", sa.String(8), nullable=False),
        sa.Column("consecutive_incorrect_current_task", sa.Integer(), nullable=False),
        sa.Column("safety_forces_recovery", sa.Boolean(), nullable=False),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("c_scaffold_event_id"),
        sa.ForeignKeyConstraint(["c_session_id"], ["c_sessions.c_session_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["c_task_opportunity_id"], ["c_task_opportunities.c_task_opportunity_id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            "scaffold_level IN ('C0', 'C1', 'C2', 'C3', 'C4')", name="ck_c_scaffold_events_scaffold_level"
        ),
        *provenance_constraints("c_scaffold_events"),
    )


def downgrade() -> None:
    op.drop_table("c_scaffold_events")
    op.drop_table("c_safety_events")
    op.drop_table("c_policy_decisions")
    op.drop_table("c_learner_local_state")
    op.drop_table("c_session_aggregate_results")
    op.drop_table("c_task_opportunity_summaries")
    op.drop_table("c_gameplay_events")
    op.drop_table("c_task_instances")
    op.drop_table("c_task_opportunities")
    op.drop_table("c_sessions")
