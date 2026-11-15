"""Referral CRUD plus nested appointment CRUD.

Authorization model: a referral belongs to its owner. The owner and
admins can read and modify it; any other authenticated user receives
403. Appointments inherit the authorization of their parent referral.
Mutations queue webhook events for the owner's subscribed endpoints.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models import Appointment, Referral, User
from app.schemas import (
    AppointmentCreate,
    AppointmentOut,
    AppointmentUpdate,
    ReferralCreate,
    ReferralOut,
    ReferralUpdate,
)
from app.services import webhooks as webhook_service

router = APIRouter(tags=["referrals"])


def _schedule_deliveries(request: Request, background: BackgroundTasks, delivery_ids: list[str]) -> None:
    for delivery_id in delivery_ids:
        background.add_task(
            webhook_service.deliver,
            delivery_id,
            session_factory=request.app.state.session_factory,
            settings=request.app.state.settings,
            client=request.app.state.webhook_client,
        )


async def _get_referral(db: AsyncSession, user: User, referral_id: str) -> Referral:
    referral = await db.get(Referral, referral_id)
    if referral is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="referral not found")
    if referral.owner_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="this referral belongs to another user",
        )
    return referral


def _referral_data(referral: Referral) -> dict:
    return {
        "id": referral.id,
        "patient_alias": referral.patient_alias,
        "clinic_name": referral.clinic_name,
        "priority": referral.priority,
        "status": referral.status,
    }


@router.post("/referrals", response_model=ReferralOut, status_code=status.HTTP_201_CREATED)
async def create_referral(
    body: ReferralCreate,
    request: Request,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Referral:
    referral = Referral(owner_id=user.id, **body.model_dump())
    db.add(referral)
    await db.commit()
    await db.refresh(referral)
    delivery_ids = await webhook_service.queue_event(
        db, owner_id=user.id, event="referral.created", data=_referral_data(referral)
    )
    _schedule_deliveries(request, background, delivery_ids)
    return referral


@router.get("/referrals", response_model=list[ReferralOut])
async def list_referrals(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    status_filter: str | None = None,
    priority: str | None = None,
) -> list[Referral]:
    query = select(Referral).order_by(Referral.created_at)
    if user.role != "admin":
        query = query.where(Referral.owner_id == user.id)
    if status_filter:
        query = query.where(Referral.status == status_filter)
    if priority:
        query = query.where(Referral.priority == priority)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/referrals/{referral_id}", response_model=ReferralOut)
async def get_referral(
    referral_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Referral:
    return await _get_referral(db, user, referral_id)


@router.patch("/referrals/{referral_id}", response_model=ReferralOut)
async def update_referral(
    referral_id: str,
    body: ReferralUpdate,
    request: Request,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Referral:
    referral = await _get_referral(db, user, referral_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(referral, field, value)
    await db.commit()
    await db.refresh(referral)
    delivery_ids = await webhook_service.queue_event(
        db, owner_id=referral.owner_id, event="referral.updated", data=_referral_data(referral)
    )
    _schedule_deliveries(request, background, delivery_ids)
    return referral


@router.delete("/referrals/{referral_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_referral(
    referral_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    referral = await _get_referral(db, user, referral_id)
    await db.delete(referral)
    await db.commit()


@router.post(
    "/referrals/{referral_id}/appointments",
    response_model=AppointmentOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_appointment(
    referral_id: str,
    body: AppointmentCreate,
    request: Request,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Appointment:
    referral = await _get_referral(db, user, referral_id)
    appointment = Appointment(referral_id=referral.id, **body.model_dump())
    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)
    delivery_ids = await webhook_service.queue_event(
        db,
        owner_id=referral.owner_id,
        event="appointment.created",
        data={
            "id": appointment.id,
            "referral_id": referral.id,
            "scheduled_for": appointment.scheduled_for.isoformat(),
            "location": appointment.location,
            "status": appointment.status,
        },
    )
    _schedule_deliveries(request, background, delivery_ids)
    return appointment


@router.get("/referrals/{referral_id}/appointments", response_model=list[AppointmentOut])
async def list_appointments(
    referral_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Appointment]:
    referral = await _get_referral(db, user, referral_id)
    result = await db.execute(
        select(Appointment)
        .where(Appointment.referral_id == referral.id)
        .order_by(Appointment.scheduled_for)
    )
    return list(result.scalars().all())


async def _get_appointment(db: AsyncSession, user: User, appointment_id: str) -> Appointment:
    appointment = await db.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="appointment not found")
    await _get_referral(db, user, appointment.referral_id)
    return appointment


@router.get("/appointments/{appointment_id}", response_model=AppointmentOut)
async def get_appointment(
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Appointment:
    return await _get_appointment(db, user, appointment_id)


@router.patch("/appointments/{appointment_id}", response_model=AppointmentOut)
async def update_appointment(
    appointment_id: str,
    body: AppointmentUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Appointment:
    appointment = await _get_appointment(db, user, appointment_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(appointment, field, value)
    await db.commit()
    await db.refresh(appointment)
    return appointment


@router.delete("/appointments/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_appointment(
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    appointment = await _get_appointment(db, user, appointment_id)
    await db.delete(appointment)
    await db.commit()
