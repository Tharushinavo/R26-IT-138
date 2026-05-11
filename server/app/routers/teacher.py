"""Teacher dashboard endpoints.

Protected routes require JWT authentication and teacher/admin role.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Optional

from fastapi import APIRouter, Depends

from app.schemas import (
    CognitiveProfile,
    InteractionEvent,
    StudentPerformance,
    StudentSummary,
    TeacherDashboardResponse,
    TeacherDashboardStats,
    TopicPerformance,
)
from app.services import supabase_client
from app.services.features import compute_features
from app.routers.auth import get_current_teacher

router = APIRouter(prefix="/teacher", tags=["teacher"])


def _unique(values: Iterable[Optional[str]]) -> List[str]:
    seen = set()
    result: List[str] = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _student_lookup_ids(row: Dict) -> List[str]:
    return _unique([row.get("user_id"), row.get("student_id"), row.get("id")])


def _student_public_id(row: Dict) -> str:
    ids = _student_lookup_ids(row)
    return ids[0] if ids else ""


def _student_name(row: Dict) -> Optional[str]:
    return row.get("name") or row.get("full_name")


def _student_code(row: Dict, student_id: str) -> Optional[str]:
    return row.get("student_code") or (f"STU{student_id[:8].upper()}" if student_id else None)


def _load_student_rows(current_user: dict) -> List[Dict]:
    role = current_user.get("role")
    teacher_id = str(current_user.get("id", ""))

    if role == "admin":
        student_rows = supabase_client.fetch_all_students()
    else:
        student_rows = supabase_client.fetch_students_for_teacher(teacher_id)

    profile_rows = supabase_client.fetch_user_profiles(role="student")
    profiles_by_id = {str(row.get("id")): row for row in profile_rows if row.get("id")}

    if not student_rows:
        return [
            {
                "id": profile.get("id"),
                "user_id": profile.get("id"),
                "name": profile.get("full_name"),
                "full_name": profile.get("full_name"),
                "grade": profile.get("grade"),
                "created_at": profile.get("created_at"),
            }
            for profile in profile_rows
        ]

    merged: List[Dict] = []
    for row in student_rows:
        copy = dict(row)
        profile = profiles_by_id.get(str(copy.get("user_id")))
        if profile:
            copy.setdefault("full_name", profile.get("full_name"))
            copy["name"] = copy.get("name") or profile.get("full_name")
            copy["grade"] = copy.get("grade") or profile.get("grade")
        merged.append(copy)
    return merged


def _find_student_row(student_id: str, current_user: dict) -> Dict:
    for row in _load_student_rows(current_user):
        if student_id in _student_lookup_ids(row):
            return row
    return {"id": student_id, "user_id": student_id}


def _to_interaction_events(rows: List[Dict]) -> List[InteractionEvent]:
    events: List[InteractionEvent] = []
    for row in rows:
        try:
            events.append(InteractionEvent(**row))
        except Exception:
            continue
    return events


def _topic_performance(events: List[InteractionEvent]) -> List[TopicPerformance]:
    grouped: Dict[str, List[InteractionEvent]] = defaultdict(list)
    for event in events:
        grouped[event.topic].append(event)

    result: List[TopicPerformance] = []
    for topic, topic_events in grouped.items():
        features = compute_features(topic_events)
        result.append(
            TopicPerformance(
                topic=topic,
                total_questions=features.total_questions,
                accuracy=round(features.accuracy, 2),
                avg_response_time_sec=round(features.avg_response_time_ms / 1000, 1),
                retry_rate=round(features.retry_rate, 2),
                hint_rate=round(features.hint_rate, 2),
            )
        )
    result.sort(key=lambda item: item.total_questions, reverse=True)
    return result


def _performance_from_events(events: List[InteractionEvent]) -> StudentPerformance:
    if not events:
        return StudentPerformance()

    features = compute_features(events)
    return StudentPerformance(
        total_questions=features.total_questions,
        completed_sessions=len({event.session_id for event in events}),
        accuracy=round(features.accuracy, 2),
        avg_response_time_sec=round(features.avg_response_time_ms / 1000, 1),
        avg_attempts=round(features.avg_attempts, 2),
        retry_rate=round(features.retry_rate, 2),
        hint_rate=round(features.hint_rate, 2),
        last_topic=events[-1].topic if events else None,
        topics=_topic_performance(events),
    )


def _has_low_profile(profile: Optional[CognitiveProfile]) -> bool:
    if profile is None:
        return False
    return (
        profile.memory_level == "low"
        or profile.attention_level == "low"
        or profile.number_sense_level == "low"
        or profile.processing_speed_level == "Slow"
    )


def _build_student_summary(row: Dict) -> StudentSummary:
    student_id = _student_public_id(row)
    lookup_ids = _student_lookup_ids(row) or [student_id]

    latest_profile_data = supabase_client.fetch_latest_profile_for_student_ids(lookup_ids)
    latest_profile = None
    if latest_profile_data:
        try:
            latest_profile = CognitiveProfile(**latest_profile_data)
        except Exception:
            latest_profile = None

    event_rows = supabase_client.fetch_events_for_student_ids(lookup_ids)
    events = _to_interaction_events(event_rows)
    performance = _performance_from_events(events)

    last_activity_date = None
    if event_rows:
        last_activity_date = str(event_rows[-1].get("created_at", ""))

    return StudentSummary(
        student_id=student_id,
        student_code=_student_code(row, student_id),
        name=_student_name(row),
        grade=row.get("grade"),
        total_interactions=len(events),
        latest_profile=latest_profile,
        last_activity_date=last_activity_date,
        performance=performance,
    )


def _dashboard_stats(students: List[StudentSummary]) -> TeacherDashboardStats:
    with_activity = [s for s in students if s.performance.total_questions > 0]
    total_questions = sum(s.performance.total_questions for s in students)
    total_response_time = sum(
        s.performance.avg_response_time_sec * s.performance.total_questions
        for s in students
    )
    avg_accuracy = (
        sum(s.performance.accuracy * s.performance.total_questions for s in students) / total_questions
        if total_questions
        else 0.0
    )
    avg_response = total_response_time / total_questions if total_questions else 0.0
    needs_support = sum(
        1
        for s in students
        if _has_low_profile(s.latest_profile)
        or (s.performance.total_questions >= 5 and s.performance.accuracy < 0.6)
    )

    return TeacherDashboardStats(
        total_students=len(students),
        students_with_profiles=sum(1 for s in students if s.latest_profile is not None),
        total_interactions=sum(s.total_interactions for s in students),
        average_accuracy=round(avg_accuracy, 2) if with_activity else 0.0,
        average_response_time_sec=round(avg_response, 1) if with_activity else 0.0,
        needs_support_count=needs_support,
    )


@router.get("/students/{student_id}/summary", response_model=StudentSummary)
def get_student_summary(
    student_id: str,
    current_user: dict = Depends(get_current_teacher)
) -> StudentSummary:
    """Return student interaction summary and latest cognitive profile."""
    return _build_student_summary(_find_student_row(student_id, current_user))


@router.get("/students", response_model=List[StudentSummary])
def list_students(current_user: dict = Depends(get_current_teacher)) -> List[StudentSummary]:
    """Return students with cognitive profiles and performance summaries."""
    return [_build_student_summary(row) for row in _load_student_rows(current_user)]


@router.get("/dashboard", response_model=TeacherDashboardResponse)
def dashboard(current_user: dict = Depends(get_current_teacher)) -> TeacherDashboardResponse:
    """Return class-level dashboard stats plus student rows."""
    students = list_students(current_user)
    return TeacherDashboardResponse(stats=_dashboard_stats(students), students=students)
