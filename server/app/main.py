from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import interactions, profile, questions, teacher

settings = get_settings()

app = FastAPI(
    title="Cognitive Skill Profiling API",
    version="0.2.0",
    description=(
        "Collects student interaction data, computes behavioural features, "
        "and generates a multi-dimensional cognitive profile using a "
        "Decision Tree model (.pkl). Part of the MathsMate adaptive "
        "mathematics learning platform."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(questions.router)
app.include_router(interactions.router)
app.include_router(profile.router)
app.include_router(teacher.router)


@app.get("/", tags=["health"])
def root() -> dict:
    return {
        "name": "cognitive-skill-profiling",
        "status": "ok",
        "service": "Cognitive Skill Profiling API",
        "env": settings.app_env,
    }


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "running", "service": "Cognitive Skill Profiling API"}
