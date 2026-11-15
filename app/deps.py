"""FastAPI dependencies: database sessions, the authenticated user,
and role enforcement."""

import jwt as pyjwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


async def get_db(request: Request) -> AsyncSession:
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        yield session


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="missing or invalid access token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        payload = decode_token(request.app.state.settings, credentials.credentials, "access")
    except (pyjwt.PyJWTError, ValueError):
        raise unauthorized
    user = await db.get(User, payload.get("sub", ""))
    if user is None or not user.is_active:
        raise unauthorized
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="admin role required",
        )
    return user
