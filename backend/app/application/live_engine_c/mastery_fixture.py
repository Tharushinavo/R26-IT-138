"""FIXTURE — stands in for a future B-owned producer that would emit the seven mastery values at
real B session completion (Phase 4 work order, planning item 6, ratified verbatim in the
implementation work order: "Keep that docstring wording — it was correct, including the explicit
refusal to claim P(L) parity.").

That producer does not exist: it is blocked on GATE-B (the safe-progress policy, unresolved).
This fixture supplies contract-shaped values for Phase 4's session-lifecycle wiring only; it is
NOT a P(L) passthrough and makes no claim that BKT P(L) (``b_learner_skill_states.p_l``) and
``BToCMasteryPayload.mastery_*`` are the same quantity — that is an unsigned scientific question
neither this fixture nor its caller may answer.

HARD LINE: this module reads NOTHING from ``b_learner_skill_states`` or any other B-private
table. Reading it would not be a fixture — it would silently make Component C the de-facto
producer of B's own mastery estimate and cross a component boundary with no gate (the work
order's own words: "worse than the fixture... exactly the C-4-in-a-new-costume failure").

PHASE 4b, R-5 (SUPERVISOR RULING, correcting the Phase 4b R1 wording): this module now ALSO
stands in for B's own IDENTITY -- ``mastery_source_student_id``, ``mastery_source_
intervention_session_id``, ``mastery_source_intervention_session_number``. R1's "caller-supplied,
never derived" meant the SERVER-SIDE producer standing in for B, not the HTTP client; accepting
these three from an HTTP request body let an untrusted caller assert B provenance it never
produced, which is strictly worse than what R1 was written to prevent (C manufacturing B's
provenance itself). ``CreateCSessionRequest`` (app/api/routes/c_session.py) no longer accepts
them from the client at all -- ``fixture_b_provenance_for_phase_4`` below is now the ONLY source
for all four things (mastery values and identity) that ``CSessionService.create`` uses for a
combined-mode session. These identity values are fixture-derived, exactly as fictional as the
mastery values above -- never client-derived, and never derived from C's own identifiers (R1).
"""

from __future__ import annotations

from typing import Mapping

# The seven frozen skill names (models.contracts.SKILLS), fixed at 0.5 (a neutral, uninformative
# midpoint -- not derived from any B computation, not a claim about any real learner).
FIXTURE_MASTERY_BY_SKILL: Mapping[str, float] = {
    "counting": 0.5,
    "number_sense": 0.5,
    "place_value": 0.5,
    "addition": 0.5,
    "subtraction": 0.5,
    "multiplication": 0.5,
    "division": 0.5,
}

# Fixture-only B identity, matching B's own frozen formats (StudentId ^STU-[0-9]{4}$,
# InterventionSessionId ^STU-[0-9]{4}-I-[0-9]{3}$) so the contract validator accepts them --
# not a claim that a real B student or session with these identifiers exists (R-5).
FIXTURE_MASTERY_SOURCE_STUDENT_ID = "STU-0001"
FIXTURE_MASTERY_SOURCE_INTERVENTION_SESSION_ID = "STU-0001-I-001"
FIXTURE_MASTERY_SOURCE_INTERVENTION_SESSION_NUMBER = 1


def fixture_b_mastery_payload_for_phase_4() -> Mapping[str, float]:
    """Returns the FIXTURE seven-value mastery mapping (see module docstring). Callers must still
    supply real B identity fields (student_id, intervention_session_id,
    intervention_session_number) themselves -- this function never invents those (G3)."""
    return dict(FIXTURE_MASTERY_BY_SKILL)


def fixture_b_provenance_for_phase_4() -> tuple[str, str, int]:
    """Returns the FIXTURE (mastery_source_student_id, mastery_source_intervention_session_id,
    mastery_source_intervention_session_number) triple (R-5, module docstring). The ONLY source
    for these three values anywhere in the combined-mode create path -- never accepted from an
    HTTP request body."""
    return (
        FIXTURE_MASTERY_SOURCE_STUDENT_ID,
        FIXTURE_MASTERY_SOURCE_INTERVENTION_SESSION_ID,
        FIXTURE_MASTERY_SOURCE_INTERVENTION_SESSION_NUMBER,
    )
