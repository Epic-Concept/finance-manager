"""BankSession model for storing Enable Banking session data."""

from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from finance_api.db.base import Base


class BankSession(Base):
    """Stores Enable Banking session data for cached bank connections."""

    __tablename__ = "bank_sessions"
    __table_args__ = (
        Index("IX_bank_sessions_expires", "session_expires"),
        {"schema": "finance"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bank_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    bank_name: Mapped[str] = mapped_column(String(200), nullable=False)
    session_id: Mapped[str] = mapped_column(String(255), nullable=False)
    session_expires: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    accounts: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<BankSession(id={self.id}, bank_key='{self.bank_key}')>"
