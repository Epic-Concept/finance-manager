"""Unit tests for the incremental transaction sync service."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from finance_api.ingestion.service import TransactionSyncService
from finance_api.ingestion.source import SourceTransaction
from finance_api.models.transaction import Transaction


class FakeSource:
    def __init__(self, rows: Sequence[SourceTransaction]) -> None:
        self.rows = list(rows)
        self.calls: list[datetime | None] = []

    def fetch_since(self, cursor: datetime | None) -> Sequence[SourceTransaction]:
        self.calls.append(cursor)
        rows = [r for r in self.rows if cursor is None or r.synced_at > cursor]
        return sorted(rows, key=lambda r: r.synced_at)


def _src(tid: str, synced: datetime, amount: str = "1.00") -> SourceTransaction:
    return SourceTransaction(
        transaction_id=tid,
        transaction_date=datetime(2026, 1, 1),
        amount=amount,
        currency="PLN",
        account_name="A",
        description=f"desc {tid}",
        merchant_name=None,
        synced_at=synced,
    )


def test_first_sync_imports_all_and_sets_cursor(db_session: Session) -> None:
    rows = [_src("t1", datetime(2026, 1, 1, 2)), _src("t2", datetime(2026, 1, 2, 2))]
    svc = TransactionSyncService(db_session)

    result = svc.sync(FakeSource(rows))

    assert result.imported == 2
    assert db_session.query(Transaction).count() == 2
    assert svc.get_cursor() == datetime(2026, 1, 2, 2)


def test_incremental_only_fetches_rows_after_cursor(db_session: Session) -> None:
    src = FakeSource(
        [
            _src("t1", datetime(2026, 1, 1, 2)),
            _src("t2", datetime(2026, 1, 2, 2)),
            _src("t3", datetime(2026, 1, 3, 2)),
        ]
    )
    svc = TransactionSyncService(db_session)
    svc.sync(src)  # imports all three, cursor -> t3

    # add a newer row and re-sync
    src.rows.append(_src("t4", datetime(2026, 1, 4, 2)))
    result = svc.sync(src)

    assert src.calls[-1] == datetime(2026, 1, 3, 2)  # fetched since last cursor
    assert result.imported == 1
    assert db_session.query(Transaction).count() == 4
    assert svc.get_cursor() == datetime(2026, 1, 4, 2)


def test_resyncing_same_rows_creates_no_duplicates(db_session: Session) -> None:
    rows = [_src("t1", datetime(2026, 1, 1, 2)), _src("t2", datetime(2026, 1, 2, 2))]
    svc = TransactionSyncService(db_session)
    svc.sync(FakeSource(rows))

    # same transaction_id seen again (e.g. re-stamped synced_at) must update, not duplicate
    again = [_src("t1", datetime(2026, 1, 5, 2), amount="9.99")]
    result = svc.sync(FakeSource(again))

    assert db_session.query(Transaction).count() == 2
    assert result.updated == 1
    t1 = db_session.query(Transaction).filter_by(external_id="t1").one()
    assert t1.amount == Decimal("9.99")


def test_failed_sync_rolls_back_and_keeps_cursor(db_session: Session) -> None:
    # good row (t1) then a row with an unparseable amount (t2) -> mid-batch failure
    rows = [
        _src("t1", datetime(2026, 1, 1, 2), amount="10.00"),
        _src("t2", datetime(2026, 1, 2, 2), amount="not-a-number"),
    ]
    svc = TransactionSyncService(db_session)

    with pytest.raises(Exception):
        svc.sync(FakeSource(rows))

    assert db_session.query(Transaction).count() == 0  # good row rolled back too
    assert svc.get_cursor() is None  # cursor not advanced
