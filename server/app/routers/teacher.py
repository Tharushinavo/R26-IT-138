"""Teacher dashboard endpoints (plan Section 7.2).
GET /teacher/students/{student_id}/summary
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException

from app.schemas import StudentSummary, CognitiveProfile
from app.services import supabase_client

router = APIRouter(prefix="/teacher", tags=["teacher"])


@router.get("/students/{student_id}/summary", response_model=StudentSummary)
def get_student_summary(student_id: str) -> StudentSummary:
    """Return student interaction summary and latest cognitive profile."""
    # Get latest profile
    latest_profile_data = supabase_client.fetch_latest_profile(student_id)
    latest_profile = None
    if latest_profile_data:
        try:
            latest_profile = CognitiveProfile(**latest_profile_data)
        except Exception:
            pass

    # Get interaction count
    events = supabase_client.fetch_user_events(student_id)
    total_interactions = len(events)

    last_activity_date = None
    if events:
        last = events[-1]
        last_activity_date = str(last.get("created_at", ""))

    return StudentSummary(
        student_id=student_id,
        total_interactions=total_interactions,
        latest_profile=latest_profile,
        last_activity_date=last_activity_date,
    )


@router.get("/students", response_model=List[StudentSummary])
def list_students() -> List[StudentSummary]:
    """Return a list of all students with their latest profiles.
    Falls back to an empty list if Supabase is not configured.
    """
    students = supabase_client.fetch_all_students()
    if not students:
        return []

    summaries = []
    for s in students:
        sid = s.get("id") or s.get("student_id", "")
        latest_data = supabase_client.fetch_latest_profile(sid)
        latest_profile = None
        if latest_data:
            try:
                latest_profile = CognitiveProfile(**latest_data)
            except Exception:
                pass

        events = supabase_client.fetch_user_events(sid)
        last_date = None
        if events:
            last_date = str(events[-1].get("created_at", ""))

        summaries.append(StudentSummary(
            student_id=sid,
            student_code=s.get("student_code"),
            name=s.get("name"),
            total_interactions=len(events),
            latest_profile=latest_profile,
            last_activity_date=last_date,
        ))

    return summaries
