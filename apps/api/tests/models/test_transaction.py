"""Tests for Transaction model."""

from datetime import date
from decimal import Decimal

from finance_api.models.transaction import Transaction


def test_transaction_creation() -> None:
    """Test Transaction can be instantiated with required fields."""
    transaction = Transaction(
        transaction_date=date(2026, 1, 15),
        description="Coffee Shop",
        amount=Decimal("4.50"),
        currency="GBP",  # Explicitly set for unit test (defaults apply on DB insert)
    )

    assert transaction.transaction_date == date(2026, 1, 15)
    assert transaction.description == "Coffee Shop"
    assert transaction.amount == Decimal("4.50")
    assert transaction.currency == "GBP"
    assert transaction.external_id is None
    assert transaction.account_name is None
    assert transaction.notes is None


def test_transaction_with_all_fields() -> None:
    """Test Transaction with all optional fields."""
    transaction = Transaction(
        transaction_date=date(2026, 1, 15),
        description="Online Purchase",
        amount=Decimal("-99.99"),
        currency="USD",
        external_id="ext_12345",
        account_name="Current Account",
        notes="Birthday gift",
    )

    assert transaction.currency == "USD"
    assert transaction.external_id == "ext_12345"
    assert transaction.account_name == "Current Account"
    assert transaction.notes == "Birthday gift"


def test_transaction_decimal_precision() -> None:
    """Test Transaction amount supports 4 decimal places."""
    transaction = Transaction(
        transaction_date=date(2026, 1, 15),
        description="Currency Exchange",
        amount=Decimal("123.4567"),
    )

    assert transaction.amount == Decimal("123.4567")


def test_transaction_repr() -> None:
    """Test Transaction string representation."""
    transaction = Transaction(
        id=1,
        transaction_date=date(2026, 1, 15),
        description="Test",
        amount=Decimal("10.00"),
    )

    assert repr(transaction) == "<Transaction(id=1, date=2026-01-15, amount=10.00)>"


def test_transaction_table_name() -> None:
    """Test Transaction table configuration."""
    assert Transaction.__tablename__ == "transactions"
    assert Transaction.__table_args__[2]["schema"] == "finance"
