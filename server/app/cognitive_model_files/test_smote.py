import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.model_selection import KFold, cross_val_score
from imblearn.over_sampling import SMOTE
import numpy as np

# Same student aggregation as before...
df = pd.read_csv('cognitive_data_master.csv')
for col in ['topic', 'difficulty', 'error_type', 'label_memory', 'label_attention', 'label_number_sense', 'label_processing_speed']:
    df[col] = df[col].str.strip()
df['is_correct'] = df['is_correct'].astype(int)
df['hint_used']  = df['hint_used'].astype(int)

def build_student_features(df):
    groups = []
    for sid, grp in df.groupby('student_id'):
        row = {'student_id': sid}
        row['avg_response_time']     = grp['response_time_sec'].mean()
        row['med_response_time']     = grp['response_time_sec'].median()
        row['total_attempts']        = grp['attempts'].sum()
        row['correct_rate']          = grp['is_correct'].mean()
        row['hint_rate']             = grp['hint_used'].mean()
        row['avg_click_count']       = grp['click_count'].mean()
        for t in ['label_memory', 'label_attention', 'label_number_sense', 'label_processing_speed']:
            row[t] = grp[t].iloc[0]
        groups.append(row)
    return pd.DataFrame(groups)

student_df = build_student_features(df)
TARGET_COLS = ['label_memory', 'label_attention', 'label_number_sense', 'label_processing_speed']
FEATURE_COLS = [c for c in student_df.columns if c not in ['student_id'] + TARGET_COLS]
X = student_df[FEATURE_COLS]
y = student_df[TARGET_COLS]

# Impute
X = pd.DataFrame(SimpleImputer(strategy='median').fit_transform(X), columns=X.columns)

# Evaluate with Random Forest
model = RandomForestClassifier(n_estimators=200, random_state=42)
kf = KFold(n_splits=5, shuffle=True, random_state=42)

accs = []
for i in range(4):
    y_target = y.iloc[:, i]
    # Evaluate raw
    scores = cross_val_score(model, X, y_target, cv=kf, scoring='accuracy')
    accs.append(scores.mean())
print('Avg Acc Raw:', np.mean(accs))

# SMOTE
smote_accs = []
for i in range(4):
    y_target = y.iloc[:, i]
    try:
        smote = SMOTE(k_neighbors=2, random_state=42)
        X_res, y_res = smote.fit_resample(X, y_target)
        scores = cross_val_score(model, X_res, y_res, cv=kf, scoring='accuracy')
        smote_accs.append(scores.mean())
    except Exception as e:
        print('SMOTE failed for', TARGET_COLS[i], e)
        smote_accs.append(accs[i])
print('Avg Acc SMOTE:', np.mean(smote_accs))
