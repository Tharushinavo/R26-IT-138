"""Liveness and readiness endpoints."""

from typing import Literal

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict

from app.core.config import get_settings
from app.infrastructure.database import probe_database


router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    """Public health-check response."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["alive", "ready"]
    request_id: str


class ReadinessResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["ready"]
    stage: Literal["infrastructure"]
    request_id: str
    checks: dict[str, str]


@router.get("/live", response_model=HealthResponse)
async def liveness(request: Request) -> HealthResponse:
    """Report that the API process is running."""

    return HealthResponse(status="alive", request_id=request.state.request_id)


@router.get("/ready", response_model=ReadinessResponse)
async def readiness(request: Request) -> ReadinessResponse:
    """Verify the implemented SQLAlchemy-to-PostgreSQL dependency."""
    try:
        await probe_database()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"stage": "infrastructure", "database": "unavailable"},
        ) from exc
    return ReadinessResponse(
        status="ready",
        stage="infrastructure",
        request_id=request.state.request_id,
        checks={
            "api_process": "ok", "database_connection": "ok", "generator": "not_checked",
            "catalogue": "not_checked", "runtime_bundle": "not_checked",
            "migrations": "not_checked", "authentication": "not_checked",
        },
    )
