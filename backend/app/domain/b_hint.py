"""BE4d (BEplan §9 BE4.5): governed hint-request response contract.

The response carries exactly the governed, learner-facing catalogue content the adapter
returned (``LiveEngineAdapter.get_hint`` — see ``app.infrastructure.live_engine.adapter``) plus
its reconstruction key. It never carries the correct answer, the accepted-answer set, or any
BKT/scientific parameter — a hint request is never a mastery observation (see
``app.application.hint_request``).
"""

from __future__ import annotations

from uuid import UUID

from app.domain.b_session import StrictModel


class HintRequestResponseFields(StrictModel):
    item_opportunity_id: UUID
    hint_level: int
    content: str
    content_id: str
    catalogue_version: str
    catalogue_checksum: str


class HintRequestResponse(HintRequestResponseFields):
    request_id: str
