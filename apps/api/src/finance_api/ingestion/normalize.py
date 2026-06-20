"""Map upstream source rows to the canonical ``Transaction`` model."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from finance_api.ingestion.source import SourceTransaction
from finance_api.models.transaction import Transaction


def _to_decimal(value: Decimal | str | float) -> Decimal:
    """Coerce an amount to an exact Decimal without introducing float error."""
    if isinstance(value, Decimal):
        return value
    # str() of a float gives the shortest round-trippable representation, so
    # Decimal(str(19.99)) == Decimal("19.99") rather than the binary expansion.
    return Decimal(str(value))


def _to_date(value: datetime | date) -> date:
    return value.date() if isinstance(value, datetime) else value


def normalize_transaction(src: SourceTransaction) -> Transaction:
    """Build an (unsaved) canonical ``Transaction`` from a source row."""
    return Transaction(
        external_id=src.transaction_id,
        transaction_date=_to_date(src.transaction_date),
        description=src.description,
        amount=_to_decimal(src.amount),
        currency=src.currency,
        account_name=src.account_name,
        merchant_name=src.merchant_name,
    )
