"""Lightning safety service.

Polls the TempestWeather sidecar (``/api/lightning/status``) for recent
strike activity and drives a state machine that gates the pool-safety
alert displayed on the pool channel.

Primary source: TempestWeather (sub-second UDP-driven strike buffer).
Fallback: Tempest Cloud REST observation (``lightning_strike_count_last_1hr``
and ``lightning_strike_last_distance``) — already polled every 5 minutes by
``TempestWeatherService``. If both sources fail, the service transitions to
``OFFLINE`` so the display can show "Monitor conditions manually" per PRD §10.2.

Standards reference
-------------------
- Red Cross / NWS / NLSI "30/30 rule":
  * Clear pool when strike is within ~10 km (6 mi)
  * Reopen 30 minutes after the LAST strike
- Configurable via SettingsService: ``lightning_threshold_km`` and
  ``lightning_countdown_minutes``.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import httpx

from . import settings_service as settings_svc
from . import tempest as tempest_module
from ..api.health import update_service_status

logger = logging.getLogger("signboard.lightning")

STATE_IDLE = "idle"
STATE_ALERT = "alert"
STATE_COUNTDOWN = "countdown"
STATE_OFFLINE = "offline"


@dataclass
class Strike:
    epoch: int
    distance_km: int  # raw km from Tempest UDP/Cloud
    source: str  # "tempest_weather" | "tempest_cloud" | "simulated"

    @property
    def distance_mi(self) -> float:
        return round(self.distance_km * 0.621371, 1)

    def to_dict(self) -> dict:
        return {
            "epoch": self.epoch,
            "time": datetime.fromtimestamp(self.epoch, tz=timezone.utc).isoformat(),
            "distance_mi": self.distance_mi,
            "source": self.source,
        }


class LightningService:
    def __init__(self) -> None:
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # State
        self._state: str = STATE_IDLE
        self._state_since: datetime = datetime.now(timezone.utc)
        self._last_strike: Optional[Strike] = None
        self._nearest_strike_in_alert: Optional[Strike] = None

        # Source health
        self._tempest_weather_ok = False
        self._tempest_cloud_ok = False

        # Dedup: last (epoch, distance) we've already accepted
        self._last_accepted_key: Optional[tuple[int, int]] = None

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._poll_loop(), name="lightning-poll")
        logger.info("Lightning service started")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None

    # ---- Public accessors ----

    def get_state(self) -> dict:
        cfg = self._config()
        alert_end = None
        countdown_remaining = None
        if self._state == STATE_COUNTDOWN and self._last_strike is not None:
            end_epoch = self._last_strike.epoch + cfg["countdown_seconds"]
            alert_end = datetime.fromtimestamp(end_epoch, tz=timezone.utc).isoformat()
            countdown_remaining = max(0, end_epoch - int(datetime.now(timezone.utc).timestamp()))

        return {
            "state": self._state,
            "state_since": self._state_since.isoformat(),
            "enabled": cfg["enabled"],
            "threshold_mi": cfg["threshold_mi"],
            "countdown_minutes": cfg["countdown_minutes"],
            "alert_channels": cfg["alert_channels"],
            "last_strike": self._last_strike.to_dict() if self._last_strike else None,
            "nearest_strike_in_alert": self._nearest_strike_in_alert.to_dict() if self._nearest_strike_in_alert else None,
            "countdown_remaining_seconds": countdown_remaining,
            "countdown_end": alert_end,
            "sources": {
                "tempest_weather": self._tempest_weather_ok,
                "tempest_cloud": self._tempest_cloud_ok,
            },
        }

    # ---- Internals ----

    def _config(self) -> dict:
        channels_raw = settings_svc.get("lightning_alert_channels") or "pool"
        return {
            "enabled": settings_svc.get_bool("lightning_enabled", False),
            "threshold_mi": settings_svc.get_int("lightning_threshold_mi", 6),
            "countdown_minutes": settings_svc.get_int("lightning_countdown_minutes", 30),
            "countdown_seconds": settings_svc.get_int("lightning_countdown_minutes", 30) * 60,
            "poll_seconds": max(5, settings_svc.get_int("lightning_poll_seconds", 10)),
            "tempest_url": (settings_svc.get("lightning_tempest_url") or "http://host.docker.internal:8036").rstrip("/"),
            "alert_channels": [c.strip() for c in channels_raw.split(",") if c.strip()],
        }

    async def _poll_loop(self) -> None:
        while self._running:
            cfg = self._config()
            try:
                tempest_strike = await self._fetch_tempest_weather(cfg["tempest_url"])
            except Exception as exc:  # noqa: BLE001
                self._tempest_weather_ok = False
                logger.debug("TempestWeather strike poll failed: %s", exc)
                tempest_strike = None
            else:
                self._tempest_weather_ok = True

            cloud_strike = self._latest_cloud_strike()
            self._tempest_cloud_ok = tempest_module.weather_service.current.last_updated is not None

            best = self._pick_newer(tempest_strike, cloud_strike)
            if best is not None:
                self._ingest_strike(best, cfg)

            self._tick_state_machine(cfg)
            self._publish_health()
            try:
                await self._broadcast_state()
            except Exception:
                pass
            await asyncio.sleep(cfg["poll_seconds"])

    async def _fetch_tempest_weather(self, base_url: str) -> Optional[Strike]:
        url = f"{base_url}/api/lightning/status"
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
        last = data.get("last_strike")
        if not last:
            return None
        try:
            return Strike(
                epoch=int(last["epoch"]),
                distance_km=int(last["distance_km"]),
                source="tempest_weather",
            )
        except (KeyError, TypeError, ValueError):
            return None

    def _latest_cloud_strike(self) -> Optional[Strike]:
        """Pull the last-strike fields from the existing Tempest Cloud observation.

        The cloud API does not publish per-strike events — only aggregates and
        ``lightning_strike_last_*`` fields. We use these as a fallback signal
        when the local TempestWeather sidecar is unreachable.
        """
        obs = getattr(tempest_module.weather_service, "_last_obs_raw", None)
        if not isinstance(obs, dict):
            return None
        last_epoch = obs.get("lightning_strike_last_epoch")
        last_distance = obs.get("lightning_strike_last_distance")
        if not last_epoch or last_distance is None:
            return None
        try:
            return Strike(
                epoch=int(last_epoch),
                distance_km=int(last_distance),
                source="tempest_cloud",
            )
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _pick_newer(a: Optional[Strike], b: Optional[Strike]) -> Optional[Strike]:
        if a is None:
            return b
        if b is None:
            return a
        return a if a.epoch >= b.epoch else b

    def _ingest_strike(self, strike: Strike, cfg: dict) -> None:
        key = (strike.epoch, strike.distance_km)
        if self._last_accepted_key == key:
            return
        # Only accept strikes newer than the one we already have
        if self._last_strike is not None and strike.epoch <= self._last_strike.epoch:
            return
        self._last_accepted_key = key
        self._last_strike = strike
        logger.info(
            "Strike recorded: %s km away at %s (source=%s)",
            strike.distance_km, strike.epoch, strike.source,
        )

        if not cfg["enabled"]:
            return

        # Only trip ALERT if within threshold — compare miles to miles
        if strike.distance_mi <= cfg["threshold_mi"]:
            if self._state != STATE_ALERT:
                self._set_state(STATE_ALERT)
                self._nearest_strike_in_alert = strike
            elif self._nearest_strike_in_alert is None or strike.distance_mi < self._nearest_strike_in_alert.distance_mi:
                self._nearest_strike_in_alert = strike

    def _tick_state_machine(self, cfg: dict) -> None:
        # If disabled, force IDLE (but keep last_strike history)
        if not cfg["enabled"]:
            if self._state != STATE_IDLE:
                self._set_state(STATE_IDLE)
                self._nearest_strike_in_alert = None
            return

        # If BOTH sources are down, enter OFFLINE
        if not self._tempest_weather_ok and not self._tempest_cloud_ok:
            if self._state != STATE_OFFLINE:
                self._set_state(STATE_OFFLINE)
            return

        now_epoch = int(datetime.now(timezone.utc).timestamp())

        if self._state == STATE_ALERT:
            # After threshold_age with no newer strike within distance → COUNTDOWN
            if self._last_strike is not None:
                age = now_epoch - self._last_strike.epoch
                # ALERT → COUNTDOWN happens immediately on first non-strike tick;
                # the clock runs from the last-strike epoch.
                if age > cfg["poll_seconds"]:
                    self._set_state(STATE_COUNTDOWN)
            return

        if self._state == STATE_COUNTDOWN and self._last_strike is not None:
            if now_epoch - self._last_strike.epoch >= cfg["countdown_seconds"]:
                self._set_state(STATE_IDLE)
                self._nearest_strike_in_alert = None
            return

        if self._state == STATE_OFFLINE and (self._tempest_weather_ok or self._tempest_cloud_ok):
            self._set_state(STATE_IDLE)
            return

    def _set_state(self, new_state: str) -> None:
        if new_state == self._state:
            return
        logger.info("Lightning state: %s → %s", self._state, new_state)
        self._state = new_state
        self._state_since = datetime.now(timezone.utc)

    def _publish_health(self) -> None:
        if not settings_svc.get_bool("lightning_enabled", False):
            update_service_status("lightning", "disabled")
            return
        if self._tempest_weather_ok:
            update_service_status("lightning", "healthy", datetime.now(timezone.utc))
        elif self._tempest_cloud_ok:
            update_service_status("lightning", "degraded")
        else:
            update_service_status("lightning", "error")

    async def _broadcast_state(self) -> None:
        """Push the current state to display clients via WebSocket."""
        try:
            from ..ws.manager import ws_manager
            await ws_manager.broadcast_to_all_displays({
                "type": "lightning_state",
                "payload": self.get_state(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        except Exception:
            pass

    # ---- Admin/test hooks ----

    def inject_test_strike(self, distance_km: int) -> None:
        """Inject a synthetic strike for smoke testing (admin-only)."""
        strike = Strike(
            epoch=int(datetime.now(timezone.utc).timestamp()),
            distance_km=max(0, int(distance_km)),
            source="simulated",
        )
        self._ingest_strike(strike, self._config())


# Singleton
lightning_service = LightningService()
