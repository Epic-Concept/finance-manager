"""SessionMessage model for storing conversation messages in refinement sessions."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from finance_api.db.base import Base

if TYPE_CHECKING:
    from finance_api.models.refinement_session import RefinementSession


class SessionMessage(Base):
    """Stores conversation messages within a refinement session.

    Tracks the full conversation history including user messages,
    assistant responses, and system messages (e.g., validation results).
    """

    __tablename__ = "session_messages"
    __table_args__ = (
        Index("IX_session_messages_session_id", "session_id"),
        {"schema": "finance"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("finance.refinement_sessions.id"), nullable=False
    )

    # Message content
    role: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # user, assistant, system
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Track proposed rules in assistant messages (JSON array)
    proposed_rules_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Relationships
    session: Mapped["RefinementSession"] = relationship(
        "RefinementSession", back_populates="messages"
    )

    def __repr__(self) -> str:
        content_preview = (
            self.content[:50] + "..." if len(self.content) > 50 else self.content
        )
        return (
            f"<SessionMessage(id={self.id}, role='{self.role}', "
            f"content='{content_preview}')>"
        )
