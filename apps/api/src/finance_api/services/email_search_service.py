"""EmailSearchService for searching emails related to transactions."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from finance_api.models.email_account import EmailAccount
from finance_api.models.transaction import Transaction
from finance_api.repositories.email_account_repository import EmailAccountRepository


@dataclass
class EmailMessage:
    """Represents an email message found by search."""

    message_id: str
    subject: str
    sender: str
    recipient: str
    date: datetime
    body_text: str
    body_html: str | None = None
    email_account_id: int | None = None


@dataclass
class EmailSearchQuery:
    """Parameters for an email search."""

    date_from: date
    date_to: date
    sender_patterns: list[str]
    subject_keywords: list[str]
    body_keywords: list[str]

    def to_imap_search(self) -> str:
        """Convert to IMAP search criteria string.

        Returns:
            IMAP search string suitable for IMAP SEARCH command.
        """
        criteria: list[str] = []

        # Date range
        criteria.append(f'SINCE "{self.date_from.strftime("%d-%b-%Y")}"')
        criteria.append(f'BEFORE "{self.date_to.strftime("%d-%b-%Y")}"')

        # Sender patterns (OR together)
        if self.sender_patterns:
            if len(self.sender_patterns) == 1:
                criteria.append(f'FROM "{self.sender_patterns[0]}"')
            else:
                # Build OR tree for multiple senders
                sender_criteria = [f'FROM "{s}"' for s in self.sender_patterns]
                or_clause = sender_criteria[0]
                for sc in sender_criteria[1:]:
                    or_clause = f"OR {or_clause} {sc}"
                criteria.append(f"({or_clause})")

        # Subject keywords (OR together)
        if self.subject_keywords:
            if len(self.subject_keywords) == 1:
                criteria.append(f'SUBJECT "{self.subject_keywords[0]}"')
            else:
                subject_criteria = [f'SUBJECT "{s}"' for s in self.subject_keywords]
                or_clause = subject_criteria[0]
                for sc in subject_criteria[1:]:
                    or_clause = f"OR {or_clause} {sc}"
                criteria.append(f"({or_clause})")

        return " ".join(criteria)


class EmailClientInterface(ABC):
    """Abstract interface for email client implementations."""

    @abstractmethod
    def connect(self, account: EmailAccount) -> bool:
        """Connect to the email server.

        Args:
            account: Email account configuration.

        Returns:
            True if connection successful.
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the email server."""
        pass

    @abstractmethod
    def search(self, query: EmailSearchQuery) -> list[EmailMessage]:
        """Search for emails matching the query.

        Args:
            query: Search parameters.

        Returns:
            List of matching email messages.
        """
        pass


# Merchant email domain mappings for common retailers
MERCHANT_EMAIL_PATTERNS: dict[str, list[str]] = {
    "amazon": ["amazon.co.uk", "amazon.com", "amazon.de", "amazon.es"],
    "allegro": ["allegro.pl"],
    "aliexpress": ["aliexpress.com"],
    "ebay": ["ebay.co.uk", "ebay.com"],
    "tesco": ["tesco.com"],
    "sainsbury": ["sainsburys.co.uk"],
    "argos": ["argos.co.uk"],
    "john lewis": ["johnlewis.com"],
    "currys": ["currys.co.uk"],
}

# Keywords that indicate order/receipt emails
ORDER_KEYWORDS = [
    "order confirmation",
    "order",
    "receipt",
    "invoice",
    "your order",
    "order dispatched",
    "shipped",
    "delivery",
    "purchase",
]


class EmailSearchService:
    """Service for searching emails related to transactions.

    This service coordinates searching across multiple email accounts
    and builds appropriate search queries based on transaction data.
    """

    def __init__(
        self,
        email_account_repository: EmailAccountRepository,
        email_client: EmailClientInterface | None = None,
        date_range_days: int = 7,
    ) -> None:
        """Initialize the service.

        Args:
            email_account_repository: Repository for email accounts.
            email_client: Email client implementation (optional for testing).
            date_range_days: Days before/after transaction to search (default 7).
        """
        self._account_repo = email_account_repository
        self._email_client = email_client
        self._date_range_days = date_range_days

    def _extract_merchant_from_description(self, description: str) -> str | None:
        """Extract merchant name from transaction description.

        Args:
            description: Transaction description string.

        Returns:
            Merchant name if recognized, None otherwise.
        """
        description_lower = description.lower()
        for merchant in MERCHANT_EMAIL_PATTERNS:
            if merchant in description_lower:
                return merchant
        return None

    def _get_sender_patterns(self, merchant: str | None) -> list[str]:
        """Get email sender patterns for a merchant.

        Args:
            merchant: Merchant name (lowercase).

        Returns:
            List of email domain patterns.
        """
        if merchant and merchant in MERCHANT_EMAIL_PATTERNS:
            return MERCHANT_EMAIL_PATTERNS[merchant]
        return []

    def build_search_query(self, transaction: Transaction) -> EmailSearchQuery:
        """Build an email search query for a transaction.

        Args:
            transaction: The transaction to find emails for.

        Returns:
            EmailSearchQuery with appropriate parameters.
        """
        # Date range: transaction date ± configured days
        date_from = transaction.transaction_date - timedelta(days=self._date_range_days)
        date_to = transaction.transaction_date + timedelta(days=self._date_range_days)

        # Extract merchant and get sender patterns
        merchant = self._extract_merchant_from_description(transaction.description)
        sender_patterns = self._get_sender_patterns(merchant)

        # Use order-related keywords
        subject_keywords = ORDER_KEYWORDS.copy()

        # Add merchant name to subject keywords if found
        if merchant:
            subject_keywords.insert(0, merchant)

        return EmailSearchQuery(
            date_from=date_from,
            date_to=date_to,
            sender_patterns=sender_patterns,
            subject_keywords=subject_keywords,
            body_keywords=[],  # Not typically used in IMAP search
        )

    def search_for_transaction(
        self, transaction: Transaction
    ) -> list[EmailMessage]:
        """Search all email accounts for emails related to a transaction.

        Iterates through active email accounts by priority and searches
        each one for relevant emails.

        Args:
            transaction: The transaction to find emails for.

        Returns:
            List of matching email messages from all accounts.
        """
        if self._email_client is None:
            raise ValueError("No email client configured")

        results: list[EmailMessage] = []
        query = self.build_search_query(transaction)

        # Get active email accounts ordered by priority
        accounts = self._account_repo.get_active_by_priority()

        for account in accounts:
            try:
                if self._email_client.connect(account):
                    messages = self._email_client.search(query)
                    # Tag messages with account ID
                    for msg in messages:
                        msg.email_account_id = account.id
                    results.extend(messages)
                    self._email_client.disconnect()
            except Exception:
                # Log error but continue with other accounts
                # In production, use proper logging
                continue

        return results

    def get_merchant_patterns(self) -> dict[str, list[str]]:
        """Get the configured merchant email patterns.

        Returns:
            Dictionary mapping merchant names to email domain patterns.
        """
        return MERCHANT_EMAIL_PATTERNS.copy()

    def add_merchant_pattern(self, merchant: str, domains: list[str]) -> None:
        """Add or update merchant email patterns.

        Args:
            merchant: Merchant name (will be lowercased).
            domains: List of email domains.
        """
        MERCHANT_EMAIL_PATTERNS[merchant.lower()] = domains
