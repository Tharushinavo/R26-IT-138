"""Component D's learner resolution and provenance stamp (Component D authorization, D-011).

Plan v5 Phase 2 says "copy B's ``_require_learner``". It is copied ONCE, here, rather than twice
into Component D's two services: the host's own duplication (``b_session_lifecycle``,
``learner_skill_states``, ``classroom_membership`` each keep a copy) is a per-COMPONENT boundary,
and reproducing it a second time inside a single component would be duplication with no boundary
to justify it. The behaviour is identical to B's, deliberately, down to which failure is a 403 and
which is a 404.

WHY THE TWO FAILURES ARE DIFFERENT CODES, since it looks arbitrary from the route:

- **403 FORBIDDEN** -- the caller authenticated and is a TEACHER. The account exists and the token
  is good; it is simply not a learner, and saying so is not a leak.
- **404 RESOURCE_NOT_FOUND** -- there is no ``app_users`` row, or the row has no learner link. The
  caller may be mid-onboarding. A 403 here would assert something about an account that may not
  exist yet.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ForbiddenError, ResourceNotFoundError
from app.domain.principal import AuthenticatedPrincipal
from app.infrastructure.repositories import AppUserRepository


# The migration that created Component D's three tables. Stamped onto every row this component
# writes, so a row can always be traced to the schema shape it was written under.
SCHEMA_REVISION = "20261021_0010"

# Mirrors C's `AUTHORIZED_C_SESSION_LIFECYCLE_COMMAND` -- the provenance block records WHICH
# authorization admitted the write, not merely that a write happened.
REASON_CODE = "AUTHORIZED_D_PROFILING_COMMAND"

SYSTEM_ACTOR = "d-cognitive-profiling"


async def require_learner(session: AsyncSession, principal: AuthenticatedPrincipal) -> UUID:
    """Resolve the caller to their learner id, or raise.

    Returns the learner id ALONE, not the ``AppUser`` as B's version does: no Component D code
    path has any business with the user row, and handing it back would make it available to one.
    """
    found = await AppUserRepository(session).find_with_learner_link_by_subject(principal.user_id)
    if found is None:
        raise ResourceNotFoundError()
    user, link = found
    if user.profile_type != "LEARNER":
        raise ForbiddenError()
    if link is None:
        raise ResourceNotFoundError()
    return link.learner_id


def provenance(*, resource_type: str, resource_id: UUID, request_id: str, operation: str) -> dict[str, object]:
    """The mandatory provenance block, filled the way C's ``_provenance`` fills it.

    ``system_actor`` is set and ``actor_user_id`` is left unset, which is what
    ``ck_*_actor_exactly_one`` requires: exactly one of the two is non-null. It is the SYSTEM
    actor rather than the user because the row is written by this component's own logic in
    response to a request, not by a person acting on another person's record -- the same reading
    B and C apply.
    """
    return {
        "system_actor": SYSTEM_ACTOR,
        "request_id": request_id,
        "operation_or_event_type": operation,
        "reason_code": REASON_CODE,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "source_class": "REAL",
        "source_system": "studentapp-api",
        "environment": "live-endpoint",
        "schema_revision": SCHEMA_REVISION,
    }
