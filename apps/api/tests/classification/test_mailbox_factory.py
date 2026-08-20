"""Tests for mailbox client factory (EmailAccount DB + env fallback)."""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

from finance_api.classification.mailbox_factory import (
    build_mailbox_clients,
    resolve_credential,
)
from finance_api.repositories.email_account_repository import EmailAccountRepository


def _settings(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "gmail_imap_user": "",
        "gmail_imap_password": "",
        "gmail_imap_host": "imap.gmail.com",
        "gmail_imap_folder": "\\All",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_resolve_credential_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_MAIL_PASS", "secret")
    assert resolve_credential("ENV:TEST_MAIL_PASS", _settings()) == "secret"


def test_build_mailbox_clients_from_email_accounts(db_session: Session) -> None:
    repo = EmailAccountRepository(db_session)
    repo.create(
        email_address="wife@example.com",
        provider="gmail",
        credential_reference="ENV:WIFE_IMAP_PASS",
    )
    repo.create(
        email_address="husband@example.com",
        provider="gmail",
        credential_reference="ENV:HUSB_IMAP_PASS",
        priority=1,
    )
    os.environ["WIFE_IMAP_PASS"] = "w-pass"
    os.environ["HUSB_IMAP_PASS"] = "h-pass"
    try:
        clients = build_mailbox_clients(db_session, _settings())
    finally:
        os.environ.pop("WIFE_IMAP_PASS", None)
        os.environ.pop("HUSB_IMAP_PASS", None)

    assert len(clients) == 2
    assert {c.mailbox_id for c in clients} == {
        "wife@example.com",
        "husband@example.com",
    }


def test_build_mailbox_clients_falls_back_to_env_gmail(db_session: Session) -> None:
    clients = build_mailbox_clients(
        db_session,
        _settings(gmail_imap_user="solo@example.com", gmail_imap_password="solo-pass"),
    )
    assert len(clients) == 1
    assert clients[0].mailbox_id == "solo@example.com"
