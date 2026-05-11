"""Loads the Colab-trained Decision Tree Pipeline and predicts cognitive profiles.

The trained model artifact is a dict with keys:
  - model: sklearn Pipeline (preprocessor + MultiOutputClassifier)
  - feature_cols: list of raw input feature names
  - target_cols: list of target label names
  - label_classes: dict of allowed classes per target

The pipeline expects raw per-interaction features (no manual encoding required).
For a student profile, we predict per-interaction and aggregate by majority vote.
"""
from __future__ import annotations

import os
import threading
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd

from app.config import get_settings
from app.schemas import CognitiveFeatures, CognitiveProfile, InteractionEvent
from app.services.features import events_to_dataframe

# Expected output dimensions and levels
DIMENSIONS: List[str] = ["memory_level", "attention_level", "number_sense_level", "processing_speed_level"]
LEVELS = ("low", "medium", "high")
SPEED_LEVELS = ("Slow", "Moderate", "Fast")


class _ModelHolder:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._artifact: Dict[str, Any] | None = None
        self._loaded_path: str | None = None

    def get(self) -> Dict[str, Any] | None:
        settings = get_settings()
        path = settings.model_path
        # Resolve relative paths from the server root directory
        if path and not os.path.isabs(path):
            # Try relative to CWD first, then relative to this file's parent
            if not os.path.isfile(path):
                server_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                path = os.path.join(server_root, path)
        if self._artifact is not None and self._loaded_path == path:
            return self._artifact
        with self._lock:
            if self._artifact is not None and self._loaded_path == path:
                return self._artifact
            if path and os.path.isfile(path):
                self._artifact = joblib.load(path)
                self._loaded_path = path
            else:
                self._artifact = None
                self._loaded_path = None
        return self._artifact


_holder = _ModelHolder()


def _rule_based_profile(features: CognitiveFeatures) -> Dict[str, str]:
    """Fallback classifier when no model is available. Purely heuristic."""
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


def _normalize_speed(value: str) -> str:
    """Normalize processing speed prediction to schema-expected values (Slow/Moderate/Fast)."""
    v = value.strip().lower()
    if v in ("slow",):
        return "Slow"
    if v in ("fast",):
        return "Fast"
    return "Moderate"


def extract_aggregated_features_for_model(df: pd.DataFrame, feature_cols: list) -> pd.DataFrame:
    """Aggregate per-interaction dataframe into a single row for the enhanced model."""
    row = {}
    row['avg_response_time']     = df['response_time_sec'].mean()
    row['med_response_time']     = df['response_time_sec'].median()
    row['max_response_time']     = df['response_time_sec'].max()
    row['min_response_time']     = df['response_time_sec'].min()
    row['avg_attempts']          = df['attempts'].mean()
    row['max_attempts']          = df['attempts'].max()
    row['total_attempts']        = df['attempts'].sum()
    row['correct_rate']          = df['is_correct'].mean()
    row['total_correct']         = df['is_correct'].sum()
    row['hint_rate']             = df['hint_used'].mean()
    row['avg_click_count']       = df['click_count'].mean()
    row['avg_session_time']      = df['session_time_sec'].mean()
    row['avg_time_between']      = df['time_between_actions'].mean()

    for diff in ['Easy', 'Medium', 'Hard']:
        sub = df[df['difficulty'] == diff]
        row[f'correct_rate_{diff.lower()}'] = sub['is_correct'].mean() if len(sub) > 0 else 0.0
        row[f'avg_attempts_{diff.lower()}'] = sub['attempts'].mean()   if len(sub) > 0 else 0.0

    for topic in ['Counting', 'Addition', 'Subtraction', 'Number Comparison', 'Division']:
        sub = df[df['topic'] == topic]
        tkey = topic.lower().replace(' ', '_')
        row[f'correct_rate_{tkey}'] = sub['is_correct'].mean() if len(sub) > 0 else 0.0

    n = len(df)
    for etype in ['none', 'calculation', 'conceptual', 'careless', 'unknown']:
        row[f'error_{etype}_rate'] = (df['error_type'] == etype).sum() / n

    std = df['response_time_sec'].std()
    row['response_time_std'] = std if pd.notna(std) else 0.0
    row['n_questions'] = len(df)

    res = pd.DataFrame([row])
    # Ensure all required features are present
    for c in feature_cols:
        if c not in res.columns:
            res[c] = 0.0
    return res[feature_cols]

def _predict_per_interaction(artifact: Dict[str, Any], df: pd.DataFrame) -> pd.DataFrame:
    """Legacy: Predict cognitive labels for each interaction row using the trained Pipeline."""
    pipeline = artifact["model"]
    feature_cols = artifact["feature_cols"]
    X = df[feature_cols]
    preds = pipeline.predict(X)
    target_cols = artifact["target_cols"]
    return pd.DataFrame(preds, columns=target_cols, index=df.index)

def _majority_vote_profile(pred_df: pd.DataFrame) -> Dict[str, str]:
    """Legacy: Aggregate per-interaction predictions to a single student profile via majority vote."""
    if pred_df.empty:
        return {
            "label_memory": "Medium", "label_attention": "Medium",
            "label_number_sense": "Medium", "label_processing_speed": "Moderate",
        }
    profile = {}
    for col in pred_df.columns:
        profile[col] = str(pred_df[col].value_counts().idxmax())
    return profile



def predict_profile(
    student_id: str,
    events: List[InteractionEvent],
    session_id: Optional[str] = None,
    language: Optional[str] = "en"
) -> CognitiveProfile:
    """Predict cognitive profile.
    
    Args:
        student_id: Student identifier
        events: List of InteractionEvent objects (per question)
        session_id: Optional session identifier
        language: Optional language code (e.g. 'si' for Sinhala, 'en' for English)
    
    Returns:
        CognitiveProfile with predicted levels and metadata
    """
    # Load model artifact
    artifact = _holder.get()
    
    if artifact is None:
        # Fallback: aggregate to features and use rule-based
        print("🧠 [COGNITIVE MODEL] Using rule-based fallback - ML model not loaded")
        from app.services.features import compute_features
        features = compute_features(events)
        labels = _rule_based_profile(features)
        model_version = "rule-based-v1"
    else:
        try:
            # Convert events to DataFrame with raw feature columns
            df = events_to_dataframe(events)
            if df.empty:
                # Fallback to rule-based if no valid events
                print("🧠 [COGNITIVE MODEL] Using rule-based fallback - empty DataFrame")
                from app.services.features import compute_features
                features = compute_features(events)
                labels = _rule_based_profile(features)
                model_version = "rule-based-v1"
            else:
                # Check if model expects student-level aggregation
                if artifact.get("aggregation") == "student_level":
                    print("🌳 [COGNITIVE MODEL] Using Enhanced ML model (V5) for prediction")
                    feature_cols = artifact.get("feature_cols", [])
                    agg_df = extract_aggregated_features_for_model(df, feature_cols)
                    
                    pipeline = artifact["model"]
                    preds = pipeline.predict(agg_df)[0]
                    
                    target_cols = artifact.get("target_cols", [
                        'label_memory', 'label_attention', 
                        'label_number_sense', 'label_processing_speed'
                    ])
                    
                    vote_profile = {target_cols[i]: str(preds[i]) for i in range(len(target_cols))}
                    model_version = artifact.get("model_version", "enhanced-model-v5")
                else:
                    # Legacy model
                    print("🌳 [COGNITIVE MODEL] Using Legacy Decision Tree ML model for prediction")
                    pred_df = _predict_per_interaction(artifact, df)
                    vote_profile = _majority_vote_profile(pred_df)
                    model_version = "decision-tree-colab-v1"

                # Map from label_* to dimension names
                # Model predicts title case (Low/Medium/High) but schema uses lowercase
                labels = {
                    "memory_level": vote_profile.get("label_memory", "Medium").lower(),
                    "attention_level": vote_profile.get("label_attention", "Medium").lower(),
                    "number_sense_level": vote_profile.get("label_number_sense", "Medium").lower(),
                    "processing_speed_level": _normalize_speed(vote_profile.get("label_processing_speed", "Moderate")),
                }
                print(f"🧠 [COGNITIVE MODEL] ML prediction complete - model_version: {model_version}")
        except Exception as e:
            # Any model error falls back to rule-based
            print(f"🧠 [COGNITIVE MODEL] ML model failed ({e}), falling back to rule-based")
            from app.services.features import compute_features
            features = compute_features(events)
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
    q = len(events)
    accuracy = sum(1 for e in events if getattr(e, 'is_correct', False)) / max(q, 1)
    confidence = min(1.0, q / 10.0) * 0.7 + accuracy * 0.3

    # Generate dynamic recommendation and insight based on predictions
    from app.services.recommendation import generate_recommendation, generate_insight
    from app.services.features import compute_features
    agg_features = compute_features(events)
    
    # Combine recommendation with dynamic insight for richer output
    rec_text = generate_recommendation(labels, language)
    insight_text = generate_insight(labels, agg_features.model_dump(), language)
    recommendation = f"{insight_text}\n\n{rec_text}"

    profile = CognitiveProfile(
        student_id=student_id,
        session_id=session_id,
        memory_level=labels["memory_level"],  # type: ignore[arg-type]
        attention_level=labels["attention_level"],  # type: ignore[arg-type]
        number_sense_level=labels["number_sense_level"],  # type: ignore[arg-type]
        processing_speed_level=labels["processing_speed_level"],  # type: ignore[arg-type]
        confidence_score=round(confidence, 2),
        recommendation=recommendation,
        model_version=model_version,
        features=agg_features,
    )

    # Final confirmation log
    print(f"🧠 [COGNITIVE MODEL] Profile generated using: {model_version} for student_id: {student_id}")

    return profile


def model_status() -> dict:
    """Return model loading status and metadata."""
    artifact = _holder.get()
    settings = get_settings()
    if artifact is None:
        return {
            "model_loaded": False,
            "model_path": settings.model_path,
            "error": "Model file not found or failed to load",
        }
    return {
        "model_loaded": True,
        "model_path": settings.model_path,
        "feature_cols": artifact.get("feature_cols"),
        "target_cols": artifact.get("target_cols"),
        "label_classes": artifact.get("label_classes"),
        "dimensions": DIMENSIONS,
    }
