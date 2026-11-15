"""Database models.

Column types are deliberately portable (String, JSON, DateTime) so the
same schema runs on PostgreSQL in production-shaped deployments and on
SQLite inside the test suite. UUIDs are generated in Python.

Domain: a community clinic referral queue. A referring provider (role
"user") creates referrals for synthetic patients; clinic coordinators
(role "admin") can see and manage every referral. Each referral can
hold appointments. Webhook endpoints let external systems subscribe to
referral and appointment events.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="user", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    referrals: Mapped[list["Referral"]] = relationship(back_populates="owner")
    webhook_endpoints: Mapped[list["WebhookEndpoint"]] = relationship(back_populates="owner")


class Referral(Base):
    __tablename__ = "referrals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    patient_alias: Mapped[str] = mapped_column(String(120), nullable=False)
    clinic_name: Mapped[str] = mapped_column(String(200), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="routine", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    owner: Mapped[User] = relationship(back_populates="referrals")
    appointments: Mapped[list["Appointment"]] = relationship(
        back_populates="referral", cascade="all, delete-orphan"
    )


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    referral_id: Mapped[str] = mapped_column(
        ForeignKey("referrals.id"), index=True, nullable=False
    )
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    clinician: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="booked", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    referral: Mapped[Referral] = relationship(back_populates="appointments")


class WebhookEndpoint(Base):
    __tablename__ = "webhook_endpoints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    events: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    secret: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    owner: Mapped[User] = relationship(back_populates="webhook_endpoints")
    deliveries: Mapped[list["WebhookDelivery"]] = relationship(
        back_populates="endpoint", cascade="all, delete-orphan"
    )


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    endpoint_id: Mapped[str] = mapped_column(
        ForeignKey("webhook_endpoints.id"), index=True, nullable=False
    )
    event: Mapped[str] = mapped_column(String(60), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    endpoint: Mapped[WebhookEndpoint] = relationship(back_populates="deliveries")
