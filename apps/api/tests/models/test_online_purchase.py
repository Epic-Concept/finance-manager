"""Tests for OnlinePurchase model."""

from datetime import datetime
from decimal import Decimal

from finance_api.models.online_purchase import OnlinePurchase


def test_online_purchase_creation() -> None:
    """Test OnlinePurchase can be instantiated with required fields."""
    purchase = OnlinePurchase(
        shop_name="Amazon",
        items="Book: Python Programming",
        purchase_datetime=datetime(2026, 1, 15, 14, 30),
        price=Decimal("29.99"),
        currency="GBP",  # Explicitly set for unit test (defaults apply on DB insert)
        is_deferred_payment=False,  # Explicitly set for unit test
    )

    assert purchase.shop_name == "Amazon"
    assert purchase.items == "Book: Python Programming"
    assert purchase.purchase_datetime == datetime(2026, 1, 15, 14, 30)
    assert purchase.price == Decimal("29.99")
    assert purchase.currency == "GBP"
    assert purchase.is_deferred_payment is False
    assert purchase.transaction_id is None


def test_online_purchase_deferred_payment() -> None:
    """Test OnlinePurchase with deferred payment."""
    purchase = OnlinePurchase(
        shop_name="Klarna Store",
        items="Laptop",
        purchase_datetime=datetime(2026, 1, 15),
        price=Decimal("999.00"),
        is_deferred_payment=True,
    )

    assert purchase.is_deferred_payment is True


def test_online_purchase_with_transaction_link() -> None:
    """Test OnlinePurchase linked to a transaction."""
    purchase = OnlinePurchase(
        shop_name="eBay",
        items="Vintage Watch",
        purchase_datetime=datetime(2026, 1, 15),
        price=Decimal("150.00"),
        transaction_id=42,
    )

    assert purchase.transaction_id == 42


def test_online_purchase_decimal_precision() -> None:
    """Test OnlinePurchase price supports 4 decimal places."""
    purchase = OnlinePurchase(
        shop_name="Test Shop",
        items="Test Item",
        purchase_datetime=datetime(2026, 1, 15),
        price=Decimal("99.9999"),
    )

    assert purchase.price == Decimal("99.9999")


def test_online_purchase_repr() -> None:
    """Test OnlinePurchase string representation."""
    purchase = OnlinePurchase(
        id=1,
        shop_name="Amazon",
        items="Test",
        purchase_datetime=datetime(2026, 1, 15),
        price=Decimal("29.99"),
    )

    assert repr(purchase) == "<OnlinePurchase(id=1, shop='Amazon', price=29.99)>"


def test_online_purchase_table_name() -> None:
    """Test OnlinePurchase table configuration."""
    assert OnlinePurchase.__tablename__ == "online_purchases"
    assert OnlinePurchase.__table_args__[2]["schema"] == "finance"
