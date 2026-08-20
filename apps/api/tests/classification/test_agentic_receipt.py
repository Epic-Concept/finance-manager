"""Tests for the agentic receipt gatherer.

The LLM drives the mailbox hunt: it composes search queries, reads candidate
emails, identifies the receipt, and extracts the itemized split. Tested with an
injected fake chat function and fake mailbox clients (no network).
"""

import json
from datetime import date
from decimal import Decimal

from finance_api.classification.evidence import EvidenceType, StrengthTier
from finance_api.classification.gatherer import GatherContext
from finance_api.classification.gatherers.agentic_receipt import (
    AgenticReceiptGatherer,
)
from finance_api.classification.gatherers.llm_inference import CategoryRef
from finance_api.classification.gatherers.mailbox import RawEmail

CATEGORIES = [CategoryRef(2, "Books"), CategoryRef(3, "Cables")]


class _FakeMailbox:
    def __init__(self, mailbox_id, emails):
        self.mailbox_id = mailbox_id
        self._emails = emails
        self.searches = []

    def search(self, terms, since, until):
        self.searches.append(terms)
        return [
            e
            for e in self._emails
            if any(t.lower() in (e.subject + e.body).lower() for t in terms)
        ]


def _chat(*messages):
    it = iter(messages)

    def chat(msgs, tools):
        return next(it)

    return chat


def _tool(name, args):
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "c",
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(args)},
            }
        ],
    }


def _final(payload):
    return {"role": "assistant", "content": json.dumps(payload), "tool_calls": None}


def _ctx(amount="20.00"):
    return GatherContext(
        transaction_id=1,
        description="AMZN MKTP",
        amount=Decimal(amount),
        currency="GBP",
        transaction_date=date(2026, 6, 10),
    )


RECEIPT_EMAIL = RawEmail(
    message_id="m1",
    mailbox="gmail:me",
    subject="Your Amazon order",
    body="Book GBP 12.00, Cable GBP 8.00, total GBP 20.00",
    date=date(2026, 6, 9),
    sender="auto-confirm@amazon.co.uk",
)


def _found_items():
    return _final(
        {
            "found": True,
            "merchant": "Amazon",
            "currency": "GBP",
            "items": [
                {"description": "Book", "amount": 12.00, "category_id": 2},
                {"description": "Cable", "amount": 8.00, "category_id": 3},
            ],
        }
    )


class TestAgenticReceiptGatherer:
    def test_agent_searches_reads_and_extracts_reconciling_receipt(self) -> None:
        mailbox = _FakeMailbox("gmail:me", [RECEIPT_EMAIL])
        chat = _chat(
            _tool("search_mailbox", {"query": "amazon order", "days": 7}),
            _tool("read_email", {"mailbox": "gmail:me", "id": "m1"}),
            _found_items(),
        )
        gatherer = AgenticReceiptGatherer(chat, [mailbox], CATEGORIES)
        evidence = gatherer.gather(_ctx("20.00"))
        assert len(evidence) == 1
        ev = evidence[0]
        assert ev.evidence_type is EvidenceType.RECEIPT
        assert ev.itemized is True
        assert ev.strength is StrengthTier.PROOF  # items sum 20.00 == charge
        assert sorted(s.amount for s in ev.claim.splits) == [
            Decimal("8.00"),
            Decimal("12.00"),
        ]
        assert mailbox.searches  # the agent actually searched the mailbox

    def test_agent_reports_not_found(self) -> None:
        mailbox = _FakeMailbox("gmail:me", [])
        chat = _chat(
            _tool("search_mailbox", {"query": "amazon", "days": 7}),
            _final({"found": False}),
        )
        gatherer = AgenticReceiptGatherer(chat, [mailbox], CATEGORIES)
        assert gatherer.gather(_ctx()) == []

    def test_non_reconciling_extraction_is_weak(self) -> None:
        mailbox = _FakeMailbox("gmail:me", [RECEIPT_EMAIL])
        chat = _chat(
            _tool("search_mailbox", {"query": "amazon", "days": 7}),
            _found_items(),  # items sum 20.00 but charge is 50.00 -> large mismatch
        )
        gatherer = AgenticReceiptGatherer(chat, [mailbox], CATEGORIES)
        ev = gatherer.gather(_ctx("50.00"))[0]
        assert ev.strength is StrengthTier.WEAK
        assert ev.itemized is True

    def test_read_email_returns_body_to_agent(self) -> None:
        # The read_email tool must surface the (stripped) body of a found email.
        mailbox = _FakeMailbox("gmail:me", [RECEIPT_EMAIL])
        captured = {}

        def chat(msgs, tools):
            # after a search + read, the tool result for read is in the messages
            for m in msgs:
                if m.get("role") == "tool" and "Book GBP 12.00" in (
                    m.get("content") or ""
                ):
                    captured["read_body_seen"] = True
            # drive: search, then read, then finish
            if not any(
                tc["function"]["name"] == "search_mailbox"
                for m in msgs
                if m.get("role") == "assistant" and m.get("tool_calls")
                for tc in m["tool_calls"]
            ):
                return _tool("search_mailbox", {"query": "amazon", "days": 7})
            if not captured.get("read_body_seen"):
                return _tool("read_email", {"mailbox": "gmail:me", "id": "m1"})
            return _final({"found": False})

        gatherer = AgenticReceiptGatherer(chat, [mailbox], CATEGORIES)
        gatherer.gather(_ctx())
        assert captured.get("read_body_seen") is True
