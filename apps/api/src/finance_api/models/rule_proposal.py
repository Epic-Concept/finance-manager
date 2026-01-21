"""RuleProposal model for storing LLM-proposed classification rules."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from finance_api.db.base import Base


class RuleProposal(Base):
    """Stores LLM-proposed classification rules for review and approval.

    Tracks the full lifecycle of a rule proposal from LLM generation through
    user review to final acceptance or rejection.
    """

    __tablename__ = "rule_proposals"
    __table_args__ = (
        Index("IX_rule_proposals_status", "status"),
        Index("IX_rule_proposals_cluster_hash", "cluster_hash"),
        {"schema": "finance"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cluster_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    cluster_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sample_descriptions: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # JSON array of sample transaction descriptions
    proposed_pattern: Mapped[str | None] = mapped_column(String(500), nullable=True)
    proposed_category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("finance.categories.id"), nullable=True
    )
    llm_confidence: Mapped[str | None] = mapped_column(String(20), nullable=True)
    llm_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_matches: Mapped[int | None] = mapped_column(Integer, nullable=True)
    validation_precision: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4), nullable=True
    )
    validation_false_positives: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON array of false positive descriptions
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending/accepted/rejected/modified
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    final_rule_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("finance.classification_rules.id"), nullable=True
    )
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    proposed_category: Mapped["Category | None"] = relationship(
        "Category",
        foreign_keys=[proposed_category_id],
    )
    final_rule: Mapped["ClassificationRule | None"] = relationship(
        "ClassificationRule",
        foreign_keys=[final_rule_id],
    )

    def __repr__(self) -> str:
        return (
            f"<RuleProposal(id={self.id}, cluster_hash='{self.cluster_hash[:8]}...', "
            f"status='{self.status}')>"
        )


# Import at bottom to avoid circular imports
from finance_api.models.category import Category  # noqa: E402
from finance_api.models.classification_rule import ClassificationRule  # noqa: E402
