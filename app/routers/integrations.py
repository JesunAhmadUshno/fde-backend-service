"""Third-party API integration endpoints (Open-Meteo, keyless)."""

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.deps import get_current_user
from app.models import User
from app.schemas import WeatherOut
from app.services import weather as weather_service

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/clinic-weather", response_model=WeatherOut)
async def clinic_weather(
    city: str,
    request: Request,
    user: User = Depends(get_current_user),
) -> dict:
    """Current weather for a clinic city, fetched from Open-Meteo and
    cached briefly. Useful context for appointment-day planning."""
    try:
        return await weather_service.fetch_city_weather(
            city,
            settings=request.app.state.settings,
            client=request.app.state.weather_client,
        )
    except weather_service.CityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"city not found: {city}"
        )
    except weather_service.UpstreamError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        )
