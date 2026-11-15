from tests.conftest import auth_headers
from tests.test_crud import _create_referral


async def test_other_user_cannot_read_referral(client, user_a, user_b):
    referral = await _create_referral(client, user_a)
    response = await client.get(f"/referrals/{referral['id']}", headers=auth_headers(user_b))
    assert response.status_code == 403


async def test_other_user_cannot_modify_or_delete_referral(client, user_a, user_b):
    referral = await _create_referral(client, user_a)
    patched = await client.patch(
        f"/referrals/{referral['id']}",
        json={"status": "cancelled"},
        headers=auth_headers(user_b),
    )
    assert patched.status_code == 403
    deleted = await client.delete(f"/referrals/{referral['id']}", headers=auth_headers(user_b))
    assert deleted.status_code == 403


async def test_other_user_list_is_empty_and_appointments_blocked(client, user_a, user_b):
    referral = await _create_referral(client, user_a)
    listed = await client.get("/referrals", headers=auth_headers(user_b))
    assert listed.json() == []
    appointments = await client.get(
        f"/referrals/{referral['id']}/appointments", headers=auth_headers(user_b)
    )
    assert appointments.status_code == 403


async def test_non_admin_cannot_use_admin_routes(client, user_a):
    listed = await client.get("/admin/users", headers=auth_headers(user_a))
    assert listed.status_code == 403
    promoted = await client.patch(
        "/admin/users/some-id/role", json={"role": "admin"}, headers=auth_headers(user_a)
    )
    assert promoted.status_code == 403


async def test_admin_sees_all_users_and_referrals(client, user_a, admin):
    referral = await _create_referral(client, user_a)
    users = await client.get("/admin/users", headers=auth_headers(admin))
    assert users.status_code == 200
    emails = {u["email"] for u in users.json()}
    assert "a@example.com" in emails
    assert "admin@example.com" in emails

    fetched = await client.get(f"/referrals/{referral['id']}", headers=auth_headers(admin))
    assert fetched.status_code == 200


async def test_admin_can_promote_a_user(client, user_a, user_b, admin):
    users = await client.get("/admin/users", headers=auth_headers(admin))
    b_id = next(u["id"] for u in users.json() if u["email"] == "b@example.com")
    promoted = await client.patch(
        f"/admin/users/{b_id}/role", json={"role": "admin"}, headers=auth_headers(admin)
    )
    assert promoted.status_code == 200
    assert promoted.json()["role"] == "admin"
    # Fresh login so the new role is in force, then the admin route opens.
    from tests.conftest import login

    fresh_b = await login(client, "b@example.com")
    listed = await client.get("/admin/users", headers=auth_headers(fresh_b))
    assert listed.status_code == 200
