"""Tests for the receipt gatherer (receipt-evidence-retrieval spec).

Ties mailbox candidates -> LLM extraction -> reconciliation banding into itemized
RECEIPT evidence. Ambiguity (a plausible receipt in more than one mailbox)
degrades strength rather than guessing.
"""

from datetime import date
from decimal import Decimal

from finance_api.classification.evidence import EvidenceType, StrengthTier
from finance_api.classification.gatherer import GatherContext
from finance_api.classification.gatherers.llm_inference import CategoryRef
from finance_api.classification.gatherers.mailbox import EmailCandidate
from finance_api.classification.gatherers.receipt import (
    ReceiptGatherer,
)
from finance_api.classification.receipt import ReceiptExtractor

CATEGORIES = [CategoryRef(5, "Books"), CategoryRef(7, "Cables")]

_RECEIPT_JSON = (
    '{"merchant": "Amazon", "currency": "GBP", "items": ['
    '{"description": "book", "amount": 12.00, "category_id": 5},'
    '{"description": "cable", "amount": 8.00, "category_id": 7}]}'
)


class _FakeClient:
    def __init__(self, reply: str) -> None:
        self._reply = reply

    def complete(self, system: str, user: str) -> str:
        return self._reply


class _FakeMailbox:
    def __init__(self, candidates: list[EmailCandidate]) -> None:
        self._candidates = candidates

    def find_candidates(self, context: GatherContext) -> list[EmailCandidate]:
        return list(self._candidates)


def _context(amount: str) -> GatherContext:
    return GatherContext(
        transaction_id=1,
        description="AMZN MKTP",
        amount=Decimal(amount),
        currency="GBP",
        transaction_date=date(2026, 6, 1),
    )


def _gatherer(
    candidates: list[EmailCandidate], reply: str = _RECEIPT_JSON
) -> ReceiptGatherer:
    return ReceiptGatherer(
        _FakeMailbox(candidates), ReceiptExtractor(_FakeClient(reply)), CATEGORIES
    )


class TestReceiptGatherer:
    def test_reconciling_receipt_in_one_mailbox_is_itemized_proof(self) -> None:
        gatherer = _gatherer([EmailCandidate("order", "joint@x.com", "m1")])
        evidence = gatherer.gather(_context("20.00"))
        assert len(evidence) == 1
        ev = evidence[0]
        assert ev.evidence_type is EvidenceType.RECEIPT
        assert ev.itemized is True
        assert ev.strength is StrengthTier.PROOF
        assert ev.claim.itemized is True
        assert sorted(s.amount for s in ev.claim.splits) == [
            Decimal("8.00"),
            Decimal("12.00"),
        ]

    def test_ambiguous_receipt_in_two_mailboxes_is_degraded(self) -> None:
        gatherer = _gatherer(
            [
                EmailCandidate("order", "wife@x.com", "m1"),
                EmailCandidate("order", "husband@x.com", "m2"),
            ]
        )
        ev = gatherer.gather(_context("20.00"))[0]
        # would be PROOF on amount, but ambiguity caps it at STRONG
        assert ev.strength is StrengthTier.STRONG

    def test_large_mismatch_is_weak_but_still_itemized(self) -> None:
        ev = _gatherer([EmailCandidate("order", "joint@x.com", "m1")]).gather(
            _context("50.00")
        )[0]
        assert ev.strength is StrengthTier.WEAK
        assert ev.itemized is True

    def test_no_candidates_emits_nothing(self) -> None:
        assert _gatherer([]).gather(_context("20.00")) == []

    def test_extraction_failure_emits_nothing(self) -> None:
        gatherer = _gatherer(
            [EmailCandidate("order", "joint@x.com", "m1")], reply="not json"
        )
        assert gatherer.gather(_context("20.00")) == []
