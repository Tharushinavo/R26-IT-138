"""Authorized profile and teacher-owned classroom use cases only."""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ClassroomNameMismatchError, ConflictError, ForbiddenError, ResourceNotFoundError
from app.domain.principal import AuthenticatedPrincipal
from app.domain.profile_classroom import ClassroomCreateRequest, ClassroomDeleteRequest, ClassroomDeleteResponse, ClassroomListItem, ClassroomListResponse, ClassroomResponse, LearnerProfileResponse, TeacherProfileResponse
from app.infrastructure.persistence_models import AppUser, AppUserLearnerLink, AuditEvent, Classroom, ClassroomInvite, ClassroomMembership, IdempotencyRecord, Learner, TeacherProfile
from app.infrastructure.repositories import AppUserLearnerLinkRepository, AppUserRepository, ClassroomRepository, IdempotencyRecordRepository, TeacherProfileRepository
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


SCHEMA_REVISION = "20260722_0004"


def fingerprint(body: dict[str, object]) -> str:
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def provenance(user_id: UUID, request_id: str, operation: str, resource_type: str, resource_id: UUID) -> dict[str, object]:
    return {"actor_user_id": user_id, "request_id": request_id, "operation_or_event_type": operation, "reason_code": "AUTHORIZED_PROFILE_CLASSROOM_COMMAND", "resource_type": resource_type, "resource_id": resource_id, "source_class": "REAL", "source_system": "studentapp-api", "environment": "live-endpoint", "schema_revision": SCHEMA_REVISION}


class ProfileClassroomService:
    def __init__(self, uow_factory=SqlAlchemyUnitOfWork) -> None:
        self._uow_factory = uow_factory

    async def _require_user(self, session: AsyncSession, principal: AuthenticatedPrincipal) -> AppUser:
        user = await AppUserRepository(session).find_by_subject(principal.user_id)
        if user is None:
            raise ResourceNotFoundError()
        return user

    async def _provision_user(self, session: AsyncSession, principal: AuthenticatedPrincipal, request_id: str) -> AppUser:
        await session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:scope, 0))"), {"scope": f"account.provision:{principal.user_id}"})
        user = await AppUserRepository(session).find_by_subject(principal.user_id)
        if user is not None:
            return user
        user_id = uuid4()
        user = AppUser(user_id=user_id, supabase_subject=principal.user_id, status="ACTIVE", profile_type=None, **provenance(user_id, request_id, "account.provisioned", "app_user", user_id))
        session.add(user)
        await session.flush()
        return user

    async def _idempotency_start(self, session: AsyncSession, user: AppUser, operation: str, key: str, body: dict[str, object], request_id: str) -> tuple[IdempotencyRecord, dict[str, object] | None]:
        await session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:scope, 0))"), {"scope": f"{user.user_id}:POST:{operation}:{key}"})
        repository = IdempotencyRecordRepository(session)
        existing = await repository.find_scoped(user.user_id, "POST", operation, key)
        request_fingerprint = fingerprint(body)
        if existing is not None:
            if existing.request_fingerprint != request_fingerprint:
                raise ConflictError()
            if existing.processing_status == "succeeded" and existing.canonical_response is not None:
                return existing, existing.canonical_response
            raise ConflictError()
        record_id = uuid4()
        record = IdempotencyRecord(idempotency_record_id=record_id, http_method="POST", operation_identifier=operation, idempotency_key=key, request_fingerprint=request_fingerprint, processing_status="in_progress", canonical_response=None, response_status=None, expires_at_utc=datetime.now(UTC) + timedelta(hours=24), **provenance(user.user_id, request_id, operation, "b_idempotency_record", record_id))
        await repository.add(record)
        return record, None

    @staticmethod
    def _finish(record: IdempotencyRecord, response: dict[str, object]) -> None:
        record.processing_status = "succeeded"
        record.canonical_response = response
        record.response_status = 201

    @staticmethod
    def _audit(session: AsyncSession, user_id: UUID, request_id: str, operation: str, resource_type: str, resource_id: UUID) -> None:
        audit_id = uuid4()
        session.add(AuditEvent(audit_event_id=audit_id, after_reference_or_version=str(resource_id), **provenance(user_id, request_id, operation, resource_type, resource_id)))

    async def create_teacher_profile(self, principal: AuthenticatedPrincipal, name: str, key: str, request_id: str) -> TeacherProfileResponse:
        async with self._uow_factory() as uow:
            user = await self._provision_user(uow.session, principal, request_id)
            idem, replay = await self._idempotency_start(uow.session, user, "teacher.profile.create", key, {"name": name}, request_id)
            if replay is not None:
                return TeacherProfileResponse.model_validate(replay)
            if user.profile_type is not None:
                raise ConflictError()
            profile_id = uuid4()
            profile = TeacherProfile(teacher_profile_id=profile_id, user_id=user.user_id, name=name, **provenance(user.user_id, request_id, "teacher.profile.created", "teacher_profile", profile_id))
            user.profile_type = "TEACHER"
            uow.session.add(profile)
            await uow.session.flush()
            self._audit(uow.session, user.user_id, request_id, "teacher.profile.created", "teacher_profile", profile_id)
            response = TeacherProfileResponse(teacher_profile_id=profile_id, user_id=user.user_id, profile_type="TEACHER", name=profile.name, email=principal.email, created_at_utc=profile.created_at_utc, request_id=request_id)
            self._finish(idem, response.model_dump(mode="json"))
            await uow.commit()
            return response

    async def get_teacher_profile(self, principal: AuthenticatedPrincipal, request_id: str) -> TeacherProfileResponse:
        async with self._uow_factory() as uow:
            user = await self._require_user(uow.session, principal)
            if user.profile_type != "TEACHER":
                raise ForbiddenError()
            profile = await TeacherProfileRepository(uow.session).find_by_user(user.user_id)
            if profile is None:
                raise ResourceNotFoundError()
            return TeacherProfileResponse(teacher_profile_id=profile.teacher_profile_id, user_id=user.user_id, profile_type="TEACHER", name=profile.name, email=principal.email, created_at_utc=profile.created_at_utc, request_id=request_id)

    async def create_learner_profile(self, principal: AuthenticatedPrincipal, name: str, key: str, request_id: str) -> LearnerProfileResponse:
        async with self._uow_factory() as uow:
            user = await self._provision_user(uow.session, principal, request_id)
            idem, replay = await self._idempotency_start(uow.session, user, "learner.profile.create", key, {"name": name}, request_id)
            if replay is not None:
                return LearnerProfileResponse.model_validate(replay)
            if user.profile_type is not None:
                raise ConflictError()
            learner_id, link_id = uuid4(), uuid4()
            learner = Learner(learner_id=learner_id, name=name, grade=None, status="ACTIVE", **provenance(user.user_id, request_id, "learner.profile.created", "b_learner", learner_id))
            link = AppUserLearnerLink(link_id=link_id, user_id=user.user_id, learner_id=learner_id, **provenance(user.user_id, request_id, "learner.owner_link.created", "app_user_learner_link", link_id))
            user.profile_type = "LEARNER"
            uow.session.add(learner)
            await uow.session.flush()
            uow.session.add(link)
            await uow.session.flush()
            self._audit(uow.session, user.user_id, request_id, "learner.profile.created", "b_learner", learner_id)
            response = LearnerProfileResponse(learner_id=learner_id, user_id=user.user_id, profile_type="LEARNER", name=name, email=principal.email, created_at_utc=learner.created_at_utc, request_id=request_id)
            self._finish(idem, response.model_dump(mode="json"))
            await uow.commit()
            return response

    async def get_learner_profile(self, principal: AuthenticatedPrincipal, request_id: str) -> LearnerProfileResponse:
        async with self._uow_factory() as uow:
            user = await self._require_user(uow.session, principal)
            if user.profile_type != "LEARNER":
                raise ForbiddenError()
            link = await AppUserLearnerLinkRepository(uow.session).find_by_user(user.user_id)
            if link is None:
                raise ResourceNotFoundError()
            learner = await uow.session.get(Learner, link.learner_id)
            if learner is None or learner.name is None:
                raise ResourceNotFoundError()
            return LearnerProfileResponse(learner_id=learner.learner_id, user_id=user.user_id, profile_type="LEARNER", name=learner.name, email=principal.email, created_at_utc=learner.created_at_utc, request_id=request_id)

    async def _teacher_context(self, session: AsyncSession, principal: AuthenticatedPrincipal) -> tuple[AppUser, TeacherProfile]:
        user = await self._require_user(session, principal)
        if user.profile_type != "TEACHER":
            raise ForbiddenError()
        profile = await TeacherProfileRepository(session).find_by_user(user.user_id)
        if profile is None:
            raise ResourceNotFoundError()
        return user, profile

    async def create_classroom(self, principal: AuthenticatedPrincipal, payload: ClassroomCreateRequest, key: str, request_id: str) -> ClassroomResponse:
        async with self._uow_factory() as uow:
            user, teacher = await self._teacher_context(uow.session, principal)
            idem, replay = await self._idempotency_start(uow.session, user, "classroom.create", key, payload.model_dump(mode="json"), request_id)
            if replay is not None:
                return ClassroomResponse.model_validate(replay)
            if payload.name is not None:
                duplicate = await uow.session.scalar(select(Classroom.classroom_id).where(Classroom.teacher_profile_id == teacher.teacher_profile_id, Classroom.deleted_at_utc.is_(None), func.lower(func.btrim(Classroom.name)) == payload.name.lower()))
                if duplicate is not None:
                    raise ConflictError()
            classroom_id = uuid4()
            classroom = Classroom(classroom_id=classroom_id, teacher_profile_id=teacher.teacher_profile_id, name=payload.name, grade=payload.grade, row_version=0, **provenance(user.user_id, request_id, "classroom.created", "classroom", classroom_id))
            uow.session.add(classroom)
            await uow.session.flush()
            self._audit(uow.session, user.user_id, request_id, "classroom.created", "classroom", classroom_id)
            response = ClassroomResponse(classroom_id=classroom_id, name=classroom.name, grade=classroom.grade, teacher_profile_id=teacher.teacher_profile_id, created_at_utc=classroom.created_at_utc, row_version=classroom.row_version, request_id=request_id)
            self._finish(idem, response.model_dump(mode="json"))
            await uow.commit()
            return response

    async def list_classrooms(self, principal: AuthenticatedPrincipal, request_id: str) -> ClassroomListResponse:
        async with self._uow_factory() as uow:
            _, teacher = await self._teacher_context(uow.session, principal)
            rows = await ClassroomRepository(uow.session).list_owned(teacher.teacher_profile_id)
            return ClassroomListResponse(classrooms=[ClassroomListItem.model_validate(row, from_attributes=True) for row in rows], request_id=request_id)

    async def get_classroom(self, principal: AuthenticatedPrincipal, classroom_id: UUID, request_id: str) -> ClassroomResponse:
        async with self._uow_factory() as uow:
            _, teacher = await self._teacher_context(uow.session, principal)
            classroom = await ClassroomRepository(uow.session).get_owned(classroom_id, teacher.teacher_profile_id)
            if classroom is None:
                raise ResourceNotFoundError()
            return ClassroomResponse(classroom_id=classroom.classroom_id, name=classroom.name, grade=classroom.grade, teacher_profile_id=teacher.teacher_profile_id, created_at_utc=classroom.created_at_utc, row_version=classroom.row_version, request_id=request_id)

    async def delete_classroom(self, principal: AuthenticatedPrincipal, classroom_id: UUID, payload: ClassroomDeleteRequest, key: str, request_id: str) -> ClassroomDeleteResponse:
        """Soft-delete a classroom the teacher owns (migration 20260914_0009).

        One transaction: the classroom is marked deleted, its join code is revoked so it can
        no longer be redeemed, and every PENDING or APPROVED membership becomes REMOVED --
        which frees each learner to join another classroom with a new code. No learner row,
        session, attempt or Component 3 row is changed or erased.
        """
        async with self._uow_factory() as uow:
            user, teacher = await self._teacher_context(uow.session, principal)
            body = {"classroom_id": str(classroom_id), "confirmation_name": payload.confirmation_name}
            idem, replay = await self._idempotency_start(uow.session, user, "classroom.delete", key, body, request_id)
            if replay is not None:
                return ClassroomDeleteResponse.model_validate(replay)
            owned = await ClassroomRepository(uow.session).get_owned(classroom_id, teacher.teacher_profile_id)
            if owned is None:
                raise ResourceNotFoundError()
            classroom = await uow.session.scalar(select(Classroom).where(Classroom.classroom_id == classroom_id).with_for_update())
            if classroom.deleted_at_utc is not None:
                raise ResourceNotFoundError()
            # Exact match after trimming the ends -- not case-insensitive. The teacher is shown
            # the name and asked to type it; "2a" for "2A" is not that.
            if classroom.name is None or payload.confirmation_name.strip() != classroom.name.strip():
                raise ClassroomNameMismatchError()
            now = datetime.now(UTC)
            classroom.deleted_at_utc = now
            classroom.deleted_by_user_id = user.user_id
            classroom.row_version += 1
            invites = await uow.session.scalars(
                select(ClassroomInvite).where(ClassroomInvite.classroom_id == classroom_id, ClassroomInvite.revoked_at_utc.is_(None)).with_for_update()
            )
            for invite in invites:
                invite.revoked_at_utc = now
                invite.row_version += 1
            memberships = await uow.session.scalars(
                select(ClassroomMembership)
                .where(ClassroomMembership.classroom_id == classroom_id, ClassroomMembership.state.in_(("PENDING", "APPROVED")))
                .with_for_update()
            )
            removed = 0
            for membership in memberships:
                membership.state = "REMOVED"
                membership.decided_at_utc = now
                membership.decided_by_user_id = user.user_id
                membership.row_version += 1
                removed += 1
            await uow.session.flush()
            self._audit(uow.session, user.user_id, request_id, "classroom.deleted", "classroom", classroom_id)
            response = ClassroomDeleteResponse(classroom_id=classroom_id, deleted_at_utc=now, removed_membership_count=removed, row_version=classroom.row_version, request_id=request_id)
            self._finish(idem, response.model_dump(mode="json"))
            idem.response_status = 200
            await uow.commit()
            return response
