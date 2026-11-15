"""Pydantic v2 request and response schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Priority = Literal["routine", "urgent", "stat"]
ReferralStatus = Literal["queued", "triaged", "accepted", "completed", "cancelled"]
AppointmentStatus = Literal["booked", "checked_in", "completed", "no_show"]
Role = Literal["user", "admin"]
WebhookEvent = Literal["referral.created", "referral.updated", "appointment.created"]


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    role: str
    is_active: bool
    created_at: datetime


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessTokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RefreshIn(BaseModel):
    refresh_token: str


class RoleUpdateIn(BaseModel):
    role: Role


class ReferralCreate(BaseModel):
    patient_alias: str = Field(min_length=1, max_length=120)
    clinic_name: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1)
    priority: Priority = "routine"
    notes: str | None = None


class ReferralUpdate(BaseModel):
    patient_alias: str | None = Field(default=None, min_length=1, max_length=120)
    clinic_name: str | None = Field(default=None, min_length=1, max_length=200)
    reason: str | None = Field(default=None, min_length=1)
    priority: Priority | None = None
    status: ReferralStatus | None = None
    notes: str | None = None


class ReferralOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    patient_alias: str
    clinic_name: str
    reason: str
    priority: str
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime


class AppointmentCreate(BaseModel):
    scheduled_for: datetime
    location: str = Field(min_length=1, max_length=200)
    clinician: str | None = Field(default=None, max_length=120)


class AppointmentUpdate(BaseModel):
    scheduled_for: datetime | None = None
    location: str | None = Field(default=None, min_length=1, max_length=200)
    clinician: str | None = Field(default=None, max_length=120)
    status: AppointmentStatus | None = None


class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    referral_id: str
    scheduled_for: datetime
    location: str
    clinician: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class WebhookCreate(BaseModel):
    url: str = Field(min_length=8, max_length=500)
    events: list[WebhookEvent] = Field(min_length=1)


class WebhookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    url: str
    events: list
    is_active: bool
    created_at: datetime


class WebhookCreatedOut(WebhookOut):
    """Returned once at creation time; the only response that carries
    the signing secret, so receivers can verify signatures."""

    secret: str


class WebhookDeliveryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    endpoint_id: str
    event: str
    payload: dict
    status: str
    attempts: int
    last_status_code: int | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class WeatherOut(BaseModel):
    city: str
    country: str | None
    latitude: float
    longitude: float
    temperature_c: float | None
    relative_humidity_percent: float | None
    weather_code: int | None
    wind_speed_kmh: float | None
    source: str = "open-meteo"
    cached: bool


class HealthOut(BaseModel):
    status: str
    database: str
