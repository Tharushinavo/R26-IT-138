# Cognitive Skill Profiling – Backend (FastAPI)

Collects student interactions, engineers behavioural features, and returns a
4-dimensional cognitive profile (memory, attention, number sense, processing
speed) using a pre-trained Decision Tree `.pkl` model. Persists data in
Supabase.

## Setup

```powershell
cd server
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # then fill in Supabase keys
```

Place your trained model at `app/ml/cognitive_profile_model.pkl`
(or update `MODEL_PATH` in `.env`).

The model may be either:
- a single multi-output `sklearn` classifier returning labels in the order
  `[memory, attention, number_sense, processing_speed]`, **or**
- a `dict` of 4 classifiers keyed by those same dimension names.

All classifiers must be trained on features in this exact order (see
`app/services/features.py`):

```
accuracy, avg_response_time_ms, response_time_std_ms, avg_attempts,
retry_rate, hint_rate, answer_change_rate, total_questions
```

If no `.pkl` is present, the API falls back to a rule-based heuristic so you
can still develop the client.

## Run

```powershell
# Short command (recommended)
.\start.ps1

# Or manually
uvicorn app.main:app --reload --host 0.0.0.0 --port 8005
```

Open Swagger: http://localhost:8005/docs

## Supabase tables

Run `supabase_schema.sql` in the Supabase SQL editor.

## Endpoints

- `GET  /health` – liveness
- `GET  /profile/status` – shows whether the `.pkl` was loaded
- `POST /interactions` – log a batch of `InteractionEvent`s
- `POST /profile/generate` – compute and store a cognitive profile from a batch
- `GET  /profile/{user_id}` – latest stored profile (or compute from stored events)
