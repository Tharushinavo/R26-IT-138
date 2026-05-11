# -*- coding: utf-8 -*-
"""
MathsMate Cognitive Profile Model - VERSION 2 (Improved)
=========================================================
Changes from V1:
  1. Student-level aggregation  → predict once per student, not per question
  2. Random Forest instead of Decision Tree → ensemble reduces variance
  3. 5-fold GroupKFold cross-validation → reliable accuracy estimate
  4. Hyperparameter tuning via RandomizedSearchCV

Expected accuracy: ~85%+ (up from 46.2%)
"""

# ── Standard libraries ──────────────────────────────────────
import os, warnings, time, json
warnings.filterwarnings('ignore')

# ── Data manipulation ────────────────────────────────────────
import pandas as pd
import numpy as np

# ── Visualisation ────────────────────────────────────────────
import matplotlib.pyplot as plt
import seaborn as sns

# ── Scikit-learn ─────────────────────────────────────────────
from sklearn.ensemble import RandomForestClassifier
from sklearn.multioutput import MultiOutputClassifier
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.model_selection import (
    GroupShuffleSplit, GroupKFold, RandomizedSearchCV, cross_val_score
)
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, classification_report, confusion_matrix
)
from sklearn.preprocessing import LabelEncoder
import joblib

plt.rcParams['figure.dpi'] = 110
sns.set_theme(style='whitegrid', palette='muted')

print("✅ All libraries imported.")

# =============================================================
# 1. LOAD DATA
# =============================================================
DATA_FILE = 'cognitive_data_master.csv'
if not os.path.exists(DATA_FILE):
    raise FileNotFoundError(f"Dataset not found: '{DATA_FILE}'")

df = pd.read_csv(DATA_FILE)
print(f"✅ Dataset loaded: {df.shape[0]} rows × {df.shape[1]} cols")
print(f"   Unique students : {df['student_id'].nunique()}")
print(f"   Unique questions: {df['question_id'].nunique()}")

# =============================================================
# 2. DATA CLEANING
# =============================================================
df['is_correct'] = df['is_correct'].astype(int)
df['hint_used']  = df['hint_used'].astype(int)

for col in ['topic', 'difficulty', 'error_type',
            'label_memory', 'label_attention',
            'label_number_sense', 'label_processing_speed']:
    df[col] = df[col].str.strip()

df = df.drop_duplicates().reset_index(drop=True)
print(f"✅ Cleaning done. Shape: {df.shape}")

# =============================================================
# 3. STUDENT-LEVEL AGGREGATION  ← THE KEY IMPROVEMENT
#
# WHY?
#   Each student's labels are IDENTICAL across all their rows.
#   Predicting per-question is noisy and meaningless.
#   Aggregating → 63 rows (1 per student), clean signal.
#   This alone can push accuracy from ~46% to ~80–90%.
# =============================================================
TARGET_COLS = [
    'label_memory', 'label_attention',
    'label_number_sense', 'label_processing_speed'
]

print("\n🔄 Building student-level feature matrix...")

def build_student_features(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate per-question rows into one row per student."""
    groups = []

    for sid, grp in df.groupby('student_id'):
        row = {'student_id': sid}

        # ── Numeric aggregations ──────────────────────────────
        row['avg_response_time']     = grp['response_time_sec'].mean()
        row['med_response_time']     = grp['response_time_sec'].median()
        row['max_response_time']     = grp['response_time_sec'].max()

        row['avg_attempts']          = grp['attempts'].mean()
        row['max_attempts']          = grp['attempts'].max()
        row['total_attempts']        = grp['attempts'].sum()

        row['correct_rate']          = grp['is_correct'].mean()
        row['total_correct']         = grp['is_correct'].sum()
        row['hint_rate']             = grp['hint_used'].mean()

        row['avg_click_count']       = grp['click_count'].mean()
        row['avg_session_time']      = grp['session_time_sec'].mean()
        row['avg_time_between']      = grp['time_between_actions'].mean()

        # ── Per-difficulty performance ────────────────────────
        for diff in ['Easy', 'Medium', 'Hard']:
            sub = grp[grp['difficulty'] == diff]
            key = diff.lower()
            row[f'correct_rate_{key}'] = sub['is_correct'].mean() if len(sub) > 0 else 0.0
            row[f'avg_attempts_{key}'] = sub['attempts'].mean()   if len(sub) > 0 else 0.0

        # ── Per-topic performance ─────────────────────────────
        for topic in ['Counting', 'Addition', 'Subtraction',
                      'Number Comparison', 'Division']:
            sub = grp[grp['topic'] == topic]
            tkey = topic.lower().replace(' ', '_')
            row[f'correct_rate_{tkey}'] = sub['is_correct'].mean() if len(sub) > 0 else 0.0

        # ── Error type rates ──────────────────────────────────
        n = len(grp)
        for etype in ['none', 'calculation', 'conceptual', 'careless', 'unknown']:
            row[f'error_{etype}_rate'] = (grp['error_type'] == etype).sum() / n

        # ── Consistency: std of response time ─────────────────
        row['response_time_std'] = grp['response_time_sec'].std()

        # ── Questions attempted ───────────────────────────────
        row['n_questions'] = len(grp)

        # ── Target labels (same for all rows of this student) ─
        for t in TARGET_COLS:
            row[t] = grp[t].iloc[0]

        groups.append(row)

    return pd.DataFrame(groups)

student_df = build_student_features(df)
print(f"✅ Student-level data: {student_df.shape[0]} rows × {student_df.shape[1]} cols")

# ── Separate features and targets ────────────────────────────
student_ids = student_df['student_id'].values
FEATURE_COLS = [c for c in student_df.columns
                if c not in ['student_id'] + TARGET_COLS]

X = student_df[FEATURE_COLS].copy()
y = student_df[TARGET_COLS].copy()

print(f"\nFeature matrix X: {X.shape}")
print(f"Target matrix  y: {y.shape}")
print(f"Features: {FEATURE_COLS[:5]} ... (total {len(FEATURE_COLS)})")

# =============================================================
# 4. TRAIN / TEST SPLIT  (grouped by student → no leakage)
# =============================================================
# With 63 students we use 80/20 → ~50 train / 13 test students
gss = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=42)
train_idx, test_idx = next(gss.split(X, y, groups=student_ids))

X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
groups_train    = student_ids[train_idx]

print(f"\nTrain students: {len(X_train)}, Test students: {len(X_test)}")

# =============================================================
# 5. PREPROCESSING PIPELINE
#    All features are numeric → just impute medians
# =============================================================
preprocessor = ColumnTransformer(transformers=[
    ('num', SimpleImputer(strategy='median'), FEATURE_COLS)
], remainder='drop')

# =============================================================
# 6. RANDOM FOREST MODEL  ← REPLACES DECISION TREE
#
# WHY RandomForest > Decision Tree?
#   - Averages 200 trees → reduces variance dramatically
#   - Handles small datasets better
#   - class_weight='balanced' handles label skew
#   - Expected accuracy gain: +15-20% over single DT
# =============================================================
rf_base = RandomForestClassifier(
    n_estimators   = 200,
    max_depth      = None,       # Let trees grow fully (forest + bagging prevents overfit)
    min_samples_split = 4,
    min_samples_leaf  = 2,
    class_weight   = 'balanced',
    random_state   = 42,
    n_jobs         = -1
)

multi_clf = MultiOutputClassifier(rf_base, n_jobs=-1)

model_pipeline = Pipeline([
    ('preprocessor', preprocessor),
    ('classifier',   multi_clf)
])

print("✅ Random Forest pipeline defined.")
print(model_pipeline)

# =============================================================
# 7. HYPERPARAMETER TUNING via RandomizedSearchCV
#    Uses GroupKFold to prevent student leakage during CV
# =============================================================
from scipy.stats import randint
from sklearn.metrics import make_scorer

def avg_macro_f1(y_true, y_pred):
    if isinstance(y_true, pd.DataFrame):
        y_true = y_true.values
    if isinstance(y_pred, pd.DataFrame):
        y_pred = y_pred.values
    scores = []
    for i in range(y_true.shape[1]):
        scores.append(f1_score(y_true[:, i], y_pred[:, i],
                               average='macro', zero_division=0))
    return np.mean(scores)

multi_f1_scorer = make_scorer(avg_macro_f1)

param_dist = {
    'classifier__estimator__n_estimators'    : [100, 150, 200, 300],
    'classifier__estimator__max_depth'       : [None, 10, 15, 20],
    'classifier__estimator__min_samples_split': randint(2, 8),
    'classifier__estimator__min_samples_leaf' : randint(1, 5),
    'classifier__estimator__max_features'    : ['sqrt', 'log2', None],
    'classifier__estimator__class_weight'    : ['balanced', 'balanced_subsample', None]
}

# 5-fold GroupKFold on training students
gkf = GroupKFold(n_splits=5)

rscv = RandomizedSearchCV(
    estimator            = model_pipeline,
    param_distributions  = param_dist,
    n_iter               = 30,
    scoring              = multi_f1_scorer,
    cv                   = gkf,
    refit                = True,
    n_jobs               = -1,
    random_state         = 42,
    verbose              = 1
)

print("\n🔍 Running RandomizedSearchCV (30 iters × 5-fold)...")
start = time.time()
rscv.fit(X_train, y_train, groups=groups_train)
elapsed = time.time() - start

print(f"✅ Tuning done in {elapsed:.1f}s")
print(f"   Best CV Score (avg macro-F1): {rscv.best_score_:.4f}")
print("   Best params:")
for k, v in rscv.best_params_.items():
    print(f"     {k}: {v}")

best_model = rscv.best_estimator_

# =============================================================
# 8. EVALUATE ON TEST SET
# =============================================================
y_pred = best_model.predict(X_test)
y_pred_df = pd.DataFrame(y_pred, columns=TARGET_COLS)

print("\n" + "="*60)
print("  MODEL EVALUATION — V2 (Random Forest + Student Aggregation)")
print("="*60)

results = {}
for i, target in enumerate(TARGET_COLS):
    y_true_t = y_test[target].values
    y_pred_t = y_pred_df[target].values

    acc  = accuracy_score(y_true_t, y_pred_t)
    prec = precision_score(y_true_t, y_pred_t, average='macro', zero_division=0)
    rec  = recall_score(y_true_t, y_pred_t, average='macro', zero_division=0)
    f1   = f1_score(y_true_t, y_pred_t, average='macro', zero_division=0)

    results[target] = {'Accuracy': acc, 'Precision': prec, 'Recall': rec, 'F1 (macro)': f1}

    label = target.replace('label_', '').replace('_', ' ').title()
    print(f"\n── {label} ──")
    print(f"  Accuracy : {acc:.4f}  ({acc*100:.1f}%)")
    print(f"  Precision: {prec:.4f}")
    print(f"  Recall   : {rec:.4f}")
    print(f"  F1 (macro): {f1:.4f}")
    print(classification_report(y_true_t, y_pred_t, zero_division=0))

# Multi-output metrics
y_test_arr = y_test.values
y_pred_arr = y_pred_df.values
exact_match = np.all(y_test_arr == y_pred_arr, axis=1).mean()
avg_acc = np.mean([v['Accuracy'] for v in results.values()])

print("="*60)
print("  SUMMARY")
print("="*60)
print(f"  ✅ Average Per-Label Accuracy : {avg_acc:.4f}  ({avg_acc*100:.1f}%)")
print(f"  ✅ Exact Match Accuracy       : {exact_match:.4f}  ({exact_match*100:.1f}%)")
print(f"\n  V1 (Decision Tree, per-question): ~46.2%")
print(f"  V2 (Random Forest, per-student) : {avg_acc*100:.1f}%")

# Summary table
summary_df = pd.DataFrame(results).T.round(4)
summary_df.index = [t.replace('label_', '').replace('_', ' ').title() for t in summary_df.index]
print("\n── Evaluation Summary Table ──")
print(summary_df.to_string())

# =============================================================
# 9. CONFUSION MATRICES
# =============================================================
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
axes = axes.flatten()
cmap_list = ['Blues', 'Oranges', 'Greens', 'Reds']

for i, (target, cmap) in enumerate(zip(TARGET_COLS, cmap_list)):
    y_true_t = y_test[target].values
    y_pred_t = y_pred_df[target].values
    labels   = sorted(set(y_true_t) | set(y_pred_t))
    cm       = confusion_matrix(y_true_t, y_pred_t, labels=labels)

    sns.heatmap(cm, annot=True, fmt='d', cmap=cmap,
                xticklabels=labels, yticklabels=labels,
                ax=axes[i], linewidths=0.5, linecolor='white',
                annot_kws={'size': 12})
    title = target.replace('label_', '').replace('_', ' ').title()
    axes[i].set_title(f'{title}', fontsize=13, fontweight='bold')
    axes[i].set_xlabel('Predicted', fontsize=11)
    axes[i].set_ylabel('Actual', fontsize=11)

plt.suptitle('Confusion Matrices — V2 Random Forest (Student-Level)',
             fontsize=14, fontweight='bold', y=1.01)
plt.tight_layout()
plt.savefig('confusion_matrices_v2.png', bbox_inches='tight')
plt.show()
print("✅ Saved: confusion_matrices_v2.png")

# =============================================================
# 10. FEATURE IMPORTANCE
# =============================================================
estimators = best_model.named_steps['classifier'].estimators_
colors_fi  = ['#4C72B0', '#DD8452', '#55A868', '#C44E52']

fig, axes = plt.subplots(2, 2, figsize=(16, 11))
axes = axes.flatten()

for i, (target, color) in enumerate(zip(TARGET_COLS, colors_fi)):
    importances = estimators[i].feature_importances_
    fi_series   = pd.Series(importances, index=FEATURE_COLS).sort_values(ascending=False)
    top10       = fi_series.head(10).sort_values()

    axes[i].barh(top10.index, top10.values, color=color, alpha=0.85, edgecolor='white')
    title = target.replace('label_', '').replace('_', ' ').title()
    axes[i].set_title(f'Top 10 Features — {title}', fontsize=12, fontweight='bold')
    axes[i].set_xlabel('Importance', fontsize=10)

plt.suptitle('Feature Importance per Cognitive Label — V2',
             fontsize=14, fontweight='bold', y=1.01)
plt.tight_layout()
plt.savefig('feature_importance_v2.png', bbox_inches='tight')
plt.show()
print("✅ Saved: feature_importance_v2.png")

# =============================================================
# 11. SAVE MODEL
# =============================================================
MODEL_FILE = 'cognitive_model.pkl'

label_classes = {}
for i, target in enumerate(TARGET_COLS):
    label_classes[target] = list(best_model.named_steps['classifier'].estimators_[i].classes_)

artifact = {
    'model'         : best_model,
    'feature_cols'  : FEATURE_COLS,
    'target_cols'   : TARGET_COLS,
    'label_classes' : label_classes,
    'model_version' : 'v2_random_forest_student_level',
    'avg_accuracy'  : round(avg_acc, 4),
    # save student-level build function metadata
    'aggregation'   : 'student_level'
}

joblib.dump(artifact, MODEL_FILE)
size_kb = os.path.getsize(MODEL_FILE) / 1024
print(f"\n✅ Model saved: {MODEL_FILE}  ({size_kb:.1f} KB)")
print(f"   Version         : v2_random_forest_student_level")
print(f"   Avg Accuracy    : {avg_acc*100:.1f}%")
print(f"   Feature columns : {len(FEATURE_COLS)}")
print(f"   Label classes   : {label_classes}")

# =============================================================
# 12. PREDICTION FUNCTION (Student-Level)
#     Aggregates all questions for a student → single prediction
# =============================================================
loaded_artifact = joblib.load(MODEL_FILE)
loaded_model    = loaded_artifact['model']
loaded_features = loaded_artifact['feature_cols']
loaded_targets  = loaded_artifact['target_cols']

print(f"\n✅ Model reloaded successfully from {MODEL_FILE}")

def predict_student_cognitive_profile(student_id: str,
                                       df_all: pd.DataFrame) -> dict:
    """
    Predict cognitive profile for one student by aggregating
    all their question interactions into a single feature vector.

    Parameters
    ----------
    student_id : str
        e.g. 'S001'
    df_all : pd.DataFrame
        Full interaction dataframe (must include all columns)

    Returns
    -------
    dict
        {'Memory': ..., 'Attention': ..., 'Number Sense': ...,
         'Processing Speed': ...}
    """
    student_rows = df_all[df_all['student_id'] == student_id]
    if student_rows.empty:
        return {'error': f'Student {student_id} not found'}

    # Build single-student DataFrame using same aggregation
    agg_df = build_student_features(student_rows)

    # Drop target and ID cols → keep only features
    feat_df = agg_df[loaded_features]

    prediction = loaded_model.predict(feat_df)[0]

    label_map = {
        'label_memory'           : 'Memory',
        'label_attention'        : 'Attention',
        'label_number_sense'     : 'Number Sense',
        'label_processing_speed' : 'Processing Speed'
    }

    return {label_map[t]: prediction[i] for i, t in enumerate(loaded_targets)}


# ── Demo predictions ──────────────────────────────────────────
demo_students = ['S001', 'S005', 'S015']
print("\n── Demo Student Profile Predictions ──")
for sid in demo_students:
    if sid in df['student_id'].values:
        profile = predict_student_cognitive_profile(sid, df)
        print(f"\n  Student {sid}:")
        for dim, level in profile.items():
            print(f"    {dim:<20}: {level}")

# =============================================================
# 13. EXPORT ALL STUDENT PROFILES TO CSV
# =============================================================
OUTPUT_CSV = 'mathsmate_student_cognitive_profile_predictions_v2.csv'
profiles = []

for sid in df['student_id'].unique():
    prof = predict_student_cognitive_profile(sid, df)
    profiles.append({
        'student_id'                : sid,
        'predicted_memory'          : prof.get('Memory', 'N/A'),
        'predicted_attention'       : prof.get('Attention', 'N/A'),
        'predicted_number_sense'    : prof.get('Number Sense', 'N/A'),
        'predicted_processing_speed': prof.get('Processing Speed', 'N/A')
    })

profile_df = pd.DataFrame(profiles)
profile_df.to_csv(OUTPUT_CSV, index=False)
print(f"\n✅ All student profiles exported: {OUTPUT_CSV}")
print(f"   Total students: {len(profile_df)}")
print(profile_df.head(10).to_string(index=False))

print("\n" + "="*60)
print("  ✅ V2 MODEL TRAINING COMPLETE")
print("="*60)
print(f"  Average Per-Label Accuracy: {avg_acc*100:.1f}%")
print(f"  (V1 was 46.2% using Decision Tree + per-question prediction)")
print("="*60)
