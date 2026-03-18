from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://flightmatch:flightmatch@localhost:5432/flightmatch"
    test_database_url: str = "postgresql+asyncpg://flightmatch_test:flightmatch_test@localhost:5433/flightmatch_test"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # Security
    api_key: str = "change-me-in-production"
    secret_key: str = "change-me-in-production-32-chars-min"
    fernet_key: str = ""

    # Email
    mail_username: str = ""
    mail_password: str = ""
    mail_from: str = "noreply@flightmatch.org"
    mail_port: int = 587
    mail_server: str = "smtp.gmail.com"
    mail_starttls: bool = True
    mail_ssl_tls: bool = False
    frontend_base_url: str = "http://localhost:8000"

    # Google Calendar
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/calendar/google/callback"

    # Outlook
    outlook_client_id: str = ""
    outlook_client_secret: str = ""
    outlook_redirect_uri: str = "http://localhost:8000/api/v1/calendar/outlook/callback"
    outlook_authority: str = "https://login.microsoftonline.com/common"

    # Sentry
    sentry_dsn: str = ""

    # App
    environment: str = "development"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
