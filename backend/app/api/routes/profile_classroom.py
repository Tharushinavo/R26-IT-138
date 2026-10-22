"""Eight governance-authorized profile and classroom endpoints (the eighth, classroom
deletion, added 2026-09-14 for the Component 3 teacher dashboard)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, status

from app.application.profile_classroom import ProfileClassroomService
from app.domain.principal import AuthenticatedPrincipal
from app.domain.profile_classroom import ClassroomCreateRequest, ClassroomDeleteRequest, ClassroomDeleteResponse, ClassroomListResponse, ClassroomResponse, LearnerProfileResponse, ProfileCreateRequest, TeacherProfileResponse
from app.infrastructure.auth import get_authenticated_principal


router = APIRouter(prefix="/api/v1", tags=["profiles-and-classrooms"])


def service() -> ProfileClassroomService:
    return ProfileClassroomService()


@router.post("/teacher/profile", response_model=TeacherProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_teacher_profile(payload: ProfileCreateRequest, request: Request, principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)], idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)], use_cases: Annotated[ProfileClassroomService, Depends(service)]) -> TeacherProfileResponse:
    return await use_cases.create_teacher_profile(principal, payload.name, idempotency_key, request.state.request_id)


@router.get("/teacher/profile", response_model=TeacherProfileResponse)
async def get_teacher_profile(request: Request, principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)], use_cases: Annotated[ProfileClassroomService, Depends(service)]) -> TeacherProfileResponse:
    return await use_cases.get_teacher_profile(principal, request.state.request_id)


@router.post("/learner/profile", response_model=LearnerProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_learner_profile(payload: ProfileCreateRequest, request: Request, principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)], idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)], use_cases: Annotated[ProfileClassroomService, Depends(service)]) -> LearnerProfileResponse:
    return await use_cases.create_learner_profile(principal, payload.name, idempotency_key, request.state.request_id)


@router.get("/learner/profile", response_model=LearnerProfileResponse)
async def get_learner_profile(request: Request, principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)], use_cases: Annotated[ProfileClassroomService, Depends(service)]) -> LearnerProfileResponse:
    return await use_cases.get_learner_profile(principal, request.state.request_id)


@router.post("/classrooms", response_model=ClassroomResponse, status_code=status.HTTP_201_CREATED)
async def create_classroom(payload: ClassroomCreateRequest, request: Request, principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)], idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)], use_cases: Annotated[ProfileClassroomService, Depends(service)]) -> ClassroomResponse:
    return await use_cases.create_classroom(principal, payload, idempotency_key, request.state.request_id)


@router.get("/classrooms", response_model=ClassroomListResponse)
async def list_classrooms(request: Request, principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)], use_cases: Annotated[ProfileClassroomService, Depends(service)]) -> ClassroomListResponse:
    return await use_cases.list_classrooms(principal, request.state.request_id)


@router.get("/classrooms/{classroom_id}", response_model=ClassroomResponse)
async def get_classroom(classroom_id: UUID, request: Request, principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)], use_cases: Annotated[ProfileClassroomService, Depends(service)]) -> ClassroomResponse:
    return await use_cases.get_classroom(principal, classroom_id, request.state.request_id)


@router.post("/classrooms/{classroom_id}/delete", response_model=ClassroomDeleteResponse)
async def delete_classroom(classroom_id: UUID, payload: ClassroomDeleteRequest, request: Request, principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)], idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)], use_cases: Annotated[ProfileClassroomService, Depends(service)]) -> ClassroomDeleteResponse:
    return await use_cases.delete_classroom(principal, classroom_id, payload, idempotency_key, request.state.request_id)
