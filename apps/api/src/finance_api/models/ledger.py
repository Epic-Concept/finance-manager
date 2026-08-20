"""Household ledger: pockets, journal entries, and balanced postings."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from finance_api.db.base import Base


class Pocket(Base):
    """An asset or liability pocket (current, savings, card, cash, clearing)."""

    __tablename__ = "pockets"
    __table_args__ = (
        UniqueConstraint("account_name", name="UQ_pockets_account_name"),
        Index("IX_pockets_kind", "kind"),
        {"schema": "finance"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_name: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="asset")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    postings: Mapped[list["Posting"]] = relationship("Posting", back_populates="pocket")

    def __repr__(self) -> str:
        return f"<Pocket(id={self.id}, name={self.name!r})>"


class JournalEntry(Base):
    """One balanced journal for an applied classification (or its reversal)."""

    __tablename__ = "journal_entries"
    __table_args__ = (
        Index("IX_journal_entries_transaction", "transaction_id"),
        Index("IX_journal_entries_decision", "decision_id"),
        {"schema": "finance"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    transaction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("finance.transactions.id"), nullable=False
    )
    decision_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("finance.classification_decisions.id"),
        nullable=True,
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    reversed_entry_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("finance.journal_entries.id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    postings: Mapped[list["Posting"]] = relationship(
        "Posting",
        back_populates="entry",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<JournalEntry(id={self.id}, kind={self.kind!r})>"


class Posting(Base):
    """One side of a journal entry: a pocket xor a nominal (category)."""

    __tablename__ = "postings"
    __table_args__ = (
        Index("IX_postings_entry", "entry_id"),
        Index("IX_postings_pocket", "pocket_id"),
        Index("IX_postings_category", "category_id"),
        CheckConstraint(
            "(pocket_id IS NOT NULL AND category_id IS NULL) OR "
            "(pocket_id IS NULL AND category_id IS NOT NULL)",
            name="CK_postings_pocket_xor_nominal",
        ),
        {"schema": "finance"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    entry_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("finance.journal_entries.id"), nullable=False
    )
    pocket_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("finance.pockets.id"), nullable=True
    )
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("finance.categories.id"), nullable=True
    )
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    entry: Mapped[JournalEntry] = relationship(
        "JournalEntry", back_populates="postings"
    )
    pocket: Mapped[Pocket | None] = relationship("Pocket", back_populates="postings")

    def __repr__(self) -> str:
        return f"<Posting(id={self.id}, amount_minor={self.amount_minor})>"
