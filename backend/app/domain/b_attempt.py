"""BE4c (BEplan §9 BE4.3 + BE4.4): attempt-submission request/response contracts.

The response is correctness + attempt/opportunity bookkeeping only — it never carries the
correct answer, the accepted-answer set, a hint, or any BKT/scientific parameter (``p_l``,
``predicted_probability``, etc. live only in the PRIVATE ``b_skill_state_transitions`` table).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.domain.b_session import StrictModel


EventKind = Literal["RESPONSE", "TIMEOUT"]


class SubmitResponseRequest(StrictModel):
    """Strict, size-capped request shape. ``client_elapsed_ms`` is TELEMETRY ONLY — never read
    for correctness or BKT; server timestamps are authoritative."""

    submitted_value: str = Field(min_length=1, max_length=255)
    client_elapsed_ms: int | None = Field(default=None, ge=0, le=3_600_000)


class AttemptResponseFields(StrictModel):
    item_opportunity_id: UUID
    attempt_index: int
    event_kind: EventKind
    response_matched: bool | None
    server_submitted_at_utc: datetime


class AttemptResponse(AttemptResponseFields):
    request_id: str
