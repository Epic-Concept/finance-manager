"""Spend totals from journal postings (transfers excluded)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from finance_api.models.ledger import JournalEntry, Posting
from finance_api.models.transaction import Transaction


class SpendTotal(BaseModel):
    amount_minor: int
    currency: str = "GBP"


def spend_total(
    session: Session,
    *,
    start: date | None = None,
    end: date | None = None,
) -> SpendTotal:
    """Sum expense nominal postings; pocket-to-pocket transfers are excluded."""
    stmt = (
        select(func.coalesce(func.sum(Posting.amount_minor), 0))
        .join(JournalEntry, Posting.entry_id == JournalEntry.id)
        .join(Transaction, JournalEntry.transaction_id == Transaction.id)
        .where(Posting.category_id.is_not(None))
        .where(JournalEntry.kind.in_(("spend", "split")))
        .where(JournalEntry.reversed_entry_id.is_(None))
    )
    # Exclude reversed originals: those whose id appears as reversed_entry_id
    reversed_ids = select(JournalEntry.reversed_entry_id).where(
        JournalEntry.reversed_entry_id.is_not(None)
    )
    stmt = stmt.where(JournalEntry.id.not_in(reversed_ids))
    if start is not None:
        stmt = stmt.where(Transaction.transaction_date >= start)
    if end is not None:
        stmt = stmt.where(Transaction.transaction_date <= end)
    total = session.scalar(stmt)
    return SpendTotal(amount_minor=int(total or 0))
