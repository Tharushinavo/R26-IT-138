"""Component D feature computation (Component D authorization, D-011; plan v5 Phase 2).

Ported from compD's ``server/app/services/features.py`` using the **standard library only** --
no scikit-learn, pandas, numpy or joblib (plan v5 N-BE rule; those arrive with a trained model,
if one ever does). compD's own ``events_to_dataframe`` and ``features_to_row`` are NOT ported:
both exist to feed a trained ``Pipeline`` that this integration does not ship, and
``FEATURE_ORDER`` existed only to keep a row's column order aligned with training. Porting them
would be carrying dead scaffolding for a model that is not here.

THE ONE FORMULA THAT CHANGED SHAPE, AND WHY IT DID NOT CHANGE VALUE
-------------------------------------------------------------------
compD's ``answer_change_rate`` computed ``mean(click_count) / total`` and never observed an
answer changing. D-011 A4 renamed it ``mean_clicks_per_question`` as a correctness fix.

That rename exposed a second problem, which is recorded here rather than quietly resolved: with
the ORIGINAL expression the new name would still be wrong. ``mean(click_count)`` already *is* the
mean clicks per question; dividing it by ``total`` again yields clicks per question per question,
which is not a quantity anything means to use.

So the feature now computes what its name says -- ``mean(click_count)``. To keep that from
silently changing anyone's profile, the extra ``/ total`` has been moved to the ONE place that
consumed it, ``d_rule_profile``'s attention heuristic, where it is visible and labelled rather
than folded into a published feature. The rule-based output is therefore **numerically identical
to compD's**, term for term, while the public feature is now true to its name.

Why this is not a free choice: the division is load-bearing for the heuristic. A child who clicks
three times per question has ``mean_clicks_per_question = 3.0``; feeding that straight into
``1.0 - min(1.0, clicks + hint_rate * 0.5)`` saturates at zero and would score almost every child
"low" attention. The division was doing the work of a normaliser. Whether a normaliser scaled by
the number of questions in the run is the right one is a research question about the heuristic,
**not** something this integration decides -- flagged for the owner (M-BE-011 backlog) and left
exactly as compD had it.
"""

from __future__ import annotations

from collections.abc import Sequence
from statistics import mean, pstdev

from app.domain.d_profile import DCognitiveProfileFeatures, DInteractionEvent


MS_PER_SECOND = 1000

# compD's own ceiling on how informative one slow response is: beyond this, slower is not more
# slow. Lives here rather than in `d_rule_profile` because it is applied to each OBSERVATION, which
# is this module's business; the level thresholds it feeds stay there.
RESPONSE_TIME_CAP_MS = 10000.0


def capped_mean_response_time_ms(events: Sequence[DInteractionEvent]) -> float:
    """The mean response time with **each response** capped first, for the speed heuristic.

    THIS EXISTS BECAUSE compD APPLIED ITS OWN CAP IN THE WRONG PLACE, and live data showed what
    that costs. compD computed `min(mean(all responses), 10s)` -- it capped the AVERAGE. The cap
    expresses "a response beyond ten seconds tells us nothing more", which is a statement about a
    single response, so it belongs to each observation and not to their mean.

    The difference is not academic. Observed on the dev database, profile `e1a9c0da`:

        responses (s): 66.8, 7.1, 4.6, 3.8, 3.5, 3.1, 2.5, 2.4, 2.3, 2.1

    One question was left open for 66.8 seconds; the other nine took 2.1 to 7.1. Capping the mean
    gives 9.82s, which scores 0.018 and reads **Slow**. Capping each response gives 4.14s, which
    scores 0.586 and reads **Moderate**. A single pause -- a child looking away, someone speaking
    to them, a tab switch -- had relabelled the whole run.

    WHY THIS AND NOT A MEDIAN, which is the more obvious robust statistic: a median also fixes that
    run, but it changes runs that were never broken. The same data, profile `346c770f`, has no
    outlier at all and reads Moderate; its median would read **Fast**. Capping each response leaves
    that run's value **bit-identical** (3.58s) and moves only the runs that actually carry an
    outlier. It also introduces no new number -- same 10s cap, same thresholds -- whereas choosing
    a median, a trimmed mean or an idle timeout would each be a new rule about how a cognitive
    attribute is inferred, which this integration does not author.

    ``avg_response_time_ms`` on the published feature vector is deliberately NOT capped: it is
    reported as what it says it is, so the 66.8s run still shows a 9.82s mean and a 19.05s standard
    deviation. That pair is exactly how a reader spots an outlier, and hiding it inside the feature
    would destroy the only published signal that the run was unusual.
    """
    if not events:
        return 0.0
    return float(
        mean(min(event.response_time_sec * MS_PER_SECOND, RESPONSE_TIME_CAP_MS) for event in events)
    )


def compute_features(events: Sequence[DInteractionEvent]) -> DCognitiveProfileFeatures:
    """Aggregate one run's events into the feature vector.

    The empty case cannot be reached through the API -- ``DProfileCreateRequest`` requires at
    least one event -- but it is handled rather than left to raise, because ``statistics.mean``
    raises on an empty sequence and a future caller (a backfill, a test fixture) should get a
    defined answer instead of a 500. ``avg_attempts`` is 1.0 rather than 0.0 in that case: no
    questions means no retries, and a mean of zero attempts would misread as "every question was
    skipped".
    """
    if not events:
        return DCognitiveProfileFeatures(
            accuracy=0.0,
            avg_response_time_ms=0.0,
            response_time_std_ms=0.0,
            avg_attempts=1.0,
            retry_rate=0.0,
            hint_rate=0.0,
            mean_clicks_per_question=0.0,
            total_questions=0,
        )

    total = len(events)
    matched = sum(1 for event in events if event.response_matched)
    response_times_ms = [event.response_time_sec * MS_PER_SECOND for event in events]
    attempts = [event.attempts for event in events]
    retried = sum(1 for event in events if event.attempts > 1)
    assisted = sum(1 for event in events if event.assist_used)
    clicks = [event.click_count for event in events]

    return DCognitiveProfileFeatures(
        accuracy=matched / total,
        avg_response_time_ms=float(mean(response_times_ms)),
        # Population standard deviation, as compD had it, not the sample one: this is the spread
        # of the run that happened, not an estimate of a wider population's spread. `pstdev`
        # needs at least one point but is meaningless for one, so a single-question run reports
        # 0.0 explicitly rather than a number that looks like evidence.
        response_time_std_ms=float(pstdev(response_times_ms)) if total > 1 else 0.0,
        avg_attempts=float(mean(attempts)),
        retry_rate=retried / total,
        hint_rate=assisted / total,
        # D-011 A4: mean clicks per question, which is what the name says. See the module
        # docstring for the `/ total` that used to live here and where it went.
        mean_clicks_per_question=float(mean(clicks)),
        total_questions=total,
    )
