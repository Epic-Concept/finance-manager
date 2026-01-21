"""EmailAccountRepository for managing email account configurations."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from finance_api.models.email_account import EmailAccount


class EmailAccountNotFoundError(Exception):
    """Raised when an email account is not found."""

    pass


class EmailAccountRepository:
    """Repository for email account CRUD operations."""

    def __init__(self, session: Session) -> None:
        """Initialize the repository with a database session.

        Args:
            session: SQLAlchemy database session.
        """
        self._session = session

    def create(
        self,
        email_address: str,
        provider: str,
        display_name: str | None = None,
        imap_server: str | None = None,
        imap_port: int = 993,
        credential_reference: str | None = None,
        priority: int = 0,
    ) -> EmailAccount:
        """Create a new email account configuration.

        Args:
            email_address: The email address.
            provider: Provider type (gmail, outlook, imap_generic).
            display_name: Optional friendly name.
            imap_server: IMAP server hostname (required for imap_generic).
            imap_port: IMAP port (default 993).
            credential_reference: Vault path or environment variable name.
            priority: Search priority (lower = higher priority).

        Returns:
            The created EmailAccount.
        """
        account = EmailAccount(
            email_address=email_address,
            display_name=display_name,
            provider=provider,
            imap_server=imap_server,
            imap_port=imap_port,
            credential_reference=credential_reference,
            is_active=True,
            priority=priority,
        )
        self._session.add(account)
        self._session.flush()
        return account

    def get(self, account_id: int) -> EmailAccount:
        """Get an email account by ID.

        Args:
            account_id: The email account ID.

        Returns:
            The EmailAccount.

        Raises:
            EmailAccountNotFoundError: If account doesn't exist.
        """
        account = self._session.get(EmailAccount, account_id)
        if account is None:
            raise EmailAccountNotFoundError(f"Email account {account_id} not found")
        return account

    def get_by_email(self, email_address: str) -> EmailAccount:
        """Get an email account by email address.

        Args:
            email_address: The email address.

        Returns:
            The EmailAccount.

        Raises:
            EmailAccountNotFoundError: If account doesn't exist.
        """
        stmt = select(EmailAccount).where(EmailAccount.email_address == email_address)
        account = self._session.execute(stmt).scalar_one_or_none()
        if account is None:
            raise EmailAccountNotFoundError(
                f"Email account with address {email_address} not found"
            )
        return account

    def get_active_by_priority(self) -> list[EmailAccount]:
        """Get all active email accounts ordered by priority.

        Returns:
            List of active EmailAccounts ordered by priority (lower first).
        """
        stmt = (
            select(EmailAccount)
            .where(EmailAccount.is_active == True)  # noqa: E712
            .order_by(EmailAccount.priority)
        )
        return list(self._session.execute(stmt).scalars().all())

    def update(
        self,
        account_id: int,
        display_name: str | None = None,
        imap_server: str | None = None,
        imap_port: int | None = None,
        credential_reference: str | None = None,
        priority: int | None = None,
    ) -> EmailAccount:
        """Update an email account.

        Args:
            account_id: The email account ID.
            display_name: New display name (None to keep current).
            imap_server: New IMAP server (None to keep current).
            imap_port: New IMAP port (None to keep current).
            credential_reference: New credential reference (None to keep current).
            priority: New priority (None to keep current).

        Returns:
            The updated EmailAccount.

        Raises:
            EmailAccountNotFoundError: If account doesn't exist.
        """
        account = self.get(account_id)

        if display_name is not None:
            account.display_name = display_name
        if imap_server is not None:
            account.imap_server = imap_server
        if imap_port is not None:
            account.imap_port = imap_port
        if credential_reference is not None:
            account.credential_reference = credential_reference
        if priority is not None:
            account.priority = priority

        return account

    def activate(self, account_id: int) -> EmailAccount:
        """Activate an email account.

        Args:
            account_id: The email account ID.

        Returns:
            The activated EmailAccount.

        Raises:
            EmailAccountNotFoundError: If account doesn't exist.
        """
        account = self.get(account_id)
        account.is_active = True
        return account

    def deactivate(self, account_id: int) -> EmailAccount:
        """Deactivate an email account.

        Args:
            account_id: The email account ID.

        Returns:
            The deactivated EmailAccount.

        Raises:
            EmailAccountNotFoundError: If account doesn't exist.
        """
        account = self.get(account_id)
        account.is_active = False
        return account

    def delete(self, account_id: int) -> None:
        """Delete an email account.

        Args:
            account_id: The email account ID.

        Raises:
            EmailAccountNotFoundError: If account doesn't exist.
        """
        account = self.get(account_id)
        self._session.delete(account)
