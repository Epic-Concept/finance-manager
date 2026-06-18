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
    # qwen3.6-35b is a reasoning model: chain-of-thought is emitted before the
    # answer, so the budget must cover reasoning + output. The gateway serves a
    # 256k context, so this is generous headroom, not a tight cap.
    litellm_max_tokens: int = 8192
    litellm_timeout_seconds: float = 120.0

    # Brave Search API (web-lookup gatherer backend)
    brave_api_key: str = ""
    brave_base_url: str = "https://api.search.brave.com/res/v1/web/search"

    # Gmail IMAP (receipt mailbox; app password, read-only)
    gmail_imap_user: str = ""
    gmail_imap_password: str = ""
    gmail_imap_host: str = "imap.gmail.com"
    gmail_imap_folder: str = "\\All"


settings = Settings()
