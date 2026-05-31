from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Security
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7
    default_admin_password: str = "signboard2026"

    # Database
    database_url: str = "sqlite:///data/signboard.db"

    # Tempest Weather
    tempest_api_token: str = ""
    tempest_station_id: str = "183092"

    # NOAA Tides — comma-separated "id:name[:local]" entries
    noaa_stations: str = "8531991:Long Branch Fishing Pier,8531712:Long Branch Reach:local,8531680:Sandy Hook"
    # Legacy single-station fallback (merged into noaa_stations if non-empty)
    noaa_station_id: str = ""

    # TagSmart
    tagsmart_api_url: str = "http://host.docker.internal:8080"
    tagsmart_api_key: str = ""

    # Display
    timezone: str = "America/New_York"

    # Server
    log_format: str = "json"
    log_level: str = "INFO"
    cors_origin: str = "http://192.168.12.136:8100"
    uploads_dir: str = "/data/uploads"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
