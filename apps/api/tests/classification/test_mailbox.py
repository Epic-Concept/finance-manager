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
    strip_html,
)


class TestStripHtml:
    def test_removes_tags_and_keeps_text(self) -> None:
        assert strip_html("<p>Hello <b>world</b></p>") == "Hello world"

    def test_drops_style_and_script_blocks(self) -> None:
        html = "<style>p{color:red}</style><p>Order total GBP 15.00</p><script>x()</script>"
        assert strip_html(html) == "Order total GBP 15.00"

    def test_decodes_entities_and_collapses_whitespace(self) -> None:
        assert strip_html("<p>Tom &amp;  Jerry\n\n  shop</p>") == "Tom & Jerry shop"

    def test_plain_text_passes_through(self) -> None:
        assert strip_html("Order total GBP 20.00") == "Order total GBP 20.00"


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

    def test_receipt_like_candidate_is_ranked_first(self) -> None:
        # A marketing email and a real receipt both match; the receipt ranks first.
        marketing = RawEmail(
            "m1",
            "gmail:me",
            "Don't miss our sale!",
            "Big discounts this week. Unsubscribe here.",
            date(2026, 6, 9),
        )
        receipt = RawEmail(
            "m2",
            "gmail:me",
            "Your order receipt",
            "Order total GBP 20.00. Invoice attached.",
            date(2026, 6, 9),
        )
        gmail = _FakeClient("gmail:me", [marketing, receipt])
        candidates = MultiMailboxSource([gmail], window_days=5).find_candidates(
            _context()
        )
        assert candidates[0].message_id == "m2"  # the receipt, not the marketing email

    def test_candidate_text_is_html_stripped(self) -> None:
        html_email = RawEmail(
            message_id="g1",
            mailbox="gmail:me",
            subject="Your order",
            body="<style>x{}</style><p>Order total <b>GBP 20.00</b></p>",
            date=date(2026, 6, 9),
        )
        gmail = _FakeClient("gmail:me", [html_email])
        candidates = MultiMailboxSource([gmail], window_days=5).find_candidates(
            _context()
        )
        assert "Order total GBP 20.00" in candidates[0].text
        assert "<" not in candidates[0].text
