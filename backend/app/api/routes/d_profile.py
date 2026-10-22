"""Component D's six student-side routes (Component D authorization, owner decision D-011 A2/A3;
API contract v4, all six rows).

Mirrors ``app.api.routes.c_session`` and ``b_learner``: the same ``get_authenticated_principal``
dependency, the same ``service()`` provider, the same thin-route shape where the handler does
nothing but hand the request to a use case. No business logic lives in this file.

ONE ROUTER, TWO PREFIX FAMILIES. ``/api/v1/d`` is the router prefix and the two families spell
themselves out below (``/learner/...`` and ``/sessions/{session_id}/...``), because splitting them
into two routers would put Component D's route list in two files and the guard asserts on the set
as a whole.

THE ``session`` IN TWO OF THESE PATHS IS CARVED OUT, NOT OVERLOOKED. ``session`` is a prohibited
path term (``PROHIBITED_SCIENTIFIC_PATH_TERMS``). D-011 A3 grants the carve-out for these two
profile routes ONLY, on exactly the pattern B's and C's lifecycle routes already use, and the
carve-out is registered as ``AUTHORIZED_D_PROFILING_OPERATIONS`` in the guard. Every OTHER
prohibited term still applies to these paths unconditionally -- there is no "attempt", "hint",
"progress", "bkt", "mastery", "sequenc", "certif" or "guess" anywhere in them.

``?language`` IS VALIDATED, NOT COERCED. It is typed ``Language``, so an unrecognised value is a
422 naming the parameter rather than a silent fallback to English (contract v4). A child whose
client sends a language the server does not have should see a failure someone can fix, not Sinhala
copy silently replaced with English.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.application.d_cognitive_profiling import DCognitiveProfilingService
from app.application.d_learner_state import DLearnerStateService
from app.domain.d_profile import (
    DCognitiveProfileResponse,
    DLatestProfileResponse,
    DLearnerStateResponse,
    DLearnerStateUpdateRequest,
    DProfileCreateRequest,
    DProfileListResponse,
    DEFAULT_HISTORY_LIMIT,
    Language,
    MAX_HISTORY_LIMIT,
    MIN_HISTORY_LIMIT,
)
from app.domain.principal import AuthenticatedPrincipal
from app.infrastructure.auth import get_authenticated_principal


router = APIRouter(prefix="/api/v1/d", tags=["d-cognitive-profiling"])


def learner_state_service() -> DLearnerStateService:
    return DLearnerStateService()


def profiling_service() -> DCognitiveProfilingService:
    return DCognitiveProfilingService()


@router.get("/learner/state", response_model=DLearnerStateResponse)
async def get_learner_state(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    use_cases: Annotated[DLearnerStateService, Depends(learner_state_service)],
) -> DLearnerStateResponse:
    return await use_cases.get_for_principal(principal, request.state.request_id)


@router.post("/learner/state", response_model=DLearnerStateResponse)
async def update_learner_state(
    body: DLearnerStateUpdateRequest,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    use_cases: Annotated[DLearnerStateService, Depends(learner_state_service)],
) -> DLearnerStateResponse:
    return await use_cases.update_for_principal(
        principal,
        request.state.request_id,
        intro_completed=body.intro_completed,
        language=body.language,
    )


@router.get("/learner/profiles/latest", response_model=DLatestProfileResponse)
async def get_latest_profile(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    use_cases: Annotated[DCognitiveProfilingService, Depends(profiling_service)],
    language: Annotated[Language, Query()] = "en",
) -> DLatestProfileResponse:
    return await use_cases.get_latest(principal, request.state.request_id, language=language)


@router.get("/learner/profiles", response_model=DProfileListResponse)
async def list_profiles(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    use_cases: Annotated[DCognitiveProfilingService, Depends(profiling_service)],
    limit: Annotated[int, Query(ge=MIN_HISTORY_LIMIT, le=MAX_HISTORY_LIMIT)] = DEFAULT_HISTORY_LIMIT,
    language: Annotated[Language, Query()] = "en",
) -> DProfileListResponse:
    return await use_cases.list_history(
        principal, request.state.request_id, limit=limit, language=language
    )


@router.post("/sessions/{session_id}/profile", response_model=DCognitiveProfileResponse)
async def create_profile(
    session_id: UUID,
    body: DProfileCreateRequest,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    use_cases: Annotated[DCognitiveProfilingService, Depends(profiling_service)],
) -> DCognitiveProfileResponse:
    """200, not 201, for both a new profile and a repeat.

    The contract fixes this: a client that retries cannot tell whether its first attempt landed,
    and a 201-then-200 pair would tell it -- which is exactly the information an idempotent
    endpoint is supposed to make irrelevant.
    """
    return await use_cases.create_for_session(
        principal,
        request.state.request_id,
        session_id=session_id,
        language=body.language,
        events=body.events,
    )


@router.get("/sessions/{session_id}/profile", response_model=DCognitiveProfileResponse)
async def get_profile(
    session_id: UUID,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    use_cases: Annotated[DCognitiveProfilingService, Depends(profiling_service)],
    language: Annotated[Language, Query()] = "en",
) -> DCognitiveProfileResponse:
    return await use_cases.get_for_session(
        principal, request.state.request_id, session_id=session_id, language=language
    )
