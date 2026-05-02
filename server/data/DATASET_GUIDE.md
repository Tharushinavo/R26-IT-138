# Synthetic Dataset Guide — Google Colab Training

This guide explains the exact CSV columns and generation rules needed to create
a large synthetic dataset for training the Cognitive Skill Profiling Decision Tree model.

---

## CSV Column Names (16 columns total)

```csv
student_id,question_id,topic,difficulty,response_time_sec,attempts,is_correct,hint_used,click_count,session_time_sec,time_between_actions,error_type,label_memory,label_attention,label_number_sense,label_processing_speed
```

### Column Details

| # | Column | Type | Role | Description | Valid Values |
|---|--------|------|------|-------------|--------------|
| 1 | `student_id` | string | ID (dropped) | Anonymous student code | S001 – S200 |
| 2 | `question_id` | string | ID (dropped) | Question identifier | Q001 – Q050 |
| 3 | `topic` | string | **Feature** | Mathematics topic | `Addition`, `Subtraction`, `Counting`, `Number Comparison` |
| 4 | `difficulty` | string | **Feature** | Question difficulty | `Easy`, `Medium`, `Hard` |
| 5 | `response_time_sec` | float | **Feature** | Seconds taken to answer | 3.0 – 45.0 |
| 6 | `attempts` | int | **Feature** | Number of attempts (≥1) | 1, 2, 3, 4, 5 |
| 7 | `is_correct` | boolean | **Feature** | Was the final answer correct? | `true`, `false` |
| 8 | `hint_used` | boolean | **Feature** | Did the student use a hint? | `true`, `false` |
| 9 | `click_count` | int | **Feature** | Taps/clicks during question | 1 – 25 |
| 10 | `session_time_sec` | float | **Feature** | Total session duration so far | 20 – 300 |
| 11 | `time_between_actions` | float | **Feature** | Avg delay between actions (sec) | 0.5 – 8.0 |
| 12 | `error_type` | string | **Feature** | Type of mistake made | `none`, `calculation`, `conceptual`, `careless`, `unknown` |
| 13 | `label_memory` | string | **Target** | Memory performance level | `Low`, `Medium`, `High` |
| 14 | `label_attention` | string | **Target** | Attention level | `Low`, `Medium`, `High` |
| 15 | `label_number_sense` | string | **Target** | Number sense level | `Low`, `Medium`, `High` |
| 16 | `label_processing_speed` | string | **Target** | Processing speed level | `Slow`, `Moderate`, `Fast` |

> **Important**: `student_id` and `question_id` are for traceability only.
> They are **dropped before training** — they are not ML features.
> The 10 actual training features are columns 3–12.

---

## Recommended Dataset Size

| Item | Target |
|------|--------|
| Total rows | 3,000 – 5,000 |
| Unique students | 150 – 200 |
| Interactions per student | 15 – 30 |
| Topics | 4 (Addition, Subtraction, Counting, Number Comparison) |
| Difficulties | 3 (Easy, Medium, Hard) |

---

## Synthetic Generation Rules

Assign each student a **cognitive profile type**, then generate their interaction
data to match that profile realistically.

### Profile A: High Performer (labels: High / High / High / Fast)
~30% of students

| Feature | Range |
|---------|-------|
| response_time_sec | 3 – 8 sec |
| attempts | 1 (rarely 2) |
| is_correct | true ~90%+ |
| hint_used | false ~90%+ |
| click_count | 1 – 5 |
| session_time_sec | 20 – 70 |
| time_between_actions | 0.5 – 1.5 sec |
| error_type | `none` ~90%, `careless` ~10% |

### Profile B: Medium Performer (labels: Medium / Medium / Medium / Moderate)
~40% of students

| Feature | Range |
|---------|-------|
| response_time_sec | 8 – 18 sec |
| attempts | 1 – 2 |
| is_correct | true ~50–75% |
| hint_used | mixed (~30–50%) |
| click_count | 4 – 10 |
| session_time_sec | 50 – 150 |
| time_between_actions | 1.5 – 3.0 sec |
| error_type | `none` ~40%, `calculation` ~40%, `careless` ~20% |

### Profile C: Low Performer (labels: Low / Low / Low / Slow)
~20% of students

| Feature | Range |
|---------|-------|
| response_time_sec | 15 – 40 sec |
| attempts | 2 – 5 |
| is_correct | false ~60%+ |
| hint_used | true ~70%+ |
| click_count | 8 – 25 |
| session_time_sec | 100 – 300 |
| time_between_actions | 3.0 – 8.0 sec |
| error_type | `conceptual` ~50%, `calculation` ~30%, `unknown` ~20% |

### Profile D: Mixed / Cross-dimension (~10–15% of students)
These students have different levels across dimensions. Examples:

| Variation | Memory | Attention | Number Sense | Speed |
|-----------|--------|-----------|--------------|-------|
| Good memory, poor attention | High | Low | Medium | Moderate |
| Fast but inaccurate | Medium | Low | Low | Fast |
| Slow but accurate | High | High | High | Slow |
| Weak number sense only | High | Medium | Low | Moderate |

Generate their features as a mix between the relevant profile ranges.
For example, "Good memory, poor attention":
- Low attempts + few retries (good memory)
- High click_count + high time_between_actions (poor attention)
- Mixed accuracy (medium number sense)
- Medium response time (moderate speed)

---

## Colab Workflow Steps

```python
# Step 1: Generate synthetic data
import numpy as np
import pandas as pd

# ... generation logic using rules above ...
df.to_csv('cognitive_dataset_large.csv', index=False)

# Step 2: Load and prepare
df = pd.read_csv('cognitive_dataset_large.csv')
df = df.drop(columns=['student_id', 'question_id'])

# Step 3: Encode categoricals
from sklearn.preprocessing import LabelEncoder
for col in ['topic', 'difficulty', 'error_type']:
    le = LabelEncoder()
    df[col] = le.fit_transform(df[col])

# Step 4: Convert booleans
df['is_correct'] = df['is_correct'].map(lambda x: 1 if str(x).lower() in ('true','1') else 0)
df['hint_used'] = df['hint_used'].map(lambda x: 1 if str(x).lower() in ('true','1') else 0)

# Step 5: Split features and targets
INPUT_FEATURES = ['topic','difficulty','response_time_sec','attempts','is_correct',
                  'hint_used','click_count','session_time_sec','time_between_actions','error_type']
TARGET_LABELS = ['label_memory','label_attention','label_number_sense','label_processing_speed']

X = df[INPUT_FEATURES].values
y = df[TARGET_LABELS].values

# Step 6: Train/test split
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Step 7: Train model
from sklearn.tree import DecisionTreeClassifier
from sklearn.multioutput import MultiOutputClassifier

model = MultiOutputClassifier(DecisionTreeClassifier(max_depth=8, min_samples_split=3, min_samples_leaf=2, random_state=42))
model.fit(X_train, y_train)

# Step 8: Evaluate
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import numpy as np

train_acc = model.score(X_train, y_train)
test_acc = model.score(X_test, y_test)
print(f"Training exact match accuracy: {train_acc:.4f}")
print(f"Testing exact match accuracy:  {test_acc:.4f}")

y_pred = model.predict(X_test)
for i, label in enumerate(TARGET_LABELS):
    print(f"\n--- {label} ---")
    print(classification_report(y_test[:, i], y_pred[:, i]))
    print("Confusion Matrix:")
    print(confusion_matrix(y_test[:, i], y_pred[:, i]))

# Step 9: Save model
import joblib
joblib.dump(model, 'cognitive_model.pkl')
print("Model saved as cognitive_model.pkl")

# Step 10: Download .pkl file
# Then place it at: server/app/ml/cognitive_model.pkl
```

---

## After Training

1. Download `cognitive_model.pkl` from Colab
2. Replace `server/app/ml/cognitive_model.pkl` with the new file
3. Restart the backend: `python run.py`
4. The server will automatically load the new model
5. Test via Swagger UI: `POST /profiles/predict`
