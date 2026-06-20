"""Live integration test for the Gmail IMAP client.

Skips unless Gmail IMAP credentials are configured, so the suite still runs
without secrets. Verifies the real connect -> resolve All-Mail -> search ->
parse path against the live mailbox.
"""

from datetime import date, timedelta

import pytest

from finance_api.classification.gatherers.imap_mailbox import ImapMailboxClient
from finance_api.core.config import settings


@pytest.fixture
def gmail_client() -> ImapMailboxClient:
    if not settings.gmail_imap_password:
        pytest.skip("GMAIL_IMAP_PASSWORD not configured")
    return ImapMailboxClient(
        mailbox_id=settings.gmail_imap_user,
        host=settings.gmail_imap_host,
        username=settings.gmail_imap_user,
        password=settings.gmail_imap_password,
        folder=settings.gmail_imap_folder,
        max_results=5,
    )


def test_search_connects_and_returns_parsed_emails(
    gmail_client: ImapMailboxClient,
) -> None:
    today = date(2026, 6, 18)
    emails = gmail_client.search(
        ["order", "receipt", "invoice"],
        today - timedelta(days=120),
        today + timedelta(days=1),
    )
    # Connection + All-Mail resolution + search worked; results are well-formed.
    assert isinstance(emails, list)
    for e in emails:
        assert e.mailbox == settings.gmail_imap_user
        assert e.subject is not None
        assert "=?" not in e.subject  # MIME-decoded, not raw-encoded
