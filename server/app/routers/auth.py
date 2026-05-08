"""Authentication router for JWT-based auth.
Endpoints:
- POST /auth/register - Register new user
- POST /auth/login - Login and get JWT token
- GET /auth/me - Get current user profile
"""
from __future__ import annotations

from typing import Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.schemas import UserRegister, UserLogin, UserProfile
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


def get_token_from_header(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """Extract Bearer token from Authorization header."""
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


async def get_current_user(token: Optional[str] = Depends(get_token_from_header)) -> dict:
    """Dependency to get current authenticated user."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user = auth_service.get_current_user_from_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return user


async def get_current_teacher(current_user: dict = Depends(get_current_user)) -> dict:
    """Dependency that requires teacher role."""
    if current_user.get("role") not in ["teacher", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher access required"
        )
    return current_user


@router.post("/register", response_model=dict)
def register(user_data: UserRegister):
    """Register a new user account."""
    success, error, user = auth_service.register_user(
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name,
        role=user_data.role
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error or "Registration failed"
        )
    
    # Create access token
    token = auth_service.create_access_token(
        user_id=user["id"],
        role=user["role"]
    )
    
    return {
        "message": "User registered successfully",
        "user": user,
        "access_token": token,
        "token_type": "bearer"
    }


@router.post("/login", response_model=dict)
def login(credentials: UserLogin):
    """Login and receive JWT access token."""
    success, error, user = auth_service.authenticate_user(
        email=credentials.email,
        password=credentials.password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error or "Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Create access token
    token = auth_service.create_access_token(
        user_id=user["id"],
        role=user["role"]
    )
    
    return {
        "message": "Login successful",
        "user": user,
        "access_token": token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserProfile)
def get_me(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user's profile."""
    return UserProfile(
        id=current_user["id"],
        email=current_user.get("email"),
        full_name=current_user.get("full_name"),
        role=current_user.get("role", "student")
    )


@router.post("/refresh", response_model=dict)
def refresh_token(current_user: dict = Depends(get_current_user)):
    """Refresh access token (get new token with extended expiry)."""
    new_token = auth_service.create_access_token(
        user_id=current_user["id"],
        role=current_user.get("role", "student")
    )
    
    return {
        "access_token": new_token,
        "token_type": "bearer"
    }
