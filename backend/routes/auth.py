"""
Authentication routes: register, login, get current user.
"""
from __future__ import annotations

import bcrypt
import jwt
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.database.models import User
from backend.errors import is_database_unavailable_error, db_unavailable_http_exception

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user: dict


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def _create_token(user_id: int, email: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiry_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _normalize_email(email: str) -> str:
    return str(email or "").strip().lower()


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(
    authorization: str = Header(default=""),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    token = authorization[7:]
    payload = _decode_token(token)
    raw_user_id = payload.get("sub")
    try:
        user_id = int(raw_user_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token subject")
    try:
        result = await db.execute(select(User).where(User.id == user_id))
    except Exception as e:
        if is_database_unavailable_error(e):
            raise db_unavailable_http_exception()
        raise
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.post("/register", response_model=AuthResponse)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    normalized_email = _normalize_email(data.email)
    if not normalized_email:
        raise HTTPException(status_code=400, detail="Email is required")

    try:
        existing = await db.execute(
            select(User)
            .where(func.lower(User.email) == normalized_email)
            .order_by(User.id.desc())
        )
    except Exception as e:
        if is_database_unavailable_error(e):
            raise db_unavailable_http_exception()
        raise
    if existing.scalars().first() is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        name=data.name,
        email=normalized_email,
        password_hash=_hash_password(data.password),
    )
    try:
        db.add(user)
        await db.commit()
        await db.refresh(user)
    except Exception as e:
        if is_database_unavailable_error(e):
            raise db_unavailable_http_exception()
        raise

    token = _create_token(user.id, user.email)
    return {
        "token": token,
        "user": {"id": user.id, "name": user.name, "email": user.email, "role": user.role},
    }


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    normalized_email = _normalize_email(data.email)
    if not normalized_email or not data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    try:
        result = await db.execute(
            select(User)
            .where(func.lower(User.email) == normalized_email)
            .order_by(User.id.desc())
        )
    except Exception as e:
        if is_database_unavailable_error(e):
            raise db_unavailable_http_exception()
        raise
    user = result.scalars().first()

    if not user or not user.password_hash or not _verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = _create_token(user.id, user.email)
    return {
        "token": token,
        "user": {"id": user.id, "name": user.name, "email": user.email, "role": user.role},
    }


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role}
