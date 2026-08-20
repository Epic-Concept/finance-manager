"""Provider-agnostic multi-mailbox receipt search (task 4.1).

Builds a merchant + date-window query, fans out across every household mailbox
behind the :class:`MailboxClient` interface, widens the window once if nothing
is found, and returns :class:`EmailCandidate` objects tagged by mailbox for the
:class:`ReceiptGatherer`. Concrete Gmail / Outlook clients implement
``MailboxClient``; this layer is transport- and auth-agnostic.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Protocol

from finance_api.classification.gatherer import GatherContext

# Tokens too short or non-alphabetic to be useful merchant search terms.
_MIN_TERM_LEN = 4
_ALPHA_TOKEN = re.compile(r"[A-Za-z]+")

_SCRIPT_STYLE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)
_TAG = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"\s+")

# Phrases that signal an actual receipt/order email rather than marketing.
_RECEIPT_KEYWORDS = (
    "receipt",
    "invoice",
    "order total",
    "order confirmation",
    "your order",
    "amount paid",
    "total paid",
    "tax invoice",
)


def _candidate_score(text: str, amount: Decimal | None) -> int:
    """Rank a candidate by how receipt-like it is (keywords + amount present)."""
    lowered = text.lower()
    score = sum(3 for keyword in _RECEIPT_KEYWORDS if keyword in lowered)
    if amount is not None and f"{amount:.2f}" in text:
        score += 5
    return score


def strip_html(content: str) -> str:
    """Reduce an HTML (or plain-text) email body to clean text for the LLM.

    Real receipt emails are mostly CSS/markup; the LLM should see the text only.
    """
    text = _SCRIPT_STYLE.sub(" ", content)
    text = _TAG.sub(" ", text)
    text = html.unescape(text)
    return _WHITESPACE.sub(" ", text).strip()


def merchant_terms(description: str) -> list[str]:
    """Extract usable merchant search terms from a transaction description."""
    tokens = _ALPHA_TOKEN.findall(description or "")
    seen: dict[str, None] = {}
    for token in tokens:
        if len(token) >= _MIN_TERM_LEN:
            seen.setdefault(token.upper(), None)
    return list(seen)


def amount_search_terms(amount: Decimal, currency: str = "") -> list[str]:
    """Build IMAP TEXT search terms for a transaction amount."""
    terms: list[str] = []
    normalized = f"{amount:.2f}"
    terms.append(normalized)
    if amount == amount.to_integral_value():
        terms.append(str(int(amount)))
    currency = (currency or "").strip().upper()
    if currency:
        terms.append(f"{normalized} {currency}")
        terms.append(f"{currency} {normalized}")
    seen: dict[str, None] = {}
    for term in terms:
        seen.setdefault(term, None)
    return list(seen)


def combined_search_terms(
    description: str, amount: Decimal, currency: str = ""
) -> list[str]:
    """Merchant + amount terms for a receipt search (deduplicated)."""
    seen: dict[str, None] = {}
    for term in merchant_terms(description) + amount_search_terms(amount, currency):
        seen.setdefault(term, None)
    return list(seen)


@dataclass(frozen=True)
class EmailCandidate:
    """A candidate receipt email found for a transaction."""

    text: str
    mailbox: str
    message_id: str


@dataclass(frozen=True)
class RawEmail:
    """A raw email returned by a mailbox client."""

    message_id: str
    mailbox: str
    subject: str
    body: str
    date: date
    sender: str = ""


class MailboxClient(Protocol):
    """A single household mailbox (Gmail or Outlook) that can be searched."""

    mailbox_id: str

    def search(self, terms: list[str], since: date, until: date) -> list[RawEmail]: ...


class MultiMailboxSource:
    """Searches several mailboxes for a transaction's receipt.

    Implements the ``MailboxSource`` protocol consumed by the receipt gatherer.
    """

    def __init__(
        self,
        clients: list[MailboxClient],
        window_days: int = 5,
        wide_window_days: int = 14,
    ) -> None:
        self._clients = clients
        self._window_days = window_days
        self._wide_window_days = wide_window_days

    @property
    def clients(self) -> list[MailboxClient]:
        """The mailbox clients searched by this source."""
        return list(self._clients)

    def _search_window(
        self, terms: list[str], center: date, days: int
    ) -> list[RawEmail]:
        since = center - timedelta(days=days)
        until = center + timedelta(days=days)
        results: list[RawEmail] = []
        for client in self._clients:
            results.extend(client.search(terms, since, until))
        return results

    def find_candidates(self, context: GatherContext) -> list[EmailCandidate]:
        terms = combined_search_terms(
            context.description, context.amount, context.currency
        )
        amount_only = amount_search_terms(context.amount, context.currency)
        center = context.transaction_date

        emails = self._search_window(terms, center, self._window_days)
        if not emails and amount_only:
            emails = self._search_window(amount_only, center, self._window_days)
        if not emails and self._wide_window_days > self._window_days:
            emails = self._search_window(terms, center, self._wide_window_days)
            if not emails and amount_only:
                emails = self._search_window(amount_only, center, self._wide_window_days)

        candidates = [
            EmailCandidate(
                text=strip_html(f"{e.subject}\n{e.body}"),
                mailbox=e.mailbox,
                message_id=e.message_id,
            )
            for e in emails
        ]
        # Most receipt-like first, so the gatherer tries the real receipt before
        # marketing/other noise. Stable sort preserves order within equal scores.
        candidates.sort(
            key=lambda c: _candidate_score(c.text, context.amount), reverse=True
        )
        return candidates
