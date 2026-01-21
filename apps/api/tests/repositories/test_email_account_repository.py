"""Tests for EmailAccountRepository."""

import pytest
from sqlalchemy.orm import Session

from finance_api.repositories.email_account_repository import (
    EmailAccountNotFoundError,
    EmailAccountRepository,
)


class TestEmailAccountRepositoryCreate:
    """Tests for EmailAccountRepository.create()."""

    def test_create_gmail_account(self, db_session: Session) -> None:
        """Test creating a Gmail account."""
        repo = EmailAccountRepository(db_session)

        account = repo.create(
            email_address="test@gmail.com",
            provider="gmail",
            display_name="Personal Gmail",
        )
        db_session.flush()

        assert account.id is not None
        assert account.email_address == "test@gmail.com"
        assert account.provider == "gmail"
        assert account.display_name == "Personal Gmail"
        assert account.is_active is True

    def test_create_generic_imap_account(self, db_session: Session) -> None:
        """Test creating a generic IMAP account."""
        repo = EmailAccountRepository(db_session)

        account = repo.create(
            email_address="user@custom.org",
            provider="imap_generic",
            imap_server="mail.custom.org",
            imap_port=143,
            credential_reference="ENV:CUSTOM_EMAIL_PASS",
            priority=1,
        )
        db_session.flush()

        assert account.email_address == "user@custom.org"
        assert account.provider == "imap_generic"
        assert account.imap_server == "mail.custom.org"
        assert account.imap_port == 143
        assert account.credential_reference == "ENV:CUSTOM_EMAIL_PASS"
        assert account.priority == 1


class TestEmailAccountRepositoryGet:
    """Tests for EmailAccountRepository.get()."""

    def test_get_existing_account(self, db_session: Session) -> None:
        """Test getting an existing account by ID."""
        repo = EmailAccountRepository(db_session)
        created = repo.create(email_address="test@example.com", provider="gmail")
        db_session.flush()

        account = repo.get(created.id)

        assert account.id == created.id
        assert account.email_address == "test@example.com"

    def test_get_nonexistent_account(self, db_session: Session) -> None:
        """Test getting a non-existent account raises error."""
        repo = EmailAccountRepository(db_session)

        with pytest.raises(EmailAccountNotFoundError):
            repo.get(9999)


class TestEmailAccountRepositoryGetByEmail:
    """Tests for EmailAccountRepository.get_by_email()."""

    def test_get_by_email_existing(self, db_session: Session) -> None:
        """Test finding account by email address."""
        repo = EmailAccountRepository(db_session)
        created = repo.create(email_address="find@example.com", provider="outlook")
        db_session.flush()

        account = repo.get_by_email("find@example.com")

        assert account.id == created.id

    def test_get_by_email_nonexistent(self, db_session: Session) -> None:
        """Test finding non-existent email raises error."""
        repo = EmailAccountRepository(db_session)

        with pytest.raises(EmailAccountNotFoundError):
            repo.get_by_email("notfound@example.com")


class TestEmailAccountRepositoryGetActiveByPriority:
    """Tests for EmailAccountRepository.get_active_by_priority()."""

    def test_get_active_ordered_by_priority(self, db_session: Session) -> None:
        """Test getting active accounts in priority order."""
        repo = EmailAccountRepository(db_session)

        # Create accounts with different priorities
        acc1 = repo.create(email_address="low@example.com", provider="gmail", priority=10)
        acc2 = repo.create(email_address="high@example.com", provider="gmail", priority=0)
        acc3 = repo.create(email_address="mid@example.com", provider="gmail", priority=5)
        db_session.flush()

        accounts = repo.get_active_by_priority()

        assert len(accounts) == 3
        assert accounts[0].id == acc2.id  # priority 0
        assert accounts[1].id == acc3.id  # priority 5
        assert accounts[2].id == acc1.id  # priority 10

    def test_get_active_excludes_inactive(self, db_session: Session) -> None:
        """Test inactive accounts are excluded."""
        repo = EmailAccountRepository(db_session)

        active = repo.create(email_address="active@example.com", provider="gmail")
        inactive = repo.create(email_address="inactive@example.com", provider="gmail")
        db_session.flush()

        repo.deactivate(inactive.id)
        db_session.flush()

        accounts = repo.get_active_by_priority()

        assert len(accounts) == 1
        assert accounts[0].id == active.id


class TestEmailAccountRepositoryUpdate:
    """Tests for EmailAccountRepository.update()."""

    def test_update_display_name(self, db_session: Session) -> None:
        """Test updating display name."""
        repo = EmailAccountRepository(db_session)
        account = repo.create(
            email_address="update@example.com",
            provider="gmail",
            display_name="Old Name",
        )
        db_session.flush()

        updated = repo.update(account.id, display_name="New Name")

        assert updated.display_name == "New Name"

    def test_update_multiple_fields(self, db_session: Session) -> None:
        """Test updating multiple fields at once."""
        repo = EmailAccountRepository(db_session)
        account = repo.create(
            email_address="multi@example.com",
            provider="imap_generic",
            imap_server="old.server.com",
            priority=5,
        )
        db_session.flush()

        updated = repo.update(
            account.id,
            imap_server="new.server.com",
            imap_port=143,
            priority=1,
        )

        assert updated.imap_server == "new.server.com"
        assert updated.imap_port == 143
        assert updated.priority == 1


class TestEmailAccountRepositoryActivateDeactivate:
    """Tests for activate/deactivate methods."""

    def test_deactivate_account(self, db_session: Session) -> None:
        """Test deactivating an account."""
        repo = EmailAccountRepository(db_session)
        account = repo.create(email_address="deactivate@example.com", provider="gmail")
        db_session.flush()

        assert account.is_active is True

        repo.deactivate(account.id)

        assert account.is_active is False

    def test_activate_account(self, db_session: Session) -> None:
        """Test reactivating an account."""
        repo = EmailAccountRepository(db_session)
        account = repo.create(email_address="reactivate@example.com", provider="gmail")
        db_session.flush()

        repo.deactivate(account.id)
        assert account.is_active is False

        repo.activate(account.id)
        assert account.is_active is True


class TestEmailAccountRepositoryDelete:
    """Tests for EmailAccountRepository.delete()."""

    def test_delete_account(self, db_session: Session) -> None:
        """Test deleting an account."""
        repo = EmailAccountRepository(db_session)
        account = repo.create(email_address="delete@example.com", provider="gmail")
        db_session.flush()
        account_id = account.id

        repo.delete(account_id)
        db_session.flush()

        with pytest.raises(EmailAccountNotFoundError):
            repo.get(account_id)

    def test_delete_nonexistent_raises_error(self, db_session: Session) -> None:
        """Test deleting non-existent account raises error."""
        repo = EmailAccountRepository(db_session)

        with pytest.raises(EmailAccountNotFoundError):
            repo.delete(9999)
