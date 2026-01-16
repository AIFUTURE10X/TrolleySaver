"""
Authentication API endpoints.

Handles user registration, login, and token management.
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.services.auth import (
    create_user,
    authenticate_user,
    create_access_token,
    get_current_user_from_token,
    is_premium_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


# ============== Schemas ==============

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    display_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    display_name: Optional[str]
    is_premium: bool
    subscription_status: str
    reputation_score: int

    class Config:
        from_attributes = True


# ============== Dependencies ==============

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get the current authenticated user (optional)."""
    if credentials is None:
        return None

    user = get_current_user_from_token(db, credentials.credentials)
    return user


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Require authentication - raises 401 if not authenticated."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_current_user_from_token(db, credentials.credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    return user


async def require_premium(
    user: User = Depends(require_auth)
) -> User:
    """Require premium subscription - raises 403 if not premium."""
    if not is_premium_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium subscription required"
        )
    return user


# ============== Endpoints ==============

@router.post("/register", response_model=UserResponse)
def register(data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user account.

    - **email**: Valid email address
    - **password**: Password (min 6 characters)
    - **display_name**: Optional display name
    """
    if len(data.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters"
        )

    user = create_user(db, data.email, data.password, data.display_name)

    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_premium=is_premium_user(user),
        subscription_status=user.subscription_status or "free",
        reputation_score=user.reputation_score
    )


@router.post("/login", response_model=Token)
def login(data: UserLogin, db: Session = Depends(get_db)):
    """
    Login with email and password.

    Returns a JWT access token valid for 7 days.
    """
    user = authenticate_user(db, data.email, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    access_token = create_access_token(
        data={"sub": str(user.id)},  # JWT sub must be a string
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(require_auth)):
    """
    Get the current authenticated user's profile.

    Requires authentication.
    """
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_premium=is_premium_user(user),
        subscription_status=user.subscription_status or "free",
        reputation_score=user.reputation_score
    )


@router.put("/me", response_model=UserResponse)
def update_me(
    display_name: Optional[str] = None,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Update the current user's profile.

    Requires authentication.
    """
    if display_name is not None:
        user.display_name = display_name
        db.commit()
        db.refresh(user)

    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_premium=is_premium_user(user),
        subscription_status=user.subscription_status or "free",
        reputation_score=user.reputation_score
    )


@router.post("/logout")
def logout():
    """
    Logout the current user.

    Note: With JWT, logout is client-side (discard the token).
    This endpoint exists for API completeness.
    """
    return {"message": "Logged out successfully"}
