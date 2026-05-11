from __future__ import annotations

import logging
import traceback
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.schemas import (
    CognitiveProfile,
    InteractionEvent,
    PredictRequest,
    ProfileRequest,
)
from app.services import supabase_client
from app.services.model import model_status, predict_profile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profiles", tags=["profiles"])


def _student_lookup_ids(student_id: str) -> List[str]:
    ids: List[str] = [student_id]
    student_row = supabase_client.fetch_student(student_id)
    if student_row:
        ids.extend([str(student_row.get("id") or ""), str(student_row.get("user_id") or "")])
    for row in supabase_client.fetch_students_by_user_id(student_id):
        ids.extend([str(row.get("id") or ""), str(row.get("user_id") or "")])
    unique_ids: List[str] = []
    for value in ids:
        if value and value not in unique_ids:
            unique_ids.append(value)
    logger.info("Profile lookup ids resolved: requested=%s ids=%s", student_id, unique_ids)
    return unique_ids


def _insert_profile_or_raise(profile: CognitiveProfile) -> None:
    """Insert profile into Supabase and fail the request if persistence fails."""
    try:
        profile_data = profile.model_dump(mode="json")
        # Serialize nested features as JSON-compatible dict for Supabase JSONB column
        if "features" in profile_data and isinstance(profile_data["features"], dict):
            import json
            profile_data["features"] = json.loads(json.dumps(profile_data["features"]))
        result = supabase_client.insert_profile(profile_data)
        if result.get("skipped"):
            raise RuntimeError("Supabase is not configured for profile persistence")
        logger.info(
            "Profile persisted: student_id=%s session_id=%s inserted=%s",
            profile.student_id,
            profile.session_id,
            result.get("inserted"),
        )
    except Exception as e:
        logger.error("Failed to insert profile into Supabase: %s", e)
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Profile persistence failed: {str(e)}")


def _persist_events_if_missing(body: ProfileRequest) -> None:
    if not body.session_id:
        logger.info("Profile generate event persistence skipped: no session_id student_id=%s", body.student_id)
        return
    try:
        existing = supabase_client.fetch_user_events(body.student_id, session_id=body.session_id)
        if existing:
            logger.info(
                "Profile generate event persistence skipped: existing events found student_id=%s session_id=%s rows=%s",
                body.student_id,
                body.session_id,
                len(existing),
            )
            return
        payload = [event.model_dump(mode="json") for event in body.events]
        result = supabase_client.insert_interactions(payload)
        if result.get("skipped"):
            raise RuntimeError("Supabase is not configured for interaction persistence")
        logger.info(
            "Profile generate persisted events: student_id=%s session_id=%s inserted=%s",
            body.student_id,
            body.session_id,
            result.get("inserted"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to persist events for profile generation: %s", e)
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Interaction persistence failed: {str(e)}")


@router.get("/status")
def status() -> dict:
    """Check model status (plan Section 7.2)."""
    return model_status()


@router.post("/generate", response_model=CognitiveProfile)
def generate_profile(body: ProfileRequest) -> CognitiveProfile:
    """Generate cognitive profile from a batch of interaction events."""
    if not body.events:
        raise HTTPException(status_code=400, detail="No events provided")

    logger.info(
        "Profile generate requested: student_id=%s session_id=%s events=%s",
        body.student_id,
        body.session_id,
        len(body.events),
    )

    try:
        profile = predict_profile(
            student_id=body.student_id, events=body.events, session_id=body.session_id
        )
    except Exception as e:
        logger.error(f"Profile prediction failed: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Profile prediction failed: {str(e)}")

    _persist_events_if_missing(body)
    _insert_profile_or_raise(profile)
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

    try:
        profile = predict_profile(
            student_id=body.student_id, events=all_events
        )
    except Exception as e:
        logger.error(f"Profile prediction failed: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Profile prediction failed: {str(e)}")

    _insert_profile_or_raise(profile)
    return profile


@router.get("/{student_id}/latest", response_model=Optional[CognitiveProfile])
def get_latest(student_id: str, session_id: Optional[str] = Query(default=None)):
    """Return the latest cognitive profile for a student (plan Section 7.2)."""
    lookup_ids = _student_lookup_ids(student_id)
    logger.info("Profile latest requested: student_id=%s session_id=%s", student_id, session_id)
    try:
        latest = supabase_client.fetch_latest_profile_for_student_ids(lookup_ids)
        if latest:
            logger.info(
                "Profile latest found: requested=%s stored_student_id=%s session_id=%s",
                student_id,
                latest.get("student_id"),
                latest.get("session_id"),
            )
            return latest
    except Exception as e:
        logger.error("Failed to fetch latest profile: %s", e)

    rows = supabase_client.fetch_events_for_student_ids(lookup_ids, session_id=session_id)
    if not rows:
        logger.warning("Profile latest missing: student_id=%s lookup_ids=%s session_id=%s", student_id, lookup_ids, session_id)
        raise HTTPException(
            status_code=404,
            detail="No stored profile or interactions found for this student",
        )
    try:
        events = [InteractionEvent(**row) for row in rows]
        profile = predict_profile(student_id=student_id, events=events, session_id=session_id)
        _insert_profile_or_raise(profile)
        return profile
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to generate profile from interactions: %s", e)
        raise HTTPException(status_code=500, detail=f"Profile generation failed: {str(e)}")


@router.get("/{student_id}/history", response_model=List[CognitiveProfile])
def get_history(student_id: str, limit: int = Query(default=20, ge=1, le=100)):
    """Return all previous cognitive profile records for a student (plan Section 7.2)."""
    lookup_ids = _student_lookup_ids(student_id)
    logger.info("Profile history requested: student_id=%s lookup_ids=%s limit=%s", student_id, lookup_ids, limit)
    try:
        profiles = supabase_client.fetch_profile_history_for_student_ids(lookup_ids, limit=limit)
        if not profiles:
            return []
        logger.info("Profile history found: student_id=%s rows=%s", student_id, len(profiles))
        return profiles
    except Exception as e:
        logger.error("Failed to fetch profile history: %s", e)
        return []
