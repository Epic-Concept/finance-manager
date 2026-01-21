"""Tests for EmailSearchService."""

from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from finance_api.models.email_account import EmailAccount
from finance_api.models.transaction import Transaction
from finance_api.repositories.email_account_repository import EmailAccountRepository
from finance_api.services.email_search_service import (
    EmailClientInterface,
    EmailMessage,
    EmailSearchQuery,
    EmailSearchService,
)


class MockEmailClient(EmailClientInterface):
    """Mock email client for testing."""

    def __init__(self, messages: list[EmailMessage] | None = None) -> None:
        self.messages = messages or []
        self.connected = False
        self.connect_called = 0
        self.disconnect_called = 0
        self.search_called = 0
        self.last_query: EmailSearchQuery | None = None

    def connect(self, account: EmailAccount) -> bool:
        self.connect_called += 1
        self.connected = True
        return True

    def disconnect(self) -> None:
        self.disconnect_called += 1
        self.connected = False

    def search(self, query: EmailSearchQuery) -> list[EmailMessage]:
        self.search_called += 1
        self.last_query = query
        return self.messages


class FailingEmailClient(EmailClientInterface):
    """Email client that fails to connect."""

    def connect(self, account: EmailAccount) -> bool:
        return False

    def disconnect(self) -> None:
        pass

    def search(self, query: EmailSearchQuery) -> list[EmailMessage]:
        return []


class ExceptionEmailClient(EmailClientInterface):
    """Email client that raises exceptions."""

    def connect(self, account: EmailAccount) -> bool:
        raise ConnectionError("Failed to connect")

    def disconnect(self) -> None:
        pass

    def search(self, query: EmailSearchQuery) -> list[EmailMessage]:
        return []


@pytest.fixture
def email_account_repo(db_session: Session) -> EmailAccountRepository:
    """Create an EmailAccountRepository instance."""
    return EmailAccountRepository(db_session)


@pytest.fixture
def test_email_account(
    db_session: Session, email_account_repo: EmailAccountRepository
) -> EmailAccount:
    """Create a test email account."""
    account = email_account_repo.create(
        email_address="test@gmail.com",
        provider="gmail",
        display_name="Test Gmail",
        priority=0,
    )
    db_session.flush()
    return account


@pytest.fixture
def secondary_email_account(
    db_session: Session, email_account_repo: EmailAccountRepository
) -> EmailAccount:
    """Create a secondary test email account."""
    account = email_account_repo.create(
        email_address="secondary@outlook.com",
        provider="outlook",
        display_name="Secondary Outlook",
        priority=1,
    )
    db_session.flush()
    return account


@pytest.fixture
def amazon_transaction(db_session: Session) -> Transaction:
    """Create an Amazon transaction."""
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
def tesco_transaction(db_session: Session) -> Transaction:
    """Create a Tesco transaction."""
    transaction = Transaction(
        transaction_date=date(2026, 1, 10),
        description="TESCO STORES 1234",
        amount=Decimal("-45.00"),
        currency="GBP",
    )
    db_session.add(transaction)
    db_session.flush()
    return transaction


@pytest.fixture
def unknown_transaction(db_session: Session) -> Transaction:
    """Create an unknown merchant transaction."""
    transaction = Transaction(
        transaction_date=date(2026, 1, 20),
        description="RANDOM STORE XYZ",
        amount=Decimal("-25.00"),
        currency="GBP",
    )
    db_session.add(transaction)
    db_session.flush()
    return transaction


class TestEmailSearchQueryToImap:
    """Tests for EmailSearchQuery.to_imap_search()."""

    def test_basic_date_range(self) -> None:
        """Test basic date range conversion."""
        query = EmailSearchQuery(
            date_from=date(2026, 1, 10),
            date_to=date(2026, 1, 20),
            sender_patterns=[],
            subject_keywords=[],
            body_keywords=[],
        )

        result = query.to_imap_search()

        assert 'SINCE "10-Jan-2026"' in result
        assert 'BEFORE "20-Jan-2026"' in result

    def test_single_sender(self) -> None:
        """Test single sender pattern."""
        query = EmailSearchQuery(
            date_from=date(2026, 1, 10),
            date_to=date(2026, 1, 20),
            sender_patterns=["amazon.co.uk"],
            subject_keywords=[],
            body_keywords=[],
        )

        result = query.to_imap_search()

        assert 'FROM "amazon.co.uk"' in result

    def test_multiple_senders(self) -> None:
        """Test multiple sender patterns creates OR clause."""
        query = EmailSearchQuery(
            date_from=date(2026, 1, 10),
            date_to=date(2026, 1, 20),
            sender_patterns=["amazon.co.uk", "amazon.com"],
            subject_keywords=[],
            body_keywords=[],
        )

        result = query.to_imap_search()

        assert "OR" in result
        assert 'FROM "amazon.co.uk"' in result
        assert 'FROM "amazon.com"' in result

    def test_single_subject(self) -> None:
        """Test single subject keyword."""
        query = EmailSearchQuery(
            date_from=date(2026, 1, 10),
            date_to=date(2026, 1, 20),
            sender_patterns=[],
            subject_keywords=["order"],
            body_keywords=[],
        )

        result = query.to_imap_search()

        assert 'SUBJECT "order"' in result

    def test_multiple_subjects(self) -> None:
        """Test multiple subject keywords creates OR clause."""
        query = EmailSearchQuery(
            date_from=date(2026, 1, 10),
            date_to=date(2026, 1, 20),
            sender_patterns=[],
            subject_keywords=["order", "receipt"],
            body_keywords=[],
        )

        result = query.to_imap_search()

        assert "OR" in result
        assert 'SUBJECT "order"' in result
        assert 'SUBJECT "receipt"' in result


class TestEmailSearchServiceBuildQuery:
    """Tests for EmailSearchService.build_search_query()."""

    def test_amazon_transaction_query(
        self,
        email_account_repo: EmailAccountRepository,
        amazon_transaction: Transaction,
    ) -> None:
        """Test building query for Amazon transaction."""
        service = EmailSearchService(email_account_repo, date_range_days=7)

        query = service.build_search_query(amazon_transaction)

        # Date range should be ±7 days
        assert query.date_from == date(2026, 1, 8)
        assert query.date_to == date(2026, 1, 22)

        # Should include Amazon email domains
        assert "amazon.co.uk" in query.sender_patterns
        assert "amazon.com" in query.sender_patterns

        # Should include order keywords
        assert "order" in query.subject_keywords

    def test_tesco_transaction_query(
        self, email_account_repo: EmailAccountRepository, tesco_transaction: Transaction
    ) -> None:
        """Test building query for Tesco transaction."""
        service = EmailSearchService(email_account_repo, date_range_days=7)

        query = service.build_search_query(tesco_transaction)

        # Should include Tesco domain
        assert "tesco.com" in query.sender_patterns

        # Should include tesco in subject keywords
        assert "tesco" in query.subject_keywords

    def test_unknown_merchant_query(
        self,
        email_account_repo: EmailAccountRepository,
        unknown_transaction: Transaction,
    ) -> None:
        """Test building query for unknown merchant."""
        service = EmailSearchService(email_account_repo, date_range_days=7)

        query = service.build_search_query(unknown_transaction)

        # No sender patterns for unknown merchant
        assert len(query.sender_patterns) == 0

        # Should still include order keywords
        assert "order" in query.subject_keywords

    def test_custom_date_range(
        self,
        email_account_repo: EmailAccountRepository,
        amazon_transaction: Transaction,
    ) -> None:
        """Test custom date range configuration."""
        service = EmailSearchService(email_account_repo, date_range_days=3)

        query = service.build_search_query(amazon_transaction)

        # Date range should be ±3 days
        assert query.date_from == date(2026, 1, 12)
        assert query.date_to == date(2026, 1, 18)


class TestEmailSearchServiceSearch:
    """Tests for EmailSearchService.search_for_transaction()."""

    def test_no_client_raises_error(
        self,
        email_account_repo: EmailAccountRepository,
        amazon_transaction: Transaction,
    ) -> None:
        """Test that searching without a client raises ValueError."""
        service = EmailSearchService(email_account_repo, email_client=None)

        with pytest.raises(ValueError, match="No email client configured"):
            service.search_for_transaction(amazon_transaction)

    def test_search_returns_messages(
        self,
        email_account_repo: EmailAccountRepository,
        test_email_account: EmailAccount,
        amazon_transaction: Transaction,
    ) -> None:
        """Test successful search returns messages."""
        mock_messages = [
            EmailMessage(
                message_id="<msg1@amazon.co.uk>",
                subject="Your Amazon.co.uk order",
                sender="no-reply@amazon.co.uk",
                recipient="test@gmail.com",
                date=datetime(2026, 1, 15, 10, 30, 0),
                body_text="Your order has been confirmed...",
            ),
        ]
        mock_client = MockEmailClient(mock_messages)
        service = EmailSearchService(email_account_repo, email_client=mock_client)

        results = service.search_for_transaction(amazon_transaction)

        assert len(results) == 1
        assert results[0].message_id == "<msg1@amazon.co.uk>"
        assert results[0].email_account_id == test_email_account.id

    def test_search_iterates_accounts_by_priority(
        self,
        email_account_repo: EmailAccountRepository,
        test_email_account: EmailAccount,
        secondary_email_account: EmailAccount,
        amazon_transaction: Transaction,
    ) -> None:
        """Test that search iterates through accounts by priority."""
        mock_client = MockEmailClient([])
        service = EmailSearchService(email_account_repo, email_client=mock_client)

        service.search_for_transaction(amazon_transaction)

        # Should have connected twice (once per account)
        assert mock_client.connect_called == 2
        assert mock_client.disconnect_called == 2

    def test_search_handles_connection_failure(
        self,
        email_account_repo: EmailAccountRepository,
        test_email_account: EmailAccount,
        amazon_transaction: Transaction,
    ) -> None:
        """Test that search handles connection failures gracefully."""
        failing_client = FailingEmailClient()
        service = EmailSearchService(email_account_repo, email_client=failing_client)

        results = service.search_for_transaction(amazon_transaction)

        # Should return empty list, not raise
        assert results == []

    def test_search_handles_exceptions(
        self,
        email_account_repo: EmailAccountRepository,
        test_email_account: EmailAccount,
        amazon_transaction: Transaction,
    ) -> None:
        """Test that search handles exceptions gracefully."""
        exception_client = ExceptionEmailClient()
        service = EmailSearchService(email_account_repo, email_client=exception_client)

        results = service.search_for_transaction(amazon_transaction)

        # Should return empty list, not raise
        assert results == []

    def test_search_aggregates_from_multiple_accounts(
        self,
        db_session: Session,
        email_account_repo: EmailAccountRepository,
        test_email_account: EmailAccount,
        secondary_email_account: EmailAccount,
        amazon_transaction: Transaction,
    ) -> None:
        """Test that search aggregates results from multiple accounts."""

        class MultiAccountMockClient(EmailClientInterface):
            """Mock that returns different messages per account."""

            def __init__(self) -> None:
                self.call_count = 0
                self.connected_account: EmailAccount | None = None

            def connect(self, account: EmailAccount) -> bool:
                self.connected_account = account
                return True

            def disconnect(self) -> None:
                self.connected_account = None

            def search(self, query: EmailSearchQuery) -> list[EmailMessage]:
                self.call_count += 1
                if self.call_count == 1:
                    return [
                        EmailMessage(
                            message_id="<msg1@gmail>",
                            subject="Order 1",
                            sender="amazon@amazon.co.uk",
                            recipient="test@gmail.com",
                            date=datetime(2026, 1, 15),
                            body_text="Order 1 body",
                        )
                    ]
                else:
                    return [
                        EmailMessage(
                            message_id="<msg2@outlook>",
                            subject="Order 2",
                            sender="amazon@amazon.co.uk",
                            recipient="secondary@outlook.com",
                            date=datetime(2026, 1, 15),
                            body_text="Order 2 body",
                        )
                    ]

        mock_client = MultiAccountMockClient()
        service = EmailSearchService(email_account_repo, email_client=mock_client)

        results = service.search_for_transaction(amazon_transaction)

        assert len(results) == 2
        message_ids = {r.message_id for r in results}
        assert "<msg1@gmail>" in message_ids
        assert "<msg2@outlook>" in message_ids


class TestEmailSearchServiceMerchantPatterns:
    """Tests for merchant pattern management."""

    def test_get_merchant_patterns(
        self, email_account_repo: EmailAccountRepository
    ) -> None:
        """Test getting merchant patterns."""
        service = EmailSearchService(email_account_repo)

        patterns = service.get_merchant_patterns()

        assert "amazon" in patterns
        assert "amazon.co.uk" in patterns["amazon"]

    def test_add_merchant_pattern(
        self, email_account_repo: EmailAccountRepository
    ) -> None:
        """Test adding a new merchant pattern."""
        service = EmailSearchService(email_account_repo)

        service.add_merchant_pattern("coolblue", ["coolblue.nl", "coolblue.be"])

        patterns = service.get_merchant_patterns()
        assert "coolblue" in patterns
        assert "coolblue.nl" in patterns["coolblue"]
