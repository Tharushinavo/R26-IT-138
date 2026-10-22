"""Learner-scoped Component B reads that are not about one session. One endpoint today: the
learner's own per-skill BKT state, for the Play prep card (app/domain/b_skill_state.py)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.application.learner_skill_states import LearnerSkillStatesService
from app.domain.b_skill_state import LearnerSkillStatesResponse
from app.domain.principal import AuthenticatedPrincipal
from app.infrastructure.auth import get_authenticated_principal


router = APIRouter(prefix="/api/v1/b/learner", tags=["b-learner"])


def service() -> LearnerSkillStatesService:
    return LearnerSkillStatesService()


@router.get("/skill-states", response_model=LearnerSkillStatesResponse)
async def get_learner_skill_states(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    use_cases: Annotated[LearnerSkillStatesService, Depends(service)],
) -> LearnerSkillStatesResponse:
    return await use_cases.list_for_principal(principal, request.state.request_id)
