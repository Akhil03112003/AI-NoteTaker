"""Central application settings. Secret values are never rendered in errors."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_DIR / ".env"


def _default_audio_storage_dir() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "ai-notetaker" / "uploads"
    return Path.home() / "AppData" / "Local" / "ai-notetaker" / "uploads"


class ConfigurationError(RuntimeError):
    """A safe-to-display settings error that omits values and raw validator data."""


def _normalize_postgres_url(value: object) -> object:
    if value is None:
        return value
    if isinstance(value, SecretStr):
        value = value.get_secret_value()
    if not isinstance(value, str):
        raise ValueError("must be a PostgreSQL URL")
    value = value.strip()
    if value.startswith("postgres://"):
        return "postgresql+psycopg://" + value.removeprefix("postgres://")
    if value.startswith("postgresql://"):
        return "postgresql+psycopg://" + value.removeprefix("postgresql://")
    if not value.startswith("postgresql+psycopg://"):
        raise ValueError("must use PostgreSQL with psycopg")
    return value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    database_url: SecretStr
    test_database_url: SecretStr | None = None
    deepgram_api_key: SecretStr | None = None
    deepgram_model: str = "nova-3"
    omniroute_api_key: SecretStr | None = None
    omniroute_base_url: str | None = "http://localhost:20128/v1"
    omniroute_model: str | None = "kr/claude-sonnet-4.5"
    provider_timeout_seconds: float = Field(default=60, gt=0, le=600)
    audio_storage_dir: Path = Field(default_factory=_default_audio_storage_dir)
    max_upload_bytes: int = Field(default=25 * 1024 * 1024, gt=0)
    cors_origins: str = (
        "http://127.0.0.1:4173,http://localhost:4173,"
        "http://127.0.0.1:5173,http://localhost:5173"
    )

    @field_validator("database_url", "test_database_url", mode="before")
    @classmethod
    def validate_database_urls(cls, value: object) -> object:
        return _normalize_postgres_url(value)

    @field_validator("audio_storage_dir", mode="before")
    @classmethod
    def normalize_audio_storage_dir(cls, value: object) -> Path:
        if value is None or str(value).strip().lower() == "uploads":
            return _default_audio_storage_dir()
        expanded = os.path.expandvars(str(value).strip())
        return Path(expanded)

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, value: str) -> str:
        origins = [item.strip() for item in value.split(",") if item.strip()]
        for origin in origins:
            parsed = urlsplit(origin)
            if (
                origin == "*"
                or parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path not in {"", "/"}
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("origins must be explicit HTTP(S) origins")
        return ",".join(origins)

    @field_validator("omniroute_base_url")
    @classmethod
    def validate_omniroute_base_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        parsed = urlsplit(value.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError("must be an HTTP(S) base URL without embedded credentials")
        return value.strip().rstrip("/")

    @property
    def cors_origin_list(self) -> list[str]:
        return [item for item in self.cors_origins.split(",") if item]

    @property
    def resolved_audio_storage_dir(self) -> Path:
        path = self.audio_storage_dir
        if not path.is_absolute():
            path = BACKEND_DIR / path
        return path.resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as exc:
        fields = sorted(
            {
                str(error["loc"][0])
                for error in exc.errors(include_url=False)
                if error.get("loc")
            }
        )
        fields_text = ", ".join(fields) if fields else "configuration"
        raise ConfigurationError(
            f"Invalid or missing backend settings for: {fields_text}. "
            "Review the setting names and formats; values were omitted."
        ) from None
