"""Nine governance-authorized classroom invite and membership endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, status

from app.application.classroom_membership import ClassroomMembershipService
from app.domain.classroom_membership import (
    ClassroomLearnerListResponse,
    InviteCreateResponse,
    InviteResolveResponse,
    InviteRevokeResponse,
    InviteTokenRequest,
    LearnerMembershipListResponse,
    MembershipDecisionResponse,
    MembershipRequestListResponse,
    MembershipRequestResponse,
)
from app.domain.principal import AuthenticatedPrincipal
from app.infrastructure.auth import get_authenticated_principal


router = APIRouter(prefix="/api/v1", tags=["classroom-invites-and-memberships"])


def service() -> ClassroomMembershipService:
    return ClassroomMembershipService()


@router.post("/classrooms/{classroom_id}/invites", response_model=InviteCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(
    classroom_id: UUID,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)],
    use_cases: Annotated[ClassroomMembershipService, Depends(service)],
) -> InviteCreateResponse:
    return await use_cases.create_invite(principal, classroom_id, idempotency_key, request.state.request_id)


@router.post("/classroom-invites/{classroom_invite_id}/revoke", response_model=InviteRevokeResponse)
async def revoke_invite(
    classroom_invite_id: UUID,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)],
    use_cases: Annotated[ClassroomMembershipService, Depends(service)],
) -> InviteRevokeResponse:
    return await use_cases.revoke_invite(principal, classroom_invite_id, idempotency_key, request.state.request_id)


@router.post("/classroom-invites/resolve", response_model=InviteResolveResponse)
async def resolve_invite(
    payload: InviteTokenRequest,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)],
    use_cases: Annotated[ClassroomMembershipService, Depends(service)],
) -> InviteResolveResponse:
    return await use_cases.resolve_invite(principal, payload, idempotency_key, request.state.request_id)


@router.post("/classroom-memberships/requests", response_model=MembershipRequestResponse, status_code=status.HTTP_201_CREATED)
async def request_membership(
    payload: InviteTokenRequest,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)],
    use_cases: Annotated[ClassroomMembershipService, Depends(service)],
) -> MembershipRequestResponse:
    return await use_cases.request_membership(principal, payload, idempotency_key, request.state.request_id)


@router.get("/classrooms/{classroom_id}/membership-requests", response_model=MembershipRequestListResponse)
async def list_membership_requests(
    classroom_id: UUID,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    use_cases: Annotated[ClassroomMembershipService, Depends(service)],
) -> MembershipRequestListResponse:
    return await use_cases.list_membership_requests(principal, classroom_id, request.state.request_id)


@router.post("/classroom-memberships/{membership_id}/approve", response_model=MembershipDecisionResponse)
async def approve_membership(
    membership_id: UUID,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)],
    use_cases: Annotated[ClassroomMembershipService, Depends(service)],
) -> MembershipDecisionResponse:
    return await use_cases.approve_membership(principal, membership_id, idempotency_key, request.state.request_id)


@router.post("/classroom-memberships/{membership_id}/reject", response_model=MembershipDecisionResponse)
async def reject_membership(
    membership_id: UUID,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)],
    use_cases: Annotated[ClassroomMembershipService, Depends(service)],
) -> MembershipDecisionResponse:
    return await use_cases.reject_membership(principal, membership_id, idempotency_key, request.state.request_id)


@router.get("/classrooms/{classroom_id}/learners", response_model=ClassroomLearnerListResponse)
async def list_classroom_learners(
    classroom_id: UUID,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    use_cases: Annotated[ClassroomMembershipService, Depends(service)],
) -> ClassroomLearnerListResponse:
    return await use_cases.list_classroom_learners(principal, classroom_id, request.state.request_id)


@router.get("/learner/classrooms", response_model=LearnerMembershipListResponse)
async def list_learner_classrooms(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    use_cases: Annotated[ClassroomMembershipService, Depends(service)],
) -> LearnerMembershipListResponse:
    return await use_cases.list_learner_classrooms(principal, request.state.request_id)
