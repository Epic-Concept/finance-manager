"""Unit tests for source -> canonical transaction normalization."""

from datetime import date, datetime
from decimal import Decimal

from finance_api.ingestion.normalize import normalize_transaction
from finance_api.ingestion.source import SourceTransaction


def _src(**overrides: object) -> SourceTransaction:
    base: dict[str, object] = {
        "transaction_id": "abc-123",
        "transaction_date": datetime(2026, 1, 15, 9, 30, 0),
        "amount": Decimal("-42.50"),
        "currency": "PLN",
        "account_name": "Wspolne",
        "description": "BIEDRONKA 1234 WARSZAWA",
        "merchant_name": "Biedronka",
        "synced_at": datetime(2026, 1, 16, 2, 0, 0),
    }
    base.update(overrides)
    return SourceTransaction(**base)  # type: ignore[arg-type]


def test_maps_source_fields_to_canonical() -> None:
    txn = normalize_transaction(_src())

    assert txn.external_id == "abc-123"
    assert txn.transaction_date == date(2026, 1, 15)
    assert txn.amount == Decimal("-42.50")
    assert txn.currency == "PLN"
    assert txn.account_name == "Wspolne"
    assert txn.description == "BIEDRONKA 1234 WARSZAWA"
    assert txn.merchant_name == "Biedronka"


def test_amount_is_exact_decimal_from_string() -> None:
    # A float like 19.99 is not exactly representable; normalization must not
    # introduce float error.
    txn = normalize_transaction(_src(amount="19.99"))
    assert txn.amount == Decimal("19.99")
    assert isinstance(txn.amount, Decimal)


def test_date_only_kept_from_datetime() -> None:
    txn = normalize_transaction(_src(transaction_date=datetime(2026, 3, 1, 23, 59, 59)))
    assert txn.transaction_date == date(2026, 3, 1)
