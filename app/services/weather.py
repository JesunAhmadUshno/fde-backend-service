"""Third-party integration: Open-Meteo (no API key required).

GET a city name, geocode it, fetch the current weather, and cache the
result in memory for a short TTL so repeated calls do not hammer the
upstream API. The HTTP client is injectable so tests can substitute a
mock transport.
"""

import time

import httpx

from app.config import Settings

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

_cache: dict[str, tuple[float, dict]] = {}


class CityNotFoundError(Exception):
    pass


class UpstreamError(Exception):
    pass


async def fetch_city_weather(
    city: str,
    *,
    settings: Settings,
    client: httpx.AsyncClient | None = None,
) -> dict:
    key = city.strip().lower()
    now = time.monotonic()
    hit = _cache.get(key)
    if hit is not None and hit[0] > now:
        return {**hit[1], "cached": True}

    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=10.0)
    try:
        try:
            geo = await client.get(
                GEOCODING_URL,
                params={"name": city, "count": 1, "language": "en", "format": "json"},
            )
            geo.raise_for_status()
            results = geo.json().get("results") or []
            if not results:
                raise CityNotFoundError(city)
            place = results[0]
            forecast = await client.get(
                FORECAST_URL,
                params={
                    "latitude": place["latitude"],
                    "longitude": place["longitude"],
                    "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
                },
            )
            forecast.raise_for_status()
            current = forecast.json().get("current") or {}
        except CityNotFoundError:
            raise
        except httpx.HTTPError as exc:
            raise UpstreamError(f"open-meteo request failed: {exc}") from exc

        result = {
            "city": place.get("name", city),
            "country": place.get("country"),
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "temperature_c": current.get("temperature_2m"),
            "relative_humidity_percent": current.get("relative_humidity_2m"),
            "weather_code": current.get("weather_code"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "source": "open-meteo",
            "cached": False,
        }
        _cache[key] = (now + settings.weather_cache_ttl_seconds, result)
        return result
    finally:
        if own_client:
            await client.aclose()
