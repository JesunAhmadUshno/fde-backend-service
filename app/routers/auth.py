"""Registration, login, token refresh, and the current-user endpoint.

Passwords are stored as argon2 hashes. Login issues a short-lived
access token plus a longer-lived refresh token; the refresh endpoint
exchanges a valid refresh token for a fresh token pair (rotation).
"""

import jwt as pyjwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models import User
from app.schemas import AccessTokenOut, LoginIn, RefreshIn, TokenOut, UserCreate, UserOut
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_pair(request: Request, user: User) -> TokenOut:
    settings = request.app.state.settings
    return TokenOut(
        access_token=create_access_token(settings, user.id, user.role),
        refresh_token=create_refresh_token(settings, user.id),
    )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(body: UserCreate, db: AsyncSession = Depends(get_db)) -> User:
    existing = await db.execute(select(User).where(User.email == body.email.lower()))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email already registered")
    user = User(
        email=body.email.lower(),
        password_hash=hash_password(body.password),
        role="user",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, request: Request, db: AsyncSession = Depends(get_db)) -> TokenOut:
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid email or password"
        )
    return _token_pair(request, user)


@router.post("/refresh", response_model=TokenOut)
async def refresh(body: RefreshIn, request: Request, db: AsyncSession = Depends(get_db)) -> TokenOut:
    settings = request.app.state.settings
    try:
        payload = decode_token(settings, body.refresh_token, "refresh")
    except (pyjwt.PyJWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid refresh token"
        )
    user = await db.get(User, payload.get("sub", ""))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid refresh token"
        )
    return _token_pair(request, user)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> User:
    return user
