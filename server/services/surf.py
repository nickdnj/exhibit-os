"""Surf service — polls Open-Meteo Marine API per spot and synthesizes
rated surf conditions combined with local wind from Tempest.
"""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

import httpx

from ..config import get_settings
from ..database import get_session
from ..models.surf_spot import SurfSpot
from ..services.tempest import weather_service
from ..api.health import update_service_status

logger = logging.getLogger("signboard.surf")
settings = get_settings()

POLL_INTERVAL_SECONDS = 3600  # hourly — wave data updates slowly


def _compass(deg: float) -> str:
    dirs = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
            'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    return dirs[int((deg + 11.25) / 22.5) % 16]


def _wind_relationship(wind_from_deg: int | None, shore_facing_deg: int) -> tuple[str, float]:
    """Return (label, weight_penalty_or_bonus) for surf quality.
    Wind direction is where wind is COMING FROM.
    shore_facing_deg is which direction the shore faces (seaward).

    Offshore wind (blowing out to sea, opposite of shore-facing): clean — bonus.
    Onshore wind (blowing toward shore, same as shore-facing): messy — penalty.
    Cross-shore: neutral.
    """
    if wind_from_deg is None:
        return ("unknown", 0.0)

    # "Offshore" = wind coming from the land side, which is 180° from shore-facing
    offshore_dir = (shore_facing_deg + 180) % 360

    def angular_diff(a, b):
        d = abs(a - b) % 360
        return min(d, 360 - d)

    diff_to_offshore = angular_diff(wind_from_deg, offshore_dir)
    diff_to_onshore = angular_diff(wind_from_deg, shore_facing_deg)

    if diff_to_offshore < 45:
        return ("offshore", 1.5)
    if diff_to_onshore < 45:
        return ("onshore", -1.5)
    if diff_to_offshore < 90:
        return ("side-offshore", 0.75)
    if diff_to_onshore < 90:
        return ("side-onshore", -0.75)
    return ("cross-shore", 0.0)


def _rate(wave_height_ft: float, wave_period_s: float, wind_adj: float) -> tuple[int, str]:
    """0-5 star surf rating + short label."""
    if wave_height_ft <= 0.2:
        return (0, "Flat")

    # Base score from wave height + period
    score = 0.0
    if wave_height_ft >= 6:
        score += 3.5
    elif wave_height_ft >= 4:
        score += 3.0
    elif wave_height_ft >= 2.5:
        score += 2.0
    elif wave_height_ft >= 1.5:
        score += 1.0
    else:
        score += 0.5

    # Period bonus — longer period = groundswell = better shape
    if wave_period_s >= 12:
        score += 1.5
    elif wave_period_s >= 9:
        score += 1.0
    elif wave_period_s >= 7:
        score += 0.5
    # short period (<6s) = wind chop, no bonus

    score += wind_adj

    score = max(0.0, min(5.0, score))

    if score >= 4.5:
        return (5, "Firing")
    if score >= 3.5:
        return (4, "Solid")
    if score >= 2.5:
        return (3, "Fun")
    if score >= 1.5:
        return (2, "Marginal")
    if score >= 0.5:
        return (1, "Small/weak")
    return (0, "Flat")


@dataclass
class SurfReading:
    """Current conditions for a spot."""
    wave_height_ft: Optional[float] = None
    wave_period_s: Optional[float] = None
    wave_direction_deg: Optional[int] = None
    swell_height_ft: Optional[float] = None
    swell_period_s: Optional[float] = None
    wind_wave_height_ft: Optional[float] = None
    fetched_at: Optional[datetime] = None
    error: Optional[str] = None
    # Hourly outlook: list of {"time": iso, "wave_height_ft": float, "wave_period_s": float}
    hourly: list[dict] = field(default_factory=list)


@dataclass
class SpotData:
    id: int
    name: str
    latitude: float
    longitude: float
    shore_facing_deg: int
    is_local: bool
    reading: SurfReading = field(default_factory=SurfReading)


class SurfService:
    def __init__(self):
        self.spots: dict[int, SpotData] = {}
        self._tz = ZoneInfo(settings.timezone)
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._reload_event = asyncio.Event()

    def load_spots_from_db(self):
        with get_session() as db:
            rows = (
                db.query(SurfSpot)
                .filter(SurfSpot.enabled == True)
                .order_by(SurfSpot.sort_order, SurfSpot.id)
                .all()
            )
            new: dict[int, SpotData] = {}
            for r in rows:
                existing = self.spots.get(r.id)
                new[r.id] = SpotData(
                    id=r.id,
                    name=r.name,
                    latitude=r.latitude,
                    longitude=r.longitude,
                    shore_facing_deg=r.shore_facing_deg,
                    is_local=r.is_local,
                    reading=existing.reading if existing else SurfReading(),
                )
            self.spots = new
        logger.info("Loaded %d surf spots from DB", len(self.spots))

    async def reload(self):
        self.load_spots_from_db()
        self._reload_event.set()

    async def start(self):
        self.load_spots_from_db()
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("Surf service started (%d spots)", len(self.spots))

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    async def _poll_loop(self):
        while self._running:
            any_success = False
            for spot in list(self.spots.values()):
                try:
                    await self._fetch_spot(spot)
                    any_success = True
                    spot.reading.error = None
                except Exception as e:
                    logger.warning("Open-Meteo fetch failed for %s: %s", spot.name, e)
                    spot.reading.error = str(e)

            if any_success:
                update_service_status("surf", "healthy", datetime.now(timezone.utc))
            elif self.spots:
                update_service_status("surf", "error")

            try:
                await asyncio.wait_for(self._reload_event.wait(), timeout=POLL_INTERVAL_SECONDS)
            except asyncio.TimeoutError:
                pass
            self._reload_event.clear()

    async def _fetch_spot(self, spot: SpotData):
        url = "https://marine-api.open-meteo.com/v1/marine"
        params = {
            "latitude": spot.latitude,
            "longitude": spot.longitude,
            "hourly": "wave_height,wave_period,wave_direction,wind_wave_height,swell_wave_height,swell_wave_period",
            "current": "wave_height,wave_period,wave_direction,swell_wave_height,swell_wave_period,wind_wave_height",
            "length_unit": "imperial",
            "timezone": settings.timezone,
            "forecast_days": 1,
        }
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        cur = data.get("current") or {}
        reading = SurfReading(
            wave_height_ft=cur.get("wave_height"),
            wave_period_s=cur.get("wave_period"),
            wave_direction_deg=cur.get("wave_direction"),
            swell_height_ft=cur.get("swell_wave_height"),
            swell_period_s=cur.get("swell_wave_period"),
            wind_wave_height_ft=cur.get("wind_wave_height"),
            fetched_at=datetime.now(timezone.utc),
        )

        hourly = data.get("hourly") or {}
        times = hourly.get("time", [])
        heights = hourly.get("wave_height", [])
        periods = hourly.get("wave_period", [])
        # Keep future-only hourly snippets (next 12h)
        now_local = datetime.now(self._tz).strftime("%Y-%m-%dT%H:00")
        hourly_out: list[dict] = []
        for t, h, p in zip(times, heights, periods):
            if t >= now_local:
                hourly_out.append({"time": t, "wave_height_ft": h, "wave_period_s": p})
            if len(hourly_out) >= 12:
                break
        reading.hourly = hourly_out

        spot.reading = reading
        logger.info("Surf updated for %s: %.1fft @ %.1fs", spot.name, reading.wave_height_ft or 0, reading.wave_period_s or 0)

    def _spot_state(self, spot: SpotData) -> dict:
        r = spot.reading
        # Pull wind from tempest
        wind_deg = weather_service.current.wind_direction
        wind_speed = weather_service.current.wind_speed_mph
        wind_rel, wind_adj = _wind_relationship(wind_deg, spot.shore_facing_deg)

        rating, label = (0, "Unknown")
        if r.wave_height_ft is not None and r.wave_period_s is not None:
            rating, label = _rate(r.wave_height_ft, r.wave_period_s, wind_adj)

        return {
            "id": spot.id,
            "name": spot.name,
            "is_local": spot.is_local,
            "latitude": spot.latitude,
            "longitude": spot.longitude,
            "shore_facing_deg": spot.shore_facing_deg,
            "status": "available" if r.wave_height_ft is not None else "unavailable",
            "error": r.error,
            "rating": rating,
            "label": label,
            "wave_height_ft": round(r.wave_height_ft, 1) if r.wave_height_ft is not None else None,
            "wave_period_s": round(r.wave_period_s, 1) if r.wave_period_s is not None else None,
            "wave_direction_deg": r.wave_direction_deg,
            "wave_direction_compass": _compass(r.wave_direction_deg) if r.wave_direction_deg is not None else None,
            "swell_height_ft": round(r.swell_height_ft, 1) if r.swell_height_ft is not None else None,
            "swell_period_s": round(r.swell_period_s, 1) if r.swell_period_s is not None else None,
            "wind_wave_height_ft": round(r.wind_wave_height_ft, 1) if r.wind_wave_height_ft is not None else None,
            "wind": {
                "speed_mph": round(wind_speed, 1) if wind_speed is not None else None,
                "direction_deg": wind_deg,
                "direction_compass": _compass(wind_deg) if wind_deg is not None else None,
                "relationship": wind_rel,
            },
            "hourly": [
                {
                    "time": h["time"].split("T")[1] if "T" in h["time"] else h["time"],
                    "wave_height_ft": round(h["wave_height_ft"], 1) if h["wave_height_ft"] is not None else None,
                    "wave_period_s": round(h["wave_period_s"], 1) if h["wave_period_s"] is not None else None,
                }
                for h in r.hourly
            ],
            "fetched_at": r.fetched_at.isoformat() if r.fetched_at else None,
        }

    def get_report(self) -> dict:
        spots = [self._spot_state(s) for s in self.spots.values()]
        spots.sort(key=lambda s: (not s["is_local"],))
        return {"spots": spots, "count": len(spots)}


surf_service = SurfService()
