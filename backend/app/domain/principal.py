"""Minimal verified identity exposed to backend application code."""

from pydantic import BaseModel, ConfigDict


class AuthenticatedPrincipal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    user_id: str
    email: str | None = None
