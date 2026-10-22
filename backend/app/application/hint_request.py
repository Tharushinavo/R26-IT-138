"""BE4d: governed hints (BEplan §9 BE4.5).

Every scientific step goes through ``app.infrastructure.live_engine.adapter.LiveEngineAdapter``
(imported lazily, function scope — mirrors ``AttemptSubmissionService``/
``OpportunitySelectionService``): ``get_hint`` is the ONLY source of hint content. No LLM, no
paraphrase, no generic fallback — a missing/blank hint or a catalogue/bundle checksum mismatch
raises (``HintUnavailableError`` / ``RuntimeBundleError`` / ``LiveEngineError``), which this
service maps to a neutral ``ConflictError``: fail closed, never synthesize or approximate, never
reveal the correct answer through the error path.

GOVERNED SEQUENCE: exactly L1 -> L2 -> L3, single-step escalation, derived server-side from
``HintEventRepository.count_for_opportunity`` under the SAME opportunity row lock
(``ItemOpportunityRepository.get_for_update``) BE4c's attempt path uses — so a concurrent
hint request for the same opportunity serializes rather than racing past L3. A request once
three hint events already exist is refused (``ConflictError``), never a fourth level.

A hint request is NEVER a mastery/BKT observation: this module never imports
``LearnerSkillStateRepository``, ``AttemptRepository``, or ``SkillStateTransitionRepository``,
and ``HintEventRecord`` (BE4d, ``b_hint_events``) is a table fully separate from
``b_attempts``/``b_skill_state_transitions`` (BE4c). Only the catalogue reconstruction key
(``content_id`` + ``catalogue_version`` + ``catalogue_checksum``) is persisted — the hint text
itself is returned to the caller but not stored, so there is no second, potentially-stale copy
of governed catalogue content living in this table.

REPLAY: reuses the same ``b_idempotency_records`` mechanism as BE4c's attempt path — a duplicate
``Idempotency-Key`` returns the original canonical response (same level, same content) and
performs no second write, no re-escalation.

Engineering bundle bridge: reuses ``opportunity_selection._ENGINEERING_TEST_BUNDLES`` (the same
TEST-provenance DRAFT fixture bridge BE4b established) rather than duplicating a second bundle
resolution mechanism.

GATE-B NOTE: the numeric bound enforced here is the governed L1-L3 hint-escalation ceiling only
(BEplan §9 BE4.5 step 1: "Allow only the governed hint sequence L1, L2, and L3"). A combined
attempt+hint numeric limit beyond that is a GATE-B item (UNRESOLVED, per the BE4 engineering-
continuation instruction) and is deliberately NOT enforced here; no fixture bound is promoted to
"approved" by this module.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.opportunity_selection import _ENGINEERING_TEST_BUNDLES, RUNTIME_BUNDLE_SCHEMA_PATH
from app.core.errors import ConflictError, ForbiddenError, ResourceNotFoundError, TechnicalFailureError
from app.domain.b_hint import HintRequestResponse
from app.domain.live_engine.errors import LiveEngineError
from app.domain.principal import AuthenticatedPrincipal
from app.domain.runtime_bundle.errors import RuntimeBundleError
from app.domain.runtime_bundle.readiness import assert_catalogue_matches_bundle
from app.infrastructure.persistence_models import AppUser, HintEventRecord, IdempotencyRecord
from app.infrastructure.repositories import (
    AppUserRepository,
    HintEventRepository,
    IdempotencyRecordRepository,
    ItemOpportunityRepository,
    RuntimeBundleRecordRepository,
    SessionRecordRepository,
)
from app.infrastructure.runtime_bundle.loader import RuntimeBundleLoader
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


if TYPE_CHECKING:
    # Deferred for the same reason as OpportunitySelectionService/AttemptSubmissionService: only
    # actually resolving a hint requires the vendored component_b_generator wheel.
    from app.infrastructure.live_engine.adapter import LiveEngineAdapter


SCHEMA_REVISION = "20260728_0002"
IDEMPOTENCY_OPERATION = "b_opportunity.hint_request"
MAX_ASSIST_LEVEL = 3


def body_fingerprint(body: dict[str, object]) -> str:
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def provenance(user_id: UUID, request_id: str, operation: str, resource_type: str, resource_id: UUID) -> dict[str, object]:
    return {
        "actor_user_id": user_id,
        "request_id": request_id,
        "operation_or_event_type": operation,
        "reason_code": "AUTHORIZED_B_HINT_REQUEST_COMMAND",
        "resource_type": resource_type,
        "resource_id": resource_id,
        "source_class": "TEST",
        "source_system": "studentapp-api",
        "environment": "live-endpoint",
        "schema_revision": SCHEMA_REVISION,
    }


class HintRequestService:
    """BE4d application service: the ``POST /api/v1/b/sessions/{session_id}/opportunities/
    {item_opportunity_id}/assists`` use case."""

    def __init__(self, uow_factory=SqlAlchemyUnitOfWork) -> None:
        self._uow_factory = uow_factory

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

    async def _reserve_idempotency(
        self, session: AsyncSession, user: AppUser, key: str, fingerprint_value: str, request_id: str
    ) -> tuple[IdempotencyRecord, dict[str, object] | None]:
        await session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:scope, 0))"),
            {"scope": f"{user.user_id}:POST:{IDEMPOTENCY_OPERATION}:{key}"},
        )
        repository = IdempotencyRecordRepository(session)
        existing = await repository.find_scoped(user.user_id, "POST", IDEMPOTENCY_OPERATION, key)
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
            operation_identifier=IDEMPOTENCY_OPERATION,
            idempotency_key=key,
            request_fingerprint=fingerprint_value,
            processing_status="in_progress",
            canonical_response=None,
            response_status=None,
            expires_at_utc=datetime.now(UTC) + timedelta(hours=24),
            **provenance(user.user_id, request_id, IDEMPOTENCY_OPERATION, "b_idempotency_record", record_id),
        )
        await repository.add(record)
        return record, None

    @staticmethod
    def _finish(record: IdempotencyRecord, response: dict[str, object], status_code: int) -> None:
        record.processing_status = "succeeded"
        record.canonical_response = response
        record.response_status = status_code

    async def request_hint(
        self,
        principal: AuthenticatedPrincipal,
        session_id: UUID,
        item_opportunity_id: UUID,
        idempotency_key: str,
        request_id: str,
    ) -> HintRequestResponse:
        async with self._uow_factory() as uow:
            try:
                response = await self._request_hint_unguarded(
                    uow.session, principal, session_id, item_opportunity_id, idempotency_key, request_id
                )
                await uow.commit()
            except IntegrityError as exc:
                raise ConflictError() from exc
            except (LiveEngineError, RuntimeBundleError) as exc:
                # Fail closed, neutral: never surfaces catalogue/bundle detail or hint content.
                raise ConflictError() from exc
            except SQLAlchemyError as exc:
                raise TechnicalFailureError() from exc
            return response

    async def _request_hint_unguarded(
        self,
        session: AsyncSession,
        principal: AuthenticatedPrincipal,
        session_id: UUID,
        item_opportunity_id: UUID,
        idempotency_key: str,
        request_id: str,
    ) -> HintRequestResponse:
        user, learner_id = await self._require_learner(session, principal)

        session_row = await SessionRecordRepository(session).get_owned(session_id, learner_id)
        if session_row is None or session_row.state != "active":
            raise ResourceNotFoundError()

        fingerprint_value = body_fingerprint(
            {"session_id": str(session_id), "item_opportunity_id": str(item_opportunity_id)}
        )
        idem, replay = await self._reserve_idempotency(session, user, idempotency_key, fingerprint_value, request_id)
        if replay is not None:
            return HintRequestResponse.model_validate(replay)

        # Same row lock BE4c's attempt path takes: serializes concurrent hint requests for this
        # opportunity so escalation-level derivation below is race-free.
        opportunity = await ItemOpportunityRepository(session).get_for_update(item_opportunity_id)
        if opportunity is None or opportunity.session_id != session_id or opportunity.learner_id != learner_id:
            raise ResourceNotFoundError()
        if opportunity.state != "OPEN":
            raise ConflictError()

        existing_count = await HintEventRepository(session).count_for_opportunity(item_opportunity_id)
        if existing_count >= MAX_ASSIST_LEVEL:
            # Beyond L3 — refuse, never a fourth level. Fail closed with no hint/answer content.
            raise ConflictError()
        next_level = existing_count + 1

        bundle_record = await RuntimeBundleRecordRepository(session).get_by_id(session_row.runtime_bundle_record_id)
        if bundle_record is None:
            raise ConflictError()
        fixture = _ENGINEERING_TEST_BUNDLES.get(bundle_record.bundle_version)
        if fixture is None:
            raise ConflictError()
        manifest_path, catalogue_path = fixture

        from app.infrastructure.live_engine.adapter import LiveEngineAdapter  # see TYPE_CHECKING note above

        adapter: "LiveEngineAdapter" = LiveEngineAdapter()
        bundle = RuntimeBundleLoader().load_and_validate(
            manifest_path,
            RUNTIME_BUNDLE_SCHEMA_PATH,
            artifact_paths={"catalogue": catalogue_path},
            require_approved=False,
        )
        catalogue = adapter.load(catalogue_path)
        catalogue_checksum = adapter.checksum(catalogue_path)
        assert_catalogue_matches_bundle(bundle, catalogue, catalogue_checksum)

        # Fail-closed by construction: adapter.get_hint raises HintUnavailableError (a
        # LiveEngineError) on missing/blank catalogue content or an out-of-range level, caught by
        # the outer guard above and mapped to a neutral ConflictError — never synthesized here.
        hint = adapter.get_hint(catalogue, catalogue_checksum, opportunity.item_template_id, next_level)

        now = datetime.now(UTC)
        event_id = uuid4()
        event_record = HintEventRecord(
            assist_event_id=event_id,
            item_opportunity_id=item_opportunity_id,
            learner_id=learner_id,
            assist_level=next_level,
            content_id=hint.content_id,
            catalogue_version=hint.catalogue_version,
            catalogue_checksum=hint.catalogue_checksum,
            requested_at_utc=now,
            **provenance(user.user_id, request_id, "b_hint_event.recorded", "b_hint_event", event_id),
        )
        session.add(event_record)
        try:
            await session.flush()
        except IntegrityError as exc:
            raise ConflictError() from exc

        response = HintRequestResponse(
            item_opportunity_id=item_opportunity_id,
            hint_level=next_level,
            content=hint.content,
            content_id=hint.content_id,
            catalogue_version=hint.catalogue_version,
            catalogue_checksum=hint.catalogue_checksum,
            request_id=request_id,
        )
        self._finish(idem, response.model_dump(mode="json"), 201)
        return response
