"""Authenticated identity endpoint; no profile or learner persistence."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.domain.principal import AuthenticatedPrincipal
from app.infrastructure.auth import get_authenticated_principal


router = APIRouter(prefix="/api/v1", tags=["identity"])


@router.get("/me", response_model=AuthenticatedPrincipal)
async def current_identity(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
) -> AuthenticatedPrincipal:
    return principal
