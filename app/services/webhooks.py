"""Outbound webhooks: HMAC-SHA256 signing, delivery with retry and
exponential backoff, and a persisted delivery log.

Receivers verify a delivery by recomputing the HMAC over the exact
request body with the endpoint secret and comparing it to the
X-FDE-Signature header (format: sha256=<hex digest>).
"""

import asyncio
import hashlib
import hmac
import json

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.logging_config import get_logger
from app.models import WebhookDelivery, WebhookEndpoint

log = get_logger("webhooks")


def sign_payload(secret: str, body: bytes) -> str:
    """Return the signature header value for a request body."""
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_signature(secret: str, body: bytes, header_value: str) -> bool:
    return hmac.compare_digest(sign_payload(secret, body), header_value or "")


async def queue_event(
    db: AsyncSession,
    *,
    owner_id: str,
    event: str,
    data: dict,
) -> list[str]:
    """Create one pending delivery row per active endpoint of the owner
    that subscribes to the event. Returns the delivery ids created."""
    result = await db.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.owner_id == owner_id,
            WebhookEndpoint.is_active.is_(True),
        )
    )
    delivery_ids: list[str] = []
    for endpoint in result.scalars().all():
        if event not in (endpoint.events or []):
            continue
        delivery = WebhookDelivery(
            endpoint_id=endpoint.id,
            event=event,
            payload={"event": event, "data": data},
            status="pending",
        )
        db.add(delivery)
        await db.flush()
        delivery_ids.append(delivery.id)
    if delivery_ids:
        await db.commit()
    return delivery_ids


async def deliver(
    delivery_id: str,
    *,
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    client: httpx.AsyncClient | None = None,
) -> None:
    """Attempt delivery with retries. Never raises: every outcome is
    written to the delivery log row."""
    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=settings.webhook_timeout_seconds)
    try:
        async with session_factory() as db:
            delivery = await db.get(WebhookDelivery, delivery_id)
            if delivery is None:
                return
            endpoint = await db.get(WebhookEndpoint, delivery.endpoint_id)
            if endpoint is None:
                delivery.status = "failed"
                delivery.last_error = "endpoint no longer exists"
                await db.commit()
                return
            body = json.dumps(
                {
                    "event": delivery.event,
                    "delivery_id": delivery.id,
                    "data": delivery.payload.get("data", {}),
                },
                separators=(",", ":"),
            ).encode("utf-8")
            headers = {
                "Content-Type": "application/json",
                "X-FDE-Event": delivery.event,
                "X-FDE-Delivery-Id": delivery.id,
                "X-FDE-Signature": sign_payload(endpoint.secret, body),
            }
            url = endpoint.url

        for attempt in range(1, settings.webhook_max_attempts + 1):
            error: str | None = None
            status_code: int | None = None
            try:
                response = await client.post(url, content=body, headers=headers)
                status_code = response.status_code
                if 200 <= status_code < 300:
                    error = None
                else:
                    error = f"receiver answered HTTP {status_code}"
            except httpx.HTTPError as exc:
                error = f"{type(exc).__name__}: {exc}"

            async with session_factory() as db:
                delivery = await db.get(WebhookDelivery, delivery_id)
                delivery.attempts = attempt
                delivery.last_status_code = status_code
                delivery.last_error = error
                delivery.status = "delivered" if error is None else "pending"
                await db.commit()

            if error is None:
                log.info("webhook_delivered", delivery_id=delivery_id, attempts=attempt)
                return
            log.warning(
                "webhook_attempt_failed",
                delivery_id=delivery_id,
                attempt=attempt,
                error=error,
            )
            if attempt < settings.webhook_max_attempts:
                backoff = settings.webhook_backoff_base_seconds * (2 ** (attempt - 1))
                if backoff > 0:
                    await asyncio.sleep(backoff)

        async with session_factory() as db:
            delivery = await db.get(WebhookDelivery, delivery_id)
            if delivery is not None and delivery.status != "delivered":
                delivery.status = "failed"
                await db.commit()
        log.error("webhook_delivery_failed", delivery_id=delivery_id)
    finally:
        if own_client:
            await client.aclose()
