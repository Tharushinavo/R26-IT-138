"""Thin Supabase wrapper. Safe to import even when credentials are absent:
the client is created lazily and calls become no-ops so the API still runs
in local development without Supabase configured.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.config import get_settings

try:
    from supabase import create_client, Client  # type: ignore
except Exception:  # pragma: no cover
    create_client = None  # type: ignore
    Client = Any  # type: ignore


_client: Optional[Any] = None
log = logging.getLogger(__name__)


_init_attempted: bool = False


def get_client() -> Optional[Any]:
    global _client, _init_attempted
    if _client is not None:
        return _client
    if _init_attempted:
        return None
    _init_attempted = True
    settings = get_settings()
    url = settings.supabase_url.strip()
    key = settings.supabase_service_role_key.strip()
    if not url or not key or "your-" in url or "your-" in key:
        return None
    if create_client is None:
        return None
    try:
        _client = create_client(url, key)
    except Exception:
        _client = None
    return _client


# ── Interactions ──

def insert_interactions(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    client = get_client()
    if client is None or not events:
        log.warning("Supabase insert_interactions skipped: client=%s events=%s", bool(client), len(events))
        return {"inserted": 0, "skipped": True}
    res = client.table("interactions").insert(events).execute()
    data = getattr(res, "data", None) or []
    log.info("Supabase insert_interactions completed: requested=%s inserted=%s", len(events), len(data))
    return {"inserted": len(data), "skipped": False}


def fetch_user_events(student_id: str, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
    client = get_client()
    if client is None:
        log.warning("Supabase fetch_user_events skipped: no client student_id=%s", student_id)
        return []
    q = client.table("interactions").select("*").eq("student_id", student_id)
    if session_id:
        q = q.eq("session_id", session_id)
    res = q.order("created_at", desc=False).execute()
    data = getattr(res, "data", None) or []
    log.info("Supabase fetch_user_events completed: student_id=%s session_id=%s rows=%s", student_id, session_id, len(data))
    return data


# ── Cognitive Profiles ──

def insert_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    client = get_client()
    if client is None:
        log.warning("Supabase insert_profile skipped: no client student_id=%s", profile.get("student_id"))
        return {"inserted": 0, "skipped": True}
    res = client.table("cognitive_profiles").insert(profile).execute()
    data = getattr(res, "data", None) or []
    log.info(
        "Supabase insert_profile completed: student_id=%s session_id=%s inserted=%s",
        profile.get("student_id"),
        profile.get("session_id"),
        len(data),
    )
    return {"inserted": len(data), "skipped": False}


def fetch_latest_profile(student_id: str) -> Optional[Dict[str, Any]]:
    client = get_client()
    if client is None:
        log.warning("Supabase fetch_latest_profile skipped: no client student_id=%s", student_id)
        return None
    res = (
        client.table("cognitive_profiles")
        .select("*")
        .eq("student_id", student_id)
        .order("generated_at", desc=True)
        .limit(1)
        .execute()
    )
    data = getattr(res, "data", None) or []
    log.info("Supabase fetch_latest_profile completed: student_id=%s rows=%s", student_id, len(data))
    return data[0] if data else None


def fetch_profile_history(student_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    client = get_client()
    if client is None:
        log.warning("Supabase fetch_profile_history skipped: no client student_id=%s", student_id)
        return []
    res = (
        client.table("cognitive_profiles")
        .select("*")
        .eq("student_id", student_id)
        .order("generated_at", desc=True)
        .limit(limit)
        .execute()
    )
    data = getattr(res, "data", None) or []
    log.info("Supabase fetch_profile_history completed: student_id=%s rows=%s", student_id, len(data))
    return data


def fetch_latest_profile_for_student_ids(student_ids: List[str]) -> Optional[Dict[str, Any]]:
    """Return the newest profile matching any known identifier for a student."""
    client = get_client()
    ids = [str(sid) for sid in student_ids if sid]
    if client is None or not ids:
        log.warning("Supabase fetch_latest_profile_for_student_ids skipped: client=%s ids=%s", bool(client), len(ids))
        return None
    try:
        res = (
            client.table("cognitive_profiles")
            .select("*")
            .in_("student_id", ids)
            .order("generated_at", desc=True)
            .limit(1)
            .execute()
        )
        data = getattr(res, "data", None) or []
        log.info("Supabase fetch_latest_profile_for_student_ids completed: ids=%s rows=%s", ids, len(data))
        return data[0] if data else None
    except Exception:
        log.exception("Supabase fetch_latest_profile_for_student_ids failed: ids=%s", ids)
        return None


def fetch_profile_history_for_student_ids(student_ids: List[str], limit: int = 20) -> List[Dict[str, Any]]:
    client = get_client()
    ids = [str(sid) for sid in student_ids if sid]
    if client is None or not ids:
        log.warning("Supabase fetch_profile_history_for_student_ids skipped: client=%s ids=%s", bool(client), len(ids))
        return []
    try:
        res = (
            client.table("cognitive_profiles")
            .select("*")
            .in_("student_id", ids)
            .order("generated_at", desc=True)
            .limit(limit)
            .execute()
        )
        data = getattr(res, "data", None) or []
        log.info("Supabase fetch_profile_history_for_student_ids completed: ids=%s rows=%s", ids, len(data))
        return data
    except Exception:
        log.exception("Supabase fetch_profile_history_for_student_ids failed: ids=%s", ids)
        return []


# ── Questions ──

def fetch_questions(
    topic: Optional[str] = None,
    difficulty: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    client = get_client()
    if client is None:
        return []
    try:
        q = client.table("questions").select("*")
        if topic:
            q = q.eq("topic", topic)
        if difficulty:
            q = q.eq("difficulty", difficulty)
        res = q.order("created_at", desc=True).limit(limit).execute()
        return getattr(res, "data", None) or []
    except Exception:
        return []


def insert_question(question: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    client = get_client()
    if client is None:
        return None
    res = client.table("questions").insert(question).execute()
    data = getattr(res, "data", None) or []
    return data[0] if data else None


def update_question(question_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    client = get_client()
    if client is None:
        return None
    res = (
        client.table("questions")
        .update(patch)
        .eq("id", question_id)
        .execute()
    )
    data = getattr(res, "data", None) or []
    return data[0] if data else None


def delete_question(question_id: str) -> bool:
    client = get_client()
    if client is None:
        return False
    res = client.table("questions").delete().eq("id", question_id).execute()
    data = getattr(res, "data", None)
    return data is not None


# â”€â”€ Teachers â”€â”€

def upsert_teacher(teacher: Dict[str, Any]) -> bool:
    client = get_client()
    if client is None:
        return False
    try:
        client.table("teachers").upsert(teacher).execute()
        return True
    except Exception:
        return False


# ── Students ──

def fetch_all_students() -> List[Dict[str, Any]]:
    client = get_client()
    if client is None:
        return []
    try:
        res = client.table("students").select("*").execute()
        return getattr(res, "data", None) or []
    except Exception:
        return []


def fetch_students_for_teacher(teacher_id: str, include_all_if_empty: bool = True) -> List[Dict[str, Any]]:
    """Fetch students assigned to a teacher, with an all-students fallback for older data."""
    client = get_client()
    if client is None:
        return []
    try:
        res = (
            client.table("students")
            .select("*")
            .eq("teacher_id", teacher_id)
            .execute()
        )
        assigned = getattr(res, "data", None) or []
    except Exception:
        assigned = []
    if assigned or not include_all_if_empty:
        return assigned
    return fetch_all_students()


def fetch_user_profiles(role: Optional[str] = None) -> List[Dict[str, Any]]:
    client = get_client()
    if client is None:
        return []
    try:
        q = client.table("user_profiles").select("*")
        if role:
            q = q.eq("role", role)
        res = q.execute()
        return getattr(res, "data", None) or []
    except Exception:
        return []


def fetch_student(student_id: str) -> Optional[Dict[str, Any]]:
    client = get_client()
    if client is None:
        return None
    try:
        res = (
            client.table("students")
            .select("*")
            .eq("id", student_id)
            .limit(1)
            .execute()
        )
        data = getattr(res, "data", None) or []
        return data[0] if data else None
    except Exception:
        log.exception("Supabase fetch_student failed: student_id=%s", student_id)
        return None


def fetch_students_by_user_id(user_id: str) -> List[Dict[str, Any]]:
    client = get_client()
    if client is None:
        return []
    try:
        res = (
            client.table("students")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        return getattr(res, "data", None) or []
    except Exception:
        log.exception("Supabase fetch_students_by_user_id failed: user_id=%s", user_id)
        return []


def fetch_events_for_student_ids(student_ids: List[str], session_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch interactions stored against either auth user id or student row id."""
    client = get_client()
    ids = [str(sid) for sid in student_ids if sid]
    if client is None or not ids:
        return []
    try:
        q = client.table("interactions").select("*").in_("student_id", ids)
        if session_id:
            q = q.eq("session_id", session_id)
        res = q.order("created_at", desc=False).execute()
        data = getattr(res, "data", None) or []
        log.info("Supabase fetch_events_for_student_ids completed: ids=%s session_id=%s rows=%s", ids, session_id, len(data))
        return data
    except Exception:
        log.exception("Supabase fetch_events_for_student_ids failed: ids=%s session_id=%s", ids, session_id)
        return []
