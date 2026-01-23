"""RefinementSession model for tracking interactive rule refinement conversations."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from finance_api.db.base import Base

if TYPE_CHECKING:
    from finance_api.models.session_message import SessionMessage
    from finance_api.models.session_rule_proposal import SessionRuleProposal


class RefinementSession(Base):
    """Tracks an interactive refinement session for a transaction cluster.

    Each session maintains its own conversation thread and can produce
    multiple classification rules for polluted clusters.
    """

    __tablename__ = "refinement_sessions"
    __table_args__ = (
        Index("IX_refinement_sessions_cluster_hash", "cluster_hash"),
        Index("IX_refinement_sessions_status", "status"),
        {"schema": "finance"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cluster_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    cluster_key: Mapped[str] = mapped_column(String(100), nullable=False)
    cluster_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sample_descriptions: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # JSON array of sample transaction descriptions

    # Session state: active, completed, skipped
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    messages: Mapped[list["SessionMessage"]] = relationship(
        "SessionMessage",
        back_populates="session",
        order_by="SessionMessage.created_at",
        cascade="all, delete-orphan",
    )
    proposals: Mapped[list["SessionRuleProposal"]] = relationship(
        "SessionRuleProposal",
        back_populates="session",
        order_by="SessionRuleProposal.created_at",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<RefinementSession(id={self.id}, cluster_key='{self.cluster_key}', "
            f"status='{self.status}')>"
        )
