from tests.conftest import auth_headers

REFERRAL = {
    "patient_alias": "patient-001",
    "clinic_name": "North Clinic",
    "reason": "Follow-up on lab results",
    "priority": "urgent",
}


async def _create_referral(client, tokens) -> dict:
    response = await client.post("/referrals", json=REFERRAL, headers=auth_headers(tokens))
    assert response.status_code == 201, response.text
    return response.json()


async def test_referral_full_crud_cycle(client, user_a):
    created = await _create_referral(client, user_a)
    assert created["status"] == "queued"
    assert created["priority"] == "urgent"
    referral_id = created["id"]

    fetched = await client.get(f"/referrals/{referral_id}", headers=auth_headers(user_a))
    assert fetched.status_code == 200
    assert fetched.json()["patient_alias"] == "patient-001"

    listed = await client.get("/referrals", headers=auth_headers(user_a))
    assert [r["id"] for r in listed.json()] == [referral_id]

    updated = await client.patch(
        f"/referrals/{referral_id}",
        json={"status": "triaged", "priority": "routine"},
        headers=auth_headers(user_a),
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "triaged"
    assert updated.json()["priority"] == "routine"

    deleted = await client.delete(f"/referrals/{referral_id}", headers=auth_headers(user_a))
    assert deleted.status_code == 204
    gone = await client.get(f"/referrals/{referral_id}", headers=auth_headers(user_a))
    assert gone.status_code == 404


async def test_referral_list_filters(client, user_a):
    await _create_referral(client, user_a)
    second = await client.post(
        "/referrals",
        json={**REFERRAL, "patient_alias": "patient-002", "priority": "routine"},
        headers=auth_headers(user_a),
    )
    assert second.status_code == 201
    urgent = await client.get("/referrals?priority=urgent", headers=auth_headers(user_a))
    assert len(urgent.json()) == 1
    assert urgent.json()[0]["patient_alias"] == "patient-001"


async def test_referral_invalid_priority_rejected(client, user_a):
    response = await client.post(
        "/referrals",
        json={**REFERRAL, "priority": "whenever"},
        headers=auth_headers(user_a),
    )
    assert response.status_code == 422


async def test_referral_requires_authentication(client):
    response = await client.post("/referrals", json=REFERRAL)
    assert response.status_code == 401


async def test_appointment_crud_cycle(client, user_a):
    referral = await _create_referral(client, user_a)
    created = await client.post(
        f"/referrals/{referral['id']}/appointments",
        json={
            "scheduled_for": "2026-12-01T09:30:00Z",
            "location": "North Clinic, Room 4",
            "clinician": "Dr. Example",
        },
        headers=auth_headers(user_a),
    )
    assert created.status_code == 201, created.text
    appointment = created.json()
    assert appointment["status"] == "booked"

    listed = await client.get(
        f"/referrals/{referral['id']}/appointments", headers=auth_headers(user_a)
    )
    assert [a["id"] for a in listed.json()] == [appointment["id"]]

    updated = await client.patch(
        f"/appointments/{appointment['id']}",
        json={"status": "checked_in"},
        headers=auth_headers(user_a),
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "checked_in"

    deleted = await client.delete(
        f"/appointments/{appointment['id']}", headers=auth_headers(user_a)
    )
    assert deleted.status_code == 204
    gone = await client.get(f"/appointments/{appointment['id']}", headers=auth_headers(user_a))
    assert gone.status_code == 404


async def test_appointment_under_missing_referral_is_404(client, user_a):
    response = await client.post(
        "/referrals/does-not-exist/appointments",
        json={"scheduled_for": "2026-12-01T09:30:00Z", "location": "North Clinic"},
        headers=auth_headers(user_a),
    )
    assert response.status_code == 404
