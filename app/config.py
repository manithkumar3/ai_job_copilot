from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Job Copilot"
    secret_key: str = "change-me"
    base_url: str = "http://127.0.0.1:8000"
    debug: bool = True

    database_url: str = f"sqlite:///{(BASE_DIR / 'ai_job_copilot.db').as_posix()}"
    upload_dir: Path = BASE_DIR / "app" / "static" / "uploads"

    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"

    google_client_id: str | None = None
    google_client_secret: str | None = None

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_sender: str = "noreply@example.com"

    reminder_days_without_response: int = 7

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"1", "true", "yes", "on", "debug"}:
                return True
            if lowered in {"0", "false", "no", "off", "release", "prod", "production"}:
                return False
        return bool(value)

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value):
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        if normalized.startswith("postgres://"):
            return normalized.replace("postgres://", "postgresql+psycopg://", 1)
        if normalized.startswith("postgresql://") and "+psycopg://" not in normalized:
            return normalized.replace("postgresql://", "postgresql+psycopg://", 1)
        return normalized


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    (settings.upload_dir / "resumes").mkdir(parents=True, exist_ok=True)
    (settings.upload_dir / "generated").mkdir(parents=True, exist_ok=True)
    return settings
