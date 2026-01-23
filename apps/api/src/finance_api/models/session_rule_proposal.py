"""SessionRuleProposal model for tracking rule proposals within refinement sessions."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from finance_api.db.base import Base

if TYPE_CHECKING:
    from finance_api.models.category import Category
    from finance_api.models.classification_rule import ClassificationRule
    from finance_api.models.refinement_session import RefinementSession


class SessionRuleProposal(Base):
    """Tracks individual rule proposals within a refinement session.

    Multiple proposals can exist per session, allowing handling of
    polluted clusters that need different rules for different merchants.
    """

    __tablename__ = "session_rule_proposals"
    __table_args__ = (
        Index("IX_session_rule_proposals_session_id", "session_id"),
        Index("IX_session_rule_proposals_status", "status"),
        {"schema": "finance"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("finance.refinement_sessions.id"), nullable=False
    )

    # Proposal details
    proposed_pattern: Mapped[str] = mapped_column(String(500), nullable=False)
    proposed_category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("finance.categories.id"), nullable=True
    )
    proposed_category_name: Mapped[str] = mapped_column(String(100), nullable=False)
    llm_confidence: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # high, medium, low
    llm_reasoning: Mapped[str] = mapped_column(Text, nullable=False)

    # Validation results (populated after validation)
    validation_matches: Mapped[int | None] = mapped_column(Integer, nullable=True)
    validation_true_positives: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    validation_false_positives: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    validation_precision: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4), nullable=True
    )
    validation_coverage: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4), nullable=True
    )
    validation_false_positives_json: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON array of false positive descriptions

    # Status: pending, accepted, rejected
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    final_rule_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("finance.classification_rules.id"), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    session: Mapped["RefinementSession"] = relationship(
        "RefinementSession", back_populates="proposals"
    )
    proposed_category: Mapped["Category"] = relationship(
        "Category", foreign_keys=[proposed_category_id]
    )
    final_rule: Mapped["ClassificationRule | None"] = relationship(
        "ClassificationRule", foreign_keys=[final_rule_id]
    )

    def __repr__(self) -> str:
        pattern_preview = (
            self.proposed_pattern[:30] + "..."
            if len(self.proposed_pattern) > 30
            else self.proposed_pattern
        )
        return (
            f"<SessionRuleProposal(id={self.id}, pattern='{pattern_preview}', "
            f"status='{self.status}')>"
        )
