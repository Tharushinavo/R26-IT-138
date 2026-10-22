"""``C-COMP-v1`` deterministic engagement/frustration composites (SPEC §19; C Parameters
§9-§10 -- weights transcribed verbatim, not redefined). **Never sampled** (DF-08/DF-10).

Reuses ``models.contracts.EngagementComponents``/``FrustrationComponents`` -- the committed
oracle's own component models -- as the output type, so a value produced here is, by
construction, assignable straight onto a ``CToComponent3Payload`` without any reshaping (the
CRITICAL ORACLE TEST in this phase's test suite relies on exactly this).

The fallback variant ``C-COMP-v1-fallback-periods`` (C Parameters §9/§10) fires ONLY when
``inactive_time_sec`` is genuinely unavailable -- signalled by the caller-supplied
``CSessionAggregate.inactive_time_available`` flag (see ``aggregation.derive`` for why this is a
caller-supplied fact rather than something inferred here), never by this module guessing at
data quality.
"""

from __future__ import annotations

from typing import Literal, Tuple

from models.contracts import EngagementComponents, FrustrationComponents

from ..aggregation.models import CSessionAggregate

CompositeFormulaVersion = Literal["C-COMP-v1", "C-COMP-v1-fallback-periods"]

# C Parameters §9 -- engagement_score weights (Sigma w = 1.00).
_ENGAGEMENT_WEIGHT_COMPLETION = 0.30
_ENGAGEMENT_WEIGHT_ACTIVITY = 0.30
_ENGAGEMENT_WEIGHT_TARGET_BAND = 0.25
_ENGAGEMENT_WEIGHT_ACCURACY = 0.15

# C Parameters §10 -- frustration_index weights (Sigma w = 1.00).
_FRUSTRATION_WEIGHT_ERROR_RUN = 0.25
_FRUSTRATION_WEIGHT_EXCESS_ATTEMPT = 0.20
_FRUSTRATION_WEIGHT_INACTIVITY_BURDEN = 0.15
_FRUSTRATION_WEIGHT_FLOOR_HIT = 0.15
_FRUSTRATION_WEIGHT_QUIT_AFTER_ERROR = 0.15
_FRUSTRATION_WEIGHT_SAFETY_OVERRIDE = 0.10


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def decide_composite_formula_version(aggregate: CSessionAggregate) -> CompositeFormulaVersion:
    """C Parameters §9/§10: the fallback-periods variant applies ONLY when
    ``inactive_time_sec`` is genuinely unavailable."""
    return "C-COMP-v1" if aggregate.inactive_time_available else "C-COMP-v1-fallback-periods"


def compute_engagement(
    aggregate: CSessionAggregate, formula_version: CompositeFormulaVersion
) -> Tuple[EngagementComponents, float]:
    """C Parameters §9: engagement components + score. Requires ``aggregate.accuracy_rate`` to
    be non-null (caller must gate on sufficient evidence before calling -- see
    ``composites.learner_state``)."""
    if aggregate.accuracy_rate is None:
        raise ValueError("compute_engagement requires a non-null accuracy_rate (insufficient evidence)")

    fallback = formula_version == "C-COMP-v1-fallback-periods"

    completion_component = _clamp01(aggregate.task_completion_rate)
    if fallback:
        activity_component = _clamp01(1 - aggregate.inactivity_periods / 5)
    else:
        activity_component = _clamp01(1 - aggregate.inactive_time_sec / aggregate.session_duration_sec)
    target_band_component = _clamp01(aggregate.time_in_target_band_sec / aggregate.session_duration_sec)
    accuracy_component = _clamp01(aggregate.accuracy_rate)

    components = EngagementComponents(
        completion_component=completion_component,
        activity_component=activity_component,
        target_band_component=target_band_component,
        accuracy_component=accuracy_component,
    )
    score = (
        _ENGAGEMENT_WEIGHT_COMPLETION * completion_component
        + _ENGAGEMENT_WEIGHT_ACTIVITY * activity_component
        + _ENGAGEMENT_WEIGHT_TARGET_BAND * target_band_component
        + _ENGAGEMENT_WEIGHT_ACCURACY * accuracy_component
    )
    return components, score


def compute_frustration(
    aggregate: CSessionAggregate, formula_version: CompositeFormulaVersion
) -> Tuple[FrustrationComponents, float]:
    """C Parameters §10: frustration components + index. Requires
    ``aggregate.avg_attempts_per_task`` to be non-null (caller must gate on sufficient evidence
    before calling)."""
    if aggregate.avg_attempts_per_task is None:
        raise ValueError("compute_frustration requires a non-null avg_attempts_per_task (insufficient evidence)")

    fallback = formula_version == "C-COMP-v1-fallback-periods"

    error_run_component = _clamp01(aggregate.consecutive_error_max / 5)
    excess_attempt_component = _clamp01((aggregate.avg_attempts_per_task - 1) / 3)
    if fallback:
        inactivity_burden_component = _clamp01(aggregate.inactivity_periods / 5)
    else:
        inactivity_burden_component = _clamp01(
            (aggregate.inactive_time_sec / aggregate.session_duration_sec) / 0.30
        )
    floor_hit_component = _clamp01(aggregate.difficulty_floor_hits / 3)
    quit_after_error_component = 1.0 if aggregate.quit_after_error else 0.0
    safety_override_component = _clamp01(aggregate.safety_override_count / 2)

    components = FrustrationComponents(
        error_run_component=error_run_component,
        excess_attempt_component=excess_attempt_component,
        inactivity_burden_component=inactivity_burden_component,
        floor_hit_component=floor_hit_component,
        quit_after_error_component=quit_after_error_component,
        safety_override_component=safety_override_component,
    )
    index = (
        _FRUSTRATION_WEIGHT_ERROR_RUN * error_run_component
        + _FRUSTRATION_WEIGHT_EXCESS_ATTEMPT * excess_attempt_component
        + _FRUSTRATION_WEIGHT_INACTIVITY_BURDEN * inactivity_burden_component
        + _FRUSTRATION_WEIGHT_FLOOR_HIT * floor_hit_component
        + _FRUSTRATION_WEIGHT_QUIT_AFTER_ERROR * quit_after_error_component
        + _FRUSTRATION_WEIGHT_SAFETY_OVERRIDE * safety_override_component
    )
    return components, index
