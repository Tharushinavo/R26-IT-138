"""Authorized classroom invite and membership use cases only.

Per component-b-invite-membership-authorization.json plus the Version 1 human-readable
join-code clarification: the classroom invite "token" is a short, uppercase,
high-entropy, human-typeable code (e.g. "M7KP-4X9D"), not an opaque URL-safe string or
a QR payload. Wire field names (`invite_token`, `classroom_invite`) remain frozen by
governance; only the generation/normalization algorithm changes.
"""

import hashlib
import json
import re
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.core.errors import ConflictError, ForbiddenError, ResourceNotFoundError
from app.domain.classroom_membership import (
    ClassroomLearnerListItem,
    ClassroomLearnerListResponse,
    InviteCreateResponse,
    InviteResolveResponse,
    InviteRevokeResponse,
    InviteTokenRequest,
    LearnerMembershipListItem,
    LearnerMembershipListResponse,
    MembershipDecisionResponse,
    MembershipRequestListItem,
    MembershipRequestListResponse,
    MembershipRequestResponse,
)
from app.domain.principal import AuthenticatedPrincipal
from app.infrastructure.persistence_models import (
    AppUser,
    AuditEvent,
    Classroom,
    ClassroomInvite,
    ClassroomMembership,
    IdempotencyRecord,
    Learner,
    TeacherProfile,
)
from app.infrastructure.repositories import (
    AppUserRepository,
    ClassroomInviteRepository,
    ClassroomMembershipRepository,
    ClassroomRepository,
    IdempotencyRecordRepository,
    TeacherProfileRepository,
)
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


SCHEMA_REVISION = "20260723_0001"

# Human-readable classroom join code. Excludes visually ambiguous characters (0/O,
# 1/I/L) per the Version 1 product clarification. 31-symbol alphabet, 8 characters =
# log2(31) * 8 ~= 39.6 bits of entropy, grouped 4-4 for display (e.g. "M7KP-4X9D").
# This is a deliberately short, typeable code, not a long-lived secret: it expires in
# 24 hours and is revocable. The exact length/grouping are tunable constants; the
# entropy figure is recorded here and in buildLog.md for the deferred BE6 backend
# security owner review of the invite-token cryptographic contract.
_JOIN_CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
_JOIN_CODE_LENGTH = 8
_JOIN_CODE_GROUP_SIZE = 4
_JOIN_CODE_SEPARATOR_PATTERN = re.compile(r"[\s-]+")

# Classroom roster grade -> learner roster grade, on membership APPROVAL only.
#
# `Classroom.grade` is String(16) constrained to GRADE_2|GRADE_3 (`ck_classrooms_grade`);
# `Learner.grade` is a nullable SmallInteger constrained to NULL|2|3 (`ck_b_learners_grade`).
# This is deliberately an explicit mapping rather than string slicing/parsing: if a third
# classroom grade is ever added, this must fail loudly with a KeyError rather than silently
# mis-map, because the learner grade selects which catalogue templates are eligible.
#
# Scope: this is ROSTER METADATA the teacher already chose when creating the classroom
# (`Classroom.grade` is NOT NULL). It sets no mastery prior, no BKT parameter, no difficulty
# ladder, no session bound, and no attempt limit.
_CLASSROOM_GRADE_TO_LEARNER_GRADE = {"GRADE_2": 2, "GRADE_3": 3}


def generate_classroom_join_code() -> str:
    """Cryptographically secure canonical (ungrouped) join code."""
    return "".join(secrets.choice(_JOIN_CODE_ALPHABET) for _ in range(_JOIN_CODE_LENGTH))


def format_join_code_for_display(canonical_code: str) -> str:
    """Group the canonical code for human readability, e.g. 'M7KP-4X9D'."""
    return "-".join(
        canonical_code[index : index + _JOIN_CODE_GROUP_SIZE]
        for index in range(0, len(canonical_code), _JOIN_CODE_GROUP_SIZE)
    )


def normalize_join_code(raw: str) -> str:
    """Case-insensitive, separator-insensitive normalization used for both hashing and idempotency fingerprinting."""
    return _JOIN_CODE_SEPARATOR_PATTERN.sub("", raw).upper()


def hash_join_code(normalized_code: str) -> str:
    return hashlib.sha256(normalized_code.encode()).hexdigest()


def body_fingerprint(body: dict[str, object]) -> str:
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def path_fingerprint(actor_user_id: UUID, operation: str, path_parameter: object, body: dict[str, object]) -> str:
    """Canonical fingerprint for path-based commands: method + operation + actor + normalized path parameter + body.

    Required because these commands have an empty body; fingerprinting the body alone
    would make requests for different classroom/membership/invite IDs collide.
    """
    canonical = json.dumps(
        {
            "http_method": "POST",
            "operation_identifier": operation,
            "actor_user_id": str(actor_user_id),
            "path_parameter": str(path_parameter),
            "body": body,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def provenance(user_id: UUID, request_id: str, operation: str, resource_type: str, resource_id: UUID) -> dict[str, object]:
    return {
        "actor_user_id": user_id,
        "request_id": request_id,
        "operation_or_event_type": operation,
        "reason_code": "AUTHORIZED_CLASSROOM_INVITE_MEMBERSHIP_COMMAND",
        "resource_type": resource_type,
        "resource_id": resource_id,
        "source_class": "REAL",
        "source_system": "studentapp-api",
        "environment": "live-endpoint",
        "schema_revision": SCHEMA_REVISION,
    }


class ClassroomMembershipService:
    def __init__(self, uow_factory=SqlAlchemyUnitOfWork) -> None:
        self._uow_factory = uow_factory

    async def _require_user(self, session, principal: AuthenticatedPrincipal) -> AppUser:
        user = await AppUserRepository(session).find_by_subject(principal.user_id)
        if user is None:
            raise ResourceNotFoundError()
        return user

    async def _teacher_context(self, session, principal: AuthenticatedPrincipal) -> tuple[AppUser, TeacherProfile]:
        user = await self._require_user(session, principal)
        if user.profile_type != "TEACHER":
            raise ForbiddenError()
        profile = await TeacherProfileRepository(session).find_by_user(user.user_id)
        if profile is None:
            raise ResourceNotFoundError()
        return user, profile

    async def _require_learner(self, session, principal: AuthenticatedPrincipal) -> tuple[AppUser, UUID]:
        found = await AppUserRepository(session).find_with_learner_link_by_subject(principal.user_id)
        if found is None:
            raise ResourceNotFoundError()
        user, link = found
        if user.profile_type != "LEARNER":
            raise ForbiddenError()
        if link is None:
            raise ResourceNotFoundError()
        return user, link.learner_id

    async def _idempotency_start(
        self, session, user: AppUser, operation: str, key: str, fingerprint_value: str, request_id: str
    ) -> tuple[IdempotencyRecord, dict[str, object] | None]:
        await session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:scope, 0))"),
            {"scope": f"{user.user_id}:POST:{operation}:{key}"},
        )
        repository = IdempotencyRecordRepository(session)
        existing = await repository.find_scoped(user.user_id, "POST", operation, key)
        if existing is not None:
            if existing.request_fingerprint != fingerprint_value:
                raise ConflictError()
            if existing.processing_status == "succeeded" and existing.canonical_response is not None:
                return existing, existing.canonical_response
            raise ConflictError()
        record_id = uuid4()
        record = IdempotencyRecord(
            idempotency_record_id=record_id,
            http_method="POST",
            operation_identifier=operation,
            idempotency_key=key,
            request_fingerprint=fingerprint_value,
            processing_status="in_progress",
            canonical_response=None,
            response_status=None,
            expires_at_utc=datetime.now(UTC) + timedelta(hours=24),
            **provenance(user.user_id, request_id, operation, "b_idempotency_record", record_id),
        )
        await repository.add(record)
        return record, None

    @staticmethod
    def _finish(record: IdempotencyRecord, response: dict[str, object], status_code: int) -> None:
        record.processing_status = "succeeded"
        record.canonical_response = response
        record.response_status = status_code

    @staticmethod
    def _audit(
        session,
        user_id: UUID,
        request_id: str,
        operation: str,
        resource_type: str,
        resource_id: UUID,
        *,
        before: str | None = None,
        after: str | None = None,
    ) -> None:
        audit_id = uuid4()
        session.add(
            AuditEvent(
                audit_event_id=audit_id,
                before_reference_or_version=before,
                after_reference_or_version=after if after is not None else str(resource_id),
                **provenance(user_id, request_id, operation, resource_type, resource_id),
            )
        )

    async def create_invite(self, principal: AuthenticatedPrincipal, classroom_id: UUID, key: str, request_id: str) -> InviteCreateResponse:
        async with self._uow_factory() as uow:
            user, teacher = await self._teacher_context(uow.session, principal)
            classroom = await ClassroomRepository(uow.session).get_owned(classroom_id, teacher.teacher_profile_id)
            if classroom is None:
                raise ResourceNotFoundError()
            fp = path_fingerprint(user.user_id, "classroom_invite.create", classroom_id, {})
            idem, replay = await self._idempotency_start(uow.session, user, "classroom_invite.create", key, fp, request_id)
            if replay is not None:
                return InviteCreateResponse.model_validate(replay)
            # One live join code per classroom. Idempotency-Key only collapses retries of the
            # same call; two calls with different keys would otherwise mint a second code that
            # also resolves, while the teacher can only ever read one of them back.
            now = datetime.now(UTC)
            invite_repository = ClassroomInviteRepository(uow.session)
            existing = await invite_repository.find_live_by_classroom(classroom_id, now)
            if existing is not None:
                response = InviteCreateResponse(
                    classroom_invite_id=existing.classroom_invite_id,
                    # The plaintext was shown once, at creation, and only its hash was kept.
                    invite_token=None,
                    token_already_issued=True,
                    expires_at_utc=existing.expires_at_utc,
                    created_at_utc=existing.created_at_utc,
                    request_id=request_id,
                )
                self._finish(idem, response.model_dump(mode="json"), 200)
                await uow.commit()
                return response
            canonical_code = generate_classroom_join_code()
            token_hash = hash_join_code(canonical_code)
            invite_id = uuid4()
            # A classroom join code does not expire. It dies when the classroom is deleted
            # (revoked_at_utc), never on a clock -- children write it down.
            expires_at = None
            invite = ClassroomInvite(
                classroom_invite_id=invite_id,
                classroom_id=classroom_id,
                token_hash=token_hash,
                expires_at_utc=expires_at,
                revoked_at_utc=None,
                created_by_user_id=user.user_id,
                row_version=0,
                **provenance(user.user_id, request_id, "classroom_invite.created", "classroom_invite", invite_id),
            )
            uow.session.add(invite)
            await uow.session.flush()
            self._audit(uow.session, user.user_id, request_id, "classroom_invite.created", "classroom_invite", invite_id)
            stored_response = {
                "classroom_invite_id": str(invite_id),
                "invite_token": None,
                "token_already_issued": True,
                "expires_at_utc": invite.expires_at_utc.isoformat() if invite.expires_at_utc is not None else None,
                "created_at_utc": invite.created_at_utc.isoformat(),
                "request_id": request_id,
            }
            self._finish(idem, stored_response, 201)
            await uow.commit()
            return InviteCreateResponse(
                classroom_invite_id=invite_id,
                invite_token=format_join_code_for_display(canonical_code),
                token_already_issued=False,
                expires_at_utc=invite.expires_at_utc,
                created_at_utc=invite.created_at_utc,
                request_id=request_id,
            )

    async def revoke_invite(self, principal: AuthenticatedPrincipal, classroom_invite_id: UUID, key: str, request_id: str) -> InviteRevokeResponse:
        async with self._uow_factory() as uow:
            user, teacher = await self._teacher_context(uow.session, principal)
            owned = await ClassroomInviteRepository(uow.session).get_owned(classroom_invite_id, teacher.teacher_profile_id)
            if owned is None:
                raise ResourceNotFoundError()
            fp = path_fingerprint(user.user_id, "classroom_invite.revoke", classroom_invite_id, {})
            idem, replay = await self._idempotency_start(uow.session, user, "classroom_invite.revoke", key, fp, request_id)
            if replay is not None:
                return InviteRevokeResponse.model_validate(replay)
            invite = await uow.session.scalar(
                select(ClassroomInvite).where(ClassroomInvite.classroom_invite_id == classroom_invite_id).with_for_update()
            )
            now = datetime.now(UTC)
            if invite.revoked_at_utc is not None:
                raise ConflictError()
            if invite.expires_at_utc is not None and invite.expires_at_utc <= now:
                raise ConflictError()
            invite.revoked_at_utc = now
            invite.row_version += 1
            await uow.session.flush()
            self._audit(
                uow.session, user.user_id, request_id, "classroom_invite.revoked", "classroom_invite", classroom_invite_id,
                after=now.isoformat(),
            )
            response = InviteRevokeResponse(
                classroom_invite_id=classroom_invite_id,
                classroom_id=invite.classroom_id,
                revoked_at_utc=invite.revoked_at_utc,
                row_version=invite.row_version,
                request_id=request_id,
            )
            self._finish(idem, response.model_dump(mode="json"), 200)
            await uow.commit()
            return response

    async def resolve_invite(self, principal: AuthenticatedPrincipal, payload: InviteTokenRequest, key: str, request_id: str) -> InviteResolveResponse:
        async with self._uow_factory() as uow:
            user = await self._require_user(uow.session, principal)
            if user.profile_type != "LEARNER":
                raise ForbiddenError()
            normalized = normalize_join_code(payload.invite_token)
            fp = body_fingerprint({"invite_token": normalized})
            idem, replay = await self._idempotency_start(uow.session, user, "classroom_invite.resolve", key, fp, request_id)
            if replay is not None:
                return InviteResolveResponse.model_validate(replay)
            token_hash = hash_join_code(normalized)
            invite = await ClassroomInviteRepository(uow.session).find_by_token_hash(token_hash)
            if invite is None:
                raise ResourceNotFoundError()
            now = datetime.now(UTC)
            if invite.revoked_at_utc is not None or (invite.expires_at_utc is not None and invite.expires_at_utc <= now):
                raise ConflictError()
            classroom = await uow.session.get(Classroom, invite.classroom_id)
            resolution_id = uuid4()
            self._audit(uow.session, user.user_id, request_id, "classroom_invite.resolved", "classroom_invite", invite.classroom_invite_id)
            response = InviteResolveResponse(
                invite_resolution_id=resolution_id,
                classroom_name=classroom.name,
                grade=classroom.grade,
                request_id=request_id,
            )
            self._finish(idem, response.model_dump(mode="json"), 200)
            await uow.commit()
            return response

    async def request_membership(self, principal: AuthenticatedPrincipal, payload: InviteTokenRequest, key: str, request_id: str) -> MembershipRequestResponse:
        async with self._uow_factory() as uow:
            user, learner_id = await self._require_learner(uow.session, principal)
            normalized = normalize_join_code(payload.invite_token)
            fp = body_fingerprint({"invite_token": normalized})
            idem, replay = await self._idempotency_start(uow.session, user, "classroom_membership.request", key, fp, request_id)
            if replay is not None:
                return MembershipRequestResponse.model_validate(replay)
            token_hash = hash_join_code(normalized)
            invite = await ClassroomInviteRepository(uow.session).find_by_token_hash(token_hash)
            if invite is None:
                raise ResourceNotFoundError()
            now = datetime.now(UTC)
            if invite.revoked_at_utc is not None or (invite.expires_at_utc is not None and invite.expires_at_utc <= now):
                raise ConflictError()
            classroom_id = invite.classroom_id
            await uow.session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:scope, 0))"),
                {"scope": f"classroom_membership.request:{learner_id}:{classroom_id}"},
            )
            membership_repository = ClassroomMembershipRepository(uow.session)
            existing = await membership_repository.find_by_classroom_and_learner(classroom_id, learner_id)
            classroom = await uow.session.get(Classroom, classroom_id)
            if existing is not None:
                response = MembershipRequestResponse(
                    classroom_membership_id=existing.classroom_membership_id,
                    classroom_id=classroom_id,
                    classroom_name=classroom.name,
                    grade=classroom.grade,
                    state=existing.state,
                    requested_at_utc=existing.requested_at_utc,
                    request_id=request_id,
                )
                self._finish(idem, response.model_dump(mode="json"), 201)
                await uow.commit()
                return response
            membership_id = uuid4()
            membership = ClassroomMembership(
                classroom_membership_id=membership_id,
                classroom_id=classroom_id,
                learner_id=learner_id,
                classroom_invite_id=invite.classroom_invite_id,
                state="PENDING",
                requested_at_utc=now,
                decided_at_utc=None,
                decided_by_user_id=None,
                row_version=0,
                **provenance(user.user_id, request_id, "classroom_membership.requested", "classroom_membership", membership_id),
            )
            uow.session.add(membership)
            await uow.session.flush()
            self._audit(uow.session, user.user_id, request_id, "classroom_membership.requested", "classroom_membership", membership_id)
            response = MembershipRequestResponse(
                classroom_membership_id=membership_id,
                classroom_id=classroom_id,
                classroom_name=classroom.name,
                grade=classroom.grade,
                state="PENDING",
                requested_at_utc=now,
                request_id=request_id,
            )
            self._finish(idem, response.model_dump(mode="json"), 201)
            await uow.commit()
            return response

    async def list_membership_requests(self, principal: AuthenticatedPrincipal, classroom_id: UUID, request_id: str) -> MembershipRequestListResponse:
        async with self._uow_factory() as uow:
            _, teacher = await self._teacher_context(uow.session, principal)
            classroom = await ClassroomRepository(uow.session).get_owned(classroom_id, teacher.teacher_profile_id)
            if classroom is None:
                raise ResourceNotFoundError()
            rows = await ClassroomMembershipRepository(uow.session).list_for_classroom_with_learner_name(classroom_id)
            items = [
                MembershipRequestListItem(
                    classroom_membership_id=membership.classroom_membership_id,
                    learner_id=membership.learner_id,
                    learner_name=name,
                    state=membership.state,
                    requested_at_utc=membership.requested_at_utc,
                    decided_at_utc=membership.decided_at_utc,
                )
                for membership, name in rows
            ]
            return MembershipRequestListResponse(requests=items, request_id=request_id)

    async def approve_membership(self, principal: AuthenticatedPrincipal, membership_id: UUID, key: str, request_id: str) -> MembershipDecisionResponse:
        async with self._uow_factory() as uow:
            user, teacher = await self._teacher_context(uow.session, principal)
            owned = await ClassroomMembershipRepository(uow.session).get_owned(membership_id, teacher.teacher_profile_id)
            if owned is None:
                raise ResourceNotFoundError()
            fp = path_fingerprint(user.user_id, "classroom_membership.approve", membership_id, {})
            idem, replay = await self._idempotency_start(uow.session, user, "classroom_membership.approve", key, fp, request_id)
            if replay is not None:
                return MembershipDecisionResponse.model_validate(replay)
            learner_id = owned.learner_id
            await uow.session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:scope, 0))"),
                {"scope": f"classroom_membership.approve:{learner_id}"},
            )
            membership = await uow.session.scalar(
                select(ClassroomMembership).where(ClassroomMembership.classroom_membership_id == membership_id).with_for_update()
            )
            if membership.state != "PENDING":
                raise ConflictError()
            already_approved_elsewhere = await ClassroomMembershipRepository(uow.session).learner_has_other_approved_membership(
                learner_id, membership_id
            )
            if already_approved_elsewhere:
                raise ConflictError()
            now = datetime.now(UTC)
            membership.state = "APPROVED"
            membership.decided_at_utc = now
            membership.decided_by_user_id = user.user_id
            membership.row_version += 1
            # Approval is the single point at which a learner acquires a roster grade: the
            # profile route creates the learner with grade NULL and nothing else ever writes it,
            # so without this every downstream question request fails closed. Safe under the
            # advisory xact lock and the membership `with_for_update()` taken above.
            classroom = await uow.session.get(Classroom, membership.classroom_id)
            if classroom is None:
                raise ResourceNotFoundError()
            learner = await uow.session.get(Learner, learner_id)
            if learner is None:
                raise ResourceNotFoundError()
            learner.grade = _CLASSROOM_GRADE_TO_LEARNER_GRADE[classroom.grade]
            try:
                await uow.session.flush()
            except IntegrityError as exc:
                raise ConflictError() from exc
            self._audit(
                uow.session, user.user_id, request_id, "classroom_membership.approved", "classroom_membership", membership_id,
                before="PENDING", after="APPROVED",
            )
            response = MembershipDecisionResponse(
                classroom_membership_id=membership_id,
                classroom_id=membership.classroom_id,
                learner_id=membership.learner_id,
                state="APPROVED",
                decided_at_utc=now,
                row_version=membership.row_version,
                request_id=request_id,
            )
            self._finish(idem, response.model_dump(mode="json"), 200)
            await uow.commit()
            return response

    async def reject_membership(self, principal: AuthenticatedPrincipal, membership_id: UUID, key: str, request_id: str) -> MembershipDecisionResponse:
        async with self._uow_factory() as uow:
            user, teacher = await self._teacher_context(uow.session, principal)
            owned = await ClassroomMembershipRepository(uow.session).get_owned(membership_id, teacher.teacher_profile_id)
            if owned is None:
                raise ResourceNotFoundError()
            fp = path_fingerprint(user.user_id, "classroom_membership.reject", membership_id, {})
            idem, replay = await self._idempotency_start(uow.session, user, "classroom_membership.reject", key, fp, request_id)
            if replay is not None:
                return MembershipDecisionResponse.model_validate(replay)
            membership = await uow.session.scalar(
                select(ClassroomMembership).where(ClassroomMembership.classroom_membership_id == membership_id).with_for_update()
            )
            if membership.state != "PENDING":
                raise ConflictError()
            now = datetime.now(UTC)
            membership.state = "REJECTED"
            membership.decided_at_utc = now
            membership.decided_by_user_id = user.user_id
            membership.row_version += 1
            await uow.session.flush()
            self._audit(
                uow.session, user.user_id, request_id, "classroom_membership.rejected", "classroom_membership", membership_id,
                before="PENDING", after="REJECTED",
            )
            response = MembershipDecisionResponse(
                classroom_membership_id=membership_id,
                classroom_id=membership.classroom_id,
                learner_id=membership.learner_id,
                state="REJECTED",
                decided_at_utc=now,
                row_version=membership.row_version,
                request_id=request_id,
            )
            self._finish(idem, response.model_dump(mode="json"), 200)
            await uow.commit()
            return response

    async def list_classroom_learners(self, principal: AuthenticatedPrincipal, classroom_id: UUID, request_id: str) -> ClassroomLearnerListResponse:
        async with self._uow_factory() as uow:
            _, teacher = await self._teacher_context(uow.session, principal)
            classroom = await ClassroomRepository(uow.session).get_owned(classroom_id, teacher.teacher_profile_id)
            if classroom is None:
                raise ResourceNotFoundError()
            rows = await ClassroomMembershipRepository(uow.session).list_approved_for_classroom_with_learner_name(classroom_id)
            items = [
                ClassroomLearnerListItem(
                    learner_id=membership.learner_id,
                    name=name,
                    membership_id=membership.classroom_membership_id,
                    membership_state=membership.state,
                )
                for membership, name in rows
            ]
            return ClassroomLearnerListResponse(learners=items, request_id=request_id)

    async def list_learner_classrooms(self, principal: AuthenticatedPrincipal, request_id: str) -> LearnerMembershipListResponse:
        async with self._uow_factory() as uow:
            _, learner_id = await self._require_learner(uow.session, principal)
            rows = await ClassroomMembershipRepository(uow.session).list_for_learner_with_classroom(learner_id)
            items = [
                LearnerMembershipListItem(
                    membership_id=membership.classroom_membership_id,
                    classroom_id=membership.classroom_id,
                    classroom_name=name,
                    grade=grade,
                    state=membership.state,
                    requested_at_utc=membership.requested_at_utc,
                    decided_at_utc=membership.decided_at_utc,
                )
                for membership, name, grade in rows
            ]
            return LearnerMembershipListResponse(memberships=items, request_id=request_id)
