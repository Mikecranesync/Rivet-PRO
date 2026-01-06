"""
Authentication router for web API.
Handles user registration, login, and JWT token management.
"""

from datetime import timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr

from rivet_pro.adapters.web.dependencies import (
    get_current_user,
    get_db,
    authenticate_user,
    get_user_by_email,
    create_access_token,
    get_password_hash,
    UserInDB
)
from rivet_pro.infra.database import Database
from rivet_pro.infra.observability import get_logger

logger = get_logger(__name__)

router = APIRouter()


class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    """Login request with email/password."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    user: dict


class LinkTelegramRequest(BaseModel):
    """Request to link Telegram account to web account."""
    telegram_user_id: str


@router.post("/register", response_model=TokenResponse)
async def register(
    request: RegisterRequest,
    db: Database = Depends(get_db)
):
    """
    Register a new user with email and password.

    Creates a new user account and returns a JWT token.
    """
    # Check if user already exists
    existing_user = await get_user_by_email(request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Hash password
    password_hash = get_password_hash(request.password)

    # Create user
    try:
        result = await db.fetchrow(
            """
            INSERT INTO users (email, full_name, password_hash, email_verified, role)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, email, full_name, role, telegram_id::text as telegram_user_id, created_at
            """,
            request.email,
            request.full_name,
            password_hash,
            False,  # Email not verified yet
            "user"  # Default role
        )

        user = dict(result)
        logger.info(f"New user registered: {user['email']} (ID: {user['id']})")

    except Exception as e:
        logger.error(f"Failed to register user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user account"
        )

    # Create access token
    access_token = create_access_token(
        data={"user_id": str(user["id"]), "email": user["email"]}
    )

    return TokenResponse(
        access_token=access_token,
        user={
            "id": str(user["id"]),
            "email": user["email"],
            "full_name": user.get("full_name"),
            "role": user.get("role"),
        }
    )


@router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Login with email and password.

    Returns a JWT token for authentication.
    OAuth2 compatible endpoint (uses form_data).
    """
    # Authenticate user
    user = await authenticate_user(form_data.username, form_data.password)

    if not user:
        logger.warning(f"Failed login attempt for: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last login timestamp
    from rivet_pro.infra.database import db
    await db.execute(
        "UPDATE users SET last_login_at = NOW() WHERE id = $1",
        user["id"]
    )

    # Create access token
    access_token = create_access_token(
        data={"user_id": str(user["id"]), "email": user["email"]}
    )

    logger.info(f"User logged in: {user['email']} (ID: {user['id']})")

    return TokenResponse(
        access_token=access_token,
        user={
            "id": str(user["id"]),
            "email": user["email"],
            "full_name": user.get("full_name"),
            "role": user.get("role"),
            "telegram_user_id": user.get("telegram_user_id"),
        }
    )


@router.get("/me")
async def get_current_user_info(current_user: UserInDB = Depends(get_current_user)):
    """
    Get current user information.

    Requires valid JWT token in Authorization header.
    """
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "telegram_user_id": current_user.telegram_user_id,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
    }


@router.post("/link-telegram")
async def link_telegram(
    request: LinkTelegramRequest,
    current_user: UserInDB = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Link Telegram account to current web user.

    Allows users to connect their Telegram bot interactions to their web account.
    """
    # Check if Telegram ID is already linked to another user
    existing = await db.fetchrow(
        "SELECT id, email FROM users WHERE telegram_id = $1 AND id != $2",
        request.telegram_user_id,
        current_user.id
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Telegram account already linked to {existing['email']}"
        )

    # Link Telegram user ID
    await db.execute(
        "UPDATE users SET telegram_id = $1 WHERE id = $2",
        request.telegram_user_id,
        current_user.id
    )

    logger.info(
        f"Telegram account linked | user={current_user.email} | telegram_id={request.telegram_user_id}"
    )

    return {
        "success": True,
        "message": "Telegram account linked successfully",
        "telegram_user_id": request.telegram_user_id
    }
