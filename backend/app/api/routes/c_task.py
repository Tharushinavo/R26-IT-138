"""Component C's two task-serving endpoints (Phase 5: ``POST .../tasks/next``,
``POST .../tasks/{c_task_instance_id}/actions``). Mirrors ``app.api.routes.c_session`` exactly:
same auth dependency (``get_authenticated_principal``), same router-registration pattern,
structured ``details=[{"location", "type"}]`` error shape via the installed handlers.

CONNECT STEP 4 (was: NOT LIVE, Phase 5 through CONNECT Step 3): the real, non-smoke call below no
longer unconditionally refuses at ``assert_generation_config_permitted`` inside
``TaskService.next_task`` -- see ``app.application.live_engine_c.task_service``'s module docstring
for the full reasoning. The guard itself is unchanged and still runs on every call; what changed is
which ``GenerationConfig``/``PolicyConfig``/``ScaffoldConfig`` it is checking, under
``APPROVAL-2026-08-26-seven-families.md``. These routes remain gated on session creation
(``session_lifecycle.create_session``'s own seven-family gate, unaffected by this file) and on the
production runtime bundle actually being registered and approved (CONNECT Step 6) -- this file
alone does not make a session reachable."""

from typing import Annotated, Any, Mapping
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.application.live_engine_c.task_service import (
    PRODUCTION_GENERATION_CONFIG,
    PRODUCTION_SCAFFOLD_CONFIG,
    TaskService,
)
from app.domain.c_session import StrictModel
from app.domain.c_task import CNextTaskResponse, CSubmitActionResult
from app.domain.principal import AuthenticatedPrincipal
from app.infrastructure.auth import get_authenticated_principal
from app.infrastructure.database import session_factory


router = APIRouter(prefix="/api/v1/c/sessions", tags=["c-task-serving"])


def service() -> TaskService:
    return TaskService()


class CSubmitActionRequest(StrictModel):
    action_payload: Mapping[str, Any]


@router.post("/{c_session_id}/tasks/next", response_model=CNextTaskResponse, status_code=201)
async def next_task(
    c_session_id: UUID,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    use_cases: Annotated[TaskService, Depends(service)],
) -> CNextTaskResponse:
    async with session_factory() as db_session:
        response = await use_cases.next_task(
            db_session,
            principal_user_id=principal.user_id,
            request_id=request.state.request_id,
            c_session_id=c_session_id,
            # See task_service.py's module docstring, "PRODUCTION GENERATION CONFIG" -- real,
            # populated, approved-for-provisional-implementation (CONNECT Step 4); smoke_mode is
            # hardcoded False and is never a client-controllable value.
            generation_config=PRODUCTION_GENERATION_CONFIG,
            smoke_mode=False,
        )
        await db_session.commit()
        return response


@router.post(
    "/{c_session_id}/tasks/{c_task_instance_id}/actions",
    response_model=CSubmitActionResult,
)
async def submit_action(
    c_session_id: UUID,
    c_task_instance_id: UUID,
    body: CSubmitActionRequest,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    use_cases: Annotated[TaskService, Depends(service)],
) -> CSubmitActionResult:
    async with session_factory() as db_session:
        response = await use_cases.submit_action(
            db_session,
            principal_user_id=principal.user_id,
            request_id=request.state.request_id,
            c_session_id=c_session_id,
            c_task_instance_id=c_task_instance_id,
            action_payload=body.action_payload,
            generation_config=PRODUCTION_GENERATION_CONFIG,
            scaffold_config=PRODUCTION_SCAFFOLD_CONFIG,
        )
        await db_session.commit()
        return response
