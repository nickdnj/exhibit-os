"""Fishing/solunar computation service.

For each configured fishing location, combines:
- Tide predictions (from linked tide station, via tide_service)
- Sun times (astral)
- Moon phase + rise/set + transit (ephem)

Produces rated 15-minute windows for today and ranks the best fishing periods.
"""
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

import ephem
from astral import LocationInfo
from astral.sun import sun

from ..config import get_settings
from ..database import get_session
from ..models.fishing_location import FishingLocation
from ..services.tides import tide_service

logger = logging.getLogger("signboard.fishing")
settings = get_settings()


# ---- Solunar theory weights -------------------------------------------------
# Major periods: ±1h around moonrise/moonset. Score boost when moon is at horizon.
# Minor periods: ±30min around moon transit (overhead) or anti-transit (underfoot).
# Dawn/dusk: ±30min around sunrise/sunset.
# Tide turn: ±45min around high or low tide (fish feed on moving water near slack).
# Moon phase: New/full adds a day-wide bonus (spring tides → more current).

MAJOR_WINDOW_MIN = 60
MINOR_WINDOW_MIN = 30
DAWN_DUSK_MIN = 30
TIDE_TURN_MIN = 45


@dataclass
class RatedMinute:
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)


def _minute_index(t: datetime, day_start: datetime) -> int:
    return int((t - day_start).total_seconds() // 60)


def _apply_window(grid: list[RatedMinute], center: Optional[datetime], day_start: datetime, half_width_min: int, weight: float, label: str):
    if center is None:
        return
    start = _minute_index(center, day_start) - half_width_min
    end = _minute_index(center, day_start) + half_width_min
    for i in range(max(0, start), min(len(grid), end + 1)):
        grid[i].score += weight
        if label not in grid[i].reasons:
            grid[i].reasons.append(label)


def _ephem_observer(lat: float, lon: float, when: datetime) -> ephem.Observer:
    obs = ephem.Observer()
    obs.lat = str(lat)
    obs.lon = str(lon)
    obs.elevation = 0
    # ephem wants UTC
    obs.date = when.astimezone(timezone.utc).replace(tzinfo=None)
    return obs


def _moon_events(lat: float, lon: float, day_start_local: datetime, tz: ZoneInfo) -> dict:
    """Compute moonrise/moonset/transit/anti-transit for the local day."""
    moon = ephem.Moon()
    obs = _ephem_observer(lat, lon, day_start_local)

    def to_local(d: ephem.Date | None) -> Optional[datetime]:
        if d is None:
            return None
        try:
            return ephem.Date(d).datetime().replace(tzinfo=timezone.utc).astimezone(tz)
        except Exception:
            return None

    # Look for rise/set/transit events within the next 36h window so we catch the ones
    # that land inside our local calendar day.
    events: dict[str, Optional[datetime]] = {"rise": None, "set": None, "transit": None, "anti_transit": None}
    day_end_local = day_start_local + timedelta(days=1)

    def _within_day(dt: Optional[datetime]) -> Optional[datetime]:
        if dt is None:
            return None
        return dt if day_start_local <= dt < day_end_local else None

    # We iterate starting 12h before day start so we don't miss early-morning rises
    cursor = day_start_local - timedelta(hours=12)
    scan_end = day_start_local + timedelta(hours=36)

    while cursor < scan_end:
        obs.date = cursor.astimezone(timezone.utc).replace(tzinfo=None)
        try:
            next_rise = to_local(obs.next_rising(moon))
        except (ephem.AlwaysUpError, ephem.NeverUpError):
            next_rise = None
        try:
            next_set = to_local(obs.next_setting(moon))
        except (ephem.AlwaysUpError, ephem.NeverUpError):
            next_set = None
        try:
            next_transit = to_local(obs.next_transit(moon))
        except Exception:
            next_transit = None
        try:
            next_anti = to_local(obs.next_antitransit(moon))
        except Exception:
            next_anti = None

        for key, value in [("rise", next_rise), ("set", next_set), ("transit", next_transit), ("anti_transit", next_anti)]:
            in_day = _within_day(value)
            if in_day and events[key] is None:
                events[key] = in_day

        # Advance cursor past the earliest event to find any subsequent ones
        candidates = [v for v in (next_rise, next_set, next_transit, next_anti) if v is not None]
        if not candidates:
            break
        cursor = min(candidates) + timedelta(minutes=1)
        if all(events.values()):
            break

    # Moon phase
    phase_info = _moon_phase(day_start_local + timedelta(hours=12))
    return {**events, **phase_info}


def _moon_phase(when: datetime) -> dict:
    """Return phase name + illumination percentage + bonus flag."""
    moon = ephem.Moon(when.astimezone(timezone.utc).replace(tzinfo=None))
    illum = float(moon.phase)  # 0-100

    # Determine phase by angle from sun
    sun_obj = ephem.Sun(when.astimezone(timezone.utc).replace(tzinfo=None))
    elong = ephem.separation(moon, sun_obj)  # radians, 0..pi
    elong_deg = float(elong) * 180.0 / 3.14159265358979

    # Compare to previous new moon to determine waxing vs waning
    prev_new = ephem.previous_new_moon(when.astimezone(timezone.utc).replace(tzinfo=None))
    next_new = ephem.next_new_moon(when.astimezone(timezone.utc).replace(tzinfo=None))
    days_since_new = (ephem.Date(when.astimezone(timezone.utc).replace(tzinfo=None)) - prev_new)
    days_until_new = (next_new - ephem.Date(when.astimezone(timezone.utc).replace(tzinfo=None)))

    if days_since_new < 1:
        phase_name = "New Moon"
    elif days_until_new < 1:
        phase_name = "New Moon"
    elif illum >= 98:
        phase_name = "Full Moon"
    elif elong_deg < 90 and days_since_new < 14:
        phase_name = "Waxing Crescent" if illum < 50 else "Waxing Gibbous"
    elif elong_deg >= 90 and days_since_new < 14:
        phase_name = "Waxing Gibbous"
    elif elong_deg >= 90:
        phase_name = "Waning Gibbous"
    else:
        phase_name = "Waning Crescent"

    # Solunar bonus near new/full moon (within 2 days)
    near_new = days_since_new < 2 or days_until_new < 2
    prev_full = ephem.previous_full_moon(when.astimezone(timezone.utc).replace(tzinfo=None))
    next_full = ephem.next_full_moon(when.astimezone(timezone.utc).replace(tzinfo=None))
    days_since_full = (ephem.Date(when.astimezone(timezone.utc).replace(tzinfo=None)) - prev_full)
    days_until_full = (next_full - ephem.Date(when.astimezone(timezone.utc).replace(tzinfo=None)))
    near_full = days_since_full < 2 or days_until_full < 2

    return {
        "phase_name": phase_name,
        "illumination_pct": round(illum, 1),
        "near_new_or_full": near_new or near_full,
    }


def _sun_times(lat: float, lon: float, the_date: date, tz: ZoneInfo) -> dict:
    loc = LocationInfo(name="loc", region="", timezone=str(tz), latitude=lat, longitude=lon)
    try:
        s = sun(loc.observer, date=the_date, tzinfo=tz)
        return {"sunrise": s["sunrise"], "sunset": s["sunset"], "dawn": s["dawn"], "dusk": s["dusk"]}
    except Exception as e:
        logger.warning("Sun calc failed for %s,%s: %s", lat, lon, e)
        return {"sunrise": None, "sunset": None, "dawn": None, "dusk": None}


def _tide_events_for_today(tide_station_id: Optional[int], tz: ZoneInfo, the_date: date) -> list[dict]:
    """Fetch today's high/low events for the linked tide station."""
    if tide_station_id is None:
        return []
    # Map db id → noaa_id via DB
    from ..models.tide_station import TideStation
    with get_session() as db:
        station = db.query(TideStation).filter(TideStation.id == tide_station_id).first()
        if not station:
            return []
        noaa_id = station.noaa_id

    station_data = tide_service.stations.get(noaa_id)
    if not station_data or not station_data.predictions:
        return []

    day_str = the_date.strftime("%Y-%m-%d")
    events = []
    for p in station_data.predictions:
        if not p.time_str.startswith(day_str):
            continue
        dt_naive = datetime.strptime(p.time_str, "%Y-%m-%d %H:%M")
        dt = dt_naive.replace(tzinfo=tz)
        events.append({
            "type": "High" if p.tide_type == "H" else "Low",
            "time": dt,
            "height_ft": round(p.height_ft, 1),
        })
    return events


def _window_to_str(start_min: int, end_min: int, day_start: datetime) -> tuple[str, str]:
    s = (day_start + timedelta(minutes=start_min)).strftime("%H:%M")
    e = (day_start + timedelta(minutes=end_min + 1)).strftime("%H:%M")
    return s, e


def compute_location(loc: FishingLocation, tz: ZoneInfo, the_date: date) -> dict:
    day_start = datetime.combine(the_date, time(0, 0), tzinfo=tz)
    grid: list[RatedMinute] = [RatedMinute() for _ in range(24 * 60)]

    # Sun
    sun_times = _sun_times(loc.latitude, loc.longitude, the_date, tz)
    _apply_window(grid, sun_times["sunrise"], day_start, DAWN_DUSK_MIN, 2.0, "dawn")
    _apply_window(grid, sun_times["sunset"], day_start, DAWN_DUSK_MIN, 2.0, "dusk")

    # Moon
    moon = _moon_events(loc.latitude, loc.longitude, day_start, tz)
    _apply_window(grid, moon.get("rise"), day_start, MAJOR_WINDOW_MIN, 2.0, "moonrise")
    _apply_window(grid, moon.get("set"), day_start, MAJOR_WINDOW_MIN, 2.0, "moonset")
    _apply_window(grid, moon.get("transit"), day_start, MINOR_WINDOW_MIN, 1.0, "moon overhead")
    _apply_window(grid, moon.get("anti_transit"), day_start, MINOR_WINDOW_MIN, 1.0, "moon underfoot")

    # Tide turns — peak fishing is the 45min on either side of slack (top/bottom)
    tide_events = _tide_events_for_today(loc.tide_station_id, tz, the_date)
    for ev in tide_events:
        label = f"{ev['type'].lower()} tide"
        _apply_window(grid, ev["time"], day_start, TIDE_TURN_MIN, 1.5, label)

    # New/full moon bonus — day-wide small bonus
    if moon.get("near_new_or_full"):
        for m in grid:
            m.score += 0.25

    # Best windows — group contiguous minutes with score >= 3.0
    best_windows = _extract_windows(grid, day_start, min_score=3.0, min_length_min=30)
    # Fallback: if no strong windows, take the top 2 peaks with score >= 2.0
    if not best_windows:
        best_windows = _extract_windows(grid, day_start, min_score=2.0, min_length_min=30)

    # Overall rating: max score of any hour, clamped/mapped to 1-5
    max_score = max((m.score for m in grid), default=0.0)
    overall_rating = _score_to_stars(max_score)

    return {
        "id": loc.id,
        "name": loc.name,
        "latitude": loc.latitude,
        "longitude": loc.longitude,
        "is_local": loc.is_local,
        "date": the_date.isoformat(),
        "overall_rating": overall_rating,
        "sun": {
            "sunrise": sun_times["sunrise"].strftime("%H:%M") if sun_times["sunrise"] else None,
            "sunset": sun_times["sunset"].strftime("%H:%M") if sun_times["sunset"] else None,
        },
        "moon": {
            "phase_name": moon["phase_name"],
            "illumination_pct": moon["illumination_pct"],
            "rise": moon["rise"].strftime("%H:%M") if moon["rise"] else None,
            "set": moon["set"].strftime("%H:%M") if moon["set"] else None,
        },
        "tides": [
            {"type": t["type"], "time": t["time"].strftime("%H:%M"), "height_ft": t["height_ft"]}
            for t in tide_events
        ],
        "best_windows": best_windows[:4],  # top 4
    }


def _extract_windows(grid: list[RatedMinute], day_start: datetime, min_score: float, min_length_min: int) -> list[dict]:
    windows = []
    i = 0
    n = len(grid)
    while i < n:
        if grid[i].score >= min_score:
            start = i
            total = 0.0
            reasons: list[str] = []
            while i < n and grid[i].score >= min_score:
                total += grid[i].score
                for r in grid[i].reasons:
                    if r not in reasons:
                        reasons.append(r)
                i += 1
            end = i - 1
            length = end - start + 1
            if length >= min_length_min:
                avg = total / max(length, 1)
                peak = max(grid[start:end + 1], key=lambda m: m.score).score
                s_str, e_str = _window_to_str(start, end, day_start)
                windows.append({
                    "start": s_str,
                    "end": e_str,
                    "length_min": length,
                    "avg_score": round(avg, 2),
                    "peak_score": round(peak, 2),
                    "rating": _score_to_stars(peak),
                    "reasons": reasons,
                })
        else:
            i += 1
    # Sort by peak score desc
    windows.sort(key=lambda w: (-w["peak_score"], w["start"]))
    return windows


def _score_to_stars(score: float) -> int:
    if score >= 5.0:
        return 5
    if score >= 4.0:
        return 4
    if score >= 3.0:
        return 3
    if score >= 2.0:
        return 2
    if score >= 1.0:
        return 1
    return 0


class FishingService:
    """Stateless — computes on demand (cheap). Could cache per-day if needed."""

    def __init__(self):
        self._tz = ZoneInfo(settings.timezone)

    def get_report(self) -> dict:
        today = datetime.now(self._tz).date()
        with get_session() as db:
            locations = (
                db.query(FishingLocation)
                .filter(FishingLocation.enabled == True)
                .order_by(FishingLocation.sort_order, FishingLocation.id)
                .all()
            )
            data = [compute_location(loc, self._tz, today) for loc in locations]

        # Local first
        data.sort(key=lambda d: (not d["is_local"],))
        return {
            "date": today.isoformat(),
            "locations": data,
            "count": len(data),
        }


fishing_service = FishingService()
