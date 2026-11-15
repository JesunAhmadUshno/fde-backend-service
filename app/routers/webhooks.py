"""Webhook endpoint management and the delivery log.

Creating an endpoint returns its signing secret exactly once. Later
reads never expose the secret. Deliveries are listed from the log so
senders can audit attempts, status codes, and failures.
"""

import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models import User, WebhookDelivery, WebhookEndpoint
from app.schemas import WebhookCreate, WebhookCreatedOut, WebhookDeliveryOut, WebhookOut

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("", response_model=WebhookCreatedOut, status_code=status.HTTP_201_CREATED)
async def create_endpoint(
    body: WebhookCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WebhookEndpoint:
    endpoint = WebhookEndpoint(
        owner_id=user.id,
        url=body.url,
        events=list(body.events),
        secret=secrets.token_urlsafe(32),
    )
    db.add(endpoint)
    await db.commit()
    await db.refresh(endpoint)
    return endpoint


@router.get("", response_model=list[WebhookOut])
async def list_endpoints(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[WebhookEndpoint]:
    query = select(WebhookEndpoint).order_by(WebhookEndpoint.created_at)
    if user.role != "admin":
        query = query.where(WebhookEndpoint.owner_id == user.id)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.delete("/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_endpoint(
    endpoint_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    endpoint = await db.get(WebhookEndpoint, endpoint_id)
    if endpoint is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="webhook endpoint not found")
    if endpoint.owner_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="this webhook endpoint belongs to another user",
        )
    await db.delete(endpoint)
    await db.commit()


@router.get("/deliveries", response_model=list[WebhookDeliveryOut])
async def list_deliveries(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    status_filter: str | None = None,
) -> list[WebhookDelivery]:
    query = (
        select(WebhookDelivery)
        .join(WebhookEndpoint, WebhookDelivery.endpoint_id == WebhookEndpoint.id)
        .order_by(WebhookDelivery.created_at.desc())
    )
    if user.role != "admin":
        query = query.where(WebhookEndpoint.owner_id == user.id)
    if status_filter:
        query = query.where(WebhookDelivery.status == status_filter)
    result = await db.execute(query)
    return list(result.scalars().all())
