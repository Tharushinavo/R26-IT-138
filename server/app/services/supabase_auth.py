"""Supabase-based authentication service.
Register / login via Supabase Auth so credentials live in Supabase permanently.
User metadata is also written to the public user_profiles and students tables.
JWT tokens are minted locally so the FastAPI app can validate them without
calling Supabase on every request.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Literal

import jwt
from email_validator import validate_email, EmailNotValidError

from app.config import get_settings
from app.services.supabase_client import get_client, upsert_teacher

try:
    from supabase import create_client  # type: ignore
except Exception:  # pragma: no cover
    create_client = None  # type: ignore

log = logging.getLogger(__name__)

UserRole = Literal["student", "teacher", "parent", "admin"]
_auth_client: Optional[Any] = None


# ── JWT helpers ──────────────────────────────────────────────────────────

def create_access_token(
    user_id: str,
    role: UserRole,
    email: str = "",
    full_name: str = "",
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token that embeds user info so we never
    need a DB round-trip to validate it."""
    settings = get_settings()
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)

    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "email": email,
        "full_name": full_name,
        "exp": now + expires_delta,
        "iat": now,
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify a JWT token.
    Returns payload dict or ``None`` for any invalid / expired token."""
    settings = get_settings()
    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError:
        log.debug("Token expired")
        return None
    except jwt.InvalidTokenError as exc:
        log.debug("Invalid token: %s", exc)
        return None


# ── Email validation ─────────────────────────────────────────────────────

def validate_email_address(email: str) -> tuple[bool, Optional[str]]:
    """Validate an email address. Returns (is_valid, normalized_email or error_message)."""
    try:
        validation = validate_email(email, check_deliverability=False)
        return True, validation.email
    except EmailNotValidError as e:
        return False, str(e)


def get_password_auth_client() -> Optional[Any]:
    """Dedicated Supabase client for password auth.

    Password sign-in mutates the client session. This must stay separate from
    the service-role database client, otherwise later inserts run under RLS.
    """
    global _auth_client
    if _auth_client is not None:
        return _auth_client
    settings = get_settings()
    url = settings.supabase_url.strip()
    key = settings.supabase_anon_key.strip() or settings.supabase_service_role_key.strip()
    if not url or not key or "your-" in url or "your-" in key or create_client is None:
        return None
    try:
        _auth_client = create_client(url, key)
    except Exception:
        log.exception("Password auth Supabase client initialization failed")
        _auth_client = None
    return _auth_client


def ensure_teacher_row(user_id: str, full_name: str, email: str = "") -> None:
    """Best-effort write to the public teachers table.

    The main user list remains user_profiles; teachers is the role-specific
    table used for teacher/admin metadata once the schema has been applied.
    """
    upsert_teacher({
        "id": user_id,
        "full_name": full_name,
        "email": email,
    })


def ensure_student_row(user_id: str, full_name: str, grade: Optional[str] = None) -> None:
    """Best-effort write to the students table for student accounts."""
    supabase = get_client()
    if supabase is None:
        log.warning("Student row ensure skipped: no Supabase client user_id=%s", user_id)
        return
    try:
        existing = supabase.table("students").select("*").eq("user_id", user_id).limit(1).execute()
        if getattr(existing, "data", None):
            return
        supabase.table("students").insert({
            "user_id": user_id,
            "student_code": f"STU{user_id[:8].upper()}",
            "name": full_name,
            "grade": grade,
        }).execute()
        log.info("Student row auto-created for user_id=%s", user_id)
    except Exception:
        log.exception("Student row ensure failed for user_id=%s", user_id)


# ── Register ─────────────────────────────────────────────────────────────

def register_user(
    email: str,
    password: str,
    full_name: str,
    role: UserRole = "student",
    grade: Optional[str] = None,
) -> tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """Register a new user via **Supabase Auth admin API** then write rows
    into ``user_profiles`` (and ``students`` if role == student).
    Returns ``(success, error_or_none, user_dict_or_none)``."""

    # ── input validation ──
    is_valid, result = validate_email_address(email)
    if not is_valid:
        return False, f"Invalid email: {result}", None
    email = result.lower()

    if len(password) < 6:
        return False, "Password must be at least 6 characters", None
    if not full_name or len(full_name.strip()) < 2:
        return False, "Full name must be at least 2 characters", None

    supabase = get_client()
    if supabase is None:
        log.error("Supabase client unavailable – cannot register")
        return False, "Server configuration error", None

    # ── 1. Create auth user ──
    try:
        auth_res = supabase.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {
                "full_name": full_name.strip(),
                "role": role,
                "grade": grade,
            },
        })
    except Exception as exc:
        msg = str(exc).lower()
        if "already registered" in msg or "duplicate" in msg or "already been registered" in msg:
            return False, "Email already registered", None
        log.exception("Supabase auth.admin.create_user failed")
        return False, f"Registration failed: {exc}", None

    user = getattr(auth_res, "user", None)
    if user is None:
        return False, "Supabase did not return a user object", None

    user_id: str = user.id
    log.info("Supabase Auth user created: %s (%s)", user_id, email)

    # ── 2. Insert into user_profiles ──
    try:
        supabase.table("user_profiles").insert({
            "id": user_id,
            "full_name": full_name.strip(),
            "role": role,
            "grade": grade,
        }).execute()
        log.info("user_profiles row inserted for %s", user_id)
    except Exception as exc:
        log.exception("Failed to insert user_profiles for %s", user_id)
        # Auth user exists but profile insert failed – still return success
        # so the user can log in; profile row will be created on next login.

    # ── 3. Insert into students (if applicable) ──
    if role == "student":
        try:
            supabase.table("students").insert({
                "user_id": user_id,
                "student_code": f"STU{user_id[:8].upper()}",
                "name": full_name.strip(),
                "grade": grade,
            }).execute()
            log.info("students row inserted for %s", user_id)
        except Exception as exc:
            log.exception("Failed to insert students for %s", user_id)
    elif role in ("teacher", "admin"):
        ensure_teacher_row(user_id, full_name.strip(), email)

    created = user.created_at
    return True, None, {
        "id": user_id,
        "email": email,
        "full_name": full_name.strip(),
        "role": role,
        "grade": grade,
        "created_at": created.isoformat() if created else datetime.now(timezone.utc).isoformat(),
    }


# ── Login ────────────────────────────────────────────────────────────────

def authenticate_user(
    email: str, password: str,
) -> tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """Authenticate via Supabase ``sign_in_with_password``.
    Credentials are validated by Supabase – they remain valid forever
    (no expiry on the Supabase side). Only our local JWT session expires."""

    email = email.lower().strip()
    auth_client = get_password_auth_client()
    supabase = get_client()
    if auth_client is None or supabase is None:
        log.error("Supabase client unavailable – cannot authenticate")
        return False, "Server configuration error", None

    try:
        auth_res = auth_client.auth.sign_in_with_password({
            "email": email,
            "password": password,
        })
    except Exception as exc:
        log.warning("sign_in_with_password failed for %s: %s", email, exc)
        return False, "Invalid email or password", None

    user = getattr(auth_res, "user", None)
    if user is None:
        return False, "Invalid email or password", None

    user_id: str = user.id
    meta = getattr(user, "user_metadata", None) or {}

    # Try to read profile row (may not exist if insert failed during register)
    profile: Optional[Dict[str, Any]] = None
    try:
        res = supabase.table("user_profiles").select("*").eq("id", user_id).execute()
        if res.data:
            profile = res.data[0]
    except Exception:
        log.exception("Could not read user_profiles for %s", user_id)

    # If profile row is missing, auto-heal by inserting it now
    if profile is None:
        try:
            supabase.table("user_profiles").insert({
                "id": user_id,
                "full_name": meta.get("full_name", ""),
                "role": meta.get("role", "student"),
                "grade": meta.get("grade"),
            }).execute()
            log.info("Auto-healed user_profiles for %s", user_id)
            res2 = supabase.table("user_profiles").select("*").eq("id", user_id).execute()
            if res2.data:
                profile = res2.data[0]
        except Exception:
            log.exception("Auto-heal user_profiles failed for %s", user_id)

    full_name = (profile or {}).get("full_name") or meta.get("full_name", "")
    role_val = (profile or {}).get("role") or meta.get("role", "student")
    grade_val = (profile or {}).get("grade") or meta.get("grade")
    created = user.created_at

    if role_val in ("teacher", "admin"):
        ensure_teacher_row(user_id, full_name, getattr(user, "email", email))
    elif role_val == "student":
        ensure_student_row(user_id, full_name, grade_val)

    avatar_url = (profile or {}).get("avatar_url")

    return True, None, {
        "id": user_id,
        "email": getattr(user, "email", email),
        "full_name": full_name,
        "role": role_val,
        "grade": grade_val,
        "avatar_url": avatar_url,
        "created_at": created.isoformat() if created else datetime.now(timezone.utc).isoformat(),
    }


# ── Token → user lookup ─────────────────────────────────────────────────

def get_current_user_from_token(token: str) -> Optional[Dict[str, Any]]:
    """Extract user info embedded in the JWT – no DB call needed."""
    payload = decode_token(token)
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    return {
        "id": user_id,
        "email": payload.get("email"),
        "full_name": payload.get("full_name"),
        "role": payload.get("role", "student"),
        "grade": payload.get("grade"),
    }


# ── Convenience helpers ──────────────────────────────────────────────────

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by ID from Supabase (without password)."""
    supabase = get_client()
    if not supabase:
        return None
    try:
        res = supabase.table("user_profiles").select("*").eq("id", user_id).execute()
        if not res.data:
            return None
        p = res.data[0]
        return {
            "id": p.get("id"),
            "full_name": p.get("full_name"),
            "role": p.get("role"),
            "grade": p.get("grade"),
            "created_at": p.get("created_at"),
        }
    except Exception:
        return None


def update_user_profile(
    user_id: str,
    full_name: Optional[str] = None,
    password: Optional[str] = None,
    avatar_url: Optional[str] = None,
) -> tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """Update user profile fields in Supabase.
    - full_name: updates user_profiles table + auth metadata
    - password: updates Supabase Auth password
    - avatar_url: updates user_profiles table
    Returns (success, error_or_none, updated_user_dict_or_none)."""

    supabase = get_client()
    if supabase is None:
        return False, "Server configuration error", None

    # Build updates for user_profiles table
    profile_patch: Dict[str, Any] = {}
    if full_name is not None:
        if len(full_name.strip()) < 2:
            return False, "Full name must be at least 2 characters", None
        profile_patch["full_name"] = full_name.strip()
    if avatar_url is not None:
        profile_patch["avatar_url"] = avatar_url

    # Update user_profiles table
    if profile_patch:
        try:
            supabase.table("user_profiles").update(profile_patch).eq("id", user_id).execute()
            log.info("user_profiles updated for %s: %s", user_id, list(profile_patch.keys()))
        except Exception as exc:
            log.exception("Failed to update user_profiles for %s", user_id)
            return False, f"Profile update failed: {exc}", None

    # Update Supabase Auth metadata (full_name) and/or password
    auth_patch: Dict[str, Any] = {}
    if full_name is not None:
        auth_patch["user_metadata"] = {"full_name": full_name.strip()}
    if password is not None:
        if len(password) < 6:
            return False, "Password must be at least 6 characters", None
        auth_patch["password"] = password

    if auth_patch:
        try:
            supabase.auth.admin.update_user_by_id(user_id, auth_patch)
            log.info("Supabase Auth updated for %s: %s", user_id, list(auth_patch.keys()))
        except Exception as exc:
            log.exception("Failed to update Supabase Auth for %s", user_id)
            return False, f"Auth update failed: {exc}", None

    # Also update students table name if applicable
    if full_name is not None:
        try:
            supabase.table("students").update({"name": full_name.strip()}).eq("user_id", user_id).execute()
        except Exception:
            pass  # best-effort

    # Return updated profile
    try:
        res = supabase.table("user_profiles").select("*").eq("id", user_id).execute()
        if res.data:
            p = res.data[0]
            return True, None, {
                "id": p.get("id"),
                "full_name": p.get("full_name"),
                "role": p.get("role"),
                "grade": p.get("grade"),
                "avatar_url": p.get("avatar_url"),
            }
    except Exception:
        pass

    return True, None, {"id": user_id}


def list_all_users(role: Optional[UserRole] = None) -> list[Dict[str, Any]]:
    """List all users from Supabase, optionally filtered by role."""
    supabase = get_client()
    if not supabase:
        return []
    try:
        q = supabase.table("user_profiles").select("*")
        if role:
            q = q.eq("role", role)
        res = q.execute()
        return [
            {
                "id": p.get("id"),
                "full_name": p.get("full_name"),
                "role": p.get("role"),
                "grade": p.get("grade"),
                "created_at": p.get("created_at"),
            }
            for p in (res.data or [])
        ]
    except Exception:
        return []
