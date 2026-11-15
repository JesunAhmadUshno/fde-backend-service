import httpx

from tests.conftest import auth_headers


def _weather_client(calls: dict) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] = calls.get("count", 0) + 1
        host = request.url.host
        if host == "geocoding-api.open-meteo.com":
            name = request.url.params.get("name", "")
            if name == "Nowhereville":
                return httpx.Response(200, json={"results": []})
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "name": name,
                            "country": "Canada",
                            "latitude": 43.65,
                            "longitude": -79.38,
                        }
                    ]
                },
            )
        if host == "api.open-meteo.com":
            return httpx.Response(
                200,
                json={
                    "current": {
                        "temperature_2m": 4.5,
                        "relative_humidity_2m": 61.0,
                        "weather_code": 3,
                        "wind_speed_10m": 14.2,
                    }
                },
            )
        return httpx.Response(404)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_clinic_weather_fetches_then_serves_from_cache(app, client, user_a):
    calls: dict = {}
    app.state.weather_client = _weather_client(calls)

    first = await client.get(
        "/integrations/clinic-weather?city=Cachetown", headers=auth_headers(user_a)
    )
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["city"] == "Cachetown"
    assert body["country"] == "Canada"
    assert body["temperature_c"] == 4.5
    assert body["weather_code"] == 3
    assert body["cached"] is False
    calls_after_first = calls["count"]
    assert calls_after_first == 2  # one geocoding call, one forecast call

    second = await client.get(
        "/integrations/clinic-weather?city=Cachetown", headers=auth_headers(user_a)
    )
    assert second.status_code == 200
    assert second.json()["cached"] is True
    assert calls["count"] == calls_after_first  # no new upstream calls


async def test_clinic_weather_unknown_city_is_404(app, client, user_a):
    calls: dict = {}
    app.state.weather_client = _weather_client(calls)
    response = await client.get(
        "/integrations/clinic-weather?city=Nowhereville", headers=auth_headers(user_a)
    )
    assert response.status_code == 404


async def test_clinic_weather_requires_authentication(app, client):
    response = await client.get("/integrations/clinic-weather?city=Toronto")
    assert response.status_code == 401
