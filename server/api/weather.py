from fastapi import APIRouter

from ..services.tempest import weather_service

router = APIRouter(prefix="/api/weather", tags=["weather"])


@router.get("/current")
def get_current_weather():
    """Public endpoint — returns current weather conditions from Tempest."""
    return weather_service.get_current_dict()


@router.get("/forecast")
def get_forecast():
    """Public endpoint — returns 5-day forecast from Tempest."""
    return weather_service.get_forecast_list()


@router.get("/hourly")
def get_hourly():
    """Public endpoint — returns next 5 hours of forecast from Tempest."""
    return weather_service.get_hourly_list()
