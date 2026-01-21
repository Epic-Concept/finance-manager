"""Tests for AIDisambiguationService."""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from finance_api.models.category import Category, CategoryClosure
from finance_api.models.transaction import Transaction
from finance_api.repositories.category_evidence_repository import (
    CategoryEvidenceRepository,
)
from finance_api.repositories.category_repository import CategoryRepository
from finance_api.repositories.email_account_repository import EmailAccountRepository
from finance_api.services.ai_disambiguation_service import (
    AIDisambiguationService,
    DisambiguationResult,
)
from finance_api.services.category_mapping_service import CategoryMappingService
from finance_api.services.email_search_service import (
    EmailClientInterface,
    EmailMessage,
    EmailSearchQuery,
    EmailSearchService,
)
from finance_api.services.receipt_extraction_service import (
    ExtractedItem,
    ExtractedReceipt,
    ReceiptExtractionError,
    ReceiptExtractionService,
)


class MockEmailClient(EmailClientInterface):
    """Mock email client that returns configured messages."""

    def __init__(self, messages: list[EmailMessage] | None = None) -> None:
        self.messages = messages or []

    def connect(self, account: object) -> bool:
        return True

    def disconnect(self) -> None:
        pass

    def search(self, query: EmailSearchQuery) -> list[EmailMessage]:
        return self.messages


class MockReceiptExtractionService:
    """Mock receipt extraction service."""

    def __init__(
        self, receipt: ExtractedReceipt | None = None, error: Exception | None = None
    ) -> None:
        self.receipt = receipt
        self.error = error
        self._model = "claude-sonnet-4-5-20250514"

    def extract(self, email: EmailMessage) -> ExtractedReceipt:
        if self.error:
            raise self.error
        if self.receipt:
            return self.receipt
        raise ReceiptExtractionError("No receipt configured")


@pytest.fixture
def electronics_category(db_session: Session) -> Category:
    """Create an Electronics category."""
    category = Category(name="Electronics")
    db_session.add(category)
    db_session.flush()
    closure = CategoryClosure(
        ancestor_id=category.id, descendant_id=category.id, depth=0
    )
    db_session.add(closure)
    db_session.flush()
    return category


@pytest.fixture
def books_category(db_session: Session) -> Category:
    """Create a Books category."""
    category = Category(name="Books")
    db_session.add(category)
    db_session.flush()
    closure = CategoryClosure(
        ancestor_id=category.id, descendant_id=category.id, depth=0
    )
    db_session.add(closure)
    db_session.flush()
    return category


@pytest.fixture
def test_email_account(
    db_session: Session,
) -> object:
    """Create a test email account."""
    repo = EmailAccountRepository(db_session)
    account = repo.create(
        email_address="test@gmail.com",
        provider="gmail",
    )
    db_session.flush()
    return account


@pytest.fixture
def amazon_transaction(db_session: Session) -> Transaction:
    """Create an Amazon transaction for testing."""
    transaction = Transaction(
        transaction_date=date(2026, 1, 15),
        description="AMAZON.CO.UK ORDER",
        amount=Decimal("-59.99"),
        currency="GBP",
    )
    db_session.add(transaction)
    db_session.flush()
    return transaction


@pytest.fixture
def sample_email() -> EmailMessage:
    """Create a sample email message."""
    return EmailMessage(
        message_id="<test123@amazon.co.uk>",
        subject="Your Amazon.co.uk order",
        sender="no-reply@amazon.co.uk",
        recipient="test@gmail.com",
        date=datetime(2026, 1, 15, 10, 30, 0),
        body_text="Order confirmation...",
        email_account_id=1,
    )


@pytest.fixture
def sample_receipt(electronics_category: Category) -> ExtractedReceipt:
    """Create a sample extracted receipt."""
    return ExtractedReceipt(
        merchant="Amazon UK",
        order_date=date(2026, 1, 15),
        items=[
            ExtractedItem(
                name="USB Cable",
                price=Decimal("9.99"),
                quantity=1,
                category_hint="Electronics",
            ),
            ExtractedItem(
                name="Wireless Mouse",
                price=Decimal("45.00"),
                quantity=1,
                category_hint="Electronics",
            ),
        ],
        shipping_cost=Decimal("5.00"),
        total=Decimal("59.99"),
        currency="GBP",
        raw_response='{"test": "response"}',
        confidence_score=Decimal("0.95"),
    )


@pytest.fixture
def email_account_repo(db_session: Session) -> EmailAccountRepository:
    """Create EmailAccountRepository."""
    return EmailAccountRepository(db_session)


@pytest.fixture
def category_repo(db_session: Session) -> CategoryRepository:
    """Create CategoryRepository."""
    return CategoryRepository(db_session)


@pytest.fixture
def evidence_repo(db_session: Session) -> CategoryEvidenceRepository:
    """Create CategoryEvidenceRepository."""
    return CategoryEvidenceRepository(db_session)


class TestAIDisambiguationServiceSuccess:
    """Tests for successful disambiguation."""

    def test_full_disambiguation_flow(
        self,
        db_session: Session,
        email_account_repo: EmailAccountRepository,
        category_repo: CategoryRepository,
        evidence_repo: CategoryEvidenceRepository,
        amazon_transaction: Transaction,
        electronics_category: Category,
        test_email_account: object,
        sample_email: EmailMessage,
        sample_receipt: ExtractedReceipt,
    ) -> None:
        """Test complete disambiguation flow succeeds."""
        # Setup mock services
        mock_client = MockEmailClient([sample_email])
        email_service = EmailSearchService(email_account_repo, email_client=mock_client)
        extraction_service = MockReceiptExtractionService(receipt=sample_receipt)
        mapping_service = CategoryMappingService(category_repo)

        service = AIDisambiguationService(
            email_search_service=email_service,
            receipt_extraction_service=extraction_service,  # type: ignore[arg-type]
            category_mapping_service=mapping_service,
            evidence_repository=evidence_repo,
            confidence_threshold=Decimal("0.9"),
        )

        result = service.disambiguate(amazon_transaction)
        db_session.flush()

        assert result.success is True
        assert result.dominant_category_id == electronics_category.id
        assert len(result.evidence_records) == 3  # 2 items + shipping
        assert result.confidence_score >= Decimal("0.9")
        assert result.error_message is None


class TestAIDisambiguationServiceFailures:
    """Tests for disambiguation failure cases."""

    def test_no_emails_found(
        self,
        db_session: Session,
        email_account_repo: EmailAccountRepository,
        category_repo: CategoryRepository,
        evidence_repo: CategoryEvidenceRepository,
        amazon_transaction: Transaction,
        electronics_category: Category,
        test_email_account: object,
    ) -> None:
        """Test failure when no emails are found."""
        mock_client = MockEmailClient([])  # No emails
        email_service = EmailSearchService(email_account_repo, email_client=mock_client)
        extraction_service = MockReceiptExtractionService()
        mapping_service = CategoryMappingService(category_repo)

        service = AIDisambiguationService(
            email_search_service=email_service,
            receipt_extraction_service=extraction_service,  # type: ignore[arg-type]
            category_mapping_service=mapping_service,
            evidence_repository=evidence_repo,
        )

        result = service.disambiguate(amazon_transaction)

        assert result.success is False
        assert result.dominant_category_id is None
        assert "No matching emails found" in (result.error_message or "")

    def test_email_client_not_configured(
        self,
        db_session: Session,
        email_account_repo: EmailAccountRepository,
        category_repo: CategoryRepository,
        evidence_repo: CategoryEvidenceRepository,
        amazon_transaction: Transaction,
        electronics_category: Category,
    ) -> None:
        """Test failure when email client not configured."""
        email_service = EmailSearchService(email_account_repo, email_client=None)
        extraction_service = MockReceiptExtractionService()
        mapping_service = CategoryMappingService(category_repo)

        service = AIDisambiguationService(
            email_search_service=email_service,
            receipt_extraction_service=extraction_service,  # type: ignore[arg-type]
            category_mapping_service=mapping_service,
            evidence_repository=evidence_repo,
        )

        result = service.disambiguate(amazon_transaction)

        assert result.success is False
        assert "configuration error" in (result.error_message or "").lower()

    def test_extraction_failure(
        self,
        db_session: Session,
        email_account_repo: EmailAccountRepository,
        category_repo: CategoryRepository,
        evidence_repo: CategoryEvidenceRepository,
        amazon_transaction: Transaction,
        electronics_category: Category,
        test_email_account: object,
        sample_email: EmailMessage,
    ) -> None:
        """Test failure when receipt extraction fails."""
        mock_client = MockEmailClient([sample_email])
        email_service = EmailSearchService(email_account_repo, email_client=mock_client)
        extraction_service = MockReceiptExtractionService(
            error=ReceiptExtractionError("Parse error")
        )
        mapping_service = CategoryMappingService(category_repo)

        service = AIDisambiguationService(
            email_search_service=email_service,
            receipt_extraction_service=extraction_service,  # type: ignore[arg-type]
            category_mapping_service=mapping_service,
            evidence_repository=evidence_repo,
        )

        result = service.disambiguate(amazon_transaction)

        assert result.success is False
        assert "extraction failed" in (result.error_message or "").lower()

    def test_no_items_mapped(
        self,
        db_session: Session,
        email_account_repo: EmailAccountRepository,
        category_repo: CategoryRepository,
        evidence_repo: CategoryEvidenceRepository,
        amazon_transaction: Transaction,
        test_email_account: object,
        sample_email: EmailMessage,
    ) -> None:
        """Test failure when no items can be mapped to categories."""
        # Receipt with unmappable items (no matching categories)
        receipt_no_match = ExtractedReceipt(
            merchant="Unknown Store",
            order_date=date(2026, 1, 15),
            items=[
                ExtractedItem(
                    name="Mystery Item",
                    price=Decimal("50.00"),
                    category_hint="UnknownCategory",
                ),
            ],
            total=Decimal("50.00"),
            currency="GBP",
            raw_response="{}",
            confidence_score=Decimal("0.9"),
        )

        mock_client = MockEmailClient([sample_email])
        email_service = EmailSearchService(email_account_repo, email_client=mock_client)
        extraction_service = MockReceiptExtractionService(receipt=receipt_no_match)
        mapping_service = CategoryMappingService(category_repo)

        service = AIDisambiguationService(
            email_search_service=email_service,
            receipt_extraction_service=extraction_service,  # type: ignore[arg-type]
            category_mapping_service=mapping_service,
            evidence_repository=evidence_repo,
        )

        result = service.disambiguate(amazon_transaction)

        assert result.success is False
        assert "could be mapped to categories" in (result.error_message or "").lower()


class TestAIDisambiguationServiceShipping:
    """Tests for shipping cost handling."""

    def test_free_shipping_creates_evidence(
        self,
        db_session: Session,
        email_account_repo: EmailAccountRepository,
        category_repo: CategoryRepository,
        evidence_repo: CategoryEvidenceRepository,
        amazon_transaction: Transaction,
        electronics_category: Category,
        test_email_account: object,
        sample_email: EmailMessage,
    ) -> None:
        """Test that free shipping ($0) still creates an evidence record."""
        # Receipt with free shipping (shipping_cost = 0)
        receipt_with_free_shipping = ExtractedReceipt(
            merchant="Amazon UK",
            order_date=date(2026, 1, 15),
            items=[
                ExtractedItem(
                    name="USB Cable",
                    price=Decimal("59.99"),
                    quantity=1,
                    category_hint="Electronics",
                ),
            ],
            shipping_cost=Decimal("0.00"),  # Free shipping
            total=Decimal("59.99"),
            currency="GBP",
            raw_response='{"test": "response"}',
            confidence_score=Decimal("0.95"),
        )

        mock_client = MockEmailClient([sample_email])
        email_service = EmailSearchService(email_account_repo, email_client=mock_client)
        extraction_service = MockReceiptExtractionService(receipt=receipt_with_free_shipping)
        mapping_service = CategoryMappingService(category_repo)

        service = AIDisambiguationService(
            email_search_service=email_service,
            receipt_extraction_service=extraction_service,  # type: ignore[arg-type]
            category_mapping_service=mapping_service,
            evidence_repository=evidence_repo,
            confidence_threshold=Decimal("0.9"),
        )

        result = service.disambiguate(amazon_transaction)
        db_session.flush()

        assert result.success is True
        # Should have 2 evidence records: 1 item + free shipping
        assert len(result.evidence_records) == 2

        # Find the shipping evidence record
        shipping_evidence = [e for e in result.evidence_records if e.item_description == "Shipping"]
        assert len(shipping_evidence) == 1
        assert shipping_evidence[0].item_price == Decimal("0.00")

    def test_no_shipping_field_does_not_create_evidence(
        self,
        db_session: Session,
        email_account_repo: EmailAccountRepository,
        category_repo: CategoryRepository,
        evidence_repo: CategoryEvidenceRepository,
        amazon_transaction: Transaction,
        electronics_category: Category,
        test_email_account: object,
        sample_email: EmailMessage,
    ) -> None:
        """Test that None shipping_cost does not create evidence."""
        # Receipt with no shipping (shipping_cost = None)
        receipt_without_shipping = ExtractedReceipt(
            merchant="Amazon UK",
            order_date=date(2026, 1, 15),
            items=[
                ExtractedItem(
                    name="USB Cable",
                    price=Decimal("59.99"),
                    quantity=1,
                    category_hint="Electronics",
                ),
            ],
            shipping_cost=None,  # No shipping info
            total=Decimal("59.99"),
            currency="GBP",
            raw_response='{"test": "response"}',
            confidence_score=Decimal("0.95"),
        )

        mock_client = MockEmailClient([sample_email])
        email_service = EmailSearchService(email_account_repo, email_client=mock_client)
        extraction_service = MockReceiptExtractionService(receipt=receipt_without_shipping)
        mapping_service = CategoryMappingService(category_repo)

        service = AIDisambiguationService(
            email_search_service=email_service,
            receipt_extraction_service=extraction_service,  # type: ignore[arg-type]
            category_mapping_service=mapping_service,
            evidence_repository=evidence_repo,
            confidence_threshold=Decimal("0.9"),
        )

        result = service.disambiguate(amazon_transaction)
        db_session.flush()

        assert result.success is True
        # Should have only 1 evidence record (just the item, no shipping)
        assert len(result.evidence_records) == 1
        assert result.evidence_records[0].item_description == "USB Cable"


class TestAIDisambiguationServiceConfidence:
    """Tests for confidence threshold handling."""

    def test_low_confidence_fails(
        self,
        db_session: Session,
        email_account_repo: EmailAccountRepository,
        category_repo: CategoryRepository,
        evidence_repo: CategoryEvidenceRepository,
        amazon_transaction: Transaction,
        electronics_category: Category,
        test_email_account: object,
        sample_email: EmailMessage,
    ) -> None:
        """Test that low confidence results are marked as failed."""
        # Receipt with low confidence
        low_confidence_receipt = ExtractedReceipt(
            merchant="Amazon UK",
            order_date=date(2026, 1, 15),
            items=[
                ExtractedItem(
                    name="USB Cable",
                    price=Decimal("10.00"),
                    category_hint="Electronics",
                ),
            ],
            total=Decimal("50.00"),  # Mismatch to lower confidence
            currency="GBP",
            raw_response="{}",
            confidence_score=Decimal("0.5"),
        )

        mock_client = MockEmailClient([sample_email])
        email_service = EmailSearchService(email_account_repo, email_client=mock_client)
        extraction_service = MockReceiptExtractionService(receipt=low_confidence_receipt)
        mapping_service = CategoryMappingService(category_repo)

        service = AIDisambiguationService(
            email_search_service=email_service,
            receipt_extraction_service=extraction_service,  # type: ignore[arg-type]
            category_mapping_service=mapping_service,
            evidence_repository=evidence_repo,
            confidence_threshold=Decimal("0.9"),
        )

        result = service.disambiguate(amazon_transaction)

        # Evidence is still stored, but marked as not successful
        assert result.success is False
        assert "below threshold" in (result.error_message or "").lower()
        assert result.confidence_score < Decimal("0.9")


class TestAIDisambiguationServiceBatch:
    """Tests for batch disambiguation."""

    def test_disambiguate_batch(
        self,
        db_session: Session,
        email_account_repo: EmailAccountRepository,
        category_repo: CategoryRepository,
        evidence_repo: CategoryEvidenceRepository,
        electronics_category: Category,
        test_email_account: object,
        sample_email: EmailMessage,
        sample_receipt: ExtractedReceipt,
    ) -> None:
        """Test batch disambiguation of multiple transactions."""
        txn1 = Transaction(
            transaction_date=date(2026, 1, 15),
            description="AMAZON ORDER 1",
            amount=Decimal("-59.99"),
            currency="GBP",
        )
        txn2 = Transaction(
            transaction_date=date(2026, 1, 16),
            description="AMAZON ORDER 2",
            amount=Decimal("-30.00"),
            currency="GBP",
        )
        db_session.add_all([txn1, txn2])
        db_session.flush()

        mock_client = MockEmailClient([sample_email])
        email_service = EmailSearchService(email_account_repo, email_client=mock_client)
        extraction_service = MockReceiptExtractionService(receipt=sample_receipt)
        mapping_service = CategoryMappingService(category_repo)

        service = AIDisambiguationService(
            email_search_service=email_service,
            receipt_extraction_service=extraction_service,  # type: ignore[arg-type]
            category_mapping_service=mapping_service,
            evidence_repository=evidence_repo,
        )

        results = service.disambiguate_batch([txn1, txn2])
        db_session.flush()

        assert len(results) == 2
        assert txn1.id in results
        assert txn2.id in results
