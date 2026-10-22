"""``decide_session_phase`` (Phase C4.0) -- the FROZEN cold-start off-by-one rule.

Verbatim from the cold-start assessment §5.3:

    Let N = eligible_combined_handoffs_completed   (state before this session)

    Before a combined session starts:
        if N < W:   run C familiarization mode
        if N >= W:  run C mastery-driven mode

    After the current combined session completes successfully (eligible handoff):
        N = N + 1

This module is a PURE function of ``(N, W)``. It does not count, store, or increment N -- the
assessment explicitly assigns that ownership to the shared orchestrator / C6 ("N is incremented
only after a successful eligible handoff"; "C-only, B-only, missed, partial-ineligible, and
technically-failed sessions do NOT increment N"). The mode is decided once, at session start,
and is fixed for the whole session (assessment §5.3/§5.4) -- callers must not re-invoke this
mid-session with a different N and switch modes partway through.

This decision reads NO B-derived signal whatsoever -- ``N`` is C's own count of its own eligible
combined handoffs, never a B readiness/observation-count/evidence mask (cold-start assessment's
withdrawn-mask revision note; SF-043).
"""

from __future__ import annotations

from ..models.enums import SessionPhase

CombinedSessionPhase = SessionPhase  # "familiarization" | "mastery_driven" (never "c_only" here)


def decide_session_phase(eligible_combined_handoffs_completed: int, window_W: int) -> str:
    """``N < W`` -> ``"familiarization"``; ``N >= W`` -> ``"mastery_driven"`` (assessment §5.3,
    frozen off-by-one). Only valid for a **combined** session -- ``session_mode == "c_only"``
    never calls this; it always maps to ``session_phase == "c_only"`` directly (selector.py)."""
    if not isinstance(eligible_combined_handoffs_completed, int) or isinstance(eligible_combined_handoffs_completed, bool):
        raise ValueError(
            f"eligible_combined_handoffs_completed must be an int, got {eligible_combined_handoffs_completed!r}"
        )
    if eligible_combined_handoffs_completed < 0:
        raise ValueError(
            f"eligible_combined_handoffs_completed must be >= 0, got {eligible_combined_handoffs_completed!r}"
        )
    if not isinstance(window_W, int) or isinstance(window_W, bool) or window_W < 1:
        raise ValueError(f"window_W must be an int >= 1, got {window_W!r}")

    if eligible_combined_handoffs_completed < window_W:
        return "familiarization"
    return "mastery_driven"
