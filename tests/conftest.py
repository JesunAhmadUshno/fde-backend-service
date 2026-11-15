"""Shared fixtures.

The suite runs against PostgreSQL when DATABASE_URL is set in the
environment (CI does this) and against a throwaway SQLite file
otherwise, so it also runs on machines without Docker or Postgres.
Every test gets a fresh schema.
"""

import os

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("WEBHOOK_BACKOFF_BASE_SECONDS", "0")

import httpx
import pytest
from httpx import ASGITransport

from app.config import Settings
from app.main import create_app
from app.models import Base, User
from app.security import hash_password


def _test_database_url(tmp_path) -> str:
    env_url = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if env_url:
        return env_url
    return f"sqlite+aiosqlite:///{tmp_path}/test.db"


@pytest.fixture
async def app(tmp_path):
    settings = Settings(
        database_url=_test_database_url(tmp_path),
        jwt_secret="test-secret",
        webhook_backoff_base_seconds=0.0,
        webhook_max_attempts=3,
    )
    application = create_app(settings)
    engine = application.state.engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield application
    await engine.dispose()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


async def register(client: httpx.AsyncClient, email: str, password: str = "password-123"):
    response = await client.post("/auth/register", json={"email": email, "password": password})
    assert response.status_code == 201, response.text
    return response.json()


async def login(client: httpx.AsyncClient, email: str, password: str = "password-123") -> dict:
    response = await client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def auth_headers(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.fixture
async def user_a(client):
    await register(client, "a@example.com")
    return await login(client, "a@example.com")


@pytest.fixture
async def user_b(client):
    await register(client, "b@example.com")
    return await login(client, "b@example.com")


@pytest.fixture
async def admin(app, client):
    """Insert an admin directly in the database, then log in by API."""
    async with app.state.session_factory() as db:
        db.add(
            User(
                email="admin@example.com",
                password_hash=hash_password("admin-password-123"),
                role="admin",
            )
        )
        await db.commit()
    return await login(client, "admin@example.com", "admin-password-123")
