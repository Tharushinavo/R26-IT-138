"""Authentication service with JWT and bcrypt.
Handles password hashing, token encoding/decoding, and user management.
Uses a simple JSON file store for users (can be swapped for Supabase later).
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Literal

import jwt
import bcrypt
from email_validator import validate_email, EmailNotValidError

from app.config import get_settings

UserRole = Literal["student", "teacher", "parent", "admin"]

# Path to local user store (JSON file)
# In production, migrate to Supabase auth or a proper database
USER_STORE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "users.json")

# Ensure data directory exists
os.makedirs(os.path.dirname(USER_STORE_PATH), exist_ok=True)


def _load_users() -> Dict[str, Dict[str, Any]]:
    """Load users from JSON file."""
    if not os.path.exists(USER_STORE_PATH):
        return {}
    try:
        with open(USER_STORE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _save_users(users: Dict[str, Dict[str, Any]]) -> None:
    """Save users to JSON file."""
    with open(USER_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    plain_bytes = plain_password.encode("utf-8")
    hash_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(plain_bytes, hash_bytes)


def create_access_token(user_id: str, role: UserRole, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    settings = get_settings()
    
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    
    expire = datetime.now(timezone.utc) + expires_delta
    
    payload = {
        "sub": user_id,  # subject (user id)
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),  # issued at
        "type": "access"
    }
    
    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    return token


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify a JWT token. Returns payload or None if invalid."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_current_user_from_token(token: str) -> Optional[Dict[str, Any]]:
    """Get current user info from a token, including full profile from store."""
    payload = decode_token(token)
    if not payload:
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    users = _load_users()
    user = users.get(user_id)
    if not user:
        return None
    
    return {
        "id": user_id,
        "email": user.get("email"),
        "full_name": user.get("full_name"),
        "role": user.get("role"),
        "grade": user.get("grade"),
        "created_at": user.get("created_at")
    }


def validate_email_address(email: str) -> tuple[bool, Optional[str]]:
    """Validate an email address. Returns (is_valid, normalized_email or error_message)."""
    try:
        validation = validate_email(email, check_deliverability=False)
        return True, validation.email
    except EmailNotValidError as e:
        return False, str(e)


def register_user(
    email: str,
    password: str,
    full_name: str,
    role: UserRole = "student",
    grade: Optional[str] = None
) -> tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Register a new user.
    Returns: (success, error_message_or_none, user_data_or_none)
    """
    # Validate email
    is_valid, normalized_email = validate_email_address(email)
    if not is_valid:
        return False, f"Invalid email: {normalized_email}", None
    
    email = normalized_email.lower()
    
    # Validate password
    if len(password) < 6:
        return False, "Password must be at least 6 characters", None
    
    # Validate full_name
    if not full_name or len(full_name.strip()) < 2:
        return False, "Full name must be at least 2 characters", None
    
    users = _load_users()
    
    # Check if email already exists
    for user in users.values():
        if user.get("email") == email:
            return False, "Email already registered", None
    
    # Create user
    user_id = str(uuid.uuid4())
    hashed_password = hash_password(password)
    
    user_data = {
        "id": user_id,
        "email": email,
        "password_hash": hashed_password,
        "full_name": full_name.strip(),
        "role": role,
        "grade": grade,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    users[user_id] = user_data
    _save_users(users)
    
    # Return user data without password
    return True, None, {
        "id": user_id,
        "email": email,
        "full_name": full_name.strip(),
        "role": role,
        "grade": grade,
        "created_at": user_data["created_at"]
    }


def authenticate_user(email: str, password: str) -> tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Authenticate a user with email and password.
    Returns: (success, error_message_or_none, user_data_or_none)
    """
    email = email.lower().strip()
    users = _load_users()
    
    # Find user by email
    user = None
    for u in users.values():
        if u.get("email") == email:
            user = u
            break
    
    if not user:
        return False, "Invalid email or password", None
    
    # Verify password
    if not verify_password(password, user.get("password_hash", "")):
        return False, "Invalid email or password", None
    
    # Return user data without password
    return True, None, {
        "id": user.get("id"),
        "email": user.get("email"),
        "full_name": user.get("full_name"),
        "role": user.get("role"),
        "grade": user.get("grade"),
        "created_at": user.get("created_at")
    }


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by ID (without password)."""
    users = _load_users()
    user = users.get(user_id)
    if not user:
        return None
    
    return {
        "id": user.get("id"),
        "email": user.get("email"),
        "full_name": user.get("full_name"),
        "role": user.get("role"),
        "grade": user.get("grade"),
        "created_at": user.get("created_at")
    }


def list_all_users(role: Optional[UserRole] = None) -> list[Dict[str, Any]]:
    """List all users, optionally filtered by role (without passwords)."""
    users = _load_users()
    result = []
    for user in users.values():
        if role is None or user.get("role") == role:
            result.append({
                "id": user.get("id"),
                "email": user.get("email"),
                "full_name": user.get("full_name"),
                "role": user.get("role"),
                "grade": user.get("grade"),
                "created_at": user.get("created_at")
            })
    return result
