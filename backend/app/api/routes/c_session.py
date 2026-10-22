"""Component C's four session-lifecycle endpoints (Phase 4b: create/start, resume, abandon,
complete). Mirrors ``app.api.routes.b_session`` exactly: same auth dependency
(``get_authenticated_principal``), same router-registration pattern, no idempotency-key header
(Phase 4a/4b ruling: v3.0 says only "idempotent by learner state", which
``find_starting_or_active_for_learner`` already satisfies -- B's fuller idempotency-key/audit-
event machinery is a scope expansion beyond that text, not built here)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.application.live_engine_c.c_session_service import CSessionService
from app.domain.c_session import CActiveSessionResponse, CSessionCommandResponse, StrictModel
from app.domain.live_engine_c.types import AttendanceStatus, Grade, SessionMode
from app.domain.principal import AuthenticatedPrincipal
from app.infrastructure.auth import get_authenticated_principal
from app.infrastructure.database import session_factory


router = APIRouter(prefix="/api/v1/c/sessions", tags=["c-session-lifecycle"])


def service() -> CSessionService:
    return CSessionService()


class CreateCSessionRequest(StrictModel):
    """R-5 (Phase 4b continuation, supervisor ruling): carries grade and session_mode ONLY. B's
    identity fields (mastery_source_student_id etc.) were removed from here -- accepting them from
    an HTTP client let an untrusted caller assert B provenance it never produced (strictly worse
    than the C-manufactures-its-own-provenance failure R1 was written to prevent). See
    app/application/live_engine_c/mastery_fixture.py's module docstring for the fixture that now
    supplies all of it, for every combined-mode session, server-side only."""

    grade: Grade
    session_mode: SessionMode


class CompleteCSessionRequest(StrictModel):
    attendance_status: AttendanceStatus
    technical_blocked_bootstrap: bool = False


@router.post("", response_model=CSessionCommandResponse, status_code=201)
async def create_session(
    body: CreateCSessionRequest,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    use_cases: Annotated[CSessionService, Depends(service)],
) -> CSessionCommandResponse:
    async with session_factory() as db_session:
        response = await use_cases.create(
            db_session,
            principal_user_id=principal.user_id,
            request_id=request.state.request_id,
            grade=body.grade,
            session_mode=body.session_mode,
        )
        await db_session.commit()
        return response


@router.get("/active", response_model=CActiveSessionResponse)
async def get_active_session(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    use_cases: Annotated[CSessionService, Depends(service)],
) -> CActiveSessionResponse:
    async with session_factory() as db_session:
        return await use_cases.get_active(
            db_session, principal_user_id=principal.user_id, request_id=request.state.request_id
        )


@router.post("/{c_session_id}/abandon", response_model=CSessionCommandResponse)
async def abandon_session(
    c_session_id: UUID,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    use_cases: Annotated[CSessionService, Depends(service)],
) -> CSessionCommandResponse:
    async with session_factory() as db_session:
        response = await use_cases.abandon(
            db_session,
            principal_user_id=principal.user_id,
            c_session_id=c_session_id,
            request_id=request.state.request_id,
        )
        await db_session.commit()
        return response


@router.post("/{c_session_id}/complete", response_model=CSessionCommandResponse)
async def complete_session(
    c_session_id: UUID,
    body: CompleteCSessionRequest,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    use_cases: Annotated[CSessionService, Depends(service)],
) -> CSessionCommandResponse:
    async with session_factory() as db_session:
        response = await use_cases.complete(
            db_session,
            principal_user_id=principal.user_id,
            c_session_id=c_session_id,
            request_id=request.state.request_id,
            attendance_status=body.attendance_status,
        )
        await db_session.commit()
        return response
