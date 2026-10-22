"""The learner-presentation acknowledgement: the client reporting that the question is now on
screen, which is what starts the answering clock (2026-09-27 owner ruling).

WHY THIS EXISTS. ``timeout_deadline_utc`` used to be fixed when the item was SELECTED. Once Home
and the preparation screen began prefetching the first question, selection moved to before the
child is looking at anything at all, so server and network time was being charged to the learner.
``component-b-closure-decisions.json``'s timeout-policy entry already rules that "infrastructure
failure is never learner failure"; this route makes the clock measure what that ruling says it
should. The numeric threshold stays PROVISIONAL and unapproved -- only the start moves.

WHY IT IS SAFE TO LET THE CLIENT SAY WHEN. The acknowledgement is recorded ONCE per opportunity:
the first one anchors the deadline and every later one returns that same deadline unchanged. So a
remount, a relaunch, a retry or a deliberate reload cannot buy more time, and cannot shorten time
already granted. Never acknowledging simply leaves the fail-safe deadline written at selection, so
silence is not an escape either. The only thing a client controls is the START, once, and only in
the direction of being shown the question later than the server selected it.

The response carries the anchored deadline so the screen can trust the server's clock rather than
its own device time -- the same field, from the same source, as the presentation itself.
"""

from __future__ import annotations

from datetime import datetime

from app.domain.b_session import StrictModel


class PresentationAckFields(StrictModel):
    item_opportunity_id: str
    server_timeout_deadline_utc: datetime
    # True only for the call that actually started the clock. Purely informational -- the client
    # renders the same countdown either way -- but it makes a replay visibly a replay in logs and
    # in tests, instead of two indistinguishable 200s.
    anchored: bool


class PresentationAckResponse(PresentationAckFields):
    request_id: str
