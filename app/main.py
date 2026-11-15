"""Application factory, lifespan (schema creation, optional admin
seed), request logging middleware, and the health endpoint."""

import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import make_engine, make_session_factory
from app.deps import get_db
from app.logging_config import configure_logging, get_logger
from app.models import Base, User
from app.routers import admin, auth, integrations, referrals, webhooks
from app.schemas import HealthOut
from app.security import hash_password

log = get_logger("main")


async def _seed_admin(app: FastAPI) -> None:
    settings: Settings = app.state.settings
    if not settings.admin_email or not settings.admin_password:
        return
    async with app.state.session_factory() as db:
        existing = await db.execute(
            select(User).where(User.email == settings.admin_email.lower())
        )
        if existing.scalar_one_or_none() is None:
            db.add(
                User(
                    email=settings.admin_email.lower(),
                    password_hash=hash_password(settings.admin_password),
                    role="admin",
                )
            )
            await db.commit()
            log.info("admin_seeded", email=settings.admin_email.lower())


def create_app(settings: Settings | None = None) -> FastAPI:
    configure_logging()
    settings = settings or get_settings()
    engine = make_engine(settings)
    session_factory = make_session_factory(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await _seed_admin(app)
        log.info("startup_complete", app=settings.app_name, environment=settings.environment)
        yield
        await engine.dispose()

    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description=(
            "Multi-user backend for a community clinic referral queue "
            "(synthetic data only). JWT auth, role-based authorization, "
            "CRUD, signed webhooks, and a keyless third-party integration."
        ),
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    # Injectable HTTP clients. None means "create a real client per call";
    # tests substitute clients backed by mock transports.
    app.state.webhook_client = None
    app.state.weather_client = None

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        log.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        return response

    @app.get("/health", response_model=HealthOut, tags=["ops"])
    async def health(db: AsyncSession = Depends(get_db)) -> HealthOut:
        try:
            await db.execute(text("SELECT 1"))
            database = "ok"
        except Exception:
            database = "unavailable"
        return HealthOut(status="ok" if database == "ok" else "degraded", database=database)

    @app.get("/", tags=["ops"])
    async def root() -> dict:
        return {
            "service": settings.app_name,
            "docs": "/docs",
            "health": "/health",
        }

    app.include_router(auth.router)
    app.include_router(referrals.router)
    app.include_router(webhooks.router)
    app.include_router(integrations.router)
    app.include_router(admin.router)
    return app


app = create_app()
