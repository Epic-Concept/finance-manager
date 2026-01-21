"""CategoryEvidence model for storing classification evidence and provenance."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from finance_api.db.base import Base


class CategoryEvidence(Base):
    """Stores classification evidence for audit and future transaction splitting."""

    __tablename__ = "category_evidence"
    __table_args__ = (
        Index("IX_category_evidence_transaction", "transaction_id"),
        Index("IX_category_evidence_category", "category_id"),
        Index("IX_category_evidence_email", "email_account_id", "email_message_id"),
        {"schema": "finance"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    transaction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("finance.transactions.id"), nullable=False
    )

    # Item details (one row per item in multi-item purchases)
    item_description: Mapped[str] = mapped_column(String(500), nullable=False)
    item_price: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    item_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="GBP")
    item_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Category assignment
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("finance.categories.id"), nullable=False
    )

    # Evidence provenance
    evidence_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # email, manual, rule, ai_inferred
    email_account_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("finance.email_accounts.id"), nullable=True
    )
    email_message_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # Email Message-ID header
    email_datetime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    evidence_summary: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Human-readable description

    # AI agent metadata
    confidence_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4), nullable=True
    )  # 0.0000 to 1.0000
    model_used: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # e.g., 'claude-sonnet-4-5-20250514'
    raw_extraction: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Full LLM JSON output for debugging

    # Audit fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    transaction: Mapped["Transaction"] = relationship(
        "Transaction",
        back_populates="category_evidence",
    )
    category: Mapped["Category"] = relationship(
        "Category",
        back_populates="category_evidence",
    )
    email_account: Mapped["EmailAccount | None"] = relationship(
        "EmailAccount",
        back_populates="category_evidence",
    )

    def __repr__(self) -> str:
        return f"<CategoryEvidence(id={self.id}, transaction_id={self.transaction_id}, item='{self.item_description[:30]}...')>"


# Import at bottom to avoid circular imports
from finance_api.models.category import Category  # noqa: E402
from finance_api.models.email_account import EmailAccount  # noqa: E402
from finance_api.models.transaction import Transaction  # noqa: E402
