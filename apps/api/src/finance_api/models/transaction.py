"""Transaction model for storing financial transactions."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from finance_api.db.base import Base


class Transaction(Base):
    """Stores financial transactions."""

    __tablename__ = "transactions"
    __table_args__ = (
        Index("IX_transactions_date", "transaction_date"),
        Index("IX_transactions_external", "external_id"),
        {"schema": "finance"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="GBP")
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    account_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    category_link: Mapped["TransactionCategory | None"] = relationship(
        "TransactionCategory",
        back_populates="transaction",
        uselist=False,
    )
    online_purchases: Mapped[list["OnlinePurchase"]] = relationship(
        "OnlinePurchase",
        back_populates="transaction",
    )

    def __repr__(self) -> str:
        return f"<Transaction(id={self.id}, date={self.transaction_date}, amount={self.amount})>"


# Import at bottom to avoid circular imports
from finance_api.models.online_purchase import OnlinePurchase  # noqa: E402
from finance_api.models.transaction_category import TransactionCategory  # noqa: E402
