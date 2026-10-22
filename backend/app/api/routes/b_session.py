"""Four governance-authorized neutral session-lifecycle endpoints (BE2.3-BE2.4), plus the
BE4b adaptive next-question selection endpoint (BEplan §9 BE4.2), the BE4c attempt-submission
endpoint (BEplan §9 BE4.3 + BE4.4), the BE4d governed-hint endpoint (BEplan §9 BE4.5), and the
BE4e next-or-complete + SAFE standing endpoints (BEplan §9 BE4.6)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, status

from app.application.attempt_submission import AttemptSubmissionService
from app.application.b_session_lifecycle import BSessionLifecycleService
from app.application.hint_request import HintRequestService
from app.application.opportunity_selection import OpportunitySelectionService
from app.application.presentation_ack import PresentationAckService
from app.application.session_completion import SessionCompletionService
from app.domain.b_attempt import AttemptResponse, SubmitResponseRequest
from app.domain.b_completion import OpportunityAdvanceResponse, SessionStandingResponse
from app.domain.b_hint import HintRequestResponse
from app.domain.b_opportunity import OpportunityPresentationResponse
from app.domain.b_presentation_ack import PresentationAckResponse
from app.domain.live_engine.locales import resolve_locale
from app.domain.b_session import ActiveSessionResponse, SessionCommandResponse
from app.domain.principal import AuthenticatedPrincipal
from app.infrastructure.auth import get_authenticated_principal


router = APIRouter(prefix="/api/v1/b/sessions", tags=["b-session-lifecycle"])


def service() -> BSessionLifecycleService:
    return BSessionLifecycleService()


def opportunity_selection_service() -> OpportunitySelectionService:
    return OpportunitySelectionService()


def attempt_submission_service() -> AttemptSubmissionService:
    return AttemptSubmissionService()


def hint_request_service() -> HintRequestService:
    return HintRequestService()


def session_completion_service() -> SessionCompletionService:
    return SessionCompletionService()


def presentation_ack_service() -> PresentationAckService:
    return PresentationAckService()


@router.post("", response_model=SessionCommandResponse, status_code=status.HTTP_201_CREATED)
async def start_session(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)],
    use_cases: Annotated[BSessionLifecycleService, Depends(service)],
) -> SessionCommandResponse:
    return await use_cases.start_session(principal, idempotency_key, request.state.request_id)


@router.get("/active", response_model=ActiveSessionResponse)
async def get_active_session(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    use_cases: Annotated[BSessionLifecycleService, Depends(service)],
) -> ActiveSessionResponse:
    return await use_cases.get_active_session(principal, request.state.request_id)


@router.post("/{session_id}/complete", response_model=SessionCommandResponse)
async def complete_session(
    session_id: UUID,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)],
    use_cases: Annotated[BSessionLifecycleService, Depends(service)],
) -> SessionCommandResponse:
    return await use_cases.complete_session(principal, session_id, idempotency_key, request.state.request_id)


@router.post("/{session_id}/abandon", response_model=SessionCommandResponse)
async def abandon_session(
    session_id: UUID,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)],
    use_cases: Annotated[BSessionLifecycleService, Depends(service)],
) -> SessionCommandResponse:
    return await use_cases.abandon_session(principal, session_id, idempotency_key, request.state.request_id)


@router.post(
    "/{session_id}/opportunities",
    response_model=OpportunityPresentationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def select_opportunity(
    session_id: UUID,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    use_cases: Annotated[OpportunitySelectionService, Depends(opportunity_selection_service)],
    accept_language: Annotated[str | None, Header(alias="Accept-Language")] = None,
) -> OpportunityPresentationResponse:
    """The question the child answers next, in the language they read.

    ``Accept-Language`` rather than a new field or a stored profile column: it is the standard way
    to say this, it is a CORS-safelisted request header so the browser sends it without a preflight
    change, and it needs no migration. An absent or unrecognised value resolves to English
    (``locales.DEFAULT_LOCALE``), so this is additive -- an older client that sends nothing keeps
    exactly the behaviour it has now.
    """
    return await use_cases.select_next_opportunity(
        principal, session_id, request.state.request_id, resolve_locale(accept_language)
    )


@router.post(
    "/{session_id}/opportunities/{item_opportunity_id}/presented",
    response_model=PresentationAckResponse,
)
async def acknowledge_presentation(
    session_id: UUID,
    item_opportunity_id: UUID,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    use_cases: Annotated[PresentationAckService, Depends(presentation_ack_service)],
) -> PresentationAckResponse:
    """The learner is now looking at this question -- start its answering clock here.

    No idempotency key and no body, for the same reason `select_opportunity` has neither: the
    operation is intrinsically once-only (the first acknowledgement anchors, every later one is a
    no-op returning the same deadline), so a key would add a token to manage without adding a
    guarantee. 200 rather than 201: nothing is created, an existing row is anchored.
    """
    return await use_cases.acknowledge_presentation(
        principal, session_id, item_opportunity_id, request.state.request_id
    )


@router.post(
    "/{session_id}/opportunities/{item_opportunity_id}/responses",
    response_model=AttemptResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_response(
    session_id: UUID,
    item_opportunity_id: UUID,
    body: SubmitResponseRequest,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)],
    use_cases: Annotated[AttemptSubmissionService, Depends(attempt_submission_service)],
) -> AttemptResponse:
    return await use_cases.submit_response(
        principal, session_id, item_opportunity_id, idempotency_key, request.state.request_id, body
    )


@router.post(
    "/{session_id}/opportunities/{item_opportunity_id}/assists",
    response_model=HintRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def request_assist(
    session_id: UUID,
    item_opportunity_id: UUID,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)],
    use_cases: Annotated[HintRequestService, Depends(hint_request_service)],
) -> HintRequestResponse:
    return await use_cases.request_hint(
        principal, session_id, item_opportunity_id, idempotency_key, request.state.request_id
    )


@router.post(
    "/{session_id}/opportunities/{item_opportunity_id}/complete",
    response_model=OpportunityAdvanceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def complete_opportunity(
    session_id: UUID,
    item_opportunity_id: UUID,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)],
    use_cases: Annotated[SessionCompletionService, Depends(session_completion_service)],
) -> OpportunityAdvanceResponse:
    return await use_cases.complete_and_advance(
        principal, session_id, item_opportunity_id, idempotency_key, request.state.request_id
    )


@router.get("/{session_id}/summary", response_model=SessionStandingResponse)
async def get_session_summary(
    session_id: UUID,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    use_cases: Annotated[SessionCompletionService, Depends(session_completion_service)],
) -> SessionStandingResponse:
    return await use_cases.get_session_standing(principal, session_id, request.state.request_id)
