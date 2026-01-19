"""TransactionCategory model for linking transactions to categories."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from finance_api.db.base import Base


class TransactionCategory(Base):
    """Links transactions to categories (one category per transaction)."""

    __tablename__ = "transaction_categories"
    __table_args__ = (
        UniqueConstraint("transaction_id", name="UQ_transaction_categories_transaction"),
        Index("IX_transaction_categories_category", "category_id"),
        {"schema": "finance"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    transaction_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("finance.transactions.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("finance.categories.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    transaction: Mapped["Transaction"] = relationship(
        "Transaction",
        back_populates="category_link",
    )
    category: Mapped["Category"] = relationship(
        "Category",
    )

    def __repr__(self) -> str:
        return f"<TransactionCategory(transaction_id={self.transaction_id}, category_id={self.category_id})>"


# Import at bottom to avoid circular imports
from finance_api.models.category import Category  # noqa: E402
from finance_api.models.transaction import Transaction  # noqa: E402
