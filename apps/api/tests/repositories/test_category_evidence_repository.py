"""Tests for CategoryEvidenceRepository."""

from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from finance_api.models.category import Category, CategoryClosure
from finance_api.models.transaction import Transaction
from finance_api.repositories.category_evidence_repository import (
    CategoryEvidenceNotFoundError,
    CategoryEvidenceRepository,
)
from finance_api.repositories.email_account_repository import EmailAccountRepository


@pytest.fixture
def test_category(db_session: Session) -> Category:
    """Create a test category."""
    category = Category(name="Electronics")
    db_session.add(category)
    db_session.flush()

    closure = CategoryClosure(
        ancestor_id=category.id,
        descendant_id=category.id,
        depth=0,
    )
    db_session.add(closure)
    db_session.flush()

    return category


@pytest.fixture
def test_category_2(db_session: Session) -> Category:
    """Create a second test category."""
    category = Category(name="Books")
    db_session.add(category)
    db_session.flush()

    closure = CategoryClosure(
        ancestor_id=category.id,
        descendant_id=category.id,
        depth=0,
    )
    db_session.add(closure)
    db_session.flush()

    return category


@pytest.fixture
def test_transaction(db_session: Session) -> Transaction:
    """Create a test transaction."""
    transaction = Transaction(
        transaction_date=date(2026, 1, 15),
        description="AMAZON.CO.UK",
        amount=Decimal("-59.97"),
        currency="GBP",
    )
    db_session.add(transaction)
    db_session.flush()
    return transaction


class TestCategoryEvidenceRepositoryCreate:
    """Tests for CategoryEvidenceRepository.create()."""

    def test_create_basic_evidence(
        self,
        db_session: Session,
        test_transaction: Transaction,
        test_category: Category,
    ) -> None:
        """Test creating basic category evidence."""
        repo = CategoryEvidenceRepository(db_session)

        evidence = repo.create(
            transaction_id=test_transaction.id,
            item_description="USB Cable",
            item_price=Decimal("9.99"),
            category_id=test_category.id,
            evidence_type="email",
        )
        db_session.flush()

        assert evidence.id is not None
        assert evidence.transaction_id == test_transaction.id
        assert evidence.item_description == "USB Cable"
        assert evidence.item_price == Decimal("9.99")
        assert evidence.category_id == test_category.id
        assert evidence.evidence_type == "email"

    def test_create_evidence_with_email_provenance(
        self,
        db_session: Session,
        test_transaction: Transaction,
        test_category: Category,
    ) -> None:
        """Test creating evidence with full email provenance."""
        email_repo = EmailAccountRepository(db_session)
        email_account = email_repo.create(
            email_address="test@example.com",
            provider="gmail",
        )
        db_session.flush()

        repo = CategoryEvidenceRepository(db_session)
        email_time = datetime(2026, 1, 10, 10, 30, 0)

        evidence = repo.create(
            transaction_id=test_transaction.id,
            item_description="Headphones",
            item_price=Decimal("49.99"),
            category_id=test_category.id,
            evidence_type="email",
            email_account_id=email_account.id,
            email_message_id="<msg123@amazon.co.uk>",
            email_datetime=email_time,
            evidence_summary="Order confirmation from Amazon",
        )
        db_session.flush()

        assert evidence.email_account_id == email_account.id
        assert evidence.email_message_id == "<msg123@amazon.co.uk>"
        assert evidence.email_datetime == email_time
        assert evidence.evidence_summary == "Order confirmation from Amazon"

    def test_create_evidence_with_ai_metadata(
        self,
        db_session: Session,
        test_transaction: Transaction,
        test_category: Category,
    ) -> None:
        """Test creating evidence with AI classification metadata."""
        repo = CategoryEvidenceRepository(db_session)

        evidence = repo.create(
            transaction_id=test_transaction.id,
            item_description="Python Book",
            item_price=Decimal("29.99"),
            category_id=test_category.id,
            evidence_type="ai_inferred",
            confidence_score=Decimal("0.95"),
            model_used="claude-sonnet-4-5-20250514",
            raw_extraction='{"items": [{"name": "Python Book"}]}',
        )
        db_session.flush()

        assert evidence.confidence_score == Decimal("0.95")
        assert evidence.model_used == "claude-sonnet-4-5-20250514"
        assert evidence.raw_extraction is not None


class TestCategoryEvidenceRepositoryCreateBatch:
    """Tests for CategoryEvidenceRepository.create_batch()."""

    def test_create_batch_multi_item(
        self,
        db_session: Session,
        test_transaction: Transaction,
        test_category: Category,
        test_category_2: Category,
    ) -> None:
        """Test creating multiple evidence records at once."""
        repo = CategoryEvidenceRepository(db_session)

        evidence_list = [
            {
                "transaction_id": test_transaction.id,
                "item_description": "USB Cable",
                "item_price": Decimal("9.99"),
                "category_id": test_category.id,
                "evidence_type": "email",
            },
            {
                "transaction_id": test_transaction.id,
                "item_description": "Programming Book",
                "item_price": Decimal("29.99"),
                "category_id": test_category_2.id,
                "evidence_type": "email",
            },
            {
                "transaction_id": test_transaction.id,
                "item_description": "Shipping",
                "item_price": Decimal("4.99"),
                "category_id": test_category.id,
                "evidence_type": "email",
            },
        ]

        created = repo.create_batch(evidence_list)
        db_session.flush()

        assert len(created) == 3
        assert created[0].item_description == "USB Cable"
        assert created[1].item_description == "Programming Book"
        assert created[2].item_description == "Shipping"


class TestCategoryEvidenceRepositoryGet:
    """Tests for CategoryEvidenceRepository.get()."""

    def test_get_existing_evidence(
        self,
        db_session: Session,
        test_transaction: Transaction,
        test_category: Category,
    ) -> None:
        """Test getting existing evidence by ID."""
        repo = CategoryEvidenceRepository(db_session)
        created = repo.create(
            transaction_id=test_transaction.id,
            item_description="Test Item",
            item_price=Decimal("10.00"),
            category_id=test_category.id,
            evidence_type="rule",
        )
        db_session.flush()

        evidence = repo.get(created.id)

        assert evidence.id == created.id

    def test_get_nonexistent_evidence(self, db_session: Session) -> None:
        """Test getting non-existent evidence raises error."""
        repo = CategoryEvidenceRepository(db_session)

        with pytest.raises(CategoryEvidenceNotFoundError):
            repo.get(9999)


class TestCategoryEvidenceRepositoryGetByTransaction:
    """Tests for CategoryEvidenceRepository.get_by_transaction()."""

    def test_get_all_evidence_for_transaction(
        self,
        db_session: Session,
        test_transaction: Transaction,
        test_category: Category,
    ) -> None:
        """Test getting all evidence for a transaction."""
        repo = CategoryEvidenceRepository(db_session)

        repo.create(
            transaction_id=test_transaction.id,
            item_description="Item 1",
            item_price=Decimal("10.00"),
            category_id=test_category.id,
            evidence_type="email",
        )
        repo.create(
            transaction_id=test_transaction.id,
            item_description="Item 2",
            item_price=Decimal("20.00"),
            category_id=test_category.id,
            evidence_type="email",
        )
        db_session.flush()

        evidence_list = repo.get_by_transaction(test_transaction.id)

        assert len(evidence_list) == 2

    def test_get_empty_for_no_evidence(
        self, db_session: Session, test_transaction: Transaction
    ) -> None:
        """Test getting empty list when no evidence exists."""
        repo = CategoryEvidenceRepository(db_session)

        evidence_list = repo.get_by_transaction(test_transaction.id)

        assert len(evidence_list) == 0


class TestCategoryEvidenceRepositoryGetTransactionTotal:
    """Tests for CategoryEvidenceRepository.get_transaction_total()."""

    def test_calculate_total(
        self,
        db_session: Session,
        test_transaction: Transaction,
        test_category: Category,
    ) -> None:
        """Test calculating total of evidence items."""
        repo = CategoryEvidenceRepository(db_session)

        repo.create(
            transaction_id=test_transaction.id,
            item_description="Item 1",
            item_price=Decimal("10.00"),
            item_quantity=2,
            category_id=test_category.id,
            evidence_type="email",
        )
        repo.create(
            transaction_id=test_transaction.id,
            item_description="Item 2",
            item_price=Decimal("25.00"),
            category_id=test_category.id,
            evidence_type="email",
        )
        db_session.flush()

        total = repo.get_transaction_total(test_transaction.id)

        # (10.00 * 2) + (25.00 * 1) = 45.00
        assert total == Decimal("45.00")

    def test_total_zero_for_no_evidence(
        self, db_session: Session, test_transaction: Transaction
    ) -> None:
        """Test total is zero when no evidence exists."""
        repo = CategoryEvidenceRepository(db_session)

        total = repo.get_transaction_total(test_transaction.id)

        assert total == Decimal("0")


class TestCategoryEvidenceRepositoryGetDominantCategory:
    """Tests for CategoryEvidenceRepository.get_dominant_category()."""

    def test_get_dominant_category(
        self,
        db_session: Session,
        test_transaction: Transaction,
        test_category: Category,
        test_category_2: Category,
    ) -> None:
        """Test finding category with highest total value."""
        repo = CategoryEvidenceRepository(db_session)

        # Electronics: 10 + 5 = 15
        repo.create(
            transaction_id=test_transaction.id,
            item_description="Cable",
            item_price=Decimal("10.00"),
            category_id=test_category.id,
            evidence_type="email",
        )
        repo.create(
            transaction_id=test_transaction.id,
            item_description="Adapter",
            item_price=Decimal("5.00"),
            category_id=test_category.id,
            evidence_type="email",
        )
        # Books: 30
        repo.create(
            transaction_id=test_transaction.id,
            item_description="Book",
            item_price=Decimal("30.00"),
            category_id=test_category_2.id,
            evidence_type="email",
        )
        db_session.flush()

        dominant = repo.get_dominant_category(test_transaction.id)

        assert dominant == test_category_2.id  # Books = 30 > Electronics = 15

    def test_dominant_category_none_for_no_evidence(
        self, db_session: Session, test_transaction: Transaction
    ) -> None:
        """Test None returned when no evidence exists."""
        repo = CategoryEvidenceRepository(db_session)

        dominant = repo.get_dominant_category(test_transaction.id)

        assert dominant is None


class TestCategoryEvidenceRepositoryDelete:
    """Tests for delete methods."""

    def test_delete_by_transaction(
        self,
        db_session: Session,
        test_transaction: Transaction,
        test_category: Category,
    ) -> None:
        """Test deleting all evidence for a transaction."""
        repo = CategoryEvidenceRepository(db_session)

        repo.create(
            transaction_id=test_transaction.id,
            item_description="Item 1",
            item_price=Decimal("10.00"),
            category_id=test_category.id,
            evidence_type="email",
        )
        repo.create(
            transaction_id=test_transaction.id,
            item_description="Item 2",
            item_price=Decimal("20.00"),
            category_id=test_category.id,
            evidence_type="email",
        )
        db_session.flush()

        deleted_count = repo.delete_by_transaction(test_transaction.id)
        db_session.flush()

        assert deleted_count == 2
        assert len(repo.get_by_transaction(test_transaction.id)) == 0

    def test_delete_single_evidence(
        self,
        db_session: Session,
        test_transaction: Transaction,
        test_category: Category,
    ) -> None:
        """Test deleting a single evidence record."""
        repo = CategoryEvidenceRepository(db_session)
        evidence = repo.create(
            transaction_id=test_transaction.id,
            item_description="Delete Me",
            item_price=Decimal("10.00"),
            category_id=test_category.id,
            evidence_type="manual",
        )
        db_session.flush()
        evidence_id = evidence.id

        repo.delete(evidence_id)
        db_session.flush()

        with pytest.raises(CategoryEvidenceNotFoundError):
            repo.get(evidence_id)
