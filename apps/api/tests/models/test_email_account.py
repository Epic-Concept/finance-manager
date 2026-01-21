"""Tests for EmailAccount model."""

from finance_api.models.email_account import EmailAccount


def test_email_account_creation() -> None:
    """Test EmailAccount can be instantiated with required fields."""
    account = EmailAccount(
        email_address="test@example.com",
        provider="gmail",
    )

    assert account.email_address == "test@example.com"
    assert account.provider == "gmail"
    assert account.display_name is None
    assert account.imap_server is None
    # Note: defaults are applied at database level, not Python level
    assert account.credential_reference is None


def test_email_account_with_all_fields() -> None:
    """Test EmailAccount with all optional fields."""
    account = EmailAccount(
        email_address="work@company.com",
        display_name="Work Email",
        provider="outlook",
        imap_server="outlook.office365.com",
        imap_port=993,
        credential_reference="ENV:WORK_EMAIL_PASSWORD",
        is_active=True,
        priority=1,
    )

    assert account.email_address == "work@company.com"
    assert account.display_name == "Work Email"
    assert account.provider == "outlook"
    assert account.imap_server == "outlook.office365.com"
    assert account.imap_port == 993
    assert account.credential_reference == "ENV:WORK_EMAIL_PASSWORD"
    assert account.is_active is True
    assert account.priority == 1


def test_email_account_generic_imap() -> None:
    """Test EmailAccount with generic IMAP provider."""
    account = EmailAccount(
        email_address="user@custom.org",
        provider="imap_generic",
        imap_server="mail.custom.org",
        imap_port=143,
    )

    assert account.provider == "imap_generic"
    assert account.imap_server == "mail.custom.org"
    assert account.imap_port == 143


def test_email_account_repr() -> None:
    """Test EmailAccount string representation."""
    account = EmailAccount(
        id=1,
        email_address="test@example.com",
        provider="gmail",
    )

    assert repr(account) == "<EmailAccount(id=1, email='test@example.com', provider='gmail')>"


def test_email_account_table_name() -> None:
    """Test EmailAccount table configuration."""
    assert EmailAccount.__tablename__ == "email_accounts"
    assert EmailAccount.__table_args__[1]["schema"] == "finance"


def test_email_account_inactive() -> None:
    """Test EmailAccount can be deactivated."""
    account = EmailAccount(
        email_address="old@example.com",
        provider="gmail",
        is_active=False,
    )

    assert account.is_active is False
