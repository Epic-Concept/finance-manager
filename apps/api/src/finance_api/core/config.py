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


settings = Settings()
