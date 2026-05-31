import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Optional

import httpx

from ..database import get_session
from ..models.tide_station import TideStation
from ..api.health import update_service_status
from . import settings_service as settings_svc

logger = logging.getLogger("signboard.tides")


@dataclass
class TidePrediction:
    time_str: str  # "2026-04-16 14:30"
    height_ft: float
    tide_type: str  # "H" or "L"


@dataclass
class StationData:
    noaa_id: str
    name: str
    is_local: bool
    predictions: list[TidePrediction] = field(default_factory=list)
    last_fetched: Optional[datetime] = None
    error: Optional[str] = None


class TideService:
    """Fetches daily tide predictions from NOAA CO-OPS for each configured station."""

    def __init__(self):
        self.stations: dict[str, StationData] = {}  # keyed by noaa_id
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._reload_event = asyncio.Event()

    @property
    def _tz(self) -> ZoneInfo:
        """Current timezone — read from SettingsService each access so UI changes take effect."""
        try:
            return ZoneInfo(settings_svc.get("timezone") or "America/New_York")
        except Exception:
            return ZoneInfo("America/New_York")

    def load_stations_from_db(self):
        """Load enabled stations from DB. Called on startup and after CRUD."""
        with get_session() as db:
            records = db.query(TideStation).filter(TideStation.enabled == True).order_by(TideStation.sort_order, TideStation.id).all()
            new_stations: dict[str, StationData] = {}
            for r in records:
                existing = self.stations.get(r.noaa_id)
                new_stations[r.noaa_id] = StationData(
                    noaa_id=r.noaa_id,
                    name=r.name,
                    is_local=r.is_local,
                    predictions=existing.predictions if existing else [],
                    last_fetched=existing.last_fetched if existing else None,
                )
            self.stations = new_stations
        logger.info("Loaded %d tide stations from DB", len(self.stations))

    async def reload(self):
        """Trigger an immediate refresh (e.g., after admin adds a station)."""
        self.load_stations_from_db()
        self._reload_event.set()

    async def start(self):
        self.load_stations_from_db()
        if not self.stations:
            logger.warning("No tide stations configured — tide service idle")
        self._running = True
        self._task = asyncio.create_task(self._daily_refresh_loop())
        logger.info("Tide service started (%d stations)", len(self.stations))

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    async def _daily_refresh_loop(self):
        while self._running:
            any_success = False
            any_error = False
            for station in list(self.stations.values()):
                try:
                    await self._fetch_station(station)
                    any_success = True
                    station.error = None
                except Exception as e:
                    logger.warning("NOAA fetch failed for %s (%s): %s", station.name, station.noaa_id, e)
                    station.error = str(e)
                    any_error = True

            if any_success and not any_error:
                update_service_status("noaa_tides", "healthy", datetime.now(timezone.utc))
            elif any_success:
                update_service_status("noaa_tides", "degraded", datetime.now(timezone.utc))
            else:
                update_service_status("noaa_tides", "error")

            # Sleep until 2 AM local time tomorrow, or 1 hour if all failed
            now = datetime.now(self._tz)
            if any_success:
                tomorrow_2am = (now + timedelta(days=1)).replace(hour=2, minute=0, second=0, microsecond=0)
                sleep_seconds = (tomorrow_2am - now).total_seconds()
            else:
                sleep_seconds = 3600

            try:
                await asyncio.wait_for(self._reload_event.wait(), timeout=max(sleep_seconds, 60))
            except asyncio.TimeoutError:
                pass
            self._reload_event.clear()

    async def _fetch_station(self, station: StationData):
        now = datetime.now(self._tz)
        begin_date = now.strftime("%Y%m%d")
        end_date = (now + timedelta(days=1)).strftime("%Y%m%d")

        url = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
        params = {
            "begin_date": begin_date,
            "end_date": end_date,
            "station": station.noaa_id,
            "product": "predictions",
            "datum": "MLLW",
            "units": "english",
            "time_zone": "lst_ldt",
            "interval": "hilo",
            "format": "json",
            "application": "SignBoard",
        }

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        predictions_raw = data.get("predictions", [])
        if not predictions_raw:
            # NOAA returns {"error": {"message": "..."}} for bad stations
            err = data.get("error", {}).get("message") if isinstance(data.get("error"), dict) else None
            if err:
                raise RuntimeError(err)
            raise RuntimeError("No predictions returned")

        station.predictions = [
            TidePrediction(time_str=p["t"], height_ft=float(p["v"]), tide_type=p["type"])
            for p in predictions_raw
        ]
        station.last_fetched = datetime.now(timezone.utc)
        logger.info("Tide predictions updated for %s: %d events", station.name, len(station.predictions))

    def _station_state(self, station: StationData) -> dict:
        if not station.predictions:
            return {
                "noaa_id": station.noaa_id,
                "name": station.name,
                "is_local": station.is_local,
                "status": "unavailable",
                "error": station.error,
                "predictions": [],
                "next_tide": None,
                "prev_tide": None,
                "direction": "unknown",
                "last_fetched": station.last_fetched.isoformat() if station.last_fetched else None,
            }

        now = datetime.now(self._tz)
        now_str = now.strftime("%Y-%m-%d %H:%M")

        next_tide = None
        prev_tide = None
        for p in station.predictions:
            if p.time_str > now_str:
                next_tide = p
                break
            prev_tide = p

        if next_tide:
            direction = "rising" if next_tide.tide_type == "H" else "falling"
        else:
            direction = "unknown"

        return {
            "noaa_id": station.noaa_id,
            "name": station.name,
            "is_local": station.is_local,
            "status": "available",
            "direction": direction,
            "next_tide": self._format_event(next_tide),
            "prev_tide": self._format_event(prev_tide),
            "predictions": [
                {
                    "time": p.time_str.split(" ")[1],
                    "date": p.time_str.split(" ")[0],
                    "height_ft": round(p.height_ft, 1),
                    "type": "High" if p.tide_type == "H" else "Low",
                }
                for p in station.predictions
            ],
            "last_fetched": station.last_fetched.isoformat() if station.last_fetched else None,
        }

    @staticmethod
    def _format_event(p: Optional[TidePrediction]) -> Optional[dict]:
        if not p:
            return None
        return {
            "type": "High" if p.tide_type == "H" else "Low",
            "time": p.time_str.split(" ")[1],
            "height_ft": round(p.height_ft, 1),
        }

    def get_current_state(self) -> dict:
        stations = [self._station_state(s) for s in self.stations.values()]
        # Put local station first, then by sort_order (already loaded in order)
        stations.sort(key=lambda s: (not s["is_local"],))
        return {
            "stations": stations,
            "count": len(stations),
        }


tide_service = TideService()
