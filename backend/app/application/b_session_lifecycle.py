"""Authorized neutral session-lifecycle use cases only (BE2.3-BE2.4).

Per the engineering-continuation authorization for this batch:
- Start resolves the currently approved+published runtime bundle, pins its
  identifier, and creates the session directly as ``active``. No approved+published
  bundle -> fail closed with CONFLICT; a bundle-less session is never created.
- A safe replay or a concurrent duplicate start for the same learner returns the
  existing active session rather than creating a second one.
- ``expires_at_utc`` is always left ``NULL``; numeric expiry/timeout policy is a
  governance-unresolved gate out of scope for this batch.
- Complete/abandon are neutral, explicit client commands (active -> completed /
  active -> abandoned) with no scientific or pedagogical completion criteria.

Excluded from this module and its callers: question selection, answer submission,
attempts, hints, BKT, mastery, certification, sequencing, and Component B live-engine
behavior.
"""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, ForbiddenError, ResourceNotFoundError
from app.domain.b_session import ActiveSessionResponse, SessionCommandResponse, SessionFields
from app.domain.principal import AuthenticatedPrincipal
from app.infrastructure.persistence_models import AppUser, AuditEvent, IdempotencyRecord, RuntimeBundleRecord, SessionRecord
from app.infrastructure.repositories import (
    AppUserRepository,
    IdempotencyRecordRepository,
    RuntimeBundleRecordRepository,
    SessionRecordRepository,
)
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


SCHEMA_REVISION = "20260723_0001"


def body_fingerprint(body: dict[str, object]) -> str:
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def path_fingerprint(actor_user_id: UUID, operation: str, path_parameter: object, body: dict[str, object]) -> str:
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
        "reason_code": "AUTHORIZED_B_SESSION_LIFECYCLE_COMMAND",
        "resource_type": resource_type,
        "resource_id": resource_id,
        "source_class": "REAL",
        "source_system": "studentapp-api",
        "environment": "live-endpoint",
        "schema_revision": SCHEMA_REVISION,
    }


def _session_fields(record: SessionRecord, bundle_version: str) -> SessionFields:
    return SessionFields(
        session_id=record.session_id,
        state=record.state,
        runtime_bundle_version=bundle_version,
        created_at_utc=record.created_at_utc,
        row_version=record.row_version,
    )


class BSessionLifecycleService:
    def __init__(self, uow_factory=SqlAlchemyUnitOfWork) -> None:
        self._uow_factory = uow_factory

    async def _require_user(self, session: AsyncSession, principal: AuthenticatedPrincipal) -> AppUser:
        user = await AppUserRepository(session).find_by_subject(principal.user_id)
        if user is None:
            raise ResourceNotFoundError()
        return user

    async def _require_learner(self, session: AsyncSession, principal: AuthenticatedPrincipal) -> tuple[AppUser, UUID]:
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
        self, session: AsyncSession, user: AppUser, operation: str, key: str, fingerprint_value: str, request_id: str
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
        session: AsyncSession,
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

    async def _resolve_pinnable_bundle(self, session: AsyncSession) -> RuntimeBundleRecord | None:
        return await RuntimeBundleRecordRepository(session).find_current_approved_published()

    async def start_session(self, principal: AuthenticatedPrincipal, key: str, request_id: str) -> SessionCommandResponse:
        async with self._uow_factory() as uow:
            user, learner_id = await self._require_learner(uow.session, principal)
            fp = body_fingerprint({})
            idem, replay = await self._idempotency_start(uow.session, user, "b_session.start", key, fp, request_id)
            if replay is not None:
                return SessionCommandResponse.model_validate(replay)

            await uow.session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:scope, 0))"),
                {"scope": f"b_session.start:{learner_id}"},
            )
            session_repository = SessionRecordRepository(uow.session)
            existing = await session_repository.find_starting_or_active_for_learner(learner_id)
            if existing is not None:
                bundle = await RuntimeBundleRecordRepository(uow.session).get_by_id(existing.runtime_bundle_record_id)
                response = SessionCommandResponse(
                    **_session_fields(existing, bundle.bundle_version).model_dump(),
                    request_id=request_id,
                )
                self._finish(idem, response.model_dump(mode="json"), 201)
                await uow.commit()
                return response

            bundle = await self._resolve_pinnable_bundle(uow.session)
            if bundle is None:
                raise ConflictError()

            session_id = uuid4()
            record = SessionRecord(
                session_id=session_id,
                learner_id=learner_id,
                runtime_bundle_record_id=bundle.runtime_bundle_record_id,
                state="active",
                expires_at_utc=None,
                row_version=0,
                **provenance(user.user_id, request_id, "b_session.started", "b_session", session_id),
            )
            uow.session.add(record)
            try:
                await uow.session.flush()
            except IntegrityError as exc:
                raise ConflictError() from exc
            self._audit(uow.session, user.user_id, request_id, "b_session.started", "b_session", session_id, after="active")
            response = SessionCommandResponse(
                **_session_fields(record, bundle.bundle_version).model_dump(),
                request_id=request_id,
            )
            self._finish(idem, response.model_dump(mode="json"), 201)
            await uow.commit()
            return response

    async def get_active_session(self, principal: AuthenticatedPrincipal, request_id: str) -> ActiveSessionResponse:
        async with self._uow_factory() as uow:
            _, learner_id = await self._require_learner(uow.session, principal)
            record = await SessionRecordRepository(uow.session).find_active_for_learner(learner_id)
            if record is None:
                return ActiveSessionResponse(session=None, request_id=request_id)
            bundle = await RuntimeBundleRecordRepository(uow.session).get_by_id(record.runtime_bundle_record_id)
            return ActiveSessionResponse(session=_session_fields(record, bundle.bundle_version), request_id=request_id)

    async def _transition(
        self,
        principal: AuthenticatedPrincipal,
        session_id: UUID,
        key: str,
        request_id: str,
        *,
        target_state: str,
        operation: str,
    ) -> SessionCommandResponse:
        async with self._uow_factory() as uow:
            user, learner_id = await self._require_learner(uow.session, principal)
            owned = await SessionRecordRepository(uow.session).get_owned(session_id, learner_id)
            if owned is None:
                raise ResourceNotFoundError()
            fp = path_fingerprint(user.user_id, operation, session_id, {})
            idem, replay = await self._idempotency_start(uow.session, user, operation, key, fp, request_id)
            if replay is not None:
                return SessionCommandResponse.model_validate(replay)

            await uow.session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:scope, 0))"),
                {"scope": f"{operation}:{learner_id}"},
            )
            # populate_existing is required here: `owned` above already loaded this row
            # into the session identity map, so without it SQLAlchemy would keep the
            # stale pre-lock attributes instead of refreshing them from this FOR UPDATE
            # read, letting two concurrent transitions on the same row both see
            # state="active".
            session_row = await uow.session.scalar(
                select(SessionRecord)
                .where(SessionRecord.session_id == session_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if session_row.state != "active":
                raise ConflictError()
            before_state = session_row.state
            session_row.state = target_state
            session_row.row_version += 1
            await uow.session.flush()
            bundle = await RuntimeBundleRecordRepository(uow.session).get_by_id(session_row.runtime_bundle_record_id)
            self._audit(
                uow.session, user.user_id, request_id, operation, "b_session", session_id,
                before=before_state, after=target_state,
            )
            response = SessionCommandResponse(
                **_session_fields(session_row, bundle.bundle_version).model_dump(),
                request_id=request_id,
            )
            self._finish(idem, response.model_dump(mode="json"), 200)
            await uow.commit()
            return response

    async def complete_session(self, principal: AuthenticatedPrincipal, session_id: UUID, key: str, request_id: str) -> SessionCommandResponse:
        return await self._transition(principal, session_id, key, request_id, target_state="completed", operation="b_session.complete")

    async def abandon_session(self, principal: AuthenticatedPrincipal, session_id: UUID, key: str, request_id: str) -> SessionCommandResponse:
        return await self._transition(principal, session_id, key, request_id, target_state="abandoned", operation="b_session.abandon")
