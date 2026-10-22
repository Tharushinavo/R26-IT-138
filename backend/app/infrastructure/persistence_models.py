"""Neutral BE2 persistence facts authorized by the governance boundary.

These models intentionally contain no lifecycle methods, scientific state, learner
responses, or synthetic-generator fields.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
    false,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


SOURCE_CLASSES = ("REAL", "SYNTHETIC", "IMPORTED", "TEST")
SESSION_STATES = (
    "starting", "active", "completing", "completed", "abandoned", "expired", "technical_failed"
)


class Base(DeclarativeBase):
    """Metadata root for the eight authorized BE2 tables."""


class ProvenanceMixin:
    """Mandatory neutral provenance and audit metadata."""

    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("app_users.user_id", ondelete="RESTRICT"), nullable=True
    )
    system_actor: Mapped[str | None] = mapped_column(String(128), nullable=True)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    operation_or_event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    before_reference_or_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    after_reference_or_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_class: Mapped[str] = mapped_column(String(16), nullable=False)
    source_system: Mapped[str] = mapped_column(String(128), nullable=False)
    source_record_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    environment: Mapped[str] = mapped_column(String(32), nullable=False)
    schema_revision: Mapped[str] = mapped_column(String(64), nullable=False)
    approval_evidence_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)

    @staticmethod
    def provenance_constraints(prefix: str) -> tuple[CheckConstraint, ...]:
        return (
            CheckConstraint(
                "source_class IN ('REAL', 'SYNTHETIC', 'IMPORTED', 'TEST')",
                name=f"ck_{prefix}_source_class",
            ),
            CheckConstraint(
                "(actor_user_id IS NOT NULL) <> (system_actor IS NOT NULL)",
                name=f"ck_{prefix}_actor_exactly_one",
            ),
            CheckConstraint(
                "environment <> '' AND source_system <> '' AND request_id <> ''",
                name=f"ck_{prefix}_required_provenance_nonblank",
            ),
        )


class AppUser(ProvenanceMixin, Base):
    __tablename__ = "app_users"
    __table_args__ = (
        UniqueConstraint("supabase_subject", name="uq_app_users_supabase_subject"),
        CheckConstraint("supabase_subject <> ''", name="ck_app_users_subject_nonblank"),
        CheckConstraint("status <> ''", name="ck_app_users_status_nonblank"),
        CheckConstraint(
            "profile_type IS NULL OR profile_type IN ('LEARNER', 'TEACHER')",
            name="ck_app_users_profile_type",
        ),
        *ProvenanceMixin.provenance_constraints("app_users"),
    )

    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    supabase_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    profile_type: Mapped[str | None] = mapped_column(String(16), nullable=True)


class Learner(ProvenanceMixin, Base):
    __tablename__ = "b_learners"
    __table_args__ = (
        CheckConstraint("grade IS NULL OR grade IN (2, 3)", name="ck_b_learners_grade"),
        CheckConstraint("status <> ''", name="ck_b_learners_status_nonblank"),
        CheckConstraint("name IS NULL OR btrim(name) <> ''", name="ck_b_learners_name_nonblank"),
        *ProvenanceMixin.provenance_constraints("b_learners"),
    )

    learner_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    grade: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)


class AppUserLearnerLink(ProvenanceMixin, Base):
    __tablename__ = "app_user_learner_links"
    __table_args__ = (
        UniqueConstraint("user_id", "learner_id", name="uq_app_user_learner_links_pair"),
        UniqueConstraint("user_id", name="uq_app_user_learner_links_user"),
        UniqueConstraint("learner_id", name="uq_app_user_learner_links_learner"),
        *ProvenanceMixin.provenance_constraints("app_user_learner_links"),
    )

    link_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("app_users.user_id", ondelete="RESTRICT"), nullable=False
    )
    learner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("b_learners.learner_id", ondelete="RESTRICT"), nullable=False
    )


class RuntimeBundleRecord(ProvenanceMixin, Base):
    __tablename__ = "b_runtime_bundle_records"
    __table_args__ = (
        UniqueConstraint("bundle_version", name="uq_b_runtime_bundle_records_version"),
        UniqueConstraint("manifest_checksum", name="uq_b_runtime_bundle_records_checksum"),
        CheckConstraint("manifest_checksum ~ '^[0-9a-f]{64}$'", name="ck_b_runtime_bundle_records_checksum"),
        CheckConstraint(
            "publication_state IN ('DRAFT', 'PUBLISHED', 'RETIRED')",
            name="ck_b_runtime_bundle_records_publication_state",
        ),
        CheckConstraint(
            "publication_state <> 'PUBLISHED' OR immutable_after_publication",
            name="ck_b_runtime_bundle_records_published_immutable",
        ),
        *ProvenanceMixin.provenance_constraints("b_runtime_bundle_records"),
    )

    runtime_bundle_record_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    bundle_version: Mapped[str] = mapped_column(String(128), nullable=False)
    manifest_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    publication_state: Mapped[str] = mapped_column(String(16), nullable=False)
    approval_status: Mapped[str] = mapped_column(String(64), nullable=False)
    immutable_after_publication: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())


class SessionRecord(ProvenanceMixin, Base):
    __tablename__ = "b_sessions"
    __table_args__ = (
        CheckConstraint(
            "state IN ('starting', 'active', 'completing', 'completed', 'abandoned', 'expired', 'technical_failed')",
            name="ck_b_sessions_state",
        ),
        CheckConstraint("row_version >= 0", name="ck_b_sessions_row_version"),
        CheckConstraint(
            "state <> 'active' OR runtime_bundle_record_id IS NOT NULL",
            name="ck_b_sessions_active_bundle_required",
        ),
        Index(
            "uq_b_sessions_one_starting_or_active_per_learner",
            "learner_id",
            unique=True,
            postgresql_where=text("state IN ('starting', 'active')"),
        ),
        *ProvenanceMixin.provenance_constraints("b_sessions"),
    )

    session_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    learner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("b_learners.learner_id", ondelete="RESTRICT"), nullable=False
    )
    runtime_bundle_record_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("b_runtime_bundle_records.runtime_bundle_record_id", ondelete="RESTRICT"),
        nullable=True,
    )
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    expires_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))


class SessionEvent(ProvenanceMixin, Base):
    __tablename__ = "b_session_events"
    __table_args__ = (*ProvenanceMixin.provenance_constraints("b_session_events"),)

    session_event_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("b_sessions.session_id", ondelete="RESTRICT"), nullable=False
    )


class IdempotencyRecord(ProvenanceMixin, Base):
    __tablename__ = "b_idempotency_records"
    __table_args__ = (
        UniqueConstraint(
            "actor_user_id", "http_method", "operation_identifier", "idempotency_key",
            name="uq_b_idempotency_records_scope",
        ),
        CheckConstraint("actor_user_id IS NOT NULL", name="ck_b_idempotency_records_actor_required"),
        CheckConstraint("processing_status <> ''", name="ck_b_idempotency_records_status_nonblank"),
        CheckConstraint("request_fingerprint ~ '^[0-9a-f]{64}$'", name="ck_b_idempotency_records_fingerprint"),
        CheckConstraint("expires_at_utc > created_at_utc", name="ck_b_idempotency_records_expiry"),
        *ProvenanceMixin.provenance_constraints("b_idempotency_records"),
    )

    idempotency_record_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    http_method: Mapped[str] = mapped_column(String(16), nullable=False)
    operation_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    processing_status: Mapped[str] = mapped_column(String(32), nullable=False)
    canonical_response: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    response_status: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    expires_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuditEvent(ProvenanceMixin, Base):
    __tablename__ = "b_audit_events"
    __table_args__ = (*ProvenanceMixin.provenance_constraints("b_audit_events"),)

    audit_event_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)


class TeacherProfile(ProvenanceMixin, Base):
    __tablename__ = "teacher_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_teacher_profiles_user"),
        CheckConstraint("btrim(name) <> ''", name="ck_teacher_profiles_name_nonblank"),
        *ProvenanceMixin.provenance_constraints("teacher_profiles"),
    )

    teacher_profile_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("app_users.user_id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class Classroom(ProvenanceMixin, Base):
    __tablename__ = "classrooms"
    __table_args__ = (
        CheckConstraint("grade IN ('GRADE_2', 'GRADE_3')", name="ck_classrooms_grade"),
        CheckConstraint("name IS NULL OR btrim(name) <> ''", name="ck_classrooms_name_nonblank"),
        # A deleted classroom no longer holds its name (migration 20260914_0009).
        Index("uq_classrooms_teacher_normalized_name", "teacher_profile_id", func.lower(func.btrim(text("name"))), unique=True, postgresql_where=text("name IS NOT NULL AND deleted_at_utc IS NULL")),
        CheckConstraint("row_version >= 0", name="ck_classrooms_row_version"),
        CheckConstraint("(deleted_at_utc IS NULL) = (deleted_by_user_id IS NULL)", name="ck_classrooms_deletion_pair"),
        *ProvenanceMixin.provenance_constraints("classrooms"),
    )

    classroom_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    teacher_profile_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("teacher_profiles.teacher_profile_id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    grade: Mapped[str] = mapped_column(String(16), nullable=False)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    # Soft delete (20260914_0009): set once by the owning teacher, never cleared. Every
    # teacher-facing read filters it out; the row stays because memberships, invites and
    # Component 3's tables all reference it with ON DELETE RESTRICT.
    deleted_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("app_users.user_id", ondelete="RESTRICT", name="fk_classrooms_deleted_by_user_id_app_users"),
        nullable=True,
    )


class ClassroomInvite(ProvenanceMixin, Base):
    __tablename__ = "classroom_invites"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_classroom_invites_token_hash"),
        CheckConstraint("token_hash ~ '^[0-9a-f]{64}$'", name="ck_classroom_invites_token_hash"),
        CheckConstraint("row_version >= 0", name="ck_classroom_invites_row_version"),
        *ProvenanceMixin.provenance_constraints("classroom_invites"),
    )

    classroom_invite_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    classroom_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("classrooms.classroom_id", ondelete="RESTRICT"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("app_users.user_id", ondelete="RESTRICT"), nullable=False)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))


class ClassroomMembership(ProvenanceMixin, Base):
    __tablename__ = "classroom_memberships"
    __table_args__ = (
        UniqueConstraint("classroom_id", "learner_id", name="uq_classroom_memberships_pair"),
        # REMOVED (20260914_0009): the membership ended because its classroom was deleted.
        CheckConstraint("state IN ('PENDING', 'APPROVED', 'REJECTED', 'REMOVED')", name="ck_classroom_memberships_state"),
        CheckConstraint("(state = 'PENDING' AND decided_at_utc IS NULL AND decided_by_user_id IS NULL) OR (state IN ('APPROVED', 'REJECTED', 'REMOVED') AND decided_at_utc IS NOT NULL AND decided_by_user_id IS NOT NULL)", name="ck_classroom_memberships_decision"),
        CheckConstraint("row_version >= 0", name="ck_classroom_memberships_row_version"),
        Index(
            "uq_classroom_memberships_one_approved_per_learner",
            "learner_id",
            unique=True,
            postgresql_where=text("state = 'APPROVED'"),
        ),
        *ProvenanceMixin.provenance_constraints("classroom_memberships"),
    )

    classroom_membership_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    classroom_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("classrooms.classroom_id", ondelete="RESTRICT"), nullable=False)
    learner_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("b_learners.learner_id", ondelete="RESTRICT"), nullable=False)
    classroom_invite_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("classroom_invites.classroom_invite_id", ondelete="RESTRICT"), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    requested_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decided_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("app_users.user_id", ondelete="RESTRICT"), nullable=True)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))


class ItemOpportunityRecord(ProvenanceMixin, Base):
    """BE4a (BEplan §9 BE4.1): one live-loop opportunity per row. PRIVATE table — the
    ``selection_provenance`` column never appears in any public DTO or log; see
    ``app.domain.b_opportunity``."""

    __tablename__ = "b_item_opportunities"
    __table_args__ = (
        CheckConstraint("state IN ('OPEN', 'CLOSED')", name="ck_b_item_opportunities_state"),
        CheckConstraint("row_version >= 0", name="ck_b_item_opportunities_row_version"),
        CheckConstraint(
            "timeout_deadline_utc > created_at_utc", name="ck_b_item_opportunities_timeout_after_created"
        ),
        Index(
            "uq_b_item_opportunities_one_open_per_session",
            "session_id",
            unique=True,
            postgresql_where=text("state = 'OPEN'"),
        ),
        *ProvenanceMixin.provenance_constraints("b_item_opportunities"),
    )

    item_opportunity_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("b_sessions.session_id", ondelete="RESTRICT"), nullable=False
    )
    learner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("b_learners.learner_id", ondelete="RESTRICT"), nullable=False
    )
    skill_id: Mapped[str] = mapped_column(String(128), nullable=False)
    item_template_id: Mapped[str] = mapped_column(String(128), nullable=False)
    opportunity_index: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    presented_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timeout_deadline_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    selection_provenance: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))


class TaskInstanceRecord(ProvenanceMixin, Base):
    """BE4a (BEplan §9 BE4.1): the constructed task for one opportunity, split into a SAFE
    presentation subset (prompt/presented_choices — computed once at creation using the same
    allow-list logic as BE3c's ``project_to_public``) and PRIVATE columns that never leave this
    table. This batch creates the schema only; BE4b populates rows via the adapter."""

    __tablename__ = "b_task_instances"
    __table_args__ = (
        UniqueConstraint("item_opportunity_id", name="uq_b_task_instances_opportunity"),
        CheckConstraint("grade IN (2, 3)", name="ck_b_task_instances_grade"),
        *ProvenanceMixin.provenance_constraints("b_task_instances"),
    )

    task_instance_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    item_opportunity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("b_item_opportunities.item_opportunity_id", ondelete="RESTRICT"), nullable=False
    )
    item_template_id: Mapped[str] = mapped_column(String(128), nullable=False)
    skill_id: Mapped[str] = mapped_column(String(128), nullable=False)
    grade: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    difficulty_level: Mapped[str] = mapped_column(String(64), nullable=False)
    representation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    response_format: Mapped[str] = mapped_column(String(64), nullable=False)
    # SAFE presentation subset (BE3c allow-list) — the only columns a public DTO may read.
    prompt: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    presented_choices: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    # PRIVATE — never read by any public-DTO projection or structured log.
    correct_answer: Mapped[str] = mapped_column(String(255), nullable=False)
    allowed_equivalent_answers: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    distractor_candidates: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    distractor_rule_ids: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    generated_operands: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    generation_seed: Mapped[int] = mapped_column(BigInteger, nullable=False)
    applied_guard_ids: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    catalogue_version: Mapped[str] = mapped_column(String(128), nullable=False)
    catalogue_checksum: Mapped[str] = mapped_column(String(64), nullable=False)


class PresentationTokenRecord(ProvenanceMixin, Base):
    """BE4a (BEplan §9 BE4.1): an opaque, short-lived presentation token bound to
    (session, opportunity, learner, runtime bundle). Only the SHA-256 hash of the token is
    stored, matching the ``classroom_invites.token_hash`` convention — the raw token is returned
    to the caller exactly once, at issuance."""

    __tablename__ = "b_presentation_tokens"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_b_presentation_tokens_token_hash"),
        CheckConstraint("token_hash ~ '^[0-9a-f]{64}$'", name="ck_b_presentation_tokens_token_hash"),
        CheckConstraint("expires_at_utc > issued_at_utc", name="ck_b_presentation_tokens_expiry"),
        *ProvenanceMixin.provenance_constraints("b_presentation_tokens"),
    )

    presentation_token_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("b_sessions.session_id", ondelete="RESTRICT"), nullable=False
    )
    item_opportunity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("b_item_opportunities.item_opportunity_id", ondelete="RESTRICT"), nullable=False
    )
    learner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("b_learners.learner_id", ondelete="RESTRICT"), nullable=False
    )
    runtime_bundle_record_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("b_runtime_bundle_records.runtime_bundle_record_id", ondelete="RESTRICT"),
        nullable=False,
    )
    issued_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LearnerSkillStateRecord(ProvenanceMixin, Base):
    """BE4b (BEplan §9 BE4.2): one row per (learner, skill) — the current P(L) mastery estimate
    and observation count. PRIVATE table. BE4b only reads and initializes (from the pinned
    bundle's TEST-fixture P(L0) priors); BE4c owns updates after the first real attempt. No
    cross-skill transfer: every row is independent."""

    __tablename__ = "b_learner_skill_states"
    __table_args__ = (
        UniqueConstraint("learner_id", "skill_id", name="uq_b_learner_skill_states_pair"),
        CheckConstraint("p_l >= 0.0 AND p_l <= 1.0", name="ck_b_learner_skill_states_p_l_bounded"),
        CheckConstraint("observation_count >= 0", name="ck_b_learner_skill_states_observation_count"),
        *ProvenanceMixin.provenance_constraints("b_learner_skill_states"),
    )

    learner_skill_state_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    learner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("b_learners.learner_id", ondelete="RESTRICT"), nullable=False
    )
    skill_id: Mapped[str] = mapped_column(String(128), nullable=False)
    p_l: Mapped[float] = mapped_column(Float, nullable=False)
    observation_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))


class AttemptRecord(ProvenanceMixin, Base):
    """BE4c (BEplan §9 BE4.3): one row per submitted attempt or governed timeout event on an
    opportunity. PRIVATE table. ``attempt_index`` is derived server-side under a row lock on the
    parent opportunity and is unique per opportunity. ``submitted_value`` is the learner's raw
    submission (never the accepted-answer set); ``response_matched`` is the server-computed
    outcome for ``RESPONSE`` events only (``NULL`` for ``TIMEOUT``). ``client_elapsed_ms`` is
    telemetry only — never used for correctness or BKT.

    BF-2 (migration 20260801_0001): ``submitted_value`` is NOT NULL unconditionally, including on
    ``TIMEOUT`` — a late-but-real answer is persisted (never scored: ``response_matched`` stays
    NULL for ``TIMEOUT``, exactly as before). Previously the constraint below required
    ``submitted_value IS NULL`` on timeout, which meant the answer was discarded and unrecoverable
    the moment the request completed."""

    __tablename__ = "b_attempts"
    __table_args__ = (
        UniqueConstraint("item_opportunity_id", "attempt_index", name="uq_b_attempts_opportunity_index"),
        CheckConstraint("event_kind IN ('RESPONSE', 'TIMEOUT')", name="ck_b_attempts_event_kind"),
        CheckConstraint("attempt_index >= 1", name="ck_b_attempts_attempt_index_positive"),
        CheckConstraint(
            "submitted_value IS NOT NULL "
            "AND ((event_kind = 'RESPONSE' AND response_matched IS NOT NULL) "
            "OR (event_kind = 'TIMEOUT' AND response_matched IS NULL))",
            name="ck_b_attempts_response_matched_consistency",
        ),
        CheckConstraint("client_elapsed_ms IS NULL OR client_elapsed_ms >= 0", name="ck_b_attempts_client_elapsed_ms_nonnegative"),
        *ProvenanceMixin.provenance_constraints("b_attempts"),
    )

    attempt_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    item_opportunity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("b_item_opportunities.item_opportunity_id", ondelete="RESTRICT"), nullable=False
    )
    learner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("b_learners.learner_id", ondelete="RESTRICT"), nullable=False
    )
    attempt_index: Mapped[int] = mapped_column(Integer, nullable=False)
    event_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    submitted_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    response_matched: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    client_elapsed_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    server_submitted_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SkillStateTransitionRecord(ProvenanceMixin, Base):
    """BE4c (BEplan §9 BE4.4): the immutable first-attempt-only BKT observation + mastery
    transition. PRIVATE table. ``uq_b_skill_state_transitions_opportunity`` is simultaneously the
    DB-level claim on the unique first-attempt observation for an opportunity and the transition
    row itself — a concurrent second claim for the same opportunity fails this unique index. No
    application code path ever updates or deletes a row in this table."""

    __tablename__ = "b_skill_state_transitions"
    __table_args__ = (
        UniqueConstraint("item_opportunity_id", name="uq_b_skill_state_transitions_opportunity"),
        UniqueConstraint("attempt_id", name="uq_b_skill_state_transitions_attempt"),
        CheckConstraint("p_l_before >= 0.0 AND p_l_before <= 1.0", name="ck_b_skill_state_transitions_p_l_before_bounded"),
        CheckConstraint(
            "predicted_probability >= 0.0 AND predicted_probability <= 1.0",
            name="ck_b_skill_state_transitions_predicted_probability_bounded",
        ),
        CheckConstraint("posterior_p_l >= 0.0 AND posterior_p_l <= 1.0", name="ck_b_skill_state_transitions_posterior_p_l_bounded"),
        CheckConstraint("p_l_after >= 0.0 AND p_l_after <= 1.0", name="ck_b_skill_state_transitions_p_l_after_bounded"),
        *ProvenanceMixin.provenance_constraints("b_skill_state_transitions"),
    )

    skill_state_transition_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    learner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("b_learners.learner_id", ondelete="RESTRICT"), nullable=False
    )
    skill_id: Mapped[str] = mapped_column(String(128), nullable=False)
    item_opportunity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("b_item_opportunities.item_opportunity_id", ondelete="RESTRICT"), nullable=False
    )
    attempt_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("b_attempts.attempt_id", ondelete="RESTRICT"), nullable=False
    )
    response_matched: Mapped[bool] = mapped_column(Boolean, nullable=False)
    p_l_before: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_probability: Mapped[float] = mapped_column(Float, nullable=False)
    posterior_p_l: Mapped[float] = mapped_column(Float, nullable=False)
    p_l_after: Mapped[float] = mapped_column(Float, nullable=False)


class HintEventRecord(ProvenanceMixin, Base):
    """BE4d (BEplan §9 BE4.5): one row per governed L1/L2/L3 assist request on an opportunity.
    PRIVATE table, SEPARATE from ``b_attempts``/``b_skill_state_transitions`` — a hint request is
    never a mastery/BKT observation and this table is never joined into any BKT computation.
    Column names avoid every ``PROHIBITED_COLUMN_TERMS`` entry (see
    ``tests/test_be2_architecture_guards.py``): the governed hint level is spelled
    ``assist_level``, not ``hint_level``. Only the catalogue reconstruction key
    (``content_id`` + ``catalogue_version`` + ``catalogue_checksum``) is persisted — never the
    hint text itself, which is always re-fetched from the governed catalogue via
    ``LiveEngineAdapter.get_hint`` at request time."""

    __tablename__ = "b_hint_events"
    __table_args__ = (
        UniqueConstraint("item_opportunity_id", "assist_level", name="uq_b_hint_events_opportunity_level"),
        CheckConstraint("assist_level >= 1 AND assist_level <= 3", name="ck_b_hint_events_assist_level_bounded"),
        *ProvenanceMixin.provenance_constraints("b_hint_events"),
    )

    assist_event_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    item_opportunity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("b_item_opportunities.item_opportunity_id", ondelete="RESTRICT"), nullable=False
    )
    learner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("b_learners.learner_id", ondelete="RESTRICT"), nullable=False
    )
    assist_level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    content_id: Mapped[str] = mapped_column(String(255), nullable=False)
    catalogue_version: Mapped[str] = mapped_column(String(128), nullable=False)
    catalogue_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SessionAggregateResultRecord(ProvenanceMixin, Base):
    """BE4e (BEplan §9 BE4.6): one immutable row per completed session — session-level aggregate
    statistics computed via ``LiveEngineAdapter.aggregate_session`` from the session's own
    attempts/hints/first-attempt outcomes. PRIVATE table: never read by any public-DTO projection
    (see ``app.domain.b_completion``). Column names avoid every ``PROHIBITED_COLUMN_TERMS`` entry
    (``outcome_pattern_distribution`` not ``error_class_distribution``,
    ``assisted_opportunity_count`` not ``hint_bearing_opportunities``). No application code path
    ever updates or deletes a row here."""

    __tablename__ = "b_session_aggregate_results"
    __table_args__ = (
        UniqueConstraint("session_id", name="uq_b_session_aggregate_results_session"),
        CheckConstraint(
            "first_attempt_match_rate IS NULL OR (first_attempt_match_rate >= 0.0 AND first_attempt_match_rate <= 1.0)",
            name="ck_b_session_aggregate_results_match_rate_bounded",
        ),
        CheckConstraint(
            "completion_rate IS NULL OR (completion_rate >= 0.0 AND completion_rate <= 1.0)",
            name="ck_b_session_aggregate_results_completion_rate_bounded",
        ),
        *ProvenanceMixin.provenance_constraints("b_session_aggregate_results"),
    )

    session_aggregate_result_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("b_sessions.session_id", ondelete="RESTRICT"), nullable=False
    )
    learner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("b_learners.learner_id", ondelete="RESTRICT"), nullable=False
    )
    opportunity_count: Mapped[int] = mapped_column(Integer, nullable=False)
    first_attempt_match_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    completion_count: Mapped[int] = mapped_column(Integer, nullable=False)
    completion_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_retry_count: Mapped[int] = mapped_column(Integer, nullable=False)
    assisted_opportunity_count: Mapped[int] = mapped_column(Integer, nullable=False)
    response_time_mean_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    response_time_median_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    response_time_std_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    outcome_pattern_distribution: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    skill_ids_practiced: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    completion_policy_version: Mapped[str] = mapped_column(String(64), nullable=False)


class SkillCertificationResultRecord(ProvenanceMixin, Base):
    """BE4e (BEplan §9 BE4.6): one immutable row per (session, skill) roll-up — the TEST-fixture
    plausibility-check and certification decision from ``LiveEngineAdapter.plausibility_floor``/
    ``evaluate``/``certify_skill``. PRIVATE table; column names avoid every
    ``PROHIBITED_COLUMN_TERMS`` entry (``skill_estimate`` not ``mastery``/``p_l``,
    ``threshold_met_flag`` not ``certified_flag``, ``plausibility_status`` not
    ``guess_guard_status``, ``first_attempt_match_count`` not ``first_attempt_correct_count``).
    GATE-B deferred: theta_B and the plausibility numerics behind this row are the
    TEST_FIXTURE_ONLY engineering config, never an approved value; never exposed through any
    public DTO (see ``app.domain.b_completion``)."""

    __tablename__ = "b_skill_certification_results"
    __table_args__ = (
        UniqueConstraint("session_id", "skill_id", name="uq_b_skill_certification_results_session_skill"),
        CheckConstraint(
            "skill_estimate IS NULL OR (skill_estimate >= 0.0 AND skill_estimate <= 1.0)",
            name="ck_b_skill_certification_results_skill_estimate_bounded",
        ),
        CheckConstraint(
            "plausibility_status IS NULL OR plausibility_status IN "
            "('NOT_TRIGGERED', 'TRIGGERED', 'INSUFFICIENT_EVIDENCE')",
            name="ck_b_skill_certification_results_plausibility_status",
        ),
        *ProvenanceMixin.provenance_constraints("b_skill_certification_results"),
    )

    skill_result_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("b_sessions.session_id", ondelete="RESTRICT"), nullable=False
    )
    learner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("b_learners.learner_id", ondelete="RESTRICT"), nullable=False
    )
    skill_id: Mapped[str] = mapped_column(String(128), nullable=False)
    opportunity_count: Mapped[int] = mapped_column(Integer, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False)
    first_attempt_match_count: Mapped[int] = mapped_column(Integer, nullable=False)
    skill_estimate: Mapped[float | None] = mapped_column(Float, nullable=True)
    plausibility_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    threshold_met_flag: Mapped[bool | None] = mapped_column(Boolean, nullable=True)


class CRuntimeBundleRecord(ProvenanceMixin, Base):
    """Component C Phase 2: mirrors ``RuntimeBundleRecord``'s (b_runtime_bundle_records)
    column set and constraint style exactly, pinning Component C's own
    (``prabathi-component-c-live-engine``) runtime-bundle manifests rather than B's. No
    relationship to ``b_runtime_bundle_records`` or any other B table."""

    __tablename__ = "c_runtime_bundle_records"
    __table_args__ = (
        UniqueConstraint("bundle_version", name="uq_c_runtime_bundle_records_version"),
        UniqueConstraint("manifest_checksum", name="uq_c_runtime_bundle_records_checksum"),
        CheckConstraint("manifest_checksum ~ '^[0-9a-f]{64}$'", name="ck_c_runtime_bundle_records_checksum"),
        CheckConstraint(
            "publication_state IN ('DRAFT', 'PUBLISHED', 'RETIRED')",
            name="ck_c_runtime_bundle_records_publication_state",
        ),
        CheckConstraint(
            "publication_state <> 'PUBLISHED' OR immutable_after_publication",
            name="ck_c_runtime_bundle_records_published_immutable",
        ),
        *ProvenanceMixin.provenance_constraints("c_runtime_bundle_records"),
    )

    c_runtime_bundle_record_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    bundle_version: Mapped[str] = mapped_column(String(128), nullable=False)
    manifest_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    publication_state: Mapped[str] = mapped_column(String(16), nullable=False)
    approval_status: Mapped[str] = mapped_column(String(64), nullable=False)
    immutable_after_publication: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())


# =====================================================================================
# Component C Phase 3a — the ten tables (Component_C_Master_Build_Plan_v3.0.md §11 Phase 3).
# Tables only: no cross-row invariant (terminal-event uniqueness, event_index continuity,
# timestamp monotonicity, attempt-count bounds) is enforced here — that is Phase 3b, per the
# owner's scope split (Phase 3a work order, "SCOPE" / "OUT OF SCOPE" sections). Two exceptions
# land in 3a because they are genuinely single-row/single-table, not cross-row: the UNIQUE on
# c_sessions(student_id, intervention_session_id), and the single-row CHECK
# event_timestamp_relative_ms >= 0 on c_gameplay_events — both BUILDER JUDGMENT, ratified as
# "R-E" in the Phase 3a work order ("UNIQUE(student_id, intervention_session_id) on c_sessions
# and the single-row CHECK event_timestamp_relative_ms >= 0 LAND IN 3a under scope item 2.
# Every other invariant in your Q6 table is 3b. Do not build a trigger this phase.").
#
# Every enum-style CHECK below cites its source: either a Literal type verified directly against
# the installed component_c_generator wheel during Phase 1b/3a planning (named per column), or
# an existing structural constant already in this file (SESSION_STATES, the grade-2/3 convention
# already used by RuntimeBundleRecord's B sibling TaskInstanceRecord). No CHECK constraint in
# this block contains an invented numeric threshold (Phase 3a work order, R-G).
# =====================================================================================


class CSessionRecord(ProvenanceMixin, Base):
    """Component C Phase 3a/4. Session lifecycle, pinned catalogue/config versions,
    ``mastery_context_mode``, ``session_phase`` (Component_C_Master_Build_Plan_v3.0.md §11
    Phase 3 table purpose). ``state`` REUSES ``SESSION_STATES`` (this file's module-level
    constant, already B's own session-lifecycle vocabulary) exactly, unchanged, all seven values
    (SUPERVISOR RULING (lead), Phase 4 work order, c_sessions.state section: "Reuse SESSION_STATES
    exactly — all seven, unchanged... reuse is precedent not invention. A subset guarantees a
    second migration when completion/expiry land; a CHECK constrains what may be WRITTEN and does
    not require every value be reachable."). This deliberately COUPLES Component C's lifecycle
    vocabulary to a constant Component B also uses — if C later needs a state B does not have,
    THE CONSTANT MUST BE SPLIT into a C-specific one, never extended in place, because extending
    it silently widens B's own ``ck_b_sessions_state`` CHECK too (same ruling, S-2). Phase 4 does
    not reach every one of the seven states from its own scope (create/start, resume, abandon) --
    see ``test_phase4_c_sessions_state_reachable_subset_is_documented`` for exactly which subset
    Phase 4's own code paths can produce (S-1); the unreached values are not dead, they are simply
    not this phase's job to produce.

    PHASE 4b: ``uq_c_sessions_one_starting_or_active_per_learner`` mirrors B's own
    ``uq_b_sessions_one_starting_or_active_per_learner`` (``persistence_models.py``,
    ``b_sessions``) exactly -- same predicate shape, ``state IN ('starting', 'active')``, matching
    ``CSessionRecordRepository.find_starting_or_active_for_learner``'s own query predicate
    field-for-field (both must cover the same set or the index prevents a race that isn't the
    race). ``create_session`` currently writes ``state="active"`` only -- ``'starting'`` is NOT
    reachable by any Phase 4 code path today; the predicate still names it, matching the query
    predicate's own two-state set exactly, rather than being narrowed to the one state C actually
    produces. This is recorded here, not silently narrowed."""

    __tablename__ = "c_sessions"
    __table_args__ = (
        UniqueConstraint(
            "student_id", "intervention_session_id", name="uq_c_sessions_student_intervention_session"
        ),
        CheckConstraint("session_mode IN ('combined', 'c_only')", name="ck_c_sessions_session_mode"),
        CheckConstraint(
            "session_phase IN ('familiarization', 'mastery_driven', 'c_only')",
            name="ck_c_sessions_session_phase",
        ),
        CheckConstraint(
            "mastery_context_mode IN ('same_session_fresh', 'unavailable_fallback')",
            name="ck_c_sessions_mastery_context_mode",
        ),
        CheckConstraint("grade IN (2, 3)", name="ck_c_sessions_grade"),
        CheckConstraint(
            "state IN ('starting', 'active', 'completing', 'completed', 'abandoned', 'expired', 'technical_failed')",
            name="ck_c_sessions_state",
        ),
        Index(
            "uq_c_sessions_one_starting_or_active_per_learner",
            "student_id",
            unique=True,
            postgresql_where=text("state IN ('starting', 'active')"),
        ),
        *ProvenanceMixin.provenance_constraints("c_sessions"),
    )

    c_session_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("b_learners.learner_id", ondelete="RESTRICT"), nullable=False
    )
    intervention_session_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    session_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    session_phase: Mapped[str] = mapped_column(String(32), nullable=False)
    # ALLOW-LISTED (AUTHORIZED_C_COLUMN_EXCEPTIONS) -- false-positive-name class (R-C): contains
    # "mastery" but its domain is exactly the two values in the CHECK above, never a mastery
    # scalar.
    mastery_context_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    catalogue_version: Mapped[str] = mapped_column(String(128), nullable=False)
    catalogue_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    c_runtime_bundle_record_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("c_runtime_bundle_records.c_runtime_bundle_record_id", ondelete="RESTRICT"),
        nullable=False,
    )
    grade: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    global_seed: Mapped[int] = mapped_column(BigInteger, nullable=False)
    started_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))


class CTaskOpportunityRecord(ProvenanceMixin, Base):
    """Component C Phase 3a. One row per offered task; selection evidence; terminal result
    (v3.0 §11 Phase 3)."""

    __tablename__ = "c_task_opportunities"
    __table_args__ = (
        CheckConstraint(
            "session_phase IN ('familiarization', 'mastery_driven', 'c_only')",
            name="ck_c_task_opportunities_session_phase",
        ),
        CheckConstraint(
            "mastery_context_mode IN ('same_session_fresh', 'unavailable_fallback')",
            name="ck_c_task_opportunities_mastery_context_mode",
        ),
        *ProvenanceMixin.provenance_constraints("c_task_opportunities"),
    )

    c_task_opportunity_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    c_session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("c_sessions.c_session_id", ondelete="RESTRICT"), nullable=False
    )
    task_index: Mapped[int] = mapped_column(Integer, nullable=False)
    selected_skill_id: Mapped[str] = mapped_column(String(128), nullable=False)
    selected_template_id: Mapped[str] = mapped_column(String(128), nullable=False)
    initial_difficulty_level: Mapped[int] = mapped_column(Integer, nullable=False)
    # ALLOW-LISTED -- false-positive-name class, same reasoning as c_sessions above.
    mastery_context_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    # ALLOW-LISTED -- carries-real-content class (R-D): SelectionResult's own returned
    # provenance for the governed clamp(round(1 + 4 x mastery), 1, 5) initial-difficulty
    # decision (C-17). C auditing its own reviewed calculation, not re-storing B's contract.
    mastery_selected_skill: Mapped[float | None] = mapped_column(Float, nullable=True)
    session_phase: Mapped[str] = mapped_column(String(32), nullable=False)
    terminal_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    task_offered_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CTaskInstanceRecord(ProvenanceMixin, Base):
    """Component C Phase 3a. PRIVATE. Instance, difficulty vector, correct answer, seed lineage
    (v3.0 §11 Phase 3). No projection to a public DTO exists in this codebase yet -- building
    one (mirroring B's BE3c ``project_task_instance_to_presentation`` allow-list pattern) is
    Phase 5's job, not this batch's. Mirrors B's ``TaskInstanceRecord`` minimal-FK style: reached
    only via ``c_task_opportunity_id``, no denormalized session/student id."""

    __tablename__ = "c_task_instances"
    __table_args__ = (
        UniqueConstraint("c_task_opportunity_id", name="uq_c_task_instances_opportunity"),
        CheckConstraint("grade_scope IN (2, 3)", name="ck_c_task_instances_grade_scope"),
        CheckConstraint(
            "scaffold_state IN ('C0', 'C1', 'C2', 'C3', 'C4')", name="ck_c_task_instances_scaffold_state"
        ),
        CheckConstraint("technical_status IN ('OK', 'FAILED')", name="ck_c_task_instances_technical_status"),
        *ProvenanceMixin.provenance_constraints("c_task_instances"),
    )

    c_task_instance_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    c_task_opportunity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("c_task_opportunities.c_task_opportunity_id", ondelete="RESTRICT"),
        nullable=False,
    )
    game_family_id: Mapped[str] = mapped_column(String(32), nullable=False)
    game_task_template_id: Mapped[str] = mapped_column(String(64), nullable=False)
    template_version: Mapped[str] = mapped_column(String(64), nullable=False)
    catalogue_version: Mapped[str] = mapped_column(String(128), nullable=False)
    generator_version: Mapped[str] = mapped_column(String(64), nullable=False)
    task_index: Mapped[int] = mapped_column(Integer, nullable=False)
    skill_id: Mapped[str] = mapped_column(String(128), nullable=False)
    curriculum_node_id: Mapped[str] = mapped_column(String(128), nullable=False)
    grade_scope: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    difficulty_level: Mapped[int] = mapped_column(Integer, nullable=False)
    difficulty_vector: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    functional_role: Mapped[str] = mapped_column(String(32), nullable=False)
    representation_mode: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    interactive_assets: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # ALLOW-LISTED -- carries-real-content class: the private, never-public correct answer.
    correct_answer_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # ALLOW-LISTED -- carries-real-content class: not named by v3.0 §8, found by this batch's
    # own term-by-term derivation (Phase 3a work order R-B): "correctness_function_id" contains
    # "correct".
    correctness_function_id: Mapped[str] = mapped_column(String(64), nullable=False)
    valid_action_space: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    completion_condition: Mapped[str] = mapped_column(String(255), nullable=False)
    failure_condition: Mapped[str] = mapped_column(String(255), nullable=False)
    scaffold_state: Mapped[str] = mapped_column(String(8), nullable=False)
    recovery_parent_instance_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("c_task_instances.c_task_instance_id", ondelete="RESTRICT"), nullable=True
    )
    technical_status: Mapped[str] = mapped_column(String(16), nullable=False)
    seed_lineage_global_seed: Mapped[int] = mapped_column(BigInteger, nullable=False)
    seed_lineage_path: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    seed_lineage_seed: Mapped[int] = mapped_column(BigInteger, nullable=False)


class CGameplayEventRecord(ProvenanceMixin, Base):
    """Component C Phase 3a/3b. The canonical stream (C3 §14). Phase 3b (R-J/R-K/R-L/R-O) added:
    a partial UNIQUE index enforcing AT MOST ONE terminal event per task (never "exactly one" --
    R-N language discipline; "at least one" is a lifecycle-completeness rule, DEFERRED to the
    task-completion path (Phase 5) and the telemetry validator (Phase 8, which v3.0 Section 11
    already requires to check this on arrival) -- not a table constraint, not built here or
    anywhere in this migration); two triggers enforcing event_index consecutiveness and
    event_timestamp_relative_ms non-decreasing order within a task, each locking the parent
    c_task_instances row via SELECT ... FOR UPDATE (same pattern as B's
    enforce_b_session_active_bundle_eligibility) -- proven by sequential provocation only; this
    suite has no precedent for driving two real concurrent connections, so concurrent-writer
    safety is NOT tested, only the row-lock mechanism itself (R-M); and a structural CHECK tying
    attempt_number to ATTEMPT_SCOPED_EVENT_TYPES -- NOT "attempt counts bounded" (I4's numeric
    bound is BLOCKED, ESCALATED TO THE OWNER, R-L, and is not built in any form). Still no
    append-only/immutable-after-insert enforcement -- out of this batch's named scope."""

    __tablename__ = "c_gameplay_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ("
            "'game_task_offered', 'game_task_started', 'action_performed', 'answer_submitted', "
            "'answer_evaluated', 'retry_started', 'pause_started', 'pause_ended', "
            "'scaffold_requested', 'scaffold_shown', 'technical_issue', 'game_task_completed', "
            "'game_task_skipped', 'game_task_quit')",
            name="ck_c_gameplay_events_event_type",
        ),
        CheckConstraint("event_timestamp_relative_ms >= 0", name="ck_c_gameplay_events_timestamp_non_negative"),
        CheckConstraint(
            "scaffold_code IS NULL OR scaffold_code IN ('C0', 'C1', 'C2', 'C3', 'C4')",
            name="ck_c_gameplay_events_scaffold_code",
        ),
        CheckConstraint(
            "terminal_reason IS NULL OR terminal_reason IN ("
            "'completed_correct', 'completed_incorrect', 'skipped', 'quit_after_error', "
            "'quit_without_recent_error', 'technical_issue', 'attempt_cap_exhausted', "
            "'timeout_no_response', 'safe_session_stop')",
            name="ck_c_gameplay_events_terminal_reason",
        ),
        # Phase 3b, R-L: structural only -- WHICH event types may carry an attempt_number, never
        # HOW MANY attempts are allowed. Sourced live from
        # component_c_generator.models.gameplay.ATTEMPT_SCOPED_EVENT_TYPES.
        CheckConstraint(
            "attempt_number IS NULL OR event_type IN ('action_performed', 'answer_submitted', 'answer_evaluated')",
            name="ck_c_gameplay_events_attempt_number_scope",
        ),
        # Phase 3b, R-K: AT MOST ONE terminal event per task -- never "exactly one". Sourced live
        # from component_c_generator.models.gameplay.TERMINAL_EVENT_TYPES.
        Index(
            "uq_c_gameplay_events_at_most_one_terminal_per_instance",
            "game_task_instance_id",
            unique=True,
            postgresql_where=text(
                "event_type IN ('game_task_completed', 'game_task_skipped', 'game_task_quit')"
            ),
        ),
        *ProvenanceMixin.provenance_constraints("c_gameplay_events"),
    )

    c_gameplay_event_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    c_session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("c_sessions.c_session_id", ondelete="RESTRICT"), nullable=False
    )
    game_task_instance_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("c_task_instances.c_task_instance_id", ondelete="RESTRICT"), nullable=False
    )
    task_index: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    event_index: Mapped[int] = mapped_column(Integer, nullable=False)
    attempt_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    event_timestamp_relative_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    action_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    evaluation_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    scaffold_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    technical_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    terminal_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    seed_lineage_global_seed: Mapped[int] = mapped_column(BigInteger, nullable=False)
    seed_lineage_path: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    seed_lineage_seed: Mapped[int] = mapped_column(BigInteger, nullable=False)
    generator_version: Mapped[str] = mapped_column(String(64), nullable=False)
    config_checksum: Mapped[str] = mapped_column(String(64), nullable=False)


class CTaskOpportunitySummaryRecord(ProvenanceMixin, Base):
    """Component C Phase 3a. Derived per-task rollup (C3 §15). Derived only, never sampled --
    AT MOST ONE summary per task instance (UNIQUE below), never "exactly one" -- a task instance
    can exist without a summary (in progress, abandoned, quit before derivation runs). Fixed from
    "exactly one" (Phase 4 work order, Q3): the constraint was always correct; only the prose was
    wrong. If a genuine exactly-one invariant is later needed for COMPLETED task instances
    specifically, that is a check on the completion path, a later phase's item, not this table's
    schema."""

    __tablename__ = "c_task_opportunity_summaries"
    __table_args__ = (
        UniqueConstraint("game_task_instance_id", name="uq_c_task_opportunity_summaries_instance"),
        CheckConstraint(
            "highest_scaffold_level IS NULL OR highest_scaffold_level IN ('C0', 'C1', 'C2', 'C3', 'C4')",
            name="ck_c_task_opportunity_summaries_highest_scaffold_level",
        ),
        CheckConstraint(
            "terminal_reason IS NULL OR terminal_reason IN ("
            "'completed_correct', 'completed_incorrect', 'skipped', 'quit_after_error', "
            "'quit_without_recent_error', 'technical_issue', 'attempt_cap_exhausted', "
            "'timeout_no_response', 'safe_session_stop')",
            name="ck_c_task_opportunity_summaries_terminal_reason",
        ),
        *ProvenanceMixin.provenance_constraints("c_task_opportunity_summaries"),
    )

    c_task_opportunity_summary_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    c_session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("c_sessions.c_session_id", ondelete="RESTRICT"), nullable=False
    )
    game_task_instance_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("c_task_instances.c_task_instance_id", ondelete="RESTRICT"), nullable=False
    )
    task_index: Mapped[int] = mapped_column(Integer, nullable=False)
    task_offered: Mapped[bool] = mapped_column(Boolean, nullable=False)
    task_started: Mapped[bool] = mapped_column(Boolean, nullable=False)
    task_completed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    task_skipped: Mapped[bool] = mapped_column(Boolean, nullable=False)
    task_quit: Mapped[bool] = mapped_column(Boolean, nullable=False)
    technical_issue: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # ALLOW-LISTED -- carries-real-content class.
    correct_task: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    total_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False)
    scaffold_requested: Mapped[bool] = mapped_column(Boolean, nullable=False)
    scaffold_count: Mapped[int] = mapped_column(Integer, nullable=False)
    highest_scaffold_level: Mapped[str | None] = mapped_column(String(8), nullable=True)
    # ALLOW-LISTED -- carries-real-content class.
    c_answer_changes: Mapped[int] = mapped_column(Integer, nullable=False)
    # ALLOW-LISTED -- carries-real-content class.
    task_latency_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    inactive_time_sec: Mapped[float] = mapped_column(Float, nullable=False)
    inactivity_periods: Mapped[int] = mapped_column(Integer, nullable=False)
    quit_after_error: Mapped[bool] = mapped_column(Boolean, nullable=False)
    terminal_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # ALLOW-LISTED -- carries-real-content class.
    first_attempt_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # ALLOW-LISTED -- carries-real-content class.
    final_attempt_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # NOT allow-listed -- verified this batch (R-B) to NOT collide: the prohibited term is
    # "error_class", and this column contains "error_max", not "error_class". v3.0 §8 names this
    # column as colliding; that is a documented error in v3.0, not reproduced here.
    consecutive_error_max_within_task: Mapped[int] = mapped_column(Integer, nullable=False)


class CSessionAggregateResultRecord(ProvenanceMixin, Base):
    """Component C Phase 3a. PRIVATE. Aggregate + C-COMP-v1 + C-LS-v1 (v3.0 §11 Phase 3). No
    projection to a public DTO exists in this codebase yet -- Phase 5's job, not this batch's."""

    __tablename__ = "c_session_aggregate_results"
    __table_args__ = (
        UniqueConstraint("c_session_id", name="uq_c_session_aggregate_results_session"),
        CheckConstraint(
            "difficulty_trend IN ('increasing', 'stable', 'decreasing')",
            name="ck_c_session_aggregate_results_difficulty_trend",
        ),
        CheckConstraint(
            "telemetry_quality_status IS NULL OR telemetry_quality_status IN "
            "('complete', 'insufficient_evidence', 'technical_issue')",
            name="ck_c_session_aggregate_results_telemetry_quality_status",
        ),
        CheckConstraint(
            "learner_state IS NULL OR learner_state IN "
            "('engaged', 'productive_struggle', 'overloaded', 'disengaged')",
            name="ck_c_session_aggregate_results_learner_state",
        ),
        CheckConstraint(
            "state_reason IS NULL OR state_reason IN ("
            "'technical_issue', 'insufficient_session_evidence', 'safety_override_with_error_burst', "
            "'quit_after_error', 'repeated_floor_hits_with_low_completion', 'high_behavioral_friction', "
            "'low_engagement_score', 'inactivity_with_low_completion', 'high_engagement_low_friction', "
            "'sustained_participation_under_challenge', 'insufficient_sustained_participation')",
            name="ck_c_session_aggregate_results_state_reason",
        ),
        *ProvenanceMixin.provenance_constraints("c_session_aggregate_results"),
    )

    c_session_aggregate_result_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    c_session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("c_sessions.c_session_id", ondelete="RESTRICT"), nullable=False
    )
    task_opportunity_count: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_task_count: Mapped[int] = mapped_column(Integer, nullable=False)
    # ALLOW-LISTED -- carries-real-content class.
    correct_task_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_attempt_count: Mapped[int] = mapped_column(Integer, nullable=False)
    accuracy_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_attempts_per_task: Mapped[float | None] = mapped_column(Float, nullable=True)
    task_completion_rate: Mapped[float] = mapped_column(Float, nullable=False)
    inactivity_periods: Mapped[int] = mapped_column(Integer, nullable=False)
    inactive_time_sec: Mapped[float] = mapped_column(Float, nullable=False)
    inactive_time_available: Mapped[bool] = mapped_column(Boolean, nullable=False)
    session_duration_sec: Mapped[float] = mapped_column(Float, nullable=False)
    time_in_target_band_sec: Mapped[float] = mapped_column(Float, nullable=False)
    consecutive_error_max: Mapped[int] = mapped_column(Integer, nullable=False)
    difficulty_floor_hits: Mapped[int] = mapped_column(Integer, nullable=False)
    quit_after_error: Mapped[bool] = mapped_column(Boolean, nullable=False)
    safety_override_count: Mapped[int] = mapped_column(Integer, nullable=False)
    # ALLOW-LISTED -- carries-real-content class.
    c_mean_game_task_latency_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    # ALLOW-LISTED -- carries-real-content class.
    c_median_game_task_latency_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_difficulty_level: Mapped[int] = mapped_column(Integer, nullable=False)
    difficulty_trend: Mapped[str] = mapped_column(String(16), nullable=False)
    session_technical_issue_flag: Mapped[bool] = mapped_column(Boolean, nullable=False)
    engagement_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    engagement_completion_component: Mapped[float | None] = mapped_column(Float, nullable=True)
    engagement_activity_component: Mapped[float | None] = mapped_column(Float, nullable=True)
    engagement_target_band_component: Mapped[float | None] = mapped_column(Float, nullable=True)
    engagement_accuracy_component: Mapped[float | None] = mapped_column(Float, nullable=True)
    frustration_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    frustration_error_run_component: Mapped[float | None] = mapped_column(Float, nullable=True)
    frustration_excess_attempt_component: Mapped[float | None] = mapped_column(Float, nullable=True)
    frustration_inactivity_burden_component: Mapped[float | None] = mapped_column(Float, nullable=True)
    frustration_floor_hit_component: Mapped[float | None] = mapped_column(Float, nullable=True)
    frustration_quit_after_error_component: Mapped[float | None] = mapped_column(Float, nullable=True)
    frustration_safety_override_component: Mapped[float | None] = mapped_column(Float, nullable=True)
    telemetry_quality_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    learner_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    state_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)


class CLearnerLocalStateRecord(ProvenanceMixin, Base):
    """Component C Phase 3a. Longitudinal: ``eligible_combined_handoffs_completed`` (N),
    per-skill ``sessions_since_last_practice``, ``prior_session_end_state`` (v3.0 §11 Phase 3).
    One row per learner."""

    __tablename__ = "c_learner_local_state"
    __table_args__ = (
        UniqueConstraint("student_id", name="uq_c_learner_local_state_student"),
        CheckConstraint(
            "prior_session_end_state IS NULL OR prior_session_end_state IN "
            "('engaged', 'productive_struggle', 'overloaded', 'disengaged')",
            name="ck_c_learner_local_state_prior_session_end_state",
        ),
        *ProvenanceMixin.provenance_constraints("c_learner_local_state"),
    )

    c_learner_local_state_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("b_learners.learner_id", ondelete="RESTRICT"), nullable=False
    )
    eligible_combined_handoffs_completed: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    sessions_since_last_practice: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    prior_session_end_state: Mapped[str | None] = mapped_column(String(32), nullable=True)


class CPolicyDecisionRecord(ProvenanceMixin, Base):
    """Component C Phase 3a. Every proposal and applied action, versioned, incl.
    ``increase_block_remaining`` (v3.0 §11 Phase 3). ``evidence_snapshot`` holds the
    ``PolicyObservableEvidence`` the decision was based on as JSONB rather than flattened
    columns -- BUILDER JUDGMENT, UNRATIFIED: flattening would add more prohibited-term columns
    (e.g. ``recent_correctness_rate``) without changing what is stored."""

    __tablename__ = "c_policy_decisions"
    __table_args__ = (
        CheckConstraint(
            "policy_mode IN ('rule_based_baseline', 'q_learning_offline', 'frozen_q_evaluation')",
            name="ck_c_policy_decisions_policy_mode",
        ),
        CheckConstraint(
            "selected_action IN ('decrease_difficulty', 'hold', 'increase_difficulty')",
            name="ck_c_policy_decisions_selected_action",
        ),
        CheckConstraint(
            "applied_action IN ('decrease_difficulty', 'hold', 'increase_difficulty')",
            name="ck_c_policy_decisions_applied_action",
        ),
        CheckConstraint(
            "rolling_strain_bucket IN ('low', 'moderate', 'high', 'severe')",
            name="ck_c_policy_decisions_rolling_strain_bucket",
        ),
        CheckConstraint(
            "session_start_state_bucket IS NULL OR session_start_state_bucket IN "
            "('engaged', 'productive_struggle', 'overloaded', 'disengaged')",
            name="ck_c_policy_decisions_session_start_state_bucket",
        ),
        *ProvenanceMixin.provenance_constraints("c_policy_decisions"),
    )

    c_policy_decision_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    c_session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("c_sessions.c_session_id", ondelete="RESTRICT"), nullable=False
    )
    c_task_opportunity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("c_task_opportunities.c_task_opportunity_id", ondelete="RESTRICT"),
        nullable=False,
    )
    policy_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    rl_state: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    selected_action: Mapped[str] = mapped_column(String(32), nullable=False)
    applied_action: Mapped[str] = mapped_column(String(32), nullable=False)
    action_overridden: Mapped[bool] = mapped_column(Boolean, nullable=False)
    safety_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    difficulty_before: Mapped[int] = mapped_column(Integer, nullable=False)
    difficulty_after: Mapped[int] = mapped_column(Integer, nullable=False)
    rolling_strain_bucket: Mapped[str] = mapped_column(String(16), nullable=False)
    session_start_state_bucket: Mapped[str | None] = mapped_column(String(32), nullable=True)
    increase_block_remaining: Mapped[int] = mapped_column(Integer, nullable=False)
    internal_reward: Mapped[float | None] = mapped_column(Float, nullable=True)
    seed_lineage_global_seed: Mapped[int] = mapped_column(BigInteger, nullable=False)
    seed_lineage_path: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    seed_lineage_seed: Mapped[int] = mapped_column(BigInteger, nullable=False)
    evidence_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # Component C backend remediation, batch 3 (F-2): mirrors the existing sibling column on
    # CScaffoldEventRecord below EXACTLY (Mapped[bool], Boolean, nullable=False) -- no invented
    # vocabulary. Carries decide_adaptation_with_safety_flags's own activate_recovery_flag
    # (batch 1's reconstruction of a field the pinned package-composed AdaptationDecision drops),
    # persisted by adaptation_service.decide_and_persist_adaptation and read back by
    # task_service.submit_action's incorrect-answer branch -- see that module's own in-line
    # comment for the read-back's no-prior-row reasoning.
    safety_forces_recovery: Mapped[bool] = mapped_column(Boolean, nullable=False)


class CSafetyEventRecord(ProvenanceMixin, Base):
    """Component C Phase 3a. Every intervention, with trigger and action (v3.0 §11 Phase 3).
    ``trigger_reason``/``action_taken`` are left without an enum CHECK -- BUILDER JUDGMENT,
    UNRATIFIED: no verified package Literal names the closed vocabulary for these two fields the
    way it does for e.g. ``policy_mode``; adding an invented enum would risk exactly the kind of
    unsourced value R-G prohibits for numeric literals, applied here to strings instead."""

    __tablename__ = "c_safety_events"
    __table_args__ = (*ProvenanceMixin.provenance_constraints("c_safety_events"),)

    c_safety_event_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    c_session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("c_sessions.c_session_id", ondelete="RESTRICT"), nullable=False
    )
    c_policy_decision_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("c_policy_decisions.c_policy_decision_id", ondelete="RESTRICT"), nullable=True
    )
    trigger_reason: Mapped[str] = mapped_column(String(128), nullable=False)
    action_taken: Mapped[str] = mapped_column(String(64), nullable=False)
    difficulty_before: Mapped[int | None] = mapped_column(Integer, nullable=True)
    difficulty_after: Mapped[int | None] = mapped_column(Integer, nullable=True)


class CScaffoldEventRecord(ProvenanceMixin, Base):
    """Component C Phase 3a. Requests and shows, C0-C4 (v3.0 §11 Phase 3). ``event_type`` is
    left without an enum CHECK -- BUILDER JUDGMENT, UNRATIFIED: "requested"/"shown" is inferred
    from v3.0's own prose ("Requests and shows"), not verified against a package Literal the way
    ``scaffold_level`` is; not adding an unsourced enum here."""

    __tablename__ = "c_scaffold_events"
    __table_args__ = (
        CheckConstraint(
            "scaffold_level IN ('C0', 'C1', 'C2', 'C3', 'C4')", name="ck_c_scaffold_events_scaffold_level"
        ),
        *ProvenanceMixin.provenance_constraints("c_scaffold_events"),
    )

    c_scaffold_event_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    c_session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("c_sessions.c_session_id", ondelete="RESTRICT"), nullable=False
    )
    c_task_opportunity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("c_task_opportunities.c_task_opportunity_id", ondelete="RESTRICT"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(16), nullable=False)
    scaffold_level: Mapped[str] = mapped_column(String(8), nullable=False)
    consecutive_incorrect_current_task: Mapped[int] = mapped_column(Integer, nullable=False)
    safety_forces_recovery: Mapped[bool] = mapped_column(Boolean, nullable=False)


class CTaskOpportunityVerdictRecord(ProvenanceMixin, Base):
    """Component C backend remediation, batch 4 (Amendment A-1): the durable exclusion-reason /
    supersession-chain record Phase 8's own K3/K4 register entries named without building
    (``buildLog1.md``, "Component C Phase 8" entry). One row per rejected-derivation judgment
    about a task instance's event stream -- written by
    ``summary_service.derive_and_persist_summary`` whenever ``telemetry_validation.
    TelemetryStreamRejectedError`` fires (K3-b: "the durable exclusion record MUST EXIST before
    first real data, not merely before the gate on session creation lifts"). Covers BOTH of K4's
    faces in one mechanism, deliberately not two tables: a never-summarized instance (wrongly
    EXCLUDED, K3) and a previously-summarized instance a later re-validation finds bad (wrongly
    PASSED, K4-b) produce the IDENTICAL row shape, differing only in whether a
    ``CTaskOpportunitySummaryRecord`` already existed for the target at write time -- one is
    ``supersedes_verdict_id IS NULL`` (first judgment), the other chains to the prior live verdict.

    RULING 1 (REFUSE THE WHOLE SESSION, confirmed): this table records a fact ABOUT a stream, never
    a corrected summary -- there is no replacement value to substitute in its place. Converting
    "bad data counted as good" into "good data missing" IS the improvement this amendment exists to
    make; skipping just the corrected task would be C-4 verbatim (computing over a truncated window
    silently weakens the safety layer). ``telemetry_validation.get_derivable_history_for_session``
    removes a suppressed summary's ``task_index`` from its own derivable set, letting the EXISTING
    gap logic (Phase 8, unchanged) raise ``DistrustedHistoryGapError`` for the whole session -- no
    new exception type, no change to either consumer (``adaptation_service.
    build_evidence_for_session``, ``aggregation_service.derive_and_persist_session_aggregate``).

    RULING 2 (KEEP THE CHAIN): ``supersedes_verdict_id`` is a nullable self-FK. The amendment's own
    text says "appended and superseding rather than overwriting," and C-9 guarantees the validator
    changes more than once, so a summary corrected under one validator version can be corrected
    again under the next -- each correction is APPENDED, never overwritten, never deleted. A
    verdict is LIVE iff no OTHER verdict's ``supersedes_verdict_id`` points at it
    (``telemetry_validation._live_verdict_ids``, the one place liveness is computed, shared by both
    the read path and the write-time chain lookup) -- only a LIVE verdict suppresses its own
    target; row presence alone is never sufficient (see this table's own test coverage,
    ``tests/test_batch4_verdict_supersession.py``, for the cross-target isolation proof an untested
    chain would otherwise leave as pure decoration).

    CONDITION 1 (``verdict_detail`` records WHY, never the rejected values): populated verbatim
    from ``TelemetryStreamRejectedError.detail`` -- already structural-only by construction (check
    name, field paths, indices, counts; see every ``telemetry_validation.py`` raise site), never a
    copy of exception text that could carry a learner-supplied payload value. Same shape as the
    pydantic ``input_value=`` leak this project already guards against elsewhere
    (``MasteryPayloadContractValidationError``, ``app/domain/live_engine_c/errors.py``).

    CONDITION 2 (``validator_check`` draws from one named tuple, no DB-level enum): sourced from
    ``telemetry_validation.TELEMETRY_VALIDATION_CHECKS``, the single place the current check-name
    vocabulary is listed -- deliberately NOT a CHECK constraint here (C-9 guarantees this
    vocabulary will grow as the validator itself changes, and an unsourced enum would risk the same
    invented-value defect R-G already prohibits for numeric thresholds, applied here to a string
    vocabulary instead).

    Two CHECK constraints only, per Amendment A-1's own scope: a nonblank guard on
    ``validator_check`` (the same discipline every other short-code text column in this file
    already carries, e.g. ``ck_teacher_profiles_name_nonblank``) and a structural guard preventing
    a verdict from citing itself as its own predecessor -- a genuine correctness property of the
    new self-referencing chain, not an invented threshold.

    HOW TO TELL AN EXCLUSION FROM A SUPERSESSION -- there is deliberately no ``verdict_kind``
    column, because the distinction is DERIVED, not stored. Join a live verdict to
    ``c_task_opportunity_summaries`` on ``game_task_instance_id``:

        live verdict + NO summary for that instance  ->  the stream was EXCLUDED at ingestion
                                                          (derivation never produced a summary)
        live verdict + a summary for that instance   ->  that summary is SUPERSEDED
                                                          (it was accepted, and later found wrong)

    This derivation is stable and cannot drift, because ``uq_c_task_opportunity_summaries_instance``
    makes summaries insert-once per instance and this store is append-only: an instance that has no
    summary can never acquire one (derivation runs exactly once, at terminal-event time, and it
    failed), and an instance that has one can never lose it. A stored discriminator would be
    redundant with this join AND capable of contradicting it, which is why it is absent.

    Amendment A-1's ratified proposal named a ``verdict_kind`` enum and a ``superseded_summary_id``
    FK. Neither was built. ``superseded_summary_id`` is redundant against the insert-once
    constraint above -- one instance has exactly one summary, so ``game_task_instance_id`` already
    identifies it -- and ``verdict_kind`` is the derived value documented here. The reduction was
    accepted on review after the fact; it was NOT flagged as a deviation when it was made, and the
    build-log entry records that separately."""

    __tablename__ = "c_task_opportunity_verdicts"
    __table_args__ = (
        CheckConstraint(
            "validator_check <> ''", name="ck_c_task_opportunity_verdicts_validator_check_nonblank"
        ),
        CheckConstraint(
            "supersedes_verdict_id IS DISTINCT FROM c_task_opportunity_verdict_id",
            name="ck_c_task_opportunity_verdicts_not_self_superseding",
        ),
        *ProvenanceMixin.provenance_constraints("c_task_opportunity_verdicts"),
    )

    c_task_opportunity_verdict_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    c_session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("c_sessions.c_session_id", ondelete="RESTRICT"), nullable=False
    )
    game_task_instance_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("c_task_instances.c_task_instance_id", ondelete="RESTRICT"), nullable=False
    )
    task_index: Mapped[int] = mapped_column(Integer, nullable=False)
    validator_check: Mapped[str] = mapped_column(String(64), nullable=False)
    verdict_detail: Mapped[str] = mapped_column(String(500), nullable=False)
    supersedes_verdict_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("c_task_opportunity_verdicts.c_task_opportunity_verdict_id", ondelete="RESTRICT"),
        nullable=True,
    )


class OutboxEventRecord(ProvenanceMixin, Base):
    """Component C batch 9c-1a (Master Build Plan v3.0 §11 Phase 9; 9b_9c plan Track 9c, "9c-1 --
    the tables and the routing"). One row per opaque outbound payload awaiting delivery, for BOTH
    components -- Phase 9's own text: "Neither B nor C has a transactional outbox today. Build
    ``outbox_events`` and ``contract_deliveries`` once, shared." Deliberately unprefixed (no
    ``b_``/``c_``) because it is shared infrastructure, not shared ownership (Component B owner's
    condition 1).

    WHAT THIS TABLE DOES NOT DO. It does not construct a payload -- per the 9c-1 planning note,
    "An outbox stores and delivers opaque payloads; it does not construct one." It does not route,
    dispatch, poll, or attempt delivery -- no code in this batch ever writes a row here; that is
    9c-1b and later. It does not enforce that a superseded record cannot be delivered (Component B
    owner's condition 4) -- that enforcement point, and whatever column it turns out to need, is
    9c-1b's design to make, not this batch's to guess.

    OWNERSHIP (condition 2 -- "Component B owns its B-side rows... Component C owns its C-side
    rows... one schema, two owners, no shared validation path"). ``owning_component`` is the single
    source of truth for which component's row this is. ``contract_deliveries`` does NOT repeat this
    column; it derives ownership transitively through its mandatory FK back to this table. A second,
    independently-writable copy on the child table could contradict the row it joins to -- exactly
    the "redundant AND capable of contradicting it" trap this same file's
    ``CTaskOpportunityVerdictRecord`` docstring already argues against for ``verdict_kind``.

    ``contract_name`` IS DELIBERATELY NOT ENUMERATED. The real, closed vocabulary
    (``"mapping"``/``"b_to_c"``/``"b_to_3"``/``"c_to_3"``) is ``PayloadKind`` at
    ``packaging/component_b_internal/validators/contract_validators.py:62`` -- a vendored contract
    module this repository does not own. A CHECK here would be a second copy of a vocabulary whose
    source of truth lives elsewhere: if that module gains a kind, a local enum silently blocks a
    legitimate insert; if it loses one, the enum goes stale with nothing to say so. Worse, an enum
    here would itself violate condition 2 -- a CHECK in the SHARED schema that validates a value
    against a contract's own vocabulary IS a shared validation path. Validating ``contract_name``
    against ``PayloadKind`` is each owning component's job when it enqueues a row, not this table's.
    Only a nonblank guard lives here.

    NO LEARNER IDENTIFIER (owner condition 3 / 9c-0's determination, ``buildLog1.md``'s 9c-0 entry).
    The only value reachable today for an outbound ``student_id``-shaped field is
    ``package_student_id()``/``student_number()`` -- exactly the derivation 9c-0 wrote down as
    prohibited, and which ``test_identity_derivation_symbols_confined_to_allowed_files`` blocks
    outside its two allow-listed files. A dedicated identifier column here would therefore be either
    permanently NULL (nothing can populate it correctly) or the exact collision trap 9c-0 exists to
    prevent. If a real assigned identifier ever rides inside ``payload_json``, sourced correctly by a
    later batch from ``SharedInterventionSessionMapping`` once that mapping exists, that is identity
    inside the opaque payload -- not the same thing as promoting it to a first-class column, which
    would be a second place identity is recorded outside the mapping. Deliberately absent.

    NO ``status``/``dispatched`` COLUMN. Whether an event has been delivered is derivable by joining
    to ``contract_deliveries`` on ``outbox_event_id`` and inspecting ``outcome`` -- the same
    derive-don't-duplicate discipline ``CTaskOpportunityVerdictRecord`` already uses to tell an
    exclusion from a supersession by joining rather than storing a redundant discriminator. NOTE:
    this derivation is correct in SHAPE but undefined in CONTENT at this commit -- ``outcome`` carries
    no enum and no defined vocabulary yet (see ``ContractDeliveryRecord``), so "a successful outcome"
    is not yet a defined value. **CORRECTION (9c-1b, work order v2 ADDENDUM A, Ruling 2): this
    docstring originally said "9c-1b, which builds the dispatcher, owns naming that vocabulary and
    owns defining delivery state against it" -- that attribution was WRONG and is corrected here,
    not merely amended. 9c-1b builds the ENQUEUE (write) side only and, in doing so, names the
    ``outcome`` vocabulary and defines delivery state against it
    (``app.application.live_engine_c.outbox_enqueue.DELIVERY_OUTCOMES``/``is_delivered``). It does
    NOT build a dispatcher. A dispatcher is the DRAIN side -- it needs a delivery target, error
    semantics, and the retry/backoff/timeout behaviour v2 §3 prohibits outright for THIS batch -- and
    belongs to a separate, later, unnamed batch. Whoever builds it must re-read v2 §3's retry/
    backoff/timeout prohibition before extending this vocabulary."""

    __tablename__ = "outbox_events"
    __table_args__ = (
        CheckConstraint("owning_component IN ('B', 'C')", name="ck_outbox_events_owning_component"),
        CheckConstraint("contract_name <> ''", name="ck_outbox_events_contract_name_nonblank"),
        *ProvenanceMixin.provenance_constraints("outbox_events"),
    )

    outbox_event_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    owning_component: Mapped[str] = mapped_column(String(1), nullable=False)
    contract_name: Mapped[str] = mapped_column(String(32), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class ContractDeliveryRecord(ProvenanceMixin, Base):
    """Component C batch 9c-1a (Master Build Plan v3.0 §11 Phase 9; 9b_9c plan Track 9c, "9c-1 --
    the tables and the routing"). One row per attempt to deliver an ``OutboxEventRecord`` payload
    to its downstream contract target -- shared infrastructure alongside ``outbox_events``, built
    for the same reason and by the same authorization; see that class's docstring for the full
    ownership, identifier, and derivation reasoning shared by both tables.

    Append-only: one row per attempt, never updated in place, so a retried delivery is a NEW row,
    not a mutation of a prior one. ``outbox_event_id`` is mandatory -- a delivery record with no
    event it attempted to deliver is not a delivery record. This table carries no ``owning_component``
    of its own; ownership is derived transitively through this same FK (see ``OutboxEventRecord``'s
    docstring on why a second, independently-writable copy would be a duplicate discriminator capable
    of contradicting the row it joins to).

    ``outcome`` HAS NO ENUM. No dispatcher exists yet to define what values it may take. Enumerating
    it now would be inventing that vocabulary ahead of the thing that owns it, the same defect
    ``CTaskOpportunityVerdictRecord.validator_check`` already avoids for its own not-yet-fixed
    vocabulary ("draws from one named tuple, no DB-level enum"). Only a nonblank guard lives here.
    **CORRECTION (9c-1b, work order v2 ADDENDUM A, Ruling 2): this docstring originally said "that is
    9c-1b's mechanism, not this batch's... 9c-1b must define the vocabulary AND what 'delivered'
    means against it" -- worded to imply 9c-1b builds a dispatcher. It does not.** 9c-1b names the
    ``outcome`` vocabulary and defines "delivered" against it
    (``app.application.live_engine_c.outbox_enqueue.DELIVERY_OUTCOMES``/``is_delivered``) as the
    ENQUEUE side's own D3 deliverable -- it builds no dispatcher and adds no `failed`/`retrying`-style
    member, because no dispatcher exists yet to source those from. A later, unnamed batch builds the
    dispatcher and extends this vocabulary from the real error semantics it introduces, after
    re-reading v2 §3's retry/backoff/timeout prohibition."""

    __tablename__ = "contract_deliveries"
    __table_args__ = (
        CheckConstraint("outcome <> ''", name="ck_contract_deliveries_outcome_nonblank"),
        CheckConstraint(
            "delivery_detail IS NULL OR delivery_detail <> ''",
            name="ck_contract_deliveries_delivery_detail_nonblank_or_null",
        ),
        *ProvenanceMixin.provenance_constraints("contract_deliveries"),
    )

    contract_delivery_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    outbox_event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("outbox_events.outbox_event_id", ondelete="RESTRICT"), nullable=False
    )
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    delivery_detail: Mapped[str | None] = mapped_column(String(500), nullable=True)


class DLearnerStateRecord(ProvenanceMixin, Base):
    """Component D (Component D authorization, D-011 A1). One row per learner: whether they have
    seen the compD intro, and the language they chose.

    ``intro_completed_at`` is a TIMESTAMP, not a boolean, and the public DTO derives
    ``intro_completed`` from ``IS NOT NULL``. Storing the moment rather than the fact costs one
    column and answers "when", which a boolean throws away for good; the API shape is unchanged.

    A learner with NO ROW is a supported state, not an error: the contract reads it as
    ``{intro_completed: false, language: "en"}`` and creates nothing. The row appears on the first
    POST. That is why ``language`` is NOT NULL here while still having a default at the API layer
    -- the default belongs to the read, not to the table, so the table never holds a language the
    learner did not pick.
    """

    __tablename__ = "d_learner_state"
    __table_args__ = (
        CheckConstraint("language IN ('en', 'si')", name="ck_d_learner_state_language"),
        *ProvenanceMixin.provenance_constraints("d_learner_state"),
    )

    learner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("b_learners.learner_id", ondelete="RESTRICT"),
        primary_key=True,
    )
    intro_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    language: Mapped[str] = mapped_column(String(2), nullable=False)


class DInteractionRecord(ProvenanceMixin, Base):
    """Component D (Component D authorization, D-011 A1). One row per question answered in a
    profiling run -- the raw evidence the feature vector is computed from.

    NAMES. ``response_matched`` and ``assist_used`` are the HOST'S OWN names for these two
    concepts (``b_attempts.response_matched``; ``b_hint_events.assist_event_id`` /
    ``assist_level``), adopted under D-011 A4. compD called them ``is_correct`` and ``hint_used``,
    which collide with ``PROHIBITED_COLUMN_TERMS``' "correct" and "hint". They are NOT in
    ``AUTHORIZED_D_COLUMN_EXCEPTIONS`` -- that set does not exist, deliberately: the authorization
    found the host already had names for both, so no exemption was asked for or granted. Do not
    "restore" the compD spellings; they would fail
    ``test_exact_authorized_model_table_set_and_no_scientific_columns`` with nothing to exempt them.

    ``response_time_sec``, ``session_time_sec`` and ``time_between_actions`` are clean as they
    stand: the prohibited term is "latency", not "time" (contrast ``b_attempts.client_elapsed_ms``,
    which took the same route, and ``c_task_opportunity_summaries.task_latency_sec``, which needed
    an exemption).

    ``session_id`` needs no exemption either: "session" is a prohibited PATH term, not a column
    term -- ``b_sessions``, ``c_sessions`` and ``b_attempts`` all carry one already.

    The unique ``(session_id, question_id)`` is what makes the profile POST idempotent at the
    database level: a retry of the identical body (N-FE-003) cannot double-insert, and the
    ``IntegrityError`` backstop turns a genuine race into a 409 rather than two rows.
    """

    __tablename__ = "d_interactions"
    __table_args__ = (
        UniqueConstraint("session_id", "question_id", name="uq_d_interactions_session_question"),
        CheckConstraint(
            "topic IN ('Counting', 'Addition', 'Subtraction', 'Division')",
            name="ck_d_interactions_topic",
        ),
        CheckConstraint("difficulty IN ('Easy', 'Medium', 'Hard')", name="ck_d_interactions_difficulty"),
        CheckConstraint(
            "error_type IN ('none', 'calculation', 'conceptual', 'careless', 'unknown')",
            name="ck_d_interactions_error_type",
        ),
        CheckConstraint("response_time_sec >= 0", name="ck_d_interactions_response_time_sec_nonnegative"),
        CheckConstraint("session_time_sec >= 0", name="ck_d_interactions_session_time_sec_nonnegative"),
        CheckConstraint(
            "time_between_actions >= 0", name="ck_d_interactions_time_between_actions_nonnegative"
        ),
        CheckConstraint("click_count >= 0", name="ck_d_interactions_click_count_nonnegative"),
        CheckConstraint("attempts >= 1", name="ck_d_interactions_attempts_at_least_one"),
        CheckConstraint("question_id <> ''", name="ck_d_interactions_question_id_nonblank"),
        *ProvenanceMixin.provenance_constraints("d_interactions"),
    )

    d_interaction_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    learner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("b_learners.learner_id", ondelete="RESTRICT"), nullable=False
    )
    session_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    question_id: Mapped[str] = mapped_column(String(128), nullable=False)
    topic: Mapped[str] = mapped_column(String(16), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(8), nullable=False)
    response_time_sec: Mapped[float] = mapped_column(Float, nullable=False)
    attempts: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    # D-011 A4: the host's own name (b_attempts.response_matched), NOT compD's `is_correct`.
    response_matched: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # D-011 A4: the host's own `assist_*` naming (b_hint_events), NOT compD's `hint_used`.
    assist_used: Mapped[bool] = mapped_column(Boolean, nullable=False)
    click_count: Mapped[int] = mapped_column(Integer, nullable=False)
    session_time_sec: Mapped[float] = mapped_column(Float, nullable=False)
    time_between_actions: Mapped[float] = mapped_column(Float, nullable=False)
    error_type: Mapped[str] = mapped_column(String(16), nullable=False)


class DCognitiveProfileRecord(ProvenanceMixin, Base):
    """Component D (Component D authorization, D-011 A1). One profile per profiling run.

    WHAT IS STORED, AND WHAT DELIBERATELY IS NOT. The four levels, the confidence score, the
    feature vector and the model version are stored. The RECOMMENDATION TEXT IS NOT: it is built
    when the profile is read, in the language the read asked for (contract v4). Persisting it
    would freeze the wording of the day it was generated, so a learner who switches to Sinhala
    would see their History in English forever -- the defect plan v5 recorded and this column list
    is the fix for.

    ``session_id`` is UNIQUE GLOBALLY, not per learner. A profile is fetched by that id alone, so
    a non-unique id would make ``GET /d/sessions/{session_id}/profile`` ambiguous; and because the
    uniqueness is global, a session id belonging to ANOTHER learner is found and then refused as a
    404 rather than silently missing -- which is what lets the route avoid confirming that someone
    else's session exists.

    ``features`` is JSONB rather than eight columns. The keys are a vector the rule-based profile
    consumes as a unit and the API returns as a unit; splitting them would add eight columns that
    are never queried individually, and would make the inevitable ninth feature a migration. Note
    the guard consequence, which is why this is recorded rather than assumed: the column guard
    reads COLUMN NAMES, so keys inside this JSONB (``mean_clicks_per_question``, ``hint_rate``)
    are not column names and are not scanned. That is not a loophole being used -- both of those
    names are clean anyway under D-011 A4 -- but a later key that carried a prohibited term would
    pass the DB guard while still being caught at the public layer by
    ``test_no_private_or_scientific_field_name_in_frozen_schema``.
    """

    __tablename__ = "d_cognitive_profiles"
    __table_args__ = (
        UniqueConstraint("session_id", name="uq_d_cognitive_profiles_session"),
        CheckConstraint(
            "memory_level IN ('low', 'medium', 'high')", name="ck_d_cognitive_profiles_memory_level"
        ),
        CheckConstraint(
            "attention_level IN ('low', 'medium', 'high')", name="ck_d_cognitive_profiles_attention_level"
        ),
        CheckConstraint(
            "number_sense_level IN ('low', 'medium', 'high')",
            name="ck_d_cognitive_profiles_number_sense_level",
        ),
        CheckConstraint(
            "processing_speed_level IN ('Slow', 'Moderate', 'Fast')",
            name="ck_d_cognitive_profiles_processing_speed_level",
        ),
        CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 1",
            name="ck_d_cognitive_profiles_confidence_score_unit_interval",
        ),
        CheckConstraint("model_version <> ''", name="ck_d_cognitive_profiles_model_version_nonblank"),
        Index(
            "ix_d_cognitive_profiles_learner_generated_at",
            "learner_id",
            text("generated_at DESC"),
        ),
        *ProvenanceMixin.provenance_constraints("d_cognitive_profiles"),
    )

    d_cognitive_profile_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    # The four level columns are String(16) although the longest permitted value ("Moderate") is
    # 8. The CHECK is the real domain; the length is only a backstop, and a tight one MASKS the
    # CHECK -- a 9-character bad value is refused as "value too long" before the constraint is
    # reached, which is a confusing error and, worse, made this file's own test pass for the wrong
    # reason until it was caught. Slack here costs nothing in Postgres.
    learner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("b_learners.learner_id", ondelete="RESTRICT"), nullable=False
    )
    session_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    memory_level: Mapped[str] = mapped_column(String(16), nullable=False)
    attention_level: Mapped[str] = mapped_column(String(16), nullable=False)
    number_sense_level: Mapped[str] = mapped_column(String(16), nullable=False)
    processing_speed_level: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    features: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


AUTHORIZED_TABLES = frozenset(Base.metadata.tables)
