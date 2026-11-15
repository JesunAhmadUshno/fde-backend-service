"""Password hashing (argon2) and JWT issuing and verification (HS256)."""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config import Settings

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def _create_token(settings: Settings, subject: str, token_type: str, expires: timedelta, role: str | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + expires,
    }
    if role is not None:
        payload["role"] = role
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(settings: Settings, user_id: str, role: str) -> str:
    return _create_token(
        settings,
        user_id,
        "access",
        timedelta(minutes=settings.access_token_expire_minutes),
        role=role,
    )


def create_refresh_token(settings: Settings, user_id: str) -> str:
    return _create_token(
        settings,
        user_id,
        "refresh",
        timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(settings: Settings, token: str, expected_type: str) -> dict:
    """Decode and validate a token. Raises jwt.PyJWTError on any problem,
    and ValueError when the token type does not match the expected type."""
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != expected_type:
        raise ValueError(f"expected a {expected_type} token")
    return payload
