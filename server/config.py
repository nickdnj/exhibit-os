from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Security
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7
    default_admin_password: str = "exhibitos2026"

    # Database
    database_url: str = "sqlite:///data/exhibitos.db"

    # Display
    timezone: str = "America/New_York"

    # Server
    log_format: str = "json"
    log_level: str = "INFO"
    cors_origin: str = "http://localhost:8100"
    uploads_dir: str = "/data/uploads"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
