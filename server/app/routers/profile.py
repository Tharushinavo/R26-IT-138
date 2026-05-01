from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.schemas import (
    CognitiveProfile,
    InteractionEvent,
    PredictRequest,
    ProfileRequest,
)
from app.services import supabase_client
from app.services.features import compute_features
from app.services.model import model_status, predict_profile

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("/status")
def status() -> dict:
    """Check model status (plan Section 7.2)."""
    return model_status()


@router.post("/generate", response_model=CognitiveProfile)
def generate_profile(body: ProfileRequest) -> CognitiveProfile:
    """Generate cognitive profile from a batch of interaction events."""
    if not body.events:
        raise HTTPException(status_code=400, detail="No events provided")

    features = compute_features(body.events)
    profile = predict_profile(
        student_id=body.student_id, features=features, session_id=body.session_id
    )

    supabase_client.insert_profile(profile.model_dump(mode="json"))
    return profile


@router.post("/predict", response_model=CognitiveProfile)
def predict_from_single(body: PredictRequest) -> CognitiveProfile:
    """Predict cognitive profile from a single interaction (plan Section 7.2).
    Also fetches stored interactions for this student to build a fuller picture.
    """
    # Build an InteractionEvent from the predict request
    current_event = InteractionEvent(
        student_id=body.student_id,
        session_id=f"predict_{body.student_id}",
        question_id=body.question_id,
        topic=body.topic,
        difficulty=body.difficulty,
        response_time_sec=body.response_time_sec,
        attempts=body.attempts,
        is_correct=body.is_correct,
        hint_used=body.hint_used,
        click_count=body.click_count,
        session_time_sec=body.session_time_sec,
        time_between_actions=body.time_between_actions,
        error_type=body.error_type,
    )

    # Try to get historical events for a richer profile
    stored_rows = supabase_client.fetch_user_events(body.student_id)
    stored_events = []
    for row in stored_rows:
        try:
            stored_events.append(InteractionEvent(**row))
        except Exception:
            pass

    all_events = stored_events + [current_event]
    features = compute_features(all_events)
    profile = predict_profile(
        student_id=body.student_id, features=features
    )

    supabase_client.insert_profile(profile.model_dump(mode="json"))
    return profile


@router.get("/{student_id}/latest", response_model=Optional[CognitiveProfile])
def get_latest(student_id: str, session_id: Optional[str] = Query(default=None)):
    """Return the latest cognitive profile for a student (plan Section 7.2)."""
    latest = supabase_client.fetch_latest_profile(student_id)
    if latest:
        return latest

    rows = supabase_client.fetch_user_events(student_id, session_id=session_id)
    if not rows:
        raise HTTPException(
            status_code=404,
            detail="No stored profile or interactions found for this student",
        )
    events = [InteractionEvent(**row) for row in rows]
    features = compute_features(events)
    profile = predict_profile(student_id=student_id, features=features, session_id=session_id)
    supabase_client.insert_profile(profile.model_dump(mode="json"))
    return profile


@router.get("/{student_id}/history", response_model=List[CognitiveProfile])
def get_history(student_id: str, limit: int = Query(default=20, ge=1, le=100)):
    """Return all previous cognitive profile records for a student (plan Section 7.2)."""
    profiles = supabase_client.fetch_profile_history(student_id, limit=limit)
    if not profiles:
        return []
    return profiles
