"""Tests for IMAP session connection reuse."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

from finance_api.classification.gatherers.imap_mailbox import ImapMailboxClient
from finance_api.classification.gatherers.mailbox_session import imap_session


@patch("finance_api.classification.gatherers.imap_mailbox.imaplib.IMAP4_SSL")
def test_imap_session_reuses_one_connection_per_client(
    imap_cls: MagicMock,
) -> None:
    conn = MagicMock()
    imap_cls.return_value = conn
    conn.list.return_value = (None, [])
    conn.search.return_value = (None, [b""])

    client = ImapMailboxClient(
        mailbox_id="me@example.com",
        host="imap.gmail.com",
        username="me@example.com",
        password="secret",
    )
    with imap_session([client]):
        client.search(["AMAZON"], date(2026, 6, 1), date(2026, 6, 10))
        client.search(["20.00"], date(2026, 6, 1), date(2026, 6, 10))

    imap_cls.assert_called_once()
    conn.login.assert_called_once()
    assert conn.search.call_count == 2
    conn.logout.assert_called_once()
