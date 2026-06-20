"""Upstream transaction source abstraction.

The ingestion logic depends only on the ``TransactionSource`` protocol, so it can
be unit-tested with an in-memory fake and wired to the real Azure SQL source in
production.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class SourceTransaction:
    """A raw transaction row as read from the upstream source."""

    transaction_id: str
    transaction_date: datetime
    amount: Decimal | str | float
    currency: str
    account_name: str | None
    description: str
    merchant_name: str | None
    synced_at: datetime


class TransactionSource(Protocol):
    """Read-only, incremental source of transactions."""

    def fetch_since(self, cursor: datetime | None) -> Sequence[SourceTransaction]:
        """Return source rows with ``synced_at`` strictly greater than ``cursor``.

        When ``cursor`` is ``None`` all available rows are returned. Results are
        ordered by ``synced_at`` ascending so the caller can advance the cursor to
        the last row on success.
        """
        ...
