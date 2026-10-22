"""Read-only learner view of Component B's per-skill BKT state. See app/domain/b_skill_state.py
for the ruling that admits this read and what it deliberately is not."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ForbiddenError, ResourceNotFoundError
from app.domain.b_skill_state import LearnerSkillStateItem, LearnerSkillStatesResponse
from app.domain.principal import AuthenticatedPrincipal
from app.infrastructure.persistence_models import AppUser
from app.infrastructure.repositories import (
    AppUserRepository,
    LearnerSkillStateRepository,
)
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


class LearnerSkillStatesService:
    def __init__(self, uow_factory=SqlAlchemyUnitOfWork) -> None:
        self._uow_factory = uow_factory

    # Same learner resolution as every other learner-facing B use case (b_session_lifecycle,
    # classroom_membership): a teacher is 403, an unlinked or unknown user is 404.
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

    async def list_for_principal(self, principal: AuthenticatedPrincipal, request_id: str) -> LearnerSkillStatesResponse:
        async with self._uow_factory() as uow:
            _, learner_id = await self._require_learner(uow.session, principal)
            rows = await LearnerSkillStateRepository(uow.session).list_for_learner(learner_id)
            # Sorted by skill_id so the response is stable across calls; the client keeps its own
            # display order (the seven fixed rows) and looks these up by id.
            items = [
                LearnerSkillStateItem(skill_id=row.skill_id, p_l=row.p_l, observation_count=row.observation_count)
                for row in sorted(rows, key=lambda row: row.skill_id)
            ]
            return LearnerSkillStatesResponse(skill_states=items, request_id=request_id)
