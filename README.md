# MathsMate — Cognitive Skill Profiling System

An AI-powered mobile learning platform that analyses student interaction
behaviour during maths activities and generates a **4-dimension cognitive
profile** (Memory, Attention, Number Sense, Processing Speed) — designed
to support children with dyscalculia.

> **Component 1 of 4** in the full MathsMate adaptive learning ecosystem.
> The cognitive profile produced here feeds into the Personalised Learning
> Engine, Adaptive Game Engine, and Early Warning System built by other
> team members.

---

## Architecture

```
┌───────────────────┐        ┌──────────────────────┐        ┌──────────────┐
│   Expo Client     │  REST  │   FastAPI Server      │  SQL   │   Supabase   │
│  (React Native)   │ ─────▶ │  + Decision Tree .pkl │ ─────▶ │  (Postgres)  │
│  11 screens · i18n│        │  7 API endpoints      │        │  6 tables    │
└───────────────────┘        └──────────────────────┘        └──────────────┘
```

**Data flow:**

1. Student solves maths questions in the mobile app.
2. The client captures behavioural signals per question (response time, attempts, accuracy, hints, clicks, error type).
3. Interaction events are posted to the FastAPI backend.
4. Backend extracts aggregated features and feeds them into a pre-trained Decision Tree model (`.pkl`) to predict 4 cognitive dimension labels.
5. The resulting cognitive profile is stored in Supabase and displayed to the student/teacher.

## Project structure

```
R26-IT-138/
├── server/                         # Python FastAPI backend
│   ├── run.py                      # Entry point: python run.py
│   ├── start.ps1 / start.bat      # One-click start scripts
│   ├── app/
│   │   ├── main.py                 # FastAPI app, CORS, router registration
│   │   ├── config.py               # pydantic-settings (.env loader)
│   │   ├── schemas.py              # Pydantic request / response models
│   │   ├── routers/
│   │   │   ├── questions.py        # GET  /questions
│   │   │   ├── interactions.py     # POST /interactions, /interactions/single
│   │   │   ├── profile.py          # POST /profiles/predict, /profiles/generate
│   │   │   │                       # GET  /profiles/{id}/latest, /history, /status
│   │   │   └── teacher.py          # GET  /teacher/students, /teacher/students/{id}/summary
│   │   ├── services/
│   │   │   ├── features.py         # Feature engineering (raw events → aggregated vector)
│   │   │   ├── model.py            # .pkl loader + rule-based fallback
│   │   │   ├── recommendation.py   # Rule-based support messages
│   │   │   ├── supabase_client.py  # Supabase CRUD wrapper
│   │   │   └── validation.py       # Input validation
│   │   └── ml/
│   │       ├── cognitive_model.pkl # Trained Decision Tree model
│   │       ├── train_model.py      # Local training script
│   │       ├── evaluate_model.py   # Evaluation metrics
│   │       └── model_columns.json  # Feature / encoder metadata
│   ├── data/
│   │   └── cognitive_dataset.csv   # Prototype dataset (76 rows)
│   ├── supabase_schema.sql         # 6 tables — run once in Supabase SQL editor
│   ├── requirements.txt
│   ├── .env / .env.example
│   └── README.md                   # Backend integration guide
│
├── client/                         # React Native Expo (Expo Go)
│   ├── App.tsx                     # Navigation stack (11 screens)
│   ├── app.json                    # Expo config
│   ├── src/
│   │   ├── theme.ts                # Cartoon-warm colour palette
│   │   ├── api/client.ts           # Typed fetch wrapper for all endpoints
│   │   ├── i18n/
│   │   │   ├── LanguageContext.tsx  # React Context for language state
│   │   │   └── translations.ts     # EN + SI translation strings
│   │   ├── components/
│   │   │   ├── PrimaryButton.tsx
│   │   │   ├── Card.tsx
│   │   │   └── LanguageToggle.tsx
│   │   ├── screens/
│   │   │   ├── LogoScreen.tsx
│   │   │   ├── SplashScreen.tsx
│   │   │   ├── LanguageSelectScreen.tsx
│   │   │   ├── LoginScreen.tsx
│   │   │   ├── SignUpScreen.tsx
│   │   │   ├── WelcomeScreen.tsx
│   │   │   ├── StudentDashboard.tsx
│   │   │   ├── MathActivityScreen.tsx
│   │   │   ├── ProfileResultScreen.tsx
│   │   │   ├── ProfileHistoryScreen.tsx
│   │   │   ├── TeacherDashboard.tsx
│   │   │   └── README.md           # Screen folder guide for 4-member integration
│   │   ├── screens/onboarding/     # Reserved: shared onboarding screens
│   │   ├── screens/auth/           # Reserved: shared auth screens
│   │   ├── screens/cognitive-profile/ # Member 1 (your) screens
│   │   ├── screens/shared/         # Cross-module screens
│   │   ├── components/ui/          # Reserved: shared UI components
│   │   ├── components/layout/      # Reserved: layout components
│   │   ├── navigation/             # Reserved: navigation config
│   │   ├── types/                  # Reserved: shared TypeScript types
│   │   └── constants/              # Reserved: app constants
│   ├── assets/images/              # Reference UI images
│   ├── .env / .env.example
│   └── package.json
│
├── Cognitive_Skill_Profiling_System_Full_Implementation_Plan.md
└── README.md                       # ← You are here
```

> **4-member integration:** The folder structure includes reserved directories
> for each team member's module. See `client/src/screens/README.md` and
> `server/app/README.md` for the integration guide.

---

## Quick start

### 1. Backend (Server)

```powershell
cd R26-IT-138/server

# First-time setup
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env          # then fill in your Supabase keys

# Start the server
python run.py
```

Server runs on **port 8000**.
Swagger UI → http://localhost:8000/docs

> Alternative: `.\start.ps1` (Windows) or `start.bat` — creates venv automatically.

### 2. Frontend (Client)

In a **new, separate terminal**:

```powershell
cd R26-IT-138/client
npm install
npx expo start -c
```

Scan the QR code with **Expo Go** on your phone.

> **API URL** — Each developer sets their own LAN IP in `client/.env`:
> ```
> EXPO_PUBLIC_API_BASE=http://YOUR_LAN_IP:8000
> EXPO_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
> EXPO_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
> ```
> Find your IP: `ipconfig` (Windows) or `ifconfig` (Mac/Linux).
> Phone and computer must be on the same WiFi.

### 3. Database (Supabase)

1. Create a [Supabase](https://supabase.com) project.
2. Run `server/supabase_schema.sql` in the Supabase SQL editor — creates 6 tables:
   - `user_profiles`, `students`, `questions`, `interactions`, `extracted_features`, `cognitive_profiles`
3. Fill in `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and `SUPABASE_ANON_KEY` in `server/.env`.

### 4. ML Model

The server loads a trained Decision Tree `.pkl` from `server/app/ml/cognitive_model.pkl`.

- **If model exists** → uses `MultiOutputClassifier(DecisionTreeClassifier)` predictions.
- **If model is absent** → uses a deterministic rule-based fallback (API still works).

To re-train locally:
```powershell
cd R26-IT-138/server
python -m app.ml.train_model
```

For production-quality training, use Google Colab with a larger synthetic dataset (3000+ rows).

---

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Server health check |
| GET | `/` | Service info |
| GET | `/questions` | List maths questions (optional `?topic=&difficulty=`) |
| POST | `/interactions` | Save batch of interaction events |
| POST | `/interactions/single` | Save a single interaction |
| POST | `/profiles/predict` | Predict cognitive profile from single interaction |
| POST | `/profiles/generate` | Generate profile from batch of events |
| GET | `/profiles/{student_id}/latest` | Latest cognitive profile |
| GET | `/profiles/{student_id}/history` | Profile history |
| GET | `/profiles/status` | ML model status |
| GET | `/teacher/students` | List all students (teacher view) |
| GET | `/teacher/students/{student_id}/summary` | Student summary for teacher |

---

## ML model details

- **Algorithm**: `MultiOutputClassifier(DecisionTreeClassifier)` — scikit-learn
- **Input features** (10): topic, difficulty, response_time_sec, attempts, is_correct, hint_used, click_count, session_time_sec, time_between_actions, error_type
- **Output labels** (4): label_memory, label_attention, label_number_sense, label_processing_speed
- **Label values**: Low / Medium / High (processing_speed: Slow / Moderate / Fast)
- **Evaluation**: accuracy, precision, recall, F1, confusion matrix, exact match accuracy

---

## Tech stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React Native, Expo SDK 54, React 19, React Navigation 7, AsyncStorage |
| **Backend** | Python 3.12, FastAPI 0.115, Pydantic 2.9, uvicorn |
| **Database** | Supabase (PostgreSQL) with Row-Level Security |
| **ML** | scikit-learn 1.5, Decision Tree classifier, joblib |
| **i18n** | Custom React Context (English + Sinhala) |
| **UI** | Cartoon kid-friendly theme with animal mascots |

---

## Environment variables

### Server (`server/.env`)
```
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
CORS_ORIGINS=*
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
SUPABASE_ANON_KEY=eyJ...
MODEL_PATH=./app/ml/cognitive_model.pkl
```

### Client (`client/.env`)
```
EXPO_PUBLIC_API_BASE=http://YOUR_LAN_IP:8000
EXPO_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
EXPO_PUBLIC_SUPABASE_ANON_KEY=eyJ...
```

---

## Team members

| Member | Component | Status |
|--------|-----------|--------|
| 1 - IT22136206 | Cognitive Skill Profiling System | Completed till the Progress Presentation 1 |
| 2 | Personalised Math Learning Engine | Pending integration |
| 3 | Adaptive Game-Based Learning Engine | Pending integration |
| 4 | Learning Insight and Early Warning System | Pending integration |
