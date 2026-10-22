"""Phase C6.1 -- the inter-session (multi-session) state machine over the committed Phase C6.0
``run_c_session``. PURE WIRING: introduces no new science, only the C-owned cross-session
bookkeeping the cold-start assessment explicitly assigns to "the shared orchestrator / C6"
(``selection.phase`` module docstring) rather than to any already-committed module.

Three pieces, verbatim from the cold-start assessment §5:

1. ``CLearnerSessionState`` -- the C-owned, non-B-derived state carried session-to-session:
   ``eligible_combined_handoffs_completed`` (N, assessment §5.3), ``sessions_since_last_practice``
   (a spacing signal already read by ``pipeline.evidence``/``policy`` as C-local context), and
   ``prior_session_end_state`` (already a ``run_c_session`` input, LS-02 spirit: only a
   ``telemetry_quality_status == "complete"`` session may overwrite it). SF-043 (assessment §5.6:
   "no cached B payload across sessions") is a STRUCTURAL guarantee here: this model declares no
   ``mastery_*`` / B-shaped field at all, so ``extra="forbid"`` rejects any attempt to smuggle one
   in, exactly as ``models.learner_state.CLocalLearnerState`` already guarantees for the
   within-session C-local state.

2. ``is_eligible_combined_handoff`` -- the five-condition ELIGIBLE COMPLETED COMBINED B->C HANDOFF
   predicate (assessment §5, all five must hold): (1) ``session_mode == "combined"``; (2) B ran
   before C AND (3) a valid fresh same-session B payload reached C -- collapsed into the single
   ``b_payload_valid`` flag, since a valid *same-session* B payload cannot exist unless B ran
   before C in that session (order is a precondition of validity, not a separately observable
   fact); (4) the slot was NOT fully missed (``attendance_status != "missed"``); (5) no technical
   failure prevented the required bootstrap opportunities (``not technical_blocked_bootstrap``).
   This reads only the three kinds of info the assessment says C already has -- "its own mode +
   whether a valid B payload arrived + the orchestrator's non-learning attendance/technical
   context" -- and adds no new B-derived learning field (SF-043).

3. ``decide_next_session_phase`` -- the session-start phase decision (assessment §5.3): ``c_only``
   always maps to the literal ``"c_only"`` phase (never calls ``decide_session_phase``);
   ``combined`` calls the committed ``selection.phase.decide_session_phase`` with the CURRENT N
   and the grade's committed window. This is the reviewed implementation of the C-16 Phase 4 step
   and depends only on already-shipped modules (``selection/phase.py``, ``selection/config.py``).

PACKAGING NOTE (prabathi-component-c-live-engine, Phase 1 batch 1a, rework): removed exactly three
things relative to the pinned commit -- (1) the line
``from .session import RunCSessionResult, run_c_session``; (2) the whole ``advance_session``
function, the per-session driver that called ``run_c_session`` and returned ``RunCSessionResult``;
and (3) ``_DRIVER_OWNED_SESSION_KWARGS``, a module-level constant verified referenced ONLY inside
``advance_session``'s body and therefore dead once that function is gone. ``pipeline/session.py``
is never-ship (Component_C_Master_Build_Plan_v3.0 §6.1: it is the C6.0 ``run_c_session`` driver,
excluded by §6.2's per-module packaging boundary), so nothing in this file may retain a live
dependency on it.

This file retains ``CLearnerSessionState``, ``initial_learner_session_state``,
``is_eligible_combined_handoff``, and ``decide_next_session_phase`` -- the four symbols the owner's
corrected trim authorization names as live-required (Cold-Start Bootstrap Readiness Assessment §5:
the C6 longitudinal state and the N counter, plus the phase-gate decision itself).
§6.2's original two-symbol list (``CLearnerSessionState``, ``is_eligible_combined_handoff`` only)
was INCOMPLETE and has been corrected by the owner; ``initial_learner_session_state`` and
``decide_next_session_phase`` are also live-required and neither touches any never-ship module.

Two items are retained DELIBERATELY, not by oversight, even though the trim above leaves them
without an in-file caller:

- ``SessionStateInputError`` -- previously raised only inside ``advance_session``, and referenced
  nowhere else in the entire pinned tree (never-ship modules included). Kept because it is public
  API and the owner's trim authorization names three items to remove, not four; removing a fourth,
  unnamed symbol would exceed the authorized scope of this batch.
- The ``from typing import Annotated, Any, Dict, Mapping, Tuple`` import -- left byte-identical
  even though ``Any``, ``Mapping``, and ``Tuple`` become unused once ``advance_session`` (the only
  user of all three) is removed. Minimal diff is the packaging discipline here: this line is not
  itself a dependency on any never-ship module, so it is not touched.

``_SEVEN_SKILLS`` is NOT dead code and was verified, not assumed, to still be required: it is
referenced by ``CLearnerSessionState._spacing_uses_known_skills``, a field validator on a KEPT
class, and removing it would break that class.

After this removal, ``run_c_session``, ``RunCSessionResult``, ``advance_session``, and
``_DRIVER_OWNED_SESSION_KWARGS`` are simply not bound names in this module's namespace
(``hasattr(module, "run_c_session")`` etc. are all ``False``), the same namespace-level guarantee
``backend/tests/test_be3_live_engine_boundary.py`` already relies on for Component B's trimmed
files. See ``backend/provenance/component-c-live-engine-manifest.json`` for the pinned source
commit and manifest.
"""

from __future__ import annotations

from typing import Annotated, Any, Dict, Mapping, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models.contracts import SKILLS

from ..models.enums import AttendanceStatus, LearnerState, SessionMode, SessionPhase
from ..selection.config import CSelectionConfig
from ..selection.phase import decide_session_phase

PIPELINE_SESSION_STATE_VERSION = "c6.1-session-state-1.0.0"

_SEVEN_SKILLS = frozenset(SKILLS)


class SessionStateInputError(ValueError):
    """Raised for C6.1 input inconsistencies caught before any ``run_c_session`` call."""


class CLearnerSessionState(BaseModel):
    """C-owned cross-session state (cold-start assessment §5). Carries NO B mastery scalar or
    payload field of any kind (SF-043) -- ``extra="forbid"`` plus the deliberate omission of any
    ``mastery_*`` / B-shaped field is the structural guarantee, exactly as
    ``models.learner_state.CLocalLearnerState`` already does for the within-session state."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    eligible_combined_handoffs_completed: Annotated[int, Field(ge=0)]
    sessions_since_last_practice: Dict[str, Annotated[int, Field(ge=0)]]
    prior_session_end_state: LearnerState | None = None

    @field_validator("sessions_since_last_practice")
    @classmethod
    def _spacing_uses_known_skills(cls, v: Dict[str, int]) -> Dict[str, int]:
        unknown = set(v.keys()) - _SEVEN_SKILLS
        if unknown:
            raise ValueError(
                f"sessions_since_last_practice keys must be among the seven frozen skills; unknown={sorted(unknown)}"
            )
        return v


def initial_learner_session_state() -> CLearnerSessionState:
    """The cross-session state for a brand-new learner: no eligible combined handoffs completed
    yet, no spacing history, no prior session-end state."""
    return CLearnerSessionState(
        eligible_combined_handoffs_completed=0,
        sessions_since_last_practice={},
        prior_session_end_state=None,
    )


def is_eligible_combined_handoff(
    session_mode: SessionMode,
    b_payload_valid: bool,
    attendance_status: AttendanceStatus,
    technical_blocked_bootstrap: bool,
) -> bool:
    """The ELIGIBLE COMPLETED COMBINED B->C HANDOFF predicate (cold-start assessment §5): all
    five conditions must hold, each individually false makes the session ineligible and it must
    NOT advance ``eligible_combined_handoffs_completed``."""
    if session_mode != "combined":
        return False
    if not b_payload_valid:
        return False
    if attendance_status == "missed":
        return False
    if technical_blocked_bootstrap:
        return False
    return True


def decide_next_session_phase(
    *,
    session_mode: SessionMode,
    grade: int,
    state: CLearnerSessionState,
    selection_config: CSelectionConfig,
) -> SessionPhase:
    """Session-start phase decision (assessment §5.3): ``c_only`` always maps to the literal
    ``"c_only"`` phase (never calls ``decide_session_phase``); ``combined`` calls the committed
    ``selection.phase.decide_session_phase`` with the CURRENT N and the grade's committed window.
    The mode is fixed for the whole session by the caller of ``run_c_session``."""
    if session_mode == "c_only":
        return "c_only"
    window_w = selection_config.window_for_grade(grade)
    phase = decide_session_phase(state.eligible_combined_handoffs_completed, window_w)
    return phase  # type: ignore[return-value]  # decide_session_phase's str is one of the two combined SessionPhase literals
