"""Incremental, idempotent transaction sync from an upstream source."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from finance_api.ingestion.normalize import normalize_transaction
from finance_api.ingestion.source import TransactionSource
from finance_api.models.sync_state import SyncState
from finance_api.models.transaction import Transaction

DEFAULT_SOURCE = "bank_transactions"


@dataclass(frozen=True)
class SyncResult:
    """Outcome of a single sync run."""

    imported: int
    updated: int
    cursor: datetime | None


class TransactionSyncService:
    """Pulls new transactions from a source and upserts them locally.

    The cursor (last successful ``synced_at``) and the imported transactions are
    committed together, so a failure mid-run rolls everything back and leaves the
    cursor unchanged for the next run to retry the same window.
    """

    def __init__(self, session: Session, source_name: str = DEFAULT_SOURCE) -> None:
        self._session = session
        self._source_name = source_name

    def get_cursor(self) -> datetime | None:
        state = self._session.get(SyncState, self._source_name)
        return state.cursor if state is not None else None

    def sync(self, source: TransactionSource) -> SyncResult:
        cursor = self.get_cursor()
        try:
            rows = source.fetch_since(cursor)
            imported = 0
            updated = 0
            new_cursor = cursor
            for row in rows:
                normalized = normalize_transaction(row)
                existing = self._session.scalar(
                    select(Transaction).where(
                        Transaction.external_id == normalized.external_id
                    )
                )
                if existing is None:
                    self._session.add(normalized)
                    imported += 1
                else:
                    existing.transaction_date = normalized.transaction_date
                    existing.description = normalized.description
                    existing.amount = normalized.amount
                    existing.currency = normalized.currency
                    existing.account_name = normalized.account_name
                    existing.merchant_name = normalized.merchant_name
                    updated += 1
                new_cursor = row.synced_at

            self._set_cursor(new_cursor)
            self._session.commit()
            return SyncResult(imported=imported, updated=updated, cursor=new_cursor)
        except Exception:
            self._session.rollback()
            raise

    def _set_cursor(self, cursor: datetime | None) -> None:
        state = self._session.get(SyncState, self._source_name)
        if state is None:
            self._session.add(SyncState(source=self._source_name, cursor=cursor))
        else:
            state.cursor = cursor
