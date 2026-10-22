"""Public contracts for the authorized BE2.3-BE2.4 neutral session-lifecycle skeleton.

Per the engineering-continuation authorization for this batch: session start/complete/
abandon are explicit client commands with no scientific or pedagogical completion
criteria. These contracts intentionally expose no question, answer, attempt, hint,
BKT, mastery, sequencing, certification, or numeric expiry/timeout field. The
``runtime_bundle_version`` is an opaque pinned identifier, never a scientific payload.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


SessionState = Literal["active", "completed", "abandoned"]


class SessionFields(StrictModel):
    session_id: UUID
    state: SessionState
    runtime_bundle_version: str
    created_at_utc: datetime
    row_version: int


class SessionCommandResponse(SessionFields):
    request_id: str


class ActiveSessionResponse(StrictModel):
    session: SessionFields | None
    request_id: str
