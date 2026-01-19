"""Tests for TransactionCategory model."""

from finance_api.models.transaction_category import TransactionCategory


def test_transaction_category_creation() -> None:
    """Test TransactionCategory can be instantiated."""
    link = TransactionCategory(
        transaction_id=1,
        category_id=5,
    )

    assert link.transaction_id == 1
    assert link.category_id == 5


def test_transaction_category_repr() -> None:
    """Test TransactionCategory string representation."""
    link = TransactionCategory(
        transaction_id=1,
        category_id=5,
    )

    assert repr(link) == "<TransactionCategory(transaction_id=1, category_id=5)>"


def test_transaction_category_table_name() -> None:
    """Test TransactionCategory table configuration."""
    assert TransactionCategory.__tablename__ == "transaction_categories"
    assert TransactionCategory.__table_args__[2]["schema"] == "finance"
