"""Integration tests for model persistence with SQL Server."""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from finance_api.models.bank_session import BankSession
from finance_api.models.category import Category, CategoryClosure
from finance_api.models.online_purchase import OnlinePurchase
from finance_api.models.transaction import Transaction
from finance_api.models.transaction_category import TransactionCategory


@pytest.mark.integration
class TestBankSessionIntegration:
    """Integration tests for BankSession model."""

    def test_create_and_retrieve_bank_session(self, sqlserver_session: Session) -> None:
        """Test BankSession can be persisted and retrieved."""
        session = BankSession(
            bank_key="test-bank-001",
            bank_name="Test Bank",
            session_id="integration-test-session",
            session_expires=datetime.utcnow() + timedelta(hours=1),
        )
        sqlserver_session.add(session)
        sqlserver_session.flush()

        assert session.id is not None

        # Retrieve from database
        retrieved = sqlserver_session.get(BankSession, session.id)
        assert retrieved is not None
        assert retrieved.session_id == "integration-test-session"
        assert retrieved.bank_key == "test-bank-001"
        assert retrieved.created_at is not None

    def test_bank_session_update(self, sqlserver_session: Session) -> None:
        """Test BankSession can be updated."""
        session = BankSession(
            bank_key="update-test-bank",
            bank_name="Update Test Bank",
            session_id="update-test",
            session_expires=datetime.utcnow() + timedelta(hours=1),
        )
        sqlserver_session.add(session)
        sqlserver_session.flush()

        session.session_id = "updated-session-id"
        sqlserver_session.flush()

        retrieved = sqlserver_session.get(BankSession, session.id)
        assert retrieved.session_id == "updated-session-id"


@pytest.mark.integration
class TestCategoryIntegration:
    """Integration tests for Category model."""

    def test_create_category_with_parent(self, sqlserver_session: Session) -> None:
        """Test Category parent-child relationship."""
        parent = Category(name="Parent Category")
        sqlserver_session.add(parent)
        sqlserver_session.flush()

        child = Category(name="Child Category", parent_id=parent.id)
        sqlserver_session.add(child)
        sqlserver_session.flush()

        # Verify relationship
        retrieved_child = sqlserver_session.get(Category, child.id)
        assert retrieved_child.parent_id == parent.id
        assert retrieved_child.parent.name == "Parent Category"

    def test_category_closure_entry(self, sqlserver_session: Session) -> None:
        """Test CategoryClosure can be created manually."""
        category = Category(name="Test Category")
        sqlserver_session.add(category)
        sqlserver_session.flush()

        # Create self-referential closure entry
        closure = CategoryClosure(
            ancestor_id=category.id,
            descendant_id=category.id,
            depth=0,
        )
        sqlserver_session.add(closure)
        sqlserver_session.flush()

        # Verify closure entry
        retrieved = (
            sqlserver_session.query(CategoryClosure)
            .filter_by(ancestor_id=category.id, descendant_id=category.id)
            .first()
        )
        assert retrieved is not None
        assert retrieved.depth == 0


@pytest.mark.integration
class TestTransactionIntegration:
    """Integration tests for Transaction model."""

    def test_create_transaction(self, sqlserver_session: Session) -> None:
        """Test Transaction can be created and retrieved."""
        transaction = Transaction(
            transaction_date=date(2026, 1, 15),
            amount=Decimal("123.45"),
            description="Test transaction",
        )
        sqlserver_session.add(transaction)
        sqlserver_session.flush()

        assert transaction.id is not None

        # Verify retrieval
        retrieved = sqlserver_session.get(Transaction, transaction.id)
        assert retrieved is not None
        assert retrieved.description == "Test transaction"
        assert retrieved.amount == Decimal("123.45")

    def test_transaction_decimal_precision(self, sqlserver_session: Session) -> None:
        """Test Transaction amount supports 4 decimal places."""
        transaction = Transaction(
            transaction_date=date(2026, 1, 15),
            amount=Decimal("99.9999"),
            description="Precision test",
        )
        sqlserver_session.add(transaction)
        sqlserver_session.flush()

        retrieved = sqlserver_session.get(Transaction, transaction.id)
        assert retrieved.amount == Decimal("99.9999")


@pytest.mark.integration
class TestOnlinePurchaseIntegration:
    """Integration tests for OnlinePurchase model."""

    def test_create_online_purchase(self, sqlserver_session: Session) -> None:
        """Test OnlinePurchase can be persisted."""
        purchase = OnlinePurchase(
            shop_name="Amazon",
            items="Python Programming Book",
            purchase_datetime=datetime(2026, 1, 15, 14, 30),
            price=Decimal("29.99"),
            currency="GBP",
            is_deferred_payment=False,
        )
        sqlserver_session.add(purchase)
        sqlserver_session.flush()

        assert purchase.id is not None

        # Verify defaults from database
        retrieved = sqlserver_session.get(OnlinePurchase, purchase.id)
        assert retrieved.currency == "GBP"
        assert retrieved.is_deferred_payment is False

    def test_online_purchase_with_transaction_link(
        self, sqlserver_session: Session
    ) -> None:
        """Test OnlinePurchase can be linked to a transaction."""
        transaction = Transaction(
            transaction_date=date(2026, 1, 15),
            amount=Decimal("29.99"),
            description="Amazon purchase",
        )
        sqlserver_session.add(transaction)
        sqlserver_session.flush()

        purchase = OnlinePurchase(
            shop_name="Amazon",
            items="Book",
            purchase_datetime=datetime(2026, 1, 15),
            price=Decimal("29.99"),
            transaction_id=transaction.id,
        )
        sqlserver_session.add(purchase)
        sqlserver_session.flush()

        # Verify relationship
        retrieved = sqlserver_session.get(OnlinePurchase, purchase.id)
        assert retrieved.transaction.description == "Amazon purchase"

    def test_online_purchase_defaults(self, sqlserver_session: Session) -> None:
        """Test OnlinePurchase defaults are applied by database."""
        purchase = OnlinePurchase(
            shop_name="Test Shop",
            items="Test Item",
            purchase_datetime=datetime(2026, 1, 15),
            price=Decimal("10.00"),
            # Not specifying currency or is_deferred_payment
        )
        sqlserver_session.add(purchase)
        sqlserver_session.flush()

        # Refresh to get database defaults
        sqlserver_session.refresh(purchase)

        assert purchase.currency == "GBP"
        assert purchase.is_deferred_payment is False


@pytest.mark.integration
class TestTransactionCategoryIntegration:
    """Integration tests for TransactionCategory linking table."""

    def test_link_transaction_to_category(self, sqlserver_session: Session) -> None:
        """Test linking a transaction to a category."""
        transaction = Transaction(
            transaction_date=date(2026, 1, 15),
            amount=Decimal("50.00"),
            description="Groceries",
        )
        category = Category(name="Food")
        sqlserver_session.add_all([transaction, category])
        sqlserver_session.flush()

        # Create link
        link = TransactionCategory(
            transaction_id=transaction.id,
            category_id=category.id,
        )
        sqlserver_session.add(link)
        sqlserver_session.flush()

        # Verify link
        retrieved = (
            sqlserver_session.query(TransactionCategory)
            .filter_by(transaction_id=transaction.id)
            .first()
        )
        assert retrieved is not None
        assert retrieved.category_id == category.id

    def test_transaction_category_relationships(
        self, sqlserver_session: Session
    ) -> None:
        """Test TransactionCategory relationships work correctly."""
        transaction = Transaction(
            transaction_date=date(2026, 1, 15),
            amount=Decimal("100.00"),
            description="Mixed purchase",
        )
        category = Category(name="Groceries")
        sqlserver_session.add_all([transaction, category])
        sqlserver_session.flush()

        # Create link
        link = TransactionCategory(transaction_id=transaction.id, category_id=category.id)
        sqlserver_session.add(link)
        sqlserver_session.flush()

        # Verify the link relationships
        retrieved = sqlserver_session.get(TransactionCategory, link.id)
        assert retrieved.transaction.description == "Mixed purchase"
        assert retrieved.category.name == "Groceries"
