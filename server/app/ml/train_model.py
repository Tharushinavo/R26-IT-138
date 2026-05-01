"""Train a Decision Tree multi-output classifier for cognitive skill profiling.

Usage (from the server/ directory):
    python -m app.ml.train_model

Reads: data/cognitive_dataset.csv
Saves: app/ml/cognitive_model.pkl  +  app/ml/model_columns.json
"""
from __future__ import annotations

import json
import os
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.multioutput import MultiOutputClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.tree import DecisionTreeClassifier

# ── Paths ──
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PATH = os.path.join(BASE_DIR, "data", "cognitive_dataset.csv")
MODEL_PATH = os.path.join(BASE_DIR, "app", "ml", "cognitive_model.pkl")
COLUMNS_PATH = os.path.join(BASE_DIR, "app", "ml", "model_columns.json")

# ── Feature and target columns ──
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
    print(f"Loading dataset from: {DATA_PATH}")
    if not os.path.isfile(DATA_PATH):
        print(f"ERROR: Dataset not found at {DATA_PATH}")
        sys.exit(1)

    df = pd.read_csv(DATA_PATH)
    print(f"Dataset shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")

    # ── Clean data ──
    # Drop identifier columns (not useful for training)
    drop_cols = ["student_id", "question_id"]
    df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")

    # Handle missing values
    df["error_type"] = df["error_type"].fillna("none")
    df["hint_used"] = df["hint_used"].map(
        lambda x: True if str(x).lower() in ("true", "1", "yes") else False
    )
    df["is_correct"] = df["is_correct"].map(
        lambda x: True if str(x).lower() in ("true", "1", "yes") else False
    )

    # ── Encode categorical features ──
    label_encoders = {}
    categorical_cols = ["topic", "difficulty", "error_type"]

    for col in categorical_cols:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))
        label_encoders[col] = le
        print(f"  Encoded '{col}': {list(le.classes_)}")

    # Convert boolean to int
    df["is_correct"] = df["is_correct"].astype(int)
    df["hint_used"] = df["hint_used"].astype(int)

    # ── Separate X and y ──
    X = df[INPUT_FEATURES].values
    y = df[TARGET_LABELS].values

    print(f"\nFeature matrix shape: {X.shape}")
    print(f"Target matrix shape:  {y.shape}")
    print(f"Target label distribution:")
    for i, label in enumerate(TARGET_LABELS):
        unique, counts = np.unique(y[:, i], return_counts=True)
        dist = dict(zip(unique, counts))
        print(f"  {label}: {dist}")

    # ── Train/test split ──
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    print(f"\nTrain size: {X_train.shape[0]}, Test size: {X_test.shape[0]}")

    # ── Train model ──
    print("\nTraining MultiOutputClassifier(DecisionTreeClassifier)...")
    base_clf = DecisionTreeClassifier(
        max_depth=8,
        min_samples_split=3,
        min_samples_leaf=2,
        random_state=42,
    )
    model = MultiOutputClassifier(base_clf)
    model.fit(X_train, y_train)

    # ── Evaluate ──
    train_score = model.score(X_train, y_train)
    test_score = model.score(X_test, y_test)
    print(f"\nTraining accuracy (exact match): {train_score:.4f}")
    print(f"Testing accuracy (exact match):  {test_score:.4f}")

    y_pred = model.predict(X_test)
    print("\nPer-label accuracy:")
    for i, label in enumerate(TARGET_LABELS):
        acc = np.mean(y_pred[:, i] == y_test[:, i])
        print(f"  {label}: {acc:.4f}")

    # ── Save model ──
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"\nModel saved to: {MODEL_PATH}")

    # Save column metadata
    columns_meta = {
        "input_features": INPUT_FEATURES,
        "target_labels": TARGET_LABELS,
        "categorical_encoders": {
            col: list(le.classes_) for col, le in label_encoders.items()
        },
    }
    with open(COLUMNS_PATH, "w") as f:
        json.dump(columns_meta, f, indent=2)
    print(f"Column metadata saved to: {COLUMNS_PATH}")

    print("\n✅ Training complete!")


if __name__ == "__main__":
    main()
