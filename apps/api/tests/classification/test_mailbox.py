"""Tests for the provider-agnostic multi-mailbox search (receipt-evidence-retrieval spec).

The search layer builds a merchant + date-window query, fans out across all
household mailboxes, widens the window once if nothing is found, and returns
candidates tagged by mailbox. Concrete Gmail/Outlook clients plug in behind the
MailboxClient interface.
"""

from datetime import date
from decimal import Decimal

from finance_api.classification.gatherer import GatherContext
from finance_api.classification.gatherers.mailbox import (
    MultiMailboxSource,
    RawEmail,
    merchant_terms,
)


class _FakeClient:
    """Records the windows it was queried with and returns canned emails."""

    def __init__(self, mailbox_id: str, emails: list[RawEmail]) -> None:
        self.mailbox_id = mailbox_id
        self._emails = emails
        self.queries: list[tuple[date, date]] = []

    def search(self, terms: list[str], since: date, until: date) -> list[RawEmail]:
        self.queries.append((since, until))
        # Only return emails that fall inside the queried window.
        return [e for e in self._emails if since <= e.date <= until]


def _context() -> GatherContext:
    return GatherContext(
        transaction_id=1,
        description="AMZN MKTP*RT4 LONDON",
        amount=Decimal("20.00"),
        currency="GBP",
        transaction_date=date(2026, 6, 10),
    )


def _email(mailbox: str, mid: str, d: date) -> RawEmail:
    return RawEmail(
        message_id=mid,
        mailbox=mailbox,
        subject="Your Amazon order",
        body="Order total GBP 20.00",
        date=d,
    )


class TestMerchantTerms:
    def test_extracts_alpha_tokens_dropping_noise(self) -> None:
        terms = merchant_terms("AMZN MKTP*RT4 LONDON")
        assert "AMZN" in terms
        assert "LONDON" in terms
        # numeric / short noise tokens dropped
        assert "RT4" not in terms


class TestMultiMailboxSource:
    def test_aggregates_candidates_across_mailboxes(self) -> None:
        gmail = _FakeClient("gmail:me", [_email("gmail:me", "g1", date(2026, 6, 9))])
        outlook = _FakeClient(
            "outlook:me", [_email("outlook:me", "o1", date(2026, 6, 11))]
        )
        source = MultiMailboxSource([gmail, outlook], window_days=5)
        candidates = source.find_candidates(_context())
        mailboxes = {c.mailbox for c in candidates}
        assert mailboxes == {"gmail:me", "outlook:me"}
        # candidate text combines subject + body
        assert "Amazon order" in candidates[0].text
        assert "20.00" in candidates[0].text

    def test_searches_within_default_window(self) -> None:
        gmail = _FakeClient("gmail:me", [])
        MultiMailboxSource([gmail], window_days=5).find_candidates(_context())
        since, until = gmail.queries[0]
        assert since == date(2026, 6, 5)
        assert until == date(2026, 6, 15)

    def test_widens_window_once_when_empty(self) -> None:
        # email is outside the narrow window but inside the wide one
        gmail = _FakeClient("gmail:me", [_email("gmail:me", "g1", date(2026, 6, 1))])
        source = MultiMailboxSource([gmail], window_days=5, wide_window_days=14)
        candidates = source.find_candidates(_context())
        assert len(gmail.queries) == 2  # narrow, then widened
        assert candidates and candidates[0].message_id == "g1"

    def test_returns_empty_when_nothing_found_even_after_widening(self) -> None:
        gmail = _FakeClient("gmail:me", [_email("gmail:me", "g1", date(2025, 1, 1))])
        source = MultiMailboxSource([gmail], window_days=5, wide_window_days=14)
        assert source.find_candidates(_context()) == []
