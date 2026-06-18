"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql+psycopg://finance:finance@localhost:5432/finance"

    # API
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # Local LLM (litellm gateway on gb10.local, OpenAI-compatible)
    litellm_base_url: str = "http://gb10.local:4000/v1"
    litellm_api_key: str = ""
    litellm_model: str = "qwen3.6-35b"
    litellm_max_tokens: int = 2048
    litellm_timeout_seconds: float = 120.0


settings = Settings()
