"""Learner-facing read of Component B's per-skill BKT state (2026-09-21, product-owner ruling).

This is the FIRST response anywhere in the API to carry a raw BKT ``p_l``. Until now every B DTO
refused it, citing the still-UNRESOLVED "safe-progress and descriptive summary policy"
(provenance/component-b-be2-governance-authorization.json: "Expose no ... mastery ... until
privacy and presentation approval"). The product owner ruled on 2026-09-21 that the Play prep
card may show each of the seven skills' mastery to the child AS BAR LENGTH ONLY -- the number
itself is never rendered, labelled, or read aloud to the child. See buildLog2.md's entry of that
date for the ruling as recorded, including that the academic/research approver's sign-off is not
on file.

What this is NOT:
- Not Component C consuming B's estimate as engine input (the C-4 boundary,
  app/application/live_engine_c/mastery_fixture.py). Component C still receives the fixture. This
  is B reading B's own table for B's own learner, over B's own route.
- Not a certification, readiness, or recommendation. ``p_l`` is the current estimate and
  ``observation_count`` is how much evidence it rests on -- a row with zero observations is the
  bundle's P(L0) prior, not something the model learned about this child, and the client is
  expected to render it as an empty bar rather than as progress.
- Not on any task-presentation DTO. The BE3c private/public split (no mastery reaches the learner
  on the task in front of them) is untouched.

Rows exist only for skills the learner has been initialised on, which happens at their first
Component B session (opportunity_selection.load_or_init_skill_states). A learner who has never
played B gets an empty list; this read never writes.
"""

from __future__ import annotations

from pydantic import Field

from app.domain.b_session import StrictModel


class LearnerSkillStateItem(StrictModel):
    skill_id: str
    p_l: float = Field(ge=0.0, le=1.0)
    observation_count: int = Field(ge=0)


class LearnerSkillStatesResponse(StrictModel):
    skill_states: list[LearnerSkillStateItem]
    request_id: str
