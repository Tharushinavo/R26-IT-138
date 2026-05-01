"""Thin Supabase wrapper. Safe to import even when credentials are absent:
the client is created lazily and calls become no-ops so the API still runs
in local development without Supabase configured.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.config import get_settings

try:
    from supabase import create_client, Client  # type: ignore
except Exception:  # pragma: no cover
    create_client = None  # type: ignore
    Client = Any  # type: ignore


_client: Optional[Any] = None


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
        return {"inserted": 0, "skipped": True}
    res = client.table("interactions").insert(events).execute()
    data = getattr(res, "data", None) or []
    return {"inserted": len(data), "skipped": False}


def fetch_user_events(student_id: str, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
    client = get_client()
    if client is None:
        return []
    q = client.table("interactions").select("*").eq("student_id", student_id)
    if session_id:
        q = q.eq("session_id", session_id)
    res = q.order("created_at", desc=False).execute()
    return getattr(res, "data", None) or []


# ── Cognitive Profiles ──

def insert_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    client = get_client()
    if client is None:
        return {"inserted": 0, "skipped": True}
    res = client.table("cognitive_profiles").insert(profile).execute()
    data = getattr(res, "data", None) or []
    return {"inserted": len(data), "skipped": False}


def fetch_latest_profile(student_id: str) -> Optional[Dict[str, Any]]:
    client = get_client()
    if client is None:
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
    return data[0] if data else None


def fetch_profile_history(student_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    client = get_client()
    if client is None:
        return []
    res = (
        client.table("cognitive_profiles")
        .select("*")
        .eq("student_id", student_id)
        .order("generated_at", desc=True)
        .limit(limit)
        .execute()
    )
    return getattr(res, "data", None) or []


# ── Questions ──

def fetch_questions(
    topic: Optional[str] = None,
    difficulty: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    client = get_client()
    if client is None:
        return []
    q = client.table("questions").select("*")
    if topic:
        q = q.eq("topic", topic)
    if difficulty:
        q = q.eq("difficulty", difficulty)
    res = q.limit(limit).execute()
    return getattr(res, "data", None) or []


# ── Students ──

def fetch_all_students() -> List[Dict[str, Any]]:
    client = get_client()
    if client is None:
        return []
    res = client.table("students").select("*").execute()
    return getattr(res, "data", None) or []


def fetch_student(student_id: str) -> Optional[Dict[str, Any]]:
    client = get_client()
    if client is None:
        return None
    res = (
        client.table("students")
        .select("*")
        .eq("id", student_id)
        .limit(1)
        .execute()
    )
    data = getattr(res, "data", None) or []
    return data[0] if data else None
