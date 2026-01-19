"""OnlinePurchase model for storing online shopping purchase details."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from finance_api.db.base import Base


class OnlinePurchase(Base):
    """Stores online shopping purchase details for transaction matching."""

    __tablename__ = "online_purchases"
    __table_args__ = (
        Index("IX_online_purchases_datetime", "purchase_datetime"),
        Index("IX_online_purchases_transaction", "transaction_id"),
        {"schema": "finance"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    shop_name: Mapped[str] = mapped_column(String(200), nullable=False)
    items: Mapped[str] = mapped_column(Text, nullable=False)
    purchase_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="GBP")
    is_deferred_payment: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    transaction_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("finance.transactions.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    transaction: Mapped["Transaction | None"] = relationship(
        "Transaction",
        back_populates="online_purchases",
    )

    def __repr__(self) -> str:
        return f"<OnlinePurchase(id={self.id}, shop='{self.shop_name}', price={self.price})>"


# Import at bottom to avoid circular imports
from finance_api.models.transaction import Transaction  # noqa: E402
