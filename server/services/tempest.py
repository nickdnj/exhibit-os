import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from . import settings_service as settings_svc
from ..api.health import update_service_status

logger = logging.getLogger("signboard.tempest")


class WeatherData:
    """Latest weather observation from Tempest."""

    def __init__(self):
        self.temperature_f: Optional[float] = None
        self.feels_like_f: Optional[float] = None
        self.humidity: Optional[float] = None
        self.wind_speed_mph: Optional[float] = None
        self.wind_direction: Optional[int] = None
        self.wind_gust_mph: Optional[float] = None
        self.pressure_inhg: Optional[float] = None
        self.pressure_trend: Optional[str] = None
        self.uv_index: Optional[float] = None
        self.rain_today_in: Optional[float] = None
        self.conditions: Optional[str] = None
        self.icon: Optional[str] = None
        self.last_updated: Optional[datetime] = None


class ForecastDay:
    """Single day forecast."""

    def __init__(self, day_name: str, high_f: float, low_f: float, conditions: str, icon: str, precip_pct: int):
        self.day_name = day_name
        self.high_f = high_f
        self.low_f = low_f
        self.conditions = conditions
        self.icon = icon
        self.precip_pct = precip_pct


class ForecastHour:
    """Single hour forecast."""

    def __init__(self, time: str, temp_f: float, conditions: str, icon: str, precip_pct: int,
                 wind_mph: Optional[float] = None, wind_dir: Optional[str] = None):
        self.time = time  # ISO 8601 UTC
        self.temp_f = temp_f
        self.conditions = conditions
        self.icon = icon
        self.precip_pct = precip_pct
        self.wind_mph = wind_mph
        self.wind_dir = wind_dir  # Cardinal string like "WNW"


class TempestWeatherService:
    """Polls Tempest Cloud API for current conditions and forecast."""

    def __init__(self):
        self.current = WeatherData()
        self.forecast: list[ForecastDay] = []
        self.hourly: list[ForecastHour] = []
        self._last_obs_raw: dict | None = None  # Raw observation dict — used by lightning fallback
        self._poll_interval_current = 300  # 5 minutes
        self._poll_interval_forecast = 1800  # 30 minutes
        self._running = False
        self._tasks: list[asyncio.Task] = []

    async def start(self):
        # Always start the polling loops — they read credentials from SettingsService
        # on each cycle, so the service picks up UI-driven config changes without restart.
        self._running = True
        self._tasks.append(asyncio.create_task(self._poll_current_loop()))
        self._tasks.append(asyncio.create_task(self._poll_forecast_loop()))
        if not settings_svc.get("tempest_api_token"):
            logger.warning("No Tempest API token configured — service idle until set")
            update_service_status("tempest_weather", "disabled")
        else:
            logger.info("Tempest weather service started (station %s)", settings_svc.get("tempest_station_id"))

    async def stop(self):
        self._running = False
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()

    async def _poll_current_loop(self):
        while self._running:
            if not settings_svc.get("tempest_api_token"):
                update_service_status("tempest_weather", "disabled")
                await asyncio.sleep(self._poll_interval_current)
                continue
            try:
                await self._fetch_current()
                update_service_status("tempest_weather", "healthy", self.current.last_updated)
                # Push weather update to display clients via WebSocket
                try:
                    from ..ws.manager import ws_manager
                    await ws_manager.send_weather_update(self.get_current_dict())
                except Exception:
                    pass  # WebSocket push is best-effort
            except Exception as e:
                logger.warning("Tempest current conditions poll failed: %s", e)
                update_service_status("tempest_weather", "error")
            await asyncio.sleep(self._poll_interval_current)

    async def _poll_forecast_loop(self):
        while self._running:
            if not settings_svc.get("tempest_api_token"):
                await asyncio.sleep(self._poll_interval_forecast)
                continue
            try:
                await self._fetch_forecast()
            except Exception as e:
                logger.warning("Tempest forecast poll failed: %s", e)
            await asyncio.sleep(self._poll_interval_forecast)

    async def _fetch_current(self):
        station_id = settings_svc.get("tempest_station_id")
        token = settings_svc.get("tempest_api_token")
        url = f"https://swd.weatherflow.com/swd/rest/observations/station/{station_id}"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params={"token": token})
            resp.raise_for_status()
            data = resp.json()

        obs = data.get("obs", [{}])[0] if data.get("obs") else {}
        if not obs:
            logger.warning("No observation data in Tempest response")
            return
        self._last_obs_raw = obs

        # Tempest observation API returns metric: °C, m/s, mb, mm
        # Convert to imperial for display
        temp_c = obs.get("air_temperature")
        feels_c = obs.get("feels_like")
        wind_ms = obs.get("wind_avg")
        gust_ms = obs.get("wind_gust")
        pressure_mb = obs.get("sea_level_pressure")
        rain_mm = obs.get("precip_accum_local_day")

        self.current.temperature_f = (temp_c * 9 / 5 + 32) if temp_c is not None else None
        self.current.feels_like_f = (feels_c * 9 / 5 + 32) if feels_c is not None else None
        self.current.humidity = obs.get("relative_humidity")
        self.current.wind_speed_mph = (wind_ms * 2.237) if wind_ms is not None else None
        self.current.wind_direction = obs.get("wind_direction")
        self.current.wind_gust_mph = (gust_ms * 2.237) if gust_ms is not None else None
        self.current.pressure_inhg = (pressure_mb * 0.02953) if pressure_mb is not None else None
        self.current.pressure_trend = obs.get("pressure_trend")
        self.current.uv_index = obs.get("uv")
        self.current.rain_today_in = (rain_mm * 0.03937) if rain_mm is not None else None
        self.current.last_updated = datetime.now(timezone.utc)

        logger.debug("Weather updated: %.1f°F (%.1f°C), %s%% humidity",
                      self.current.temperature_f or 0, temp_c or 0, self.current.humidity or 0)

    async def _fetch_forecast(self):
        station_id = settings_svc.get("tempest_station_id")
        token = settings_svc.get("tempest_api_token")
        url = f"https://swd.weatherflow.com/swd/rest/better_forecast"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                url,
                params={
                    "station_id": station_id,
                    "token": token,
                    "units_temp": "f",
                    "units_wind": "mph",
                    "units_pressure": "inhg",
                    "units_precip": "in",
                    "units_distance": "mi",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        daily = data.get("forecast", {}).get("daily", [])
        self.forecast = []
        for day in daily[:5]:
            self.forecast.append(
                ForecastDay(
                    day_name=day.get("day_name", ""),
                    high_f=day.get("air_temp_high", 0),
                    low_f=day.get("air_temp_low", 0),
                    conditions=day.get("conditions", ""),
                    icon=day.get("icon", ""),
                    precip_pct=day.get("precip_probability", 0),
                )
            )

        hourly = data.get("forecast", {}).get("hourly", [])
        now_epoch = int(datetime.now(timezone.utc).timestamp())
        current_hour_epoch = now_epoch - (now_epoch % 3600)
        upcoming = [h for h in hourly if h.get("time", 0) >= current_hour_epoch]
        self.hourly = []
        for h in upcoming[:5]:
            t = h.get("time", 0)
            self.hourly.append(
                ForecastHour(
                    time=datetime.fromtimestamp(t, tz=timezone.utc).isoformat(),
                    temp_f=h.get("air_temperature", 0),
                    conditions=h.get("conditions", ""),
                    icon=h.get("icon", ""),
                    precip_pct=h.get("precip_probability", 0),
                    wind_mph=h.get("wind_avg"),
                    wind_dir=h.get("wind_direction_cardinal"),
                )
            )
        logger.debug("Forecast updated: %d days, %d hours", len(self.forecast), len(self.hourly))

    def get_current_dict(self) -> dict:
        c = self.current
        return {
            "temperature_f": round(c.temperature_f, 1) if c.temperature_f is not None else None,
            "feels_like_f": round(c.feels_like_f, 1) if c.feels_like_f is not None else None,
            "humidity": round(c.humidity) if c.humidity is not None else None,
            "wind_speed_mph": round(c.wind_speed_mph, 1) if c.wind_speed_mph is not None else None,
            "wind_direction": c.wind_direction,
            "wind_gust_mph": round(c.wind_gust_mph, 1) if c.wind_gust_mph is not None else None,
            "pressure_inhg": round(c.pressure_inhg, 2) if c.pressure_inhg is not None else None,
            "pressure_trend": c.pressure_trend,
            "uv_index": round(c.uv_index, 1) if c.uv_index is not None else None,
            "rain_today_in": round(c.rain_today_in, 2) if c.rain_today_in is not None else None,
            "conditions": c.conditions,
            "icon": c.icon,
            "last_updated": c.last_updated.isoformat() if c.last_updated else None,
        }

    def get_forecast_list(self) -> list[dict]:
        return [
            {
                "day_name": f.day_name,
                "high_f": f.high_f,
                "low_f": f.low_f,
                "conditions": f.conditions,
                "icon": f.icon,
                "precip_pct": f.precip_pct,
            }
            for f in self.forecast
        ]

    def get_hourly_list(self) -> list[dict]:
        return [
            {
                "time": h.time,
                "temp_f": round(h.temp_f, 1) if h.temp_f is not None else None,
                "conditions": h.conditions,
                "icon": h.icon,
                "precip_pct": h.precip_pct,
                "wind_mph": round(h.wind_mph, 1) if h.wind_mph is not None else None,
                "wind_dir": h.wind_dir,
            }
            for h in self.hourly
        ]


# Singleton instance
weather_service = TempestWeatherService()
