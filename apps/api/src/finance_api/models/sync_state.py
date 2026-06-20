"""Persisted incremental-sync cursor state, keyed by source."""

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from finance_api.db.base import Base


class SyncState(Base):
    """Tracks the last successfully-synced watermark for an upstream source."""

    __tablename__ = "sync_state"
    __table_args__ = {"schema": "finance"}

    source: Mapped[str] = mapped_column(String(100), primary_key=True)
    cursor: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<SyncState(source={self.source!r}, cursor={self.cursor})>"
