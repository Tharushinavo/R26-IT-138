"""BF-3: estimator-input parity - proves the backend feeds the reviewed package's own estimator
functions statistically correct arguments, not merely that it constructs tasks correctly or ships
the right code.

Why this file exists, precisely. Two guarantees already exist and neither could have caught BF-1:

- ``test_be4f_parity.py`` proves TASK-CONSTRUCTION agreement between the adapter and a direct
  package call - it never touches the Guess-Guard or aggregation estimators at all.
- The wheel's pinned sha256 (``requirements.lock`` / the manifest / the bundle fixture) proves
  CODE IDENTITY - the shipped ``evaluate_guess_guard`` and ``_population_std`` are byte-identical
  to what was reviewed.

Neither can detect the backend calling a correct, reviewed function with the wrong statistical
arguments. That is exactly how BF-1 shipped and stayed undetected: ``evaluate_guess_guard`` itself
was, and remains, correct; ``session_completion.py`` was computing its floor and its median from
the identical current-session-only sample, which made ``TRIGGERED`` mathematically unreachable for
any input. This file asserts on ESTIMATOR INPUTS AND OUTPUTS directly - hand-computed expected
values, not just "did a task get built" - which is the level at which BF-1's defect was actually
visible.

Uses ``LiveEngineAdapter`` directly (never the raw package), matching the reuse-boundary
discipline every other test in this suite follows - the same call path ``session_completion.py``
itself uses, just invoked directly rather than through the full HTTP/service stack (that
integration-level proof - real learner, real sessions, real TRIGGERED outcome - is
``test_be4e_session_completion.py``'s job; this file is the narrower, numeric one).
"""

from __future__ import annotations

import pytest

pytest.importorskip(
    "component_b_generator",
    reason="upadya-component-b-live-engine is not installed; see backend/requirements.in",
)

from app.domain.live_engine.types import (
    GuessGuardStatus,
    OpportunityResponse,
    SessionIdentity,
    SkillMasteryUpdate,
)
from app.infrastructure.live_engine.adapter import LiveEngineAdapter


_THETA_B = 0.8
_FLOOR_QUANTILE = 0.1
_FLOOR_MIN_OBS = 5
_MEDIAN_QUANTILE = 0.5
_MEDIAN_MIN_OBSERVATIONS = 1


# ---------------------------------------------------------------------------
# Guess-Guard: hand-computed quantile floor, asserted exactly - not just "a status came back"
# ---------------------------------------------------------------------------

# Type-7 (numpy-default) linear-interpolation quantile at q=0.1 for n=5 sorted values:
# h = (n-1)*q = 4*0.1 = 0.4; floor = values[0] + (values[1]-values[0])*0.4
# = 2.0 + (2.5-2.0)*0.4 = 2.2 exactly. Deliberately non-identical values (unlike BF-1's
# integration test, which uses 5 identical 3.0s observations) so this exercises real
# interpolation, not just the degenerate all-equal case.
_PRIOR_RTS_SEC = [2.0, 2.5, 3.0, 3.5, 4.0]
_EXPECTED_FLOOR_SEC = 2.2


def test_plausibility_floor_matches_hand_computed_type7_quantile() -> None:
    adapter = LiveEngineAdapter()
    floor = adapter.plausibility_floor(_PRIOR_RTS_SEC, _FLOOR_QUANTILE, _FLOOR_MIN_OBS)
    assert floor == pytest.approx(_EXPECTED_FLOOR_SEC)


def test_guess_guard_triggers_when_current_median_is_below_the_hand_computed_floor() -> None:
    """The BF-1 regression, at the estimator level. Before the fix, this exact combination
    (mastery above theta_b, an implausibly fast current-session median, a real prior-session
    history whose floor the fast median is genuinely below) was unreachable because the caller
    passed the same sample for both quantiles - never because `evaluate_guess_guard` itself was
    wrong. It is not; this proves it, given inputs it was always meant to trigger on."""
    adapter = LiveEngineAdapter()
    status = adapter.evaluate(
        0.9,  # p_l > theta_b
        0.05,  # 50ms current-session median: far below the 2.2s floor
        _PRIOR_RTS_SEC,
        _THETA_B, _FLOOR_QUANTILE, _FLOOR_MIN_OBS,
    )
    assert status is GuessGuardStatus.TRIGGERED


def test_guess_guard_not_triggered_when_current_median_is_at_or_above_the_floor() -> None:
    adapter = LiveEngineAdapter()
    status = adapter.evaluate(
        0.9,
        3.0,  # >= the 2.2s floor: a normal-speed response, not implausibly fast
        _PRIOR_RTS_SEC,
        _THETA_B, _FLOOR_QUANTILE, _FLOOR_MIN_OBS,
    )
    assert status is GuessGuardStatus.NOT_TRIGGERED


def test_guess_guard_insufficient_evidence_below_floor_min_obs() -> None:
    """One observation short of n_min (4, not 5) must yield INSUFFICIENT_EVIDENCE regardless of
    how fast the current response was or how high mastery is - never a fabricated floor."""
    adapter = LiveEngineAdapter()
    below_min = _PRIOR_RTS_SEC[:4]
    assert adapter.plausibility_floor(below_min, _FLOOR_QUANTILE, _FLOOR_MIN_OBS) is None
    status = adapter.evaluate(
        0.9,
        0.05,  # implausibly fast - would trigger if a floor existed
        below_min,
        _THETA_B, _FLOOR_QUANTILE, _FLOOR_MIN_OBS,
    )
    assert status is GuessGuardStatus.INSUFFICIENT_EVIDENCE


def test_guess_guard_current_sessions_own_median_input_never_becomes_its_own_floor() -> None:
    """Directly encodes the exact shape of the original bug at the estimator boundary: passing
    the SAME sample as both the median source and the floor source must never trigger, because a
    quantile function is monotonically non-decreasing in q - floor(q=0.1) can never exceed
    median(q=0.5) on one identical sample. This is what made TRIGGERED unreachable before BF-1;
    asserting it stays true for `evaluate_guess_guard` itself (which is correct and untouched)
    documents why the defect was in the caller, never in this function."""
    adapter = LiveEngineAdapter()
    same_sample = [0.05, 0.05, 0.05, 0.05, 0.05]  # if reused for both median and floor
    median_from_same_sample = adapter.plausibility_floor(same_sample, _MEDIAN_QUANTILE, _MEDIAN_MIN_OBSERVATIONS)
    status = adapter.evaluate(
        0.9,
        median_from_same_sample,
        same_sample,
        _THETA_B, _FLOOR_QUANTILE, _FLOOR_MIN_OBS,
    )
    assert status is not GuessGuardStatus.TRIGGERED


# ---------------------------------------------------------------------------
# RT aggregates: n<2 and zero-variance edge cases - xfail until BF-4 (wheel rebuild) lands
# ---------------------------------------------------------------------------


def _single_opportunity_response(response_time_ms: int) -> OpportunityResponse:
    return OpportunityResponse(
        learner_id="learner-bf3",
        session_id="session-bf3",
        scheduled_session_index=1,
        item_opportunity_id="STU-0003-B001-I001",
        task_instance_id="STU-0003-B001-I001",
        item_template_id="B-ADD04-2D-NO-REGROUP",
        skill_id="addition",
        first_attempt_correct=True,
        first_attempt_error_pattern="correct",
        total_attempts=1,
        hint_requested=False,
        hint_count=0,
        final_item_completed=True,
        assisted_completion=False,
        unassisted_completion=True,
        total_response_time_ms=response_time_ms,
        first_attempt_response_time_ms=response_time_ms,
    )


def test_response_time_std_is_none_not_zero_for_a_single_observation() -> None:
    """A standard deviation computed from exactly one sample is undefined, not zero. The B->3
    contract field `b_item_response_time_std_sec` is `PositiveTiming | None` (`gt=0.0`), so 0.0 is
    rejected at that boundary - "no usable evidence" must be represented as None, matching the
    existing all-timeout precedent (an empty RT list already returns None for all three stats).

    BF-4: previously `xfail(strict=True)`, blocked on a wheel rebuild (Component_B_Measurement_
    And_Parity_Review.md finding F1) — the shipped wheel's aggregation/session.py computed an
    unguarded population std, returning 0.0 for a single observation. The wheel is now rebuilt
    from a Yass main commit containing the fix (e41b641). The marker is removed per its own
    reason string's instruction ("this test will XPASS ... the point is to force that removal").

    Also fixed here, independent of BF-4: this test's own fixture data was malformed twice over —
    `student_id="STU-BF03-0001"` and `item_opportunity_id`/`task_instance_id` of
    `"opportunity-bf3-1"`/`"task-bf3-1"` never matched the package's real id formats
    (`^STU-[0-9]{4}-B-[0-9]{3}$` for a session id, `^STU-[0-9]{4}-B[0-9]{3}-I[0-9]{3}$` for an
    opportunity/task-instance id — confirmed against `tests/test_be4f_parity.py`'s established
    convention). Neither defect was ever visible: `xfail(strict=True)` marks any exception as the
    expected failure regardless of cause, so this test had been xfailing for the wrong reason
    since BF-3 — a validation error, not the std assertion — and only surfaced once `--runxfail`
    was used to check what the test does with the marker removed, which is exactly how this
    should be caught before trusting a converted xfail as proof a fix landed."""
    adapter = LiveEngineAdapter()
    aggregate = adapter.aggregate_session(
        session_identity=SessionIdentity(
            student_id="STU-0003", b_session_index=1, scheduled_session_number=1, status="attended",
        ),
        opportunities=[_single_opportunity_response(2000)],
        skill_mastery_updates=[
            SkillMasteryUpdate(
                student_id="STU-0003", skill_id="addition", b_session_index=1,
                mastery_before=0.6, predicted_correct_probability=0.8, posterior_l=0.87, mastery_after=0.89,
            )
        ],
    )
    assert aggregate.stats.response_time_std_ms is None
