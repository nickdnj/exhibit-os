"""Settings service — DB-backed config with env-var fallback.

Pattern: services and APIs call `settings_service.get("tempest_api_token")`
rather than reading from `config.get_settings()` directly. This means admins
can change values in the UI and they take effect on the next read cycle
(e.g., next weather poll) without a container restart.

On first boot, `seed_defaults()` populates the DB from env vars so existing
deployments keep working unchanged. Env vars remain the fallback if a key
is missing from the DB.
"""
from __future__ import annotations

import logging
import threading
from typing import Optional

from ..config import get_settings
from ..database import get_session
from ..models.setting import Setting

logger = logging.getLogger("signboard.settings_service")


# Registry: defines every setting the UI knows about.
# (key, group, value_type, label, description, options, is_secret, is_readonly, sort_order)
# value at runtime comes from DB → env fallback → registry default.
SETTING_REGISTRY: list[dict] = [
    # --- Weather ---
    {"key": "tempest_station_id", "group": "weather", "value_type": "text",
     "label": "Tempest Station ID", "description": "WeatherFlow device ID for current conditions",
     "is_secret": False, "sort_order": 10},
    {"key": "tempest_api_token", "group": "weather", "value_type": "password",
     "label": "Tempest API Token", "description": "Cloud API credential for Tempest REST requests",
     "is_secret": True, "sort_order": 20},
    {"key": "timezone", "group": "weather", "value_type": "text",
     "label": "Local Timezone", "description": "IANA name, e.g. America/New_York. Affects tide direction and schedule times.",
     "is_secret": False, "sort_order": 30},

    # --- Integrations ---
    {"key": "tagsmart_api_url", "group": "integrations", "value_type": "text",
     "label": "TagSmart API URL", "description": "Endpoint for fob → resident lookup",
     "is_secret": False, "sort_order": 10},
    {"key": "tagsmart_api_key", "group": "integrations", "value_type": "password",
     "label": "TagSmart API Key", "description": "Read-only credentials for fob/slip queries",
     "is_secret": True, "sort_order": 20},

    # --- Display ---
    {"key": "default_rotation_interval", "group": "display", "value_type": "number",
     "label": "Default Rotation Interval (seconds)",
     "description": "Global fallback page duration when not set per-channel",
     "is_secret": False, "sort_order": 10},
    {"key": "transition_animation", "group": "display", "value_type": "dropdown",
     "label": "Transition Animation", "description": "Page transition style",
     "options": "fade,slide,none",
     "is_secret": False, "sort_order": 20},

    # --- Lightning ---
    {"key": "lightning_enabled", "group": "lightning", "value_type": "toggle",
     "label": "Enable Lightning Monitor",
     "description": "Interrupt pool channel with safety alert when strikes are detected",
     "is_secret": False, "sort_order": 10},
    {"key": "lightning_threshold_mi", "group": "lightning", "value_type": "number",
     "label": "Alert Distance (miles)",
     "description": "Strikes within this distance trigger the pool closed alert. Red Cross / NWS 30-30 rule standard is 6 miles.",
     "is_secret": False, "sort_order": 20},
    {"key": "lightning_countdown_minutes", "group": "lightning", "value_type": "number",
     "label": "All-Clear Countdown (minutes)",
     "description": "Minutes after last strike before rotation resumes (Red Cross / NWS 30/30 rule = 30)",
     "is_secret": False, "sort_order": 30},
    {"key": "lightning_tempest_url", "group": "lightning", "value_type": "text",
     "label": "TempestWeather API URL",
     "description": "Base URL for the TempestWeather strike API. Usually http://host.docker.internal:8036",
     "is_secret": False, "sort_order": 40},
    {"key": "lightning_poll_seconds", "group": "lightning", "value_type": "number",
     "label": "Poll Interval (seconds)",
     "description": "How often SignBoard polls TempestWeather for new strikes",
     "is_secret": False, "sort_order": 50},
    {"key": "lightning_alert_channels", "group": "lightning", "value_type": "text",
     "label": "Alert Channels",
     "description": "Comma-separated channel slugs to interrupt. Default: pool. Set to 'pool,office' to alert on both.",
     "is_secret": False, "sort_order": 60},

    # --- System ---
    {"key": "log_level", "group": "system", "value_type": "dropdown",
     "label": "Log Level", "description": "Server log verbosity",
     "options": "DEBUG,INFO,WARNING,ERROR",
     "is_secret": False, "sort_order": 10},
    {"key": "log_format", "group": "system", "value_type": "dropdown",
     "label": "Log Format", "description": "Server log output format",
     "options": "json,text",
     "is_secret": False, "sort_order": 20},
    {"key": "cors_origin", "group": "system", "value_type": "text",
     "label": "CORS Origin",
     "description": "Allowed browser origin for admin dashboard",
     "is_secret": False, "sort_order": 30},
]


# Mapping: setting key → (config.py attribute name, default)
# Used both for env-seeding and for get() fallback.
ENV_FALLBACKS: dict[str, tuple[Optional[str], object]] = {
    "tempest_station_id": ("tempest_station_id", "183092"),
    "tempest_api_token": ("tempest_api_token", ""),
    "timezone": ("timezone", "America/New_York"),
    "tagsmart_api_url": ("tagsmart_api_url", "http://host.docker.internal:8080"),
    "tagsmart_api_key": ("tagsmart_api_key", ""),
    "default_rotation_interval": (None, 30),  # No env var — registry-only
    "transition_animation": (None, "fade"),
    "lightning_enabled": (None, False),
    "lightning_threshold_mi": (None, 6),
    "lightning_countdown_minutes": (None, 30),
    "lightning_tempest_url": (None, "http://host.docker.internal:8036"),
    "lightning_poll_seconds": (None, 10),
    "lightning_alert_channels": (None, "pool"),
    "log_level": ("log_level", "INFO"),
    "log_format": ("log_format", "json"),
    "cors_origin": ("cors_origin", "http://192.168.12.136:8100"),
}


class SettingsService:
    """DB-backed config with env fallback and in-memory cache."""

    def __init__(self):
        self._cache: dict[str, str] = {}
        self._lock = threading.RLock()
        self._loaded = False

    def _load_cache(self):
        """Read all settings into cache in a single query."""
        with self._lock:
            with get_session() as db:
                rows = db.query(Setting).all()
                self._cache = {r.key: r.value for r in rows}
                self._loaded = True

    def _env_default(self, key: str) -> str:
        """Look up the env-var / registry default for a key."""
        if key not in ENV_FALLBACKS:
            return ""
        attr, default = ENV_FALLBACKS[key]
        if attr is not None:
            env_settings = get_settings()
            val = getattr(env_settings, attr, None)
            if val not in (None, ""):
                return str(val)
        return str(default) if default is not None else ""

    def get(self, key: str) -> str:
        """Return raw string value for a setting. DB → env → registry default."""
        with self._lock:
            if not self._loaded:
                self._load_cache()
            val = self._cache.get(key)
        if val is None or val == "":
            return self._env_default(key)
        return val

    def get_int(self, key: str, default: int = 0) -> int:
        try:
            return int(self.get(key) or default)
        except (TypeError, ValueError):
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        v = (self.get(key) or "").strip().lower()
        if v in ("1", "true", "yes", "on"):
            return True
        if v in ("0", "false", "no", "off", ""):
            return False
        return default

    def set(self, key: str, value: str):
        """Persist a setting to the DB and update cache."""
        with self._lock:
            with get_session() as db:
                row = db.query(Setting).filter(Setting.key == key).first()
                if row is None:
                    # Create a minimal row (UI never creates unknown settings, but be safe).
                    row = Setting(key=key, value=value)
                    db.add(row)
                else:
                    row.value = value
                db.commit()
            self._cache[key] = value

    def invalidate(self):
        """Force reload on next read (e.g., after bulk update)."""
        with self._lock:
            self._loaded = False

    def list_registry(self) -> list[dict]:
        """Return the registry merged with current values, for the UI."""
        if not self._loaded:
            self._load_cache()
        out = []
        for entry in SETTING_REGISTRY:
            key = entry["key"]
            out.append({
                **entry,
                "value": self.get(key),
            })
        return out

    def seed_defaults(self):
        """Populate the DB on first boot using env-var fallbacks. Idempotent."""
        with self._lock:
            with get_session() as db:
                existing_keys = {r.key for r in db.query(Setting.key).all()}
                created = 0
                for entry in SETTING_REGISTRY:
                    key = entry["key"]
                    if key in existing_keys:
                        # Backfill metadata in case the registry changed
                        row = db.query(Setting).filter(Setting.key == key).first()
                        if row is not None:
                            row.group = entry["group"]
                            row.value_type = entry["value_type"]
                            row.label = entry["label"]
                            row.description = entry.get("description")
                            row.options = entry.get("options")
                            row.is_secret = entry.get("is_secret", False)
                            row.is_readonly = entry.get("is_readonly", False)
                            row.sort_order = entry.get("sort_order", 0)
                        continue
                    initial_value = self._env_default(key)
                    db.add(Setting(
                        key=key,
                        value=initial_value,
                        group=entry["group"],
                        value_type=entry["value_type"],
                        label=entry["label"],
                        description=entry.get("description"),
                        options=entry.get("options"),
                        is_secret=entry.get("is_secret", False),
                        is_readonly=entry.get("is_readonly", False),
                        sort_order=entry.get("sort_order", 0),
                    ))
                    created += 1
                db.commit()
                if created:
                    logger.info("Seeded %d settings from registry/env", created)
            self._loaded = False  # Force reload on next read


# Singleton
settings_service = SettingsService()


def get(key: str) -> str:
    return settings_service.get(key)


def get_int(key: str, default: int = 0) -> int:
    return settings_service.get_int(key, default)


def get_bool(key: str, default: bool = False) -> bool:
    return settings_service.get_bool(key, default)


def _get_timezone() -> Optional["ZoneInfo"]:  # type: ignore[name-defined]
    """Convenience: return a ZoneInfo for the configured timezone, or None."""
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(get("timezone") or "America/New_York")
    except Exception:
        return None
