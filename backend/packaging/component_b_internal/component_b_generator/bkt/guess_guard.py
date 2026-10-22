"""Guess-Guard response-time plausibility check (Phase B3.3).

Estimator-side, per-learner/per-skill check: a learner whose BKT mastery estimate is above the
global certification threshold ``theta_B`` but who is responding implausibly fast (below their
own historical floor) is a guess-pattern risk, not a mastered learner. This module computes the
floor and the 3-valued guard status only — it does **not** decide certification (that is B3.4).

Below the minimum-observation threshold the floor is undefined and the guard does **not** block
(SPEC §A.5): the status is ``INSUFFICIENT_EVIDENCE``, distinct from ``NOT_TRIGGERED``, so a later
slice can choose how to treat thin evidence without this module making that call.

The floor value itself is B-internal and must never be placed on any exported/contract model;
only the 3-valued status (and the ``TRIGGERED``-only count) may surface downstream.
"""

from __future__ import annotations

from enum import Enum
from typing import Iterable, Sequence


class GuessGuardStatus(str, Enum):
    NOT_TRIGGERED = "NOT_TRIGGERED"
    TRIGGERED = "TRIGGERED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


def _valid_rts(rt_history: Iterable[float | None]) -> list[float]:
    """Defensively drop non-positive/None entries. Timeouts are not valid RT observations and
    must never appear in ``rt_history`` to begin with — the caller passes only valid first-attempt
    RTs; this is a defence-in-depth filter, not the mechanism that excludes timeouts."""
    return [rt for rt in rt_history if rt is not None and rt > 0.0]


def _quantile(sorted_values: Sequence[float], q: float) -> float:
    """Deterministic linear-interpolation quantile (the "linear"/type-7 method, matching
    ``numpy.quantile``'s default): index ``h = (n - 1) * q`` into the sorted sample, then
    linearly interpolate between the floor and ceiling ranks of ``h``."""
    n = len(sorted_values)
    if n == 1:
        return sorted_values[0]
    h = (n - 1) * q
    lo = int(h)
    hi = min(lo + 1, n - 1)
    frac = h - lo
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * frac


def plausibility_floor(rt_history: Iterable[float | None], q: float, n_min: int) -> float | None:
    """Per-learner/per-skill RT floor: the ``q``-quantile of the learner's valid first-attempt
    response times for one skill. ``rt_history`` must already exclude timeouts (they are not
    valid RT observations); this function additionally drops any non-positive/None entries
    defensively. Returns ``None`` (floor undefined / insufficient evidence) when the valid
    observation count is below ``n_min``.
    """
    valid = sorted(_valid_rts(rt_history))
    if len(valid) < n_min:
        return None
    return _quantile(valid, q)


def evaluate_guess_guard(
    p_l: float,
    median_item_response_time_sec: float,
    rt_history: Iterable[float | None],
    theta_B: float,
    q: float,
    n_min: int,
) -> GuessGuardStatus:
    """3-valued Guess-Guard status (FROZEN rule, SPEC §A.5 precedence).

    1. If the floor is undefined (valid RT count < ``n_min``) -> ``INSUFFICIENT_EVIDENCE``. This
       does **not** block certification; it is a distinct, honest status.
    2. Otherwise, FROZEN rule: ``TRIGGERED`` iff ``p_l > theta_B AND median_item_response_time_sec
       < floor``; else ``NOT_TRIGGERED``.
    """
    floor = plausibility_floor(rt_history, q, n_min)
    if floor is None:
        return GuessGuardStatus.INSUFFICIENT_EVIDENCE

    if p_l > theta_B and median_item_response_time_sec < floor:
        return GuessGuardStatus.TRIGGERED
    return GuessGuardStatus.NOT_TRIGGERED


def guess_guard_triggered_count(statuses: Iterable[GuessGuardStatus]) -> int:
    """Count only ``TRIGGERED`` statuses. ``INSUFFICIENT_EVIDENCE`` is not a block and is not
    counted (matches the exported ``guess_guard_triggered`` semantics: blocks only)."""
    return sum(1 for status in statuses if status is GuessGuardStatus.TRIGGERED)
