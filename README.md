# Cognitive Skill Profiling System

An AI-powered module that collects student interaction data from a math
learning platform and generates a multi-dimensional cognitive profile
(memory, attention, number sense, processing speed) — especially designed
for students with dyscalculia.

## Architecture

```
┌──────────────┐         ┌─────────────────┐         ┌──────────────┐
│  Expo Client │ ──API── │  FastAPI Server  │ ──SQL── │   Supabase   │
│ (React Native)│         │  + ML (.pkl)     │         │  (Postgres)  │
└──────────────┘         └─────────────────┘         └──────────────┘
```

**Data flow:**
1. Student plays a math quiz in the client.
2. The client captures behavioural signals per question (response time,
   accuracy, retries, hints, answer changes).
3. Events are posted to the FastAPI backend.
4. Backend engineers aggregated features and feeds them into a pre-trained
   Decision Tree model (`.pkl`) to produce 4 cognitive dimension labels.
5. The resulting profile is stored in Supabase and returned to the client.

## Project structure

```
Research Client 01/
├── server/                  # Python FastAPI backend
│   ├── app/
│   │   ├── main.py          # FastAPI app & CORS
│   │   ├── config.py        # pydantic-settings
│   │   ├── schemas.py       # Request / response models
│   │   ├── routers/
│   │   │   ├── interactions.py
│   │   │   └── profile.py
│   │   ├── services/
│   │   │   ├── features.py  # Feature engineering
│   │   │   ├── model.py     # .pkl loader + rule-based fallback
│   │   │   └── supabase_client.py
│   │   └── ml/              # Place your trained .pkl here
│   ├── supabase_schema.sql  # Run once in Supabase SQL editor
│   ├── requirements.txt
│   └── .env.example
│
├── client/                  # React Native Expo (Expo Go)
│   ├── App.tsx              # Navigation stack
│   ├── src/
│   │   ├── theme.ts         # Light sky blue / white / blue palette
│   │   ├── api/client.ts    # Typed fetch wrapper
│   │   ├── utils/questions.ts
│   │   ├── components/
│   │   │   ├── PrimaryButton.tsx
│   │   │   └── Card.tsx
│   │   └── screens/
│   │       ├── HomeScreen.tsx
│   │       ├── QuizScreen.tsx
│   │       └── ProfileScreen.tsx
│   ├── app.json
│   └── package.json
│
└── README.md                # ← You are here
```

## Quick start

### 1. Backend (Server)

```powershell
cd server
.\start.ps1
```

That's it! The script activates the virtual environment and starts the server on port `8005`.
Swagger UI → http://localhost:8005/docs

> First-time setup? Run these once before `.\start.ps1`:
> ```powershell
> python -m venv .venv
> .\.venv\Scripts\Activate.ps1
> pip install -r requirements.txt
> copy .env.example .env
> ```

Run python -m app.ml.train_model from server/ to train and save the ML model

### 2. Frontend (Client)

In a **new, separate terminal**:

```powershell
cd client
npm run start
```

Scan the QR code with Expo Go on your phone.

> **API URL** — Each developer sets their own LAN IP in `client/.env`:
> ```
> EXPO_PUBLIC_API_BASE=http://YOUR_LAN_IP:8005
> ```
> Find your IP: run `ipconfig` on Windows or `ifconfig` on Mac/Linux.
> Your phone and computer must be on the same WiFi network.
> A `.env.example` is provided as a template.

### 3. Database (Optional)

If you want to persist data, create a Supabase project and:
1.  Run `server/supabase_schema.sql` in the Supabase SQL editor.
2.  Fill in `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in `server/.env`.

### 4. ML Model (Optional)

Place your trained `.pkl` at `server/app/ml/cognitive_profile_model.pkl`.
If no model is present, the server uses a rule-based fallback.

## Tech stack

- **Backend** – Python 3.11+, FastAPI, Pydantic, scikit-learn, joblib, Supabase Python SDK
- **Frontend** – React Native, Expo SDK 54, React 19, React Navigation 7, AsyncStorage
- **Database** – Supabase (Postgres)
- **ML** – Decision Tree classifier (scikit-learn `.pkl`)
