"""Centralised application settings loaded from environment / .env file."""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Auth
    secret_key: str = Field(default="dev-secret-key-change-in-production")
    access_token_expire_hours: int = Field(default=24)

    # External APIs
    openweather_api_key: Optional[str] = Field(default=None)
    foursquare_api_key: Optional[str] = Field(default=None)
    foursquare_enabled: bool = Field(default=True)
    nominatim_user_agent: str = Field(
        default="local-trip-suggester/2.0 (contact@example.com)"
    )

    # AWS Bedrock
    aws_region: str = Field(default="us-east-1")
    aws_access_key_id: Optional[str] = Field(default=None)
    aws_secret_access_key: Optional[str] = Field(default=None)
    bedrock_model_id: str = Field(default="amazon.nova-lite-v1:0")
    llm_mock: bool = Field(default=False)

    # Database
    database_url: str = Field(default="sqlite:///./local_travel.db")

    # Tuning
    http_timeout_seconds: float = Field(default=10.0)
    place_cache_ttl_hours: int = Field(default=24)
    weather_cache_ttl_minutes: int = Field(default=30)
    default_max_results: int = Field(default=5)
    log_level: str = Field(default="INFO")

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgres")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached accessor — Settings is built exactly once per process."""
    return Settings()
