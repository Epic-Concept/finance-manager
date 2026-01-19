"""SQLAlchemy engine configuration."""

from sqlalchemy import create_engine

from finance_api.core.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)
