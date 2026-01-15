"""
FastAPI dependencies for authentication and database access.
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from rivet_pro.config.settings import settings
from rivet_pro.infra.database import db, Database
from rivet_pro.infra.observability import get_logger

logger = get_logger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class TokenData(BaseModel):
    """JWT token payload data."""
    user_id: UUID
    email: str


class UserInDB(BaseModel):
    """User model from database."""
    id: UUID
    email: str
    full_name: Optional[str] = None
    role: Optional[str] = None
    telegram_user_id: Optional[str] = None
    created_at: datetime


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Token payload (should include user_id and email)
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expiration_minutes)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )

    return encoded_jwt


async def get_user_by_email(email: str) -> Optional[dict]:
    """Get user by email from database."""
    result = await db.fetchrow(
        "SELECT id, email, full_name, role, telegram_id::text as telegram_user_id, password_hash, created_at FROM users WHERE email = $1",
        email
    )
    return dict(result) if result else None


async def get_user_by_id(user_id: UUID) -> Optional[dict]:
    """Get user by ID from database."""
    result = await db.fetchrow(
        "SELECT id, email, full_name, role, telegram_id::text as telegram_user_id, password_hash, created_at FROM users WHERE id = $1",
        user_id
    )
    return dict(result) if result else None


async def authenticate_user(email: str, password: str) -> Optional[dict]:
    """
    Authenticate a user by email and password.

    Args:
        email: User email
        password: Plain text password

    Returns:
        User dict if authenticated, None otherwise
    """
    user = await get_user_by_email(email)

    if not user:
        return None

    if not user.get("password_hash"):
        logger.warning(f"User {email} has no password set")
        return None

    if not verify_password(password, user["password_hash"]):
        return None

    return user


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    """
    Get the current authenticated user from JWT token.

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )

        user_id_str: str = payload.get("user_id")
        email: str = payload.get("email")

        if user_id_str is None or email is None:
            raise credentials_exception

        user_id = UUID(user_id_str)

    except (JWTError, ValueError) as e:
        logger.warning(f"JWT decode error: {e}")
        raise credentials_exception

    # Fetch user from database
    user = await get_user_by_id(user_id)

    if user is None:
        raise credentials_exception

    return UserInDB(**user)


async def get_db() -> Database:
    """
    Dependency for accessing database connection.

    Returns:
        Database instance (singleton)
    """
    return db


async def admin_required(current_user: UserInDB = Depends(get_current_user)) -> dict:
    """
    Dependency that requires the user to have admin role.

    Args:
        current_user: The authenticated user

    Returns:
        User dict if admin

    Raises:
        HTTPException: If user is not an admin
    """
    if current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return {
        'id': str(current_user.id),
        'email': current_user.email,
        'role': current_user.role
    }
