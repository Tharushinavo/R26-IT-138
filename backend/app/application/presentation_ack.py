"""Records that a question reached the learner's screen, anchoring its answering clock there.

See app/domain/b_presentation_ack.py for the ruling this implements and why a client-supplied
start is safe when it can only ever be recorded once.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.opportunity_persistence import OpportunityPersistenceService
from app.core.errors import ForbiddenError, ResourceNotFoundError
from app.domain.b_presentation_ack import PresentationAckResponse
from app.domain.principal import AuthenticatedPrincipal
from app.infrastructure.persistence_models import AppUser
from app.infrastructure.repositories import (
    AppUserRepository,
    SessionRecordRepository,
)
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


class PresentationAckService:
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

    async def acknowledge_presentation(
        self,
        principal: AuthenticatedPrincipal,
        session_id: UUID,
        item_opportunity_id: UUID,
        request_id: str,
    ) -> PresentationAckResponse:
        from app.application.opportunity_selection import DEFAULT_TIMEOUT

        async with self._uow_factory() as uow:
            _, learner_id = await self._require_learner(uow.session, principal)

            # Same lock scope the selection path uses, so an acknowledgement can never interleave
            # with the re-issue of the very opportunity it is anchoring.
            await uow.session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:scope, 0))"),
                {"scope": f"b_opportunity.select:{learner_id}"},
            )

            # The session must be the learner's own and still active; otherwise this is a 404 for
            # a session that is not theirs, exactly as the selection path treats it.
            session_row = await SessionRecordRepository(uow.session).get_owned(session_id, learner_id)
            if session_row is None:
                raise ResourceNotFoundError()

            service = OpportunityPersistenceService(uow.session)
            record, anchored = await service.anchor_presentation(
                item_opportunity_id=item_opportunity_id,
                learner_id=learner_id,
                timeout=DEFAULT_TIMEOUT,
            )
            # An opportunity belonging to a DIFFERENT session of the same learner is not this
            # session's to anchor; the path parameters must agree.
            if record.session_id != session_id:
                raise ResourceNotFoundError()

            response = PresentationAckResponse(
                item_opportunity_id=str(record.item_opportunity_id),
                server_timeout_deadline_utc=record.timeout_deadline_utc,
                anchored=anchored,
                request_id=request_id,
            )
            await uow.commit()
            return response
