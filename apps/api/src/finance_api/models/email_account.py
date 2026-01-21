"""EmailAccount model for storing email account configurations."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from finance_api.db.base import Base


class EmailAccount(Base):
    """Stores email account configurations for purchase receipt retrieval."""

    __tablename__ = "email_accounts"
    __table_args__ = (
        Index("IX_email_accounts_active_priority", "is_active", "priority"),
        {"schema": "finance"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email_address: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    provider: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # gmail, outlook, imap_generic
    imap_server: Mapped[str | None] = mapped_column(String(255), nullable=True)
    imap_port: Mapped[int] = mapped_column(Integer, nullable=False, default=993)
    credential_reference: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )  # vault path or env var name
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # lower = higher priority
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    category_evidence: Mapped[list["CategoryEvidence"]] = relationship(
        "CategoryEvidence",
        back_populates="email_account",
    )

    def __repr__(self) -> str:
        return f"<EmailAccount(id={self.id}, email='{self.email_address}', provider='{self.provider}')>"


# Import at bottom to avoid circular imports
from finance_api.models.category_evidence import CategoryEvidence  # noqa: E402
