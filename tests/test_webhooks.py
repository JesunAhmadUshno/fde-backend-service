import asyncio
import json

import httpx

from app.services.webhooks import sign_payload, verify_signature
from tests.conftest import auth_headers
from tests.test_crud import REFERRAL


def test_sign_and_verify_round_trip():
    body = b'{"event":"referral.created"}'
    header = sign_payload("s3cret", body)
    assert header.startswith("sha256=")
    assert verify_signature("s3cret", body, header)
    assert not verify_signature("s3cret", b'{"event":"tampered"}', header)
    assert not verify_signature("wrong-secret", body, header)


async def _create_endpoint(client, tokens, events) -> dict:
    response = await client.post(
        "/webhooks",
        json={"url": "https://receiver.example/hook", "events": events},
        headers=auth_headers(tokens),
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _wait_for_deliveries(client, tokens, wanted_status: str, timeout: float = 5.0) -> list:
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        response = await client.get("/webhooks/deliveries", headers=auth_headers(tokens))
        deliveries = response.json()
        if deliveries and all(d["status"] == wanted_status for d in deliveries):
            return deliveries
        if asyncio.get_event_loop().time() > deadline:
            return deliveries
        await asyncio.sleep(0.1)


async def test_secret_is_returned_once_and_never_listed(client, user_a):
    created = await _create_endpoint(client, user_a, ["referral.created"])
    assert created["secret"]
    listed = await client.get("/webhooks", headers=auth_headers(user_a))
    assert listed.status_code == 200
    assert "secret" not in listed.json()[0]


async def test_delivery_is_signed_and_logged(app, client, user_a):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = request.headers
        captured["body"] = request.content
        return httpx.Response(200, json={"ok": True})

    app.state.webhook_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    endpoint = await _create_endpoint(client, user_a, ["referral.created"])

    created = await client.post("/referrals", json=REFERRAL, headers=auth_headers(user_a))
    assert created.status_code == 201

    deliveries = await _wait_for_deliveries(client, user_a, "delivered")
    assert len(deliveries) == 1
    delivery = deliveries[0]
    assert delivery["status"] == "delivered"
    assert delivery["attempts"] == 1
    assert delivery["last_status_code"] == 200
    assert delivery["event"] == "referral.created"

    signature = captured["headers"]["x-fde-signature"]
    assert captured["headers"]["x-fde-event"] == "referral.created"
    assert verify_signature(endpoint["secret"], captured["body"], signature)
    payload = json.loads(captured["body"])
    assert payload["data"]["patient_alias"] == "patient-001"


async def test_delivery_retries_then_fails_and_logs_attempts(app, client, user_a):
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(500, text="receiver broken")

    app.state.webhook_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    await _create_endpoint(client, user_a, ["referral.created"])

    created = await client.post("/referrals", json=REFERRAL, headers=auth_headers(user_a))
    assert created.status_code == 201

    deliveries = await _wait_for_deliveries(client, user_a, "failed")
    assert len(deliveries) == 1
    delivery = deliveries[0]
    assert delivery["status"] == "failed"
    assert delivery["attempts"] == 3
    assert delivery["last_status_code"] == 500
    assert calls["count"] == 3


async def test_unsubscribed_event_creates_no_delivery(app, client, user_a):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    app.state.webhook_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    await _create_endpoint(client, user_a, ["appointment.created"])

    created = await client.post("/referrals", json=REFERRAL, headers=auth_headers(user_a))
    assert created.status_code == 201
    await asyncio.sleep(0.3)
    response = await client.get("/webhooks/deliveries", headers=auth_headers(user_a))
    assert response.json() == []


async def test_delete_endpoint_and_ownership(client, user_a, user_b):
    endpoint = await _create_endpoint(client, user_a, ["referral.created"])
    forbidden = await client.delete(f"/webhooks/{endpoint['id']}", headers=auth_headers(user_b))
    assert forbidden.status_code == 403
    deleted = await client.delete(f"/webhooks/{endpoint['id']}", headers=auth_headers(user_a))
    assert deleted.status_code == 204
    listed = await client.get("/webhooks", headers=auth_headers(user_a))
    assert listed.json() == []
