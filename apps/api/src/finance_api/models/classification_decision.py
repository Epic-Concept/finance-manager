"""Models for evidence-driven classification decisions.

A classification decision records the policy outcome for a transaction, the
categorization as one or more splits that sum to the transaction total, and the
evidence chain that justified it (the audit trail). Decisions with outcome
``review`` form the review queue.
"""

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


class ClassificationDecision(Base):
    """A policy decision for a transaction (auto-applied or routed to review)."""

    __tablename__ = "classification_decisions"
    __table_args__ = (
        Index("IX_classification_decisions_transaction", "transaction_id"),
        Index("IX_classification_decisions_outcome", "outcome"),
        {"schema": "finance"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    transaction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("finance.transactions.id"), nullable=False
    )
    outcome: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # auto_apply | review
    merchant_class: Mapped[str] = mapped_column(String(20), nullable=False)
    strength: Mapped[int] = mapped_column(Integer, nullable=False)  # StrengthTier value
    reason: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    splits: Mapped[list["CategorizationSplit"]] = relationship(
        "CategorizationSplit",
        back_populates="decision",
        cascade="all, delete-orphan",
    )
    evidence: Mapped[list["DecisionEvidence"]] = relationship(
        "DecisionEvidence",
        back_populates="decision",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<ClassificationDecision(id={self.id}, "
            f"transaction_id={self.transaction_id}, outcome='{self.outcome}')>"
        )


class CategorizationSplit(Base):
    """One ``(category, amount)`` component of a decision's categorization."""

    __tablename__ = "categorization_splits"
    __table_args__ = (
        Index("IX_categorization_splits_decision", "decision_id"),
        Index("IX_categorization_splits_category", "category_id"),
        {"schema": "finance"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    decision_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("finance.classification_decisions.id"),
        nullable=False,
    )
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("finance.categories.id"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    decision: Mapped["ClassificationDecision"] = relationship(
        "ClassificationDecision", back_populates="splits"
    )


class DecisionEvidence(Base):
    """One piece of the evidence chain that justified a decision (audit trail)."""

    __tablename__ = "decision_evidence"
    __table_args__ = (
        Index("IX_decision_evidence_decision", "decision_id"),
        {"schema": "finance"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    decision_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("finance.classification_decisions.id"),
        nullable=False,
    )
    evidence_type: Mapped[str] = mapped_column(String(30), nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    strength: Mapped[int] = mapped_column(Integer, nullable=False)
    itemized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    decision: Mapped["ClassificationDecision"] = relationship(
        "ClassificationDecision", back_populates="evidence"
    )
