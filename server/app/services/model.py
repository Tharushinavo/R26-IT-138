"""Loads the trained Decision Tree classifier from a .pkl file and
produces a cognitive profile.

The trained model is expected to be one of:
  (A) A single multi-output classifier that predicts 4 labels in order:
      [memory, attention, number_sense, processing_speed]
      with each label being one of: "low" | "medium" | "high".

  (B) A dict of 4 independent classifiers:
      {"memory": clf, "attention": clf, "number_sense": clf, "processing_speed": clf}

If no model file is present, a deterministic rule-based fallback is used
so the API is still usable during development.
"""
from __future__ import annotations

import os
import threading
from typing import Any, Dict, List

import joblib
import numpy as np

from app.config import get_settings
from app.schemas import CognitiveFeatures, CognitiveProfile
from app.services.features import FEATURE_ORDER, features_to_row


DIMENSIONS: List[str] = ["memory_level", "attention_level", "number_sense_level", "processing_speed_level"]
LEVELS = ("low", "medium", "high")
SPEED_LEVELS = ("Slow", "Moderate", "Fast")


class _ModelHolder:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._model: Any = None
        self._loaded_path: str | None = None

    def get(self) -> Any:
        settings = get_settings()
        path = settings.model_path
        if self._model is not None and self._loaded_path == path:
            return self._model
        with self._lock:
            if self._model is not None and self._loaded_path == path:
                return self._model
            if path and os.path.isfile(path):
                self._model = joblib.load(path)
                self._loaded_path = path
            else:
                self._model = None
                self._loaded_path = None
        return self._model


_holder = _ModelHolder()


def _rule_based_profile(features: CognitiveFeatures) -> Dict[str, str]:
    """Fallback classifier when no .pkl is available. Purely heuristic."""
    def bucket(value: float, low_thr: float, high_thr: float) -> str:
        if value <= low_thr:
            return "low"
        if value >= high_thr:
            return "high"
        return "medium"

    def speed_bucket(value: float, low_thr: float, high_thr: float) -> str:
        if value <= low_thr:
            return "Slow"
        if value >= high_thr:
            return "Fast"
        return "Moderate"

    # Memory: inverse of retry rate (more retries -> weaker memory)
    memory = bucket(1.0 - features.retry_rate, 0.4, 0.75)
    # Attention: inverse of answer-change rate & hint rate
    attention_score = 1.0 - min(1.0, features.answer_change_rate + features.hint_rate * 0.5)
    attention = bucket(attention_score, 0.4, 0.75)
    # Number sense: accuracy
    number_sense = bucket(features.accuracy, 0.4, 0.75)
    # Processing speed: faster avg response -> higher (cap at 10s)
    speed_score = max(0.0, 1.0 - min(features.avg_response_time_ms, 10000) / 10000)
    processing_speed = speed_bucket(speed_score, 0.35, 0.7)

    return {
        "memory_level": memory,
        "attention_level": attention,
        "number_sense_level": number_sense,
        "processing_speed_level": processing_speed,
    }


def _predict_with_model(model: Any, row: List[float]) -> Dict[str, str]:
    X = np.array([row], dtype=float)

    # Case B: dict of per-dimension classifiers
    if isinstance(model, dict):
        out: Dict[str, str] = {}
        for dim in DIMENSIONS:
            clf = model.get(dim)
            if clf is None:
                raise ValueError(f"Model dict missing key: {dim}")
            pred = clf.predict(X)[0]
            out[dim] = str(pred)
        return out

    # Case A: single (multi-output) estimator
    preds = model.predict(X)
    preds = np.array(preds)
    if preds.ndim == 1:
        # If model returns a single label, broadcast to every dimension as a fallback
        label = str(preds[0])
        return {d: label for d in DIMENSIONS}
    row0 = preds[0]
    if len(row0) != len(DIMENSIONS):
        raise ValueError(
            f"Model output has {len(row0)} labels, expected {len(DIMENSIONS)} "
            f"in order {DIMENSIONS}"
        )
    return {d: str(row0[i]) for i, d in enumerate(DIMENSIONS)}


def predict_profile(
    student_id: str,
    features: CognitiveFeatures,
    session_id: str | None = None,
) -> CognitiveProfile:
    row = features_to_row(features)
    model = _holder.get()
    if model is None:
        labels = _rule_based_profile(features)
        model_version = "rule-based-v1"
    else:
        try:
            labels = _predict_with_model(model, row)
            model_version = "decision-tree-v1"
        except Exception:
            labels = _rule_based_profile(features)
            model_version = "rule-based-v1"

    # Clamp to known levels
    for k, v in labels.items():
        if k == "processing_speed_level":
            if v not in SPEED_LEVELS:
                labels[k] = "Moderate"
        else:
            if v not in LEVELS:
                labels[k] = "medium"

    # Compute confidence score (simple heuristic: based on number of events)
    q = features.total_questions
    confidence = min(1.0, q / 10.0) * 0.7 + features.accuracy * 0.3

    # Generate recommendation
    from app.services.recommendation import generate_recommendation
    recommendation = generate_recommendation(labels)

    return CognitiveProfile(
        student_id=student_id,
        session_id=session_id,
        memory_level=labels["memory_level"],  # type: ignore[arg-type]
        attention_level=labels["attention_level"],  # type: ignore[arg-type]
        number_sense_level=labels["number_sense_level"],  # type: ignore[arg-type]
        processing_speed_level=labels["processing_speed_level"],  # type: ignore[arg-type]
        confidence_score=round(confidence, 2),
        recommendation=recommendation,
        model_version=model_version,
        features=features,
    )


def model_status() -> dict:
    model = _holder.get()
    settings = get_settings()
    return {
        "model_loaded": model is not None,
        "model_path": settings.model_path,
        "feature_order": FEATURE_ORDER,
        "dimensions": DIMENSIONS,
    }
