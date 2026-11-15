async def test_health_reports_database_ok(client):
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"


async def test_root_names_the_service(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "fde-backend-service"
