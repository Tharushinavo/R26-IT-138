"""BE4e (BEplan §9 BE4.6): completion/next-or-complete + SAFE session-standing contracts.

Both responses are the SAFE, non-diagnostic subset only (BEplan §9 BE4.6 step 5): session state
and coarse opportunity counts. Neither carries any raw BKT value (``p_l``/mastery probability),
private selection rationale, plausibility-check internals, an answer, or a scientific parameter —
those are computed and persisted PRIVATELY (``app.application.session_completion``,
``b_session_aggregate_results`` / ``b_skill_certification_results``) and never reach either DTO.
Per-skill mastery/certification is architecturally GATE-B UNRESOLVED (safe-progress policy) and is
therefore not exposed here at all — not even in aggregate form.

``next_opportunity``, when present, is BE4a/BE4b's own already-safe
``OpportunityPresentationFields`` (reused, never re-derived) — the same allow-listed DTO the
standalone selection endpoint returns.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from app.domain.b_opportunity import OpportunityPresentationFields
from app.domain.b_session import StrictModel


SessionStandingState = Literal["active", "completed"]


class OpportunityAdvanceFields(StrictModel):
    item_opportunity_id: UUID
    session_state: SessionStandingState
    opportunities_completed: int
    opportunities_total_bound: int
    next_opportunity: OpportunityPresentationFields | None


class OpportunityAdvanceResponse(OpportunityAdvanceFields):
    request_id: str


class SessionStandingFields(StrictModel):
    session_id: UUID
    session_state: SessionStandingState
    opportunities_completed: int
    opportunities_total_bound: int


class SessionStandingResponse(SessionStandingFields):
    request_id: str
