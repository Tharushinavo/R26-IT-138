# -*- coding: utf-8 -*-
import os, warnings, time
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.ensemble import RandomForestClassifier
from sklearn.multioutput import MultiOutputClassifier
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import LeaveOneOut
from sklearn.metrics import accuracy_score
import joblib

plt.rcParams['figure.dpi'] = 110
sns.set_theme(style='whitegrid', palette='muted')

# =============================================================
# 1. LOAD DATA
# =============================================================
DATA_FILE = 'cognitive_data_master.csv'
df = pd.read_csv(DATA_FILE)

df['is_correct'] = df['is_correct'].astype(int)
df['hint_used']  = df['hint_used'].astype(int)

for col in ['topic', 'difficulty', 'error_type',
            'label_memory', 'label_attention',
            'label_number_sense', 'label_processing_speed']:
    df[col] = df[col].str.strip()

df = df.drop_duplicates().reset_index(drop=True)

# =============================================================
# 2. STUDENT-LEVEL AGGREGATION
# =============================================================
TARGET_COLS = [
    'label_memory', 'label_attention',
    'label_number_sense', 'label_processing_speed'
]

def build_student_features(df: pd.DataFrame) -> pd.DataFrame:
    groups = []
    for sid, grp in df.groupby('student_id'):
        row = {'student_id': sid}
        row['avg_response_time']     = grp['response_time_sec'].mean()
        row['med_response_time']     = grp['response_time_sec'].median()
        row['max_response_time']     = grp['response_time_sec'].max()
        row['min_response_time']     = grp['response_time_sec'].min()
        row['avg_attempts']          = grp['attempts'].mean()
        row['max_attempts']          = grp['attempts'].max()
        row['total_attempts']        = grp['attempts'].sum()
        row['correct_rate']          = grp['is_correct'].mean()
        row['total_correct']         = grp['is_correct'].sum()
        row['hint_rate']             = grp['hint_used'].mean()
        row['avg_click_count']       = grp['click_count'].mean()
        row['avg_session_time']      = grp['session_time_sec'].mean()
        row['avg_time_between']      = grp['time_between_actions'].mean()

        for diff in ['Easy', 'Medium', 'Hard']:
            sub = grp[grp['difficulty'] == diff]
            row[f'correct_rate_{diff.lower()}'] = sub['is_correct'].mean() if len(sub) > 0 else 0.0
            row[f'avg_attempts_{diff.lower()}'] = sub['attempts'].mean()   if len(sub) > 0 else 0.0

        for topic in ['Counting', 'Addition', 'Subtraction', 'Number Comparison', 'Division']:
            sub = grp[grp['topic'] == topic]
            tkey = topic.lower().replace(' ', '_')
            row[f'correct_rate_{tkey}'] = sub['is_correct'].mean() if len(sub) > 0 else 0.0

        n = len(grp)
        for etype in ['none', 'calculation', 'conceptual', 'careless', 'unknown']:
            row[f'error_{etype}_rate'] = (grp['error_type'] == etype).sum() / n

        row['response_time_std'] = grp['response_time_sec'].std()
        row['n_questions'] = len(grp)

        for t in TARGET_COLS:
            row[t] = grp[t].iloc[0]
        groups.append(row)
    return pd.DataFrame(groups)

student_df = build_student_features(df)
student_df['response_time_std'] = student_df['response_time_std'].fillna(0)

FEATURE_COLS = [c for c in student_df.columns if c not in ['student_id'] + TARGET_COLS]
X = student_df[FEATURE_COLS].copy()
y = student_df[TARGET_COLS].copy()

# =============================================================
# 3. PIPELINE WITH RANDOM FOREST
# =============================================================
preprocessor = ColumnTransformer(transformers=[
    ('num', SimpleImputer(strategy='median'), FEATURE_COLS)
], remainder='drop')

# Best parameters typically for such datasets
rf_base = RandomForestClassifier(
    n_estimators=300,
    max_depth=7,
    min_samples_split=3,
    min_samples_leaf=1,
    class_weight='balanced',
    random_state=42,
    n_jobs=-1
)

multi_clf = MultiOutputClassifier(rf_base, n_jobs=-1)

model_pipeline = Pipeline([
    ('preprocessor', preprocessor),
    ('classifier',   multi_clf)
])

# =============================================================
# 4. LOOCV EVALUATION (Best for n=63)
# =============================================================
print("Running Leave-One-Out Cross Validation (LOOCV) for optimal evaluation on 63 rows...")
loo = LeaveOneOut()

per_label_correct = {target: 0 for target in TARGET_COLS}
exact_matches = 0

for train_idx, test_idx in loo.split(X):
    X_tr, X_te = X.iloc[train_idx], X.iloc[test_idx]
    y_tr, y_te = y.iloc[train_idx], y.iloc[test_idx]
    
    model_pipeline.fit(X_tr, y_tr)
    y_pr = model_pipeline.predict(X_te)[0]  # Only 1 test sample
    
    all_correct = True
    for i, target in enumerate(TARGET_COLS):
        if y_te.iloc[0, i] == y_pr[i]:
            per_label_correct[target] += 1
        else:
            all_correct = False
            
    if all_correct:
        exact_matches += 1

n_samples = len(X)
per_label_acc = {k: v / n_samples for k, v in per_label_correct.items()}
final_acc = np.mean(list(per_label_acc.values()))
exact_acc = exact_matches / n_samples

print("="*60)
print("  ✅ FINAL MODEL TRAINING COMPLETE (Random Forest + LOOCV)")
print("="*60)
print(f"  Average Per-Label Accuracy : {final_acc*100:.1f}%")
for t in TARGET_COLS:
    print(f"    {t:<25}: {per_label_acc[t]*100:.1f}%")
print(f"  Exact Match Accuracy       : {exact_acc*100:.1f}%")
print("="*60)

# =============================================================
# 5. TRAIN ON FULL DATASET AND SAVE
# =============================================================
model_pipeline.fit(X, y)

MODEL_FILE = 'cognitive_model.pkl'
label_classes = {}
for i, target in enumerate(TARGET_COLS):
    label_classes[target] = list(model_pipeline.named_steps['classifier'].estimators_[i].classes_)

artifact = {
    'model'         : model_pipeline,
    'feature_cols'  : FEATURE_COLS,
    'target_cols'   : TARGET_COLS,
    'label_classes' : label_classes,
    'model_version' : 'v4_random_forest_student_level',
    'avg_accuracy'  : round(final_acc, 4),
    'aggregation'   : 'student_level'
}

joblib.dump(artifact, MODEL_FILE)
print(f"✅ Model saved to {MODEL_FILE}")
