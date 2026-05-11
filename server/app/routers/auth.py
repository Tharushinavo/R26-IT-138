"""Authentication router – Supabase Auth backed.
Endpoints:
- POST /auth/register  – create user in Supabase Auth + user_profiles table
- POST /auth/login     – validate via Supabase, return local JWT
- GET  /auth/me        – return current user from JWT
- POST /auth/refresh   – mint a fresh JWT
"""
from __future__ import annotations


import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Header

from app.schemas import UserRegister, UserLogin, UserProfile, UserProfileUpdate
from app.services import supabase_auth

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


# ── Dependencies ─────────────────────────────────────────────────────────

def get_token_from_header(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """Extract Bearer token from Authorization header."""
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def get_current_user(token: Optional[str] = Depends(get_token_from_header)) -> dict:
    """Dependency – extracts user from JWT (no DB call)."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = supabase_auth.get_current_user_from_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_teacher(current_user: dict = Depends(get_current_user)) -> dict:
    """Dependency that requires teacher role."""
    if current_user.get("role") not in ["teacher", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher access required",
        )
    return current_user


# ── Endpoints ────────────────────────────────────────────────────────────

@router.post("/register", response_model=dict)
def register(user_data: UserRegister):
    """Register a new user account via Supabase Auth."""
    logger.info("Auth register requested: email=%s role=%s", user_data.email.lower().strip(), user_data.role)
    success, error, user = supabase_auth.register_user(
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name,
        role=user_data.role,
    )
    if not success:
        logger.warning("Auth register failed: email=%s error=%s", user_data.email.lower().strip(), error)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error or "Registration failed",
        )

    logger.info("Auth register succeeded: user_id=%s role=%s", user["id"], user["role"])
    token = supabase_auth.create_access_token(
        user_id=user["id"],
        role=user["role"],
        email=user.get("email", ""),
        full_name=user.get("full_name", ""),
    )
    settings = supabase_auth.get_settings()
    return {
        "message": "User registered successfully",
        "user": user,
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
    }


@router.post("/login", response_model=dict)
def login(credentials: UserLogin):
    """Login via Supabase Auth and receive a local JWT."""
    logger.info("Auth login requested: email=%s", credentials.email.lower().strip())
    success, error, user = supabase_auth.authenticate_user(
        email=credentials.email,
        password=credentials.password,
    )
    if not success:
        logger.warning("Auth login failed: email=%s error=%s", credentials.email.lower().strip(), error)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error or "Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info("Auth login succeeded: user_id=%s role=%s", user["id"], user["role"])
    token = supabase_auth.create_access_token(
        user_id=user["id"],
        role=user["role"],
        email=user.get("email", ""),
        full_name=user.get("full_name", ""),
    )
    settings = supabase_auth.get_settings()
    return {
        "message": "Login successful",
        "user": user,
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
    }


@router.get("/me", response_model=UserProfile)
def get_me(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user's profile (from JWT)."""
    return UserProfile(
        id=current_user["id"],
        email=current_user.get("email"),
        full_name=current_user.get("full_name"),
        role=current_user.get("role", "student"),
    )


@router.put("/profile", response_model=dict)
def update_profile(
    updates: UserProfileUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update current user's profile (name, password, avatar)."""
    if not updates.full_name and not updates.password and updates.avatar_url is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    success, error, user = supabase_auth.update_user_profile(
        user_id=current_user["id"],
        full_name=updates.full_name,
        password=updates.password,
        avatar_url=updates.avatar_url,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error or "Update failed",
        )

    # Mint a fresh token with updated info so client stays in sync
    updated_name = (user or {}).get("full_name") or current_user.get("full_name", "")
    new_token = supabase_auth.create_access_token(
        user_id=current_user["id"],
        role=current_user.get("role", "student"),
        email=current_user.get("email", ""),
        full_name=updated_name,
    )
    settings = supabase_auth.get_settings()
    return {
        "message": "Profile updated successfully",
        "user": {
            "id": current_user["id"],
            "email": current_user.get("email"),
            "full_name": updated_name,
            "role": current_user.get("role", "student"),
            "avatar_url": (user or {}).get("avatar_url"),
        },
        "access_token": new_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
    }


@router.post("/refresh", response_model=dict)
def refresh_token(current_user: dict = Depends(get_current_user)):
    """Refresh access token (get new token with extended expiry)."""
    new_token = supabase_auth.create_access_token(
        user_id=current_user["id"],
        role=current_user.get("role", "student"),
        email=current_user.get("email", ""),
        full_name=current_user.get("full_name", ""),
    )
    settings = supabase_auth.get_settings()
    return {
        "access_token": new_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
    }
