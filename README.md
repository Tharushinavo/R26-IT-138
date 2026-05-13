# EduInsight — Learning Insight & Early Warning System

An AI-powered learning analytics platform that identifies mathematical difficulty profiles and predicts learning risk for children with dyscalculia. The system aggregates session-level data from peer learning engines, applies longitudinal feature engineering, and surfaces interpretable early warning indicators through teacher and parent dashboards.

This component is part of a larger adaptive learning ecosystem developed for dyscalculia learners (Project R26-IT-138). The Learning Insight & Early Warning System focuses on identifying **which students are at risk**, **why they are struggling**, and **what teachers should do next** — using Gaussian Mixture Model clustering and Logistic Regression risk classification.

---

## Architecture

```
┌──────────────────────────┐        REST API        ┌────────────────────────────┐       Database        ┌──────────────────────┐
│   React Native (Expo)    │ ──────────────────────▶ │   FastAPI (Python)         │ ────────────────────▶ │   Supabase           │
│   Teacher Dashboard      │                         │   Data Ingestion API       │                       │   session_records    │
│   Parent Portal          │ ◀────────────────────── │   ML Pipeline Integration  │ ◀──────────────────── │   risk_predictions   │
└──────────────────────────┘                         └────────────────────────────┘                       └──────────────────────┘
                                                                  │
                                                                  ▼
                                                     ┌────────────────────────┐
                                                     │   ML Pipeline          │
                                                     │   Python / Scikit-learn│
                                                     │   GMM Clustering       │
                                                     │   Logistic Regression  │
                                                     └────────────────────────┘
```

**Data Flow:**

1. Components B and C export session-level CSV records at the end of each learning session
2. Records are ingested via FastAPI endpoints and stored in Supabase
3. The longitudinal feature engineering module computes session-to-session trends
4. GMM clustering assigns each student to a difficulty profile (NRW, MCD, GLP, or IBS)
5. Logistic Regression classifies each student as Low, Moderate, or High risk
6. Risk predictions are stored in Supabase and surfaced through the dashboards
7. Teachers view class-wide analytics, cluster maps, and intervention recommendations
8. Parents view their own child's progress and skill mastery summary

---

## Team Members

| Member | Component | Status |
|--------|-----------|--------|
| IT22136206 | Cognitive Skill Profiling System | Completed till Progress Presentation 1 |
| IT22224316 | Personalised Math Learning Engine | Pending integration |
| IT22117878 | Adaptive Game-Based Learning Engine | Pending integration |
| **IT21275524** | **Learning Insight & Early Warning System** | **Pending integration** |

---

## ML Model Details

**Primary Algorithms**
- Gaussian Mixture Models (GMM) — learner difficulty profile clustering
- Logistic Regression — risk level classification (Low / Moderate / High)

**Benchmark Algorithms**
- Decision Tree Classifier — explainability and feature importance analysis
- Random Forest Classifier — ensemble performance benchmark

**Input Features**
- BKT mastery scores across 5 skills (number recognition, counting, magnitude comparison, addition, subtraction)
- Session accuracy rate and response time
- Hint requests and error count
- Task completion rate and engagement score
- Inactivity periods and learner state (from Component C)
- RL difficulty trend (from Component C)

**Longitudinal Features (engineered)**
- Session-to-session accuracy gain
- Response time delta trend
- Stagnation score (proportion of sessions without improvement)
- Persistent error recurrence count
- Engagement volatility across sessions

**GMM Cluster Profiles (4)**

| Cluster | Code | Description |
|---------|------|-------------|
| Number Recognition Weakness | NRW | Low BKT mastery on number_recognition; other skills near average |
| Magnitude Comparison Difficulty | MCD | Low BKT mastery on magnitude_comparison; other skills relatively intact |
| Global Low Performer | GLP | Uniformly low mastery across all 5 skills; high hint dependency; low engagement |
| Improving but Slow | IBS | Positive accuracy and engagement trend but below age-expected performance |

**Risk Classification Output**

| Risk Level | Condition |
|------------|-----------|
| Low | Positive trend, engagement stable or increasing, mastery > 0.65 or improving |
| Moderate | Mixed signals — some skills improving, others stagnant; engagement variable |
| High | Flat or negative trend, mastery < 0.45, persistent errors over 5+ sessions |

**Evaluation Metrics**
- GMM: Silhouette Score (target > 0.4), Davies–Bouldin Index (target < 2.0)
- Logistic Regression: Accuracy, Precision, Recall, F1-Score (macro), AUC-ROC, Confusion Matrix

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Mobile Application | React Native (Expo) |
| Navigation | React Navigation v6 (stack + bottom tabs) |
| Data Visualisation | react-native-chart-kit (LineChart, PieChart, BarChart) |
| HTTP Client | Axios |
| Backend API | FastAPI (Python) |
| Machine Learning | Python, Scikit-learn, Pandas, NumPy |
| Database | Supabase (PostgreSQL) |
| API Documentation | Swagger (FastAPI auto-generated) |
| State Management | React Context (auth, user role) |

---

## Project Structure

```
EduInsight/
├── App.tsx                               ← Entry point
├── app/
│   ├── navigation/
│   │   ├── AppNavigator.tsx              ← Root navigator (Auth vs Main)
│   │   ├── AuthNavigator.tsx             ← Login flow
│   │   ├── TeacherNavigator.tsx          ← Teacher stack navigator
│   │   ├── ParentNavigator.tsx           ← Parent stack navigator
│   │   └── types.ts                      ← Route and param types
│   │
│   ├── screens/
│   │   ├── auth/
│   │   │   └── LoginScreen.tsx           ← Role-based login (Teacher / Parent)
│   │   ├── teacher/
│   │   │   ├── HomeScreen.tsx            ← Overview stats, risk distribution, all students
│   │   │   ├── StudentDetailScreen.tsx   ← Individual student profile, cluster, risk, trends
│   │   │   ├── SessionHistoryScreen.tsx  ← All sessions for a selected student
│   │   │   ├── ClusterViewScreen.tsx     ← Students grouped by GMM cluster
│   │   │   ├── AlertsScreen.tsx          ← Early warning alerts by risk level
│   │   │   └── ReportsScreen.tsx         ← Class-level trends and summaries
│   │   └── parent/
│   │       └── HomeScreen.tsx            ← Child progress, mastery, recommendations
│   │
│   ├── components/
│   │   ├── RiskBadge.tsx                 ← Colour-coded risk level pill (High/Moderate/Low)
│   │   ├── StudentCard.tsx               ← Compact student summary with sparkline
│   │   ├── MiniSparkline.tsx             ← Small 150×40 accuracy trend chart
│   │   ├── ClusterBadge.tsx              ← Colour-coded cluster pill (NRW/MCD/GLP/IBS)
│   │   ├── SkillBar.tsx                  ← Labelled BKT mastery progress bar
│   │   └── SectionHeader.tsx             ← Bold section title with optional subtitle
│   │
│   ├── services/
│   │   └── api.ts                        ← All FastAPI calls (Axios + JWT refresh)
│   │
│   ├── context/
│   │   ├── AuthContext.tsx               ← User state, role, isAuthenticated
│   │   └── ThemeContext.tsx              ← Light/dark mode, colour palette
│   │
│   └── constants/
│       ├── colors.ts                     ← Risk colours, cluster colours, palette
│       ├── typography.ts                 ← Font sizes, weights, text presets
│       └── spacing.ts                    ← Spacing scale, border radius, shadows
│
├── backend/
│   ├── main.py                           ← FastAPI entry point
│   ├── routers/
│   │   ├── ingest.py                     ← POST /data/math-engine, POST /data/game-engine
│   │   ├── predict.py                    ← POST /predict (risk scoring)
│   │   ├── dashboard.py                  ← GET /students, GET /alerts, GET /reports
│   │   └── parent.py                     ← GET /child-progress (restricted)
│   ├── models/
│   │   ├── session_record.py             ← Pydantic schema for incoming session data
│   │   └── risk_prediction.py            ← Pydantic schema for prediction output
│   ├── ml/
│   │   ├── preprocessing.py              ← Normalisation, missing value imputation
│   │   ├── feature_engineering.py        ← Longitudinal feature computation
│   │   ├── clustering.py                 ← GMM and K-Means clustering
│   │   └── risk_classifier.py            ← Logistic Regression, DT, RF
│   └── database/
│       └── supabase_client.py            ← Supabase connection and queries
│
└── notebooks/
    ├── 01_preprocessing.ipynb            ← Data cleaning and normalisation
    ├── 02_feature_engineering.ipynb      ← Longitudinal feature derivation
    ├── 03_gmm_clustering.ipynb           ← GMM training and cluster evaluation
    ├── 04_risk_classification.ipynb      ← LR, DT, RF training and comparison
    └── 05_evaluation.ipynb               ← Full pipeline evaluation metrics
```

---

## Data Schema

### Input (from Components B and C — one row per student session)

| Column | Type | Source | Nullable | Range |
|--------|------|--------|----------|-------|
| student_id | string | B, C | NOT NULL | STU_001… |
| session_date | date | B, C | NOT NULL | YYYY-MM-DD |
| session_number | integer | B, C | NOT NULL | 1, 2, 3… |
| mastery_number_recognition | float | B | NOT NULL | 0.0 – 1.0 |
| mastery_counting | float | B | NOT NULL | 0.0 – 1.0 |
| mastery_magnitude_comparison | float | B | NOT NULL | 0.0 – 1.0 |
| mastery_addition | float | B | NOT NULL | 0.0 – 1.0 |
| mastery_subtraction | float | B | NOT NULL | 0.0 – 1.0 |
| difficulty_trend | string | C | NOT NULL | increasing / stable / decreasing |
| learner_state | string | C | NOT NULL | struggling / on-track / disengaged |
| accuracy_rate | float | B, C | NOT NULL | 0.0 – 1.0 |
| avg_response_time_sec | float | B, C | NOT NULL | > 0.0 |
| task_completion_rate | float | C | NOT NULL | 0.0 – 1.0 |
| engagement_score | float | C | NOT NULL | 0.0 – 1.0 |
| inactivity_periods | integer | C | NOT NULL | >= 0 |
| hint_requests | integer | B | NOT NULL | >= 0 |
| error_count | integer | B | NOT NULL | >= 0 |

### Output (ML pipeline — stored in Supabase risk_predictions table)

| Column | Type | Range |
|--------|------|-------|
| student_id | string | STU_001… |
| session_number | integer | 1, 2, 3… |
| gmm_cluster | string | NRW / MCD / GLP / IBS |
| gmm_cluster_prob | float | 0.0 – 1.0 |
| risk_level | string | low / moderate / high |
| risk_score | float | 0.0 – 1.0 |
| recommended_intervention | string | Text description |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /data/math-engine | Ingest session records from the Personalised Math Learning Engine (Component B) |
| POST | /data/game-engine | Ingest session records from the Adaptive Game-Based Learning Engine (Component C) |
| POST | /predict | Run risk scoring pipeline for a student or batch of students |
| GET | /students | Retrieve all students with current cluster and risk level (teacher only) |
| GET | /students/{id} | Retrieve individual student detail with full session history |
| GET | /alerts | Retrieve high and moderate risk alerts for teacher dashboard |
| GET | /reports | Retrieve class-level cluster and risk distribution summaries |
| GET | /child-progress | Retrieve own child's progress summary (parent only) |

Swagger UI → `http://localhost:8000/docs`

---

## Quick Start

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Server runs on port 8000. Swagger UI → http://localhost:8000/docs

Create a `.env` file in `/backend`:

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
SUPABASE_ANON_KEY=your_anon_key
```

### 2. Frontend

In a new, separate terminal:

```bash
cd frontend
npm install
npm start
```

Scan the QR code with Expo Go on your phone.

Create a `.env` file in `/frontend`:

```
EXPO_PUBLIC_API_BASE=http://YOUR_LAN_IP:8000
EXPO_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
EXPO_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
```

> Find your IP: `ipconfig` (Windows) or `ifconfig` (Mac/Linux). Phone and computer must be on the same WiFi.

### 3. Database (Supabase)

1. Create a Supabase project at [supabase.com](https://supabase.com)
2. Run `backend/database/supabase_schema.sql` in the Supabase SQL editor — creates the following tables:
   - `session_records` — raw ingested session data from Components B and C
   - `risk_predictions` — ML pipeline output (cluster, risk level, intervention)
3. Fill in `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and `SUPABASE_ANON_KEY` in `backend/.env`

### 4. ML Pipeline

Run the Jupyter notebooks in order:

```bash
cd notebooks
jupyter notebook
```

Open and run:
1. `01_preprocessing.ipynb`
2. `02_feature_engineering.ipynb`
3. `03_gmm_clustering.ipynb`
4. `04_risk_classification.ipynb`
5. `05_evaluation.ipynb`

Trained models are saved as `.pkl` files and loaded by the FastAPI backend for inference.

---

## Implementation Phases

| Phase | Week | Deliverable |
|-------|------|-------------|
| Phase 1 — Data Integration | Week 1 | Formal data request documents sent to Components B and C; agreed CSV schema |
| Phase 2 — Frontend Development | Week 1–2 | All 8 screens and 6 reusable components built with mock data; testable in Expo Go |
| Phase 3 — FastAPI Backend | Week 2 | Data ingestion endpoints live; raw session records stored in Supabase |
| Phase 4 — ML Pipeline | Week 2–3 | GMM and Logistic Regression trained; evaluation notebooks complete |
| Phase 5 — Risk Scoring | Week 3 | Risk prediction endpoint live; all sessions scored; interventions generated |
| Phase 6 — Integration & Deployment | Week 3–4 | Frontend connected to backend; end-to-end system tested and deployed |

---

## Dependencies

### External Component Dependencies

| Component | Owner | Data Provided | Dependency Type |
|-----------|-------|---------------|-----------------|
| Personalised Math Learning Engine | IT22224316 | BKT mastery scores, session statistics | Hard — required for ML pipeline |
| Adaptive Game-Based Learning Engine | IT22117878 | RL difficulty trend, learner state, engagement metrics | Hard — required for ML pipeline |
| Cognitive Skill Profiling System | IT22136206 | Cognitive context (memory, attention, processing speed) | Soft — deferred to Phase 2 |

### Assumptions
- Student IDs are unique and consistent across all components
- Session dates are in `YYYY-MM-DD` format
- Batch processing is acceptable (no real-time streaming required)
- Student authentication is handled externally

---

## Adaptive Learning Features

- Longitudinal learner profiling across multiple sessions
- Probabilistic cluster assignment via Gaussian Mixture Models
- Interpretable Logistic Regression risk scoring with confidence levels
- Real-time Teacher Analytics Dashboard with drill-down navigation
- Role-based access control (teacher vs. parent views)
- Colour-coded risk badges and cluster badges
- Personalised intervention recommendations per cluster and risk level
- Parent Portal with emoji-based engagement indicators and simplified charts
