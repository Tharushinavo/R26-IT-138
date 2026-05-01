"""Feature engineering: turn a list of raw InteractionEvent objects into
the aggregated CognitiveFeatures vector that the trained model expects.

Keep the feature order in `FEATURE_ORDER` identical to the order used
during training of the decision-tree model.
"""
from __future__ import annotations

from statistics import mean, pstdev
from typing import List

from app.schemas import CognitiveFeatures, InteractionEvent


FEATURE_ORDER: list[str] = [
    "accuracy",
    "avg_response_time_ms",
    "response_time_std_ms",
    "avg_attempts",
    "retry_rate",
    "hint_rate",
    "answer_change_rate",
    "total_questions",
]


def compute_features(events: List[InteractionEvent]) -> CognitiveFeatures:
    if not events:
        return CognitiveFeatures(
            accuracy=0.0,
            avg_response_time_ms=0.0,
            response_time_std_ms=0.0,
            avg_attempts=1.0,
            retry_rate=0.0,
            hint_rate=0.0,
            answer_change_rate=0.0,
            total_questions=0,
        )

    total = len(events)
    correct = sum(1 for e in events if e.is_correct)
    rts = [e.response_time_sec * 1000 for e in events]
    attempts = [e.attempts for e in events]
    retries = sum(1 for e in events if e.attempts > 1)
    hints = sum(1 for e in events if e.hint_used)
    clicks = [e.click_count for e in events]

    return CognitiveFeatures(
        accuracy=correct / total,
        avg_response_time_ms=float(mean(rts)),
        response_time_std_ms=float(pstdev(rts)) if total > 1 else 0.0,
        avg_attempts=float(mean(attempts)),
        retry_rate=retries / total,
        hint_rate=hints / total,
        answer_change_rate=float(mean(clicks)) / max(total, 1),
        total_questions=total,
    )


def features_to_row(features: CognitiveFeatures) -> list[float]:
    d = features.model_dump()
    return [float(d[k]) for k in FEATURE_ORDER]
