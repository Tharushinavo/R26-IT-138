"""Component D's rule-based cognitive profile (Component D authorization, D-011; plan v5
Phase 2: "the rule-based profile, standard library only").

Ported from compD's ``server/app/services/model.py``: ``_rule_based_profile`` and the confidence
expression out of ``predict_profile``. **Every threshold, coefficient and comparison below is
compD's, unchanged**, and the port carries no judgement about whether they are the right numbers --
that is a research question with an owner.

**ONE DELIBERATE DIVERGENCE, directed by the owner on 2026-10-21 after live data exposed the
defect.** ``processing_speed_level`` now receives ``mean(min(response, 10s))`` instead of
``min(mean(responses), 10s)`` -- the same 10-second ceiling, applied to each response rather than to
their average, which is where a statement about a single response belongs. No threshold,
coefficient or comparison moved. ``MODEL_VERSION`` is bumped to ``rule-based-v2`` so profiles
produced before and after the change are distinguishable. The full reasoning, the alternatives
rejected, and the live run that forced it are in ``d_features.capped_mean_response_time_ms``.

BE-2's differential proof against compD's source was **re-run after this change and is still
IDENTICAL on all 768 cases**, speed included. That is not luck and it is the best argument for this
particular fix: the two formulas agree wherever a run's response times are of a similar magnitude,
which is every case that grid contains. They diverge only when one response is an extreme outlier
among otherwise-quick answers -- the shape live play produced and a synthetic grid of uniform
timings never does.

WHAT WAS NOT PORTED, AND WHY
----------------------------
- **The trained model, and every path to it.** ``_ModelHolder``, ``_predict_with_rf_artifact``,
  ``_predict_per_interaction``, ``_majority_vote_profile``, ``extract_student_level_features``
  and ``model_status`` all require scikit-learn and joblib, which plan v5 forbids until a trained
  model exists (B2). ``model_version`` is therefore always rule-based here. The ML path is
  not stubbed, flagged or feature-switched: it is absent, so there is no dormant branch to
  mistake for a working one.
- **``_normalize_speed``.** It existed to coerce a model's free-text prediction into the three
  allowed values. The rule-based path produces those values directly, so a normaliser would only
  be able to hide a bug in this file.
- **compD's ``print`` lines.** Plan v5 ("don't port the ``print(student_id...)`` lines"). They
  carried a learner identifier into stdout, which this codebase does not do anywhere.
- **The clamp loop.** compD re-checked its own labels against the allowed sets after predicting,
  because a trained model could return anything. ``bucket`` and ``speed_bucket`` below are total
  over the reals -- every path returns one of the literals -- and the DTO's ``Literal`` types and
  the table's CHECK constraints would both refuse anything else. Re-clamping would be dead code
  that made a future bug here silently produce "medium" instead of failing.
"""

from __future__ import annotations

from app.application.d_features import RESPONSE_TIME_CAP_MS as _RESPONSE_TIME_CAP_MS
from app.domain.d_profile import DCognitiveProfileFeatures, Level, SpeedLevel


# compD's thresholds, verbatim (`model.py:_rule_based_profile`). Named rather than inlined so a
# future calibration is one reviewable edit in one place.
LEVEL_LOW_AT_OR_BELOW = 0.4
LEVEL_HIGH_AT_OR_ABOVE = 0.75
SPEED_SLOW_AT_OR_BELOW = 0.35
SPEED_FAST_AT_OR_ABOVE = 0.7

# The cap itself is compD's. It now lives in `d_features` because it is applied per OBSERVATION
# rather than to their mean -- see `capped_mean_response_time_ms` for what that fixes and why. Kept
# importable from here too, because the score below divides by it.
RESPONSE_TIME_CAP_MS = _RESPONSE_TIME_CAP_MS

# compD's confidence expression: 70% from how much evidence there is (saturating at ten
# questions) and 30% from accuracy.
CONFIDENCE_EVIDENCE_WEIGHT = 0.7
CONFIDENCE_ACCURACY_WEIGHT = 0.3
CONFIDENCE_SATURATION_QUESTIONS = 10.0
CONFIDENCE_DECIMAL_PLACES = 2

# compD weights assistance at half a click when scoring attention.
ASSIST_WEIGHT_IN_ATTENTION = 0.5

# BUMPED FROM "rule-based-v1" when `processing_speed_level` stopped capping the mean and started
# capping each response (see `d_features.capped_mean_response_time_ms`). The whole purpose of this
# field is to say which generation of the rule produced a profile, so a change in what the rule
# COMPUTES has to move it -- otherwise the two profiles already stored on the dev database, which
# were produced by the old rule, would be indistinguishable from new ones. Those two rows keep
# `rule-based-v1` and are NOT recomputed: a stored profile is a record of what was reported at the
# time, not a cache to be refreshed.
#
# This is a change in a public VALUE, not in the contract's schema -- the field is a free string
# and no route, type or required-field list moves.
MODEL_VERSION = "rule-based-v2"


def _bucket(value: float) -> Level:
    if value <= LEVEL_LOW_AT_OR_BELOW:
        return "low"
    if value >= LEVEL_HIGH_AT_OR_ABOVE:
        return "high"
    return "medium"


def _speed_bucket(value: float) -> SpeedLevel:
    if value <= SPEED_SLOW_AT_OR_BELOW:
        return "Slow"
    if value >= SPEED_FAST_AT_OR_ABOVE:
        return "Fast"
    return "Moderate"


def _attention_score(features: DCognitiveProfileFeatures) -> float:
    """compD's attention expression, preserving its value exactly.

    compD read ``answer_change_rate``, which was ``mean(click_count) / total_questions``. That
    feature now computes ``mean(click_count)`` -- what its new name
    (``mean_clicks_per_question``, D-011 A4) actually says -- so the division compD folded into
    the feature is applied HERE instead, which is the only place that ever consumed it. Same
    arithmetic, same result; see ``d_features``'s module docstring for the full reasoning.

    The division is a normaliser by the length of the run, and whether that is the right
    normaliser is an open research question, not something this integration settled. It is left
    as compD had it.
    """
    questions = max(features.total_questions, 1)
    clicks_per_question_per_question = features.mean_clicks_per_question / questions
    distraction = clicks_per_question_per_question + features.hint_rate * ASSIST_WEIGHT_IN_ATTENTION
    return 1.0 - min(1.0, distraction)


def memory_level(features: DCognitiveProfileFeatures) -> Level:
    """compD: the inverse of the retry rate -- more retries reads as weaker recall."""
    return _bucket(1.0 - features.retry_rate)


def attention_level(features: DCognitiveProfileFeatures) -> Level:
    """compD: the inverse of clicking and asking for help.

    Recorded as a known weakness rather than presented as sound: this makes attention a function
    of CLICK VOLUME, so a child on a touch screen that registers stray taps, or one who likes
    tapping, scores lower on "attention" for reasons that have nothing to do with attending. The
    authorization raised this and did not approve the heuristic -- it approved storing what the
    heuristic produces. Backlog.
    """
    return _bucket(_attention_score(features))


def number_sense_level(features: DCognitiveProfileFeatures) -> Level:
    """compD: accuracy, directly."""
    return _bucket(features.accuracy)


def processing_speed_level(capped_mean_response_time_ms: float) -> SpeedLevel:
    """Faster responses score higher. compD's scale and thresholds, applied to a robust input.

    **This is the one place Component D deliberately diverges from compD.** The divergence is
    narrower than it sounds: BE-2's 768-case differential against compD's source was re-run after
    the change and is still identical, speed included. The two formulas agree whenever a run's
    response times are of a similar magnitude, and part company only when one response is an
    extreme outlier among otherwise-quick answers.

    The scale below is unchanged: score `1 - capped/10000`, Slow at or below 0.35, Fast at or above
    0.7. What changed is the ARGUMENT. compD passed `min(mean(responses), 10s)`, capping the
    average; this takes `mean(min(response, 10s))`, capping each response. Both use the same 10s
    ceiling, because it is compD's own and expresses a property of a single response.

    Why it had to change is in `d_features.capped_mean_response_time_ms`, with the live run that
    demonstrated it: one 66.8-second pause among nine answers of 2-7 seconds was reading as a
    "Slow" child.

    Takes the number rather than the whole feature vector, so the call site cannot accidentally
    pass the uncapped `features.avg_response_time_ms` -- which is still published, still uncapped,
    and would silently restore the defect if this took a `DCognitiveProfileFeatures`.
    """
    capped = min(capped_mean_response_time_ms, RESPONSE_TIME_CAP_MS)
    score = max(0.0, 1.0 - capped / RESPONSE_TIME_CAP_MS)
    return _speed_bucket(score)


def confidence_score(features: DCognitiveProfileFeatures) -> float:
    """How much the profile should be trusted, NOT how well the child did.

    Rounded to two places because it is displayed, and an unrounded float would imply a precision
    a four-rule heuristic over ten questions does not have.
    """
    evidence = min(1.0, features.total_questions / CONFIDENCE_SATURATION_QUESTIONS)
    raw = evidence * CONFIDENCE_EVIDENCE_WEIGHT + features.accuracy * CONFIDENCE_ACCURACY_WEIGHT
    return round(raw, CONFIDENCE_DECIMAL_PLACES)
