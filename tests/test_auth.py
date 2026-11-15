from tests.conftest import auth_headers, login, register


async def test_register_returns_user_without_password(client):
    body = await register(client, "new@example.com")
    assert body["email"] == "new@example.com"
    assert body["role"] == "user"
    assert "password" not in body
    assert "password_hash" not in body


async def test_register_duplicate_email_conflicts(client):
    await register(client, "dup@example.com")
    response = await client.post(
        "/auth/register", json={"email": "dup@example.com", "password": "password-123"}
    )
    assert response.status_code == 409


async def test_register_short_password_rejected(client):
    response = await client.post(
        "/auth/register", json={"email": "short@example.com", "password": "short"}
    )
    assert response.status_code == 422


async def test_login_issues_tokens_and_me_works(client):
    await register(client, "login@example.com")
    tokens = await login(client, "login@example.com")
    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"]
    assert tokens["refresh_token"]
    me = await client.get("/auth/me", headers=auth_headers(tokens))
    assert me.status_code == 200
    assert me.json()["email"] == "login@example.com"


async def test_login_wrong_password_unauthorized(client):
    await register(client, "wrong@example.com")
    response = await client.post(
        "/auth/login", json={"email": "wrong@example.com", "password": "not-the-password"}
    )
    assert response.status_code == 401


async def test_login_unknown_email_unauthorized(client):
    response = await client.post(
        "/auth/login", json={"email": "ghost@example.com", "password": "password-123"}
    )
    assert response.status_code == 401


async def test_refresh_rotates_tokens(client):
    await register(client, "refresh@example.com")
    tokens = await login(client, "refresh@example.com")
    response = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 200
    new_tokens = response.json()
    assert new_tokens["access_token"]
    assert new_tokens["refresh_token"] != tokens["refresh_token"]
    me = await client.get("/auth/me", headers=auth_headers(new_tokens))
    assert me.status_code == 200


async def test_refresh_rejects_access_token(client):
    await register(client, "types@example.com")
    tokens = await login(client, "types@example.com")
    response = await client.post("/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert response.status_code == 401


async def test_me_requires_a_valid_token(client):
    assert (await client.get("/auth/me")).status_code == 401
    bad = {"Authorization": "Bearer not-a-real-token"}
    assert (await client.get("/auth/me", headers=bad)).status_code == 401
