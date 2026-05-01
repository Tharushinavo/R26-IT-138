"""Evaluate the trained Decision Tree model for cognitive skill profiling.

Usage (from the server/ directory):
    python -m app.ml.evaluate_model

Reads: app/ml/cognitive_model.pkl  +  data/cognitive_dataset.csv
Outputs: Evaluation metrics (accuracy, precision, recall, F1, confusion matrix)
"""
from __future__ import annotations

import os
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PATH = os.path.join(BASE_DIR, "data", "cognitive_dataset.csv")
MODEL_PATH = os.path.join(BASE_DIR, "app", "ml", "cognitive_model.pkl")

INPUT_FEATURES = [
    "topic", "difficulty", "response_time_sec", "attempts",
    "is_correct", "hint_used", "click_count", "session_time_sec",
    "time_between_actions", "error_type",
]

TARGET_LABELS = [
    "label_memory", "label_attention",
    "label_number_sense", "label_processing_speed",
]


def main() -> None:
    if not os.path.isfile(MODEL_PATH):
        print(f"ERROR: Model not found at {MODEL_PATH}")
        print("Run `python -m app.ml.train_model` first.")
        sys.exit(1)

    if not os.path.isfile(DATA_PATH):
        print(f"ERROR: Dataset not found at {DATA_PATH}")
        sys.exit(1)

    print("Loading model and dataset...")
    model = joblib.load(MODEL_PATH)
    df = pd.read_csv(DATA_PATH)

    # Preprocess same as training
    drop_cols = ["student_id", "question_id"]
    df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")
    df["error_type"] = df["error_type"].fillna("none")
    df["hint_used"] = df["hint_used"].map(
        lambda x: True if str(x).lower() in ("true", "1", "yes") else False
    )
    df["is_correct"] = df["is_correct"].map(
        lambda x: True if str(x).lower() in ("true", "1", "yes") else False
    )

    categorical_cols = ["topic", "difficulty", "error_type"]
    for col in categorical_cols:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))

    df["is_correct"] = df["is_correct"].astype(int)
    df["hint_used"] = df["hint_used"].astype(int)

    X = df[INPUT_FEATURES].values
    y = df[TARGET_LABELS].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Predictions
    y_pred_train = model.predict(X_train)
    y_pred_test = model.predict(X_test)

    print("=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)

    # Exact match accuracy
    train_exact = np.mean(np.all(y_pred_train == y_train, axis=1))
    test_exact = np.mean(np.all(y_pred_test == y_test, axis=1))
    print(f"\nExact Match Accuracy (all 4 labels correct):")
    print(f"  Training: {train_exact:.4f}")
    print(f"  Testing:  {test_exact:.4f}")

    # Per-label evaluation
    for i, label in enumerate(TARGET_LABELS):
        print(f"\n{'─' * 40}")
        print(f"Label: {label}")
        print(f"{'─' * 40}")

        y_true = y_test[:, i]
        y_pred = y_pred_test[:, i]

        acc = accuracy_score(y_true, y_pred)
        print(f"Accuracy: {acc:.4f}")

        unique_labels = sorted(set(list(y_true) + list(y_pred)))
        print(f"\nClassification Report:")
        print(classification_report(y_true, y_pred, labels=unique_labels, zero_division=0))

        print(f"Confusion Matrix:")
        cm = confusion_matrix(y_true, y_pred, labels=unique_labels)
        print(f"Labels: {unique_labels}")
        print(cm)

    print(f"\n{'=' * 60}")
    print("Evaluation complete.")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
