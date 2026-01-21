"""ClassificationRule model for storing transaction classification rules."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from finance_api.db.base import Base


class ClassificationRule(Base):
    """Stores classification rules for the rules engine."""

    __tablename__ = "classification_rules"
    __table_args__ = (
        Index("IX_classification_rules_active_priority", "is_active", "priority"),
        {"schema": "finance"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    rule_expression: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # rule-engine expression
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("finance.categories.id"), nullable=False
    )
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # lower = higher priority
    requires_disambiguation: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    category: Mapped["Category"] = relationship(
        "Category",
        back_populates="classification_rules",
    )

    def __repr__(self) -> str:
        return f"<ClassificationRule(id={self.id}, name='{self.name}', priority={self.priority})>"


# Import at bottom to avoid circular imports
from finance_api.models.category import Category  # noqa: E402
