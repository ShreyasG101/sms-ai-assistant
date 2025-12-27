"""Application configuration with validation and defaults."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Required
    openai_api_key: str

    # AI Configuration
    ai_provider: str = "openai"
    ai_model: str = "gpt-4o-mini"
    system_prompt: str = "You are a helpful assistant. Keep responses concise for SMS."
    max_context_messages: int = 20

    # Authorization (empty list = allow all)
    allowed_phone_numbers: list[str] = []

    # Server
    host: str = "0.0.0.0"
    port: int = 8080

    # Database
    database_path: str = "./data/sms_assistant.db"

    # Optional: API key for httpSMS authentication
    sms_api_key: str | None = None

    @field_validator("allowed_phone_numbers", mode="before")
    @classmethod
    def parse_phone_numbers(cls, v: str | list[str]) -> list[str]:
        """Parse comma-separated phone numbers from env var."""
        if isinstance(v, list):
            return v
        if not v or not v.strip():
            return []
        return [num.strip() for num in v.split(",") if num.strip()]

    @field_validator("ai_provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Validate AI provider is supported."""
        supported = {"openai"}
        if v.lower() not in supported:
            raise ValueError(f"Unsupported AI provider: {v}. Supported: {supported}")
        return v.lower()


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
