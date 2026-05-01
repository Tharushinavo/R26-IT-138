# Server Folder Structure

This backend serves the **MathsMate** platform — a 4-member integrated system.

## Folder Layout

```
server/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Pydantic settings (.env loader)
│   ├── schemas.py           # Shared Pydantic models
│   │
│   ├── routers/             # API route handlers
│   │   ├── questions.py     # GET /questions
│   │   ├── interactions.py  # POST /interactions
│   │   ├── profile.py       # POST /profiles/predict, GET /profiles/*
│   │   └── teacher.py       # GET /teacher/students/*
│   │
│   ├── services/            # Business logic
│   │   ├── supabase_client.py  # Supabase DB CRUD
│   │   ├── features.py      # Feature extraction
│   │   ├── model.py         # ML model loader + fallback
│   │   ├── recommendation.py   # Rule-based recommendations
│   │   └── validation.py    # Data validation/processing
│   │
│   └── ml/                  # Machine learning
│       ├── train_model.py   # Model training script
│       └── evaluate_model.py   # Evaluation metrics
│
├── data/                    # Training datasets
├── supabase_schema.sql      # Database schema (6 tables)
├── requirements.txt         # Python dependencies
└── start.ps1 / start.bat   # Server start scripts
```

## Integration for Other Members

Each member can:
1. Add new routers under `app/routers/` for their module endpoints
2. Add new services under `app/services/` for business logic
3. Extend `app/schemas.py` with their Pydantic models
4. Register new routers in `app/main.py`
5. Add new tables to `supabase_schema.sql`
