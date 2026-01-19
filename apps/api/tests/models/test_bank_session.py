"""Tests for BankSession model."""

from datetime import datetime

from finance_api.models.bank_session import BankSession


def test_bank_session_creation() -> None:
    """Test BankSession can be instantiated with required fields."""
    session = BankSession(
        bank_key="test_bank",
        bank_name="Test Bank",
        session_id="sess_123",
        session_expires=datetime(2026, 12, 31, 23, 59, 59),
    )

    assert session.bank_key == "test_bank"
    assert session.bank_name == "Test Bank"
    assert session.session_id == "sess_123"
    assert session.session_expires == datetime(2026, 12, 31, 23, 59, 59)
    assert session.accounts is None


def test_bank_session_with_accounts() -> None:
    """Test BankSession with optional accounts field."""
    accounts_json = '{"accounts": [{"id": "acc1", "name": "Current"}]}'
    session = BankSession(
        bank_key="test_bank",
        bank_name="Test Bank",
        session_id="sess_123",
        session_expires=datetime(2026, 12, 31),
        accounts=accounts_json,
    )

    assert session.accounts == accounts_json


def test_bank_session_repr() -> None:
    """Test BankSession string representation."""
    session = BankSession(
        id=1,
        bank_key="test_bank",
        bank_name="Test Bank",
        session_id="sess_123",
        session_expires=datetime(2026, 12, 31),
    )

    assert repr(session) == "<BankSession(id=1, bank_key='test_bank')>"


def test_bank_session_table_name() -> None:
    """Test BankSession table configuration."""
    assert BankSession.__tablename__ == "bank_sessions"
    assert BankSession.__table_args__[1]["schema"] == "finance"
