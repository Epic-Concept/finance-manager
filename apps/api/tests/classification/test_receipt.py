"""Tests for receipt extraction and reconciliation banding (receipt-evidence-retrieval spec)."""

from decimal import Decimal

import pytest

from finance_api.classification.evidence import StrengthTier
from finance_api.classification.gatherers.llm_inference import CategoryRef
from finance_api.classification.receipt import (
    ReceiptExtractionError,
    ReceiptExtractor,
    reconciliation_tier,
)


class _FakeClient:
    def __init__(self, reply: str) -> None:
        self._reply = reply

    def complete(self, system: str, user: str) -> str:
        return self._reply


CATEGORIES = [CategoryRef(5, "Books"), CategoryRef(6, "Toys"), CategoryRef(7, "Cables")]


class TestReconciliationTier:
    def test_within_tolerance_is_proof(self) -> None:
        assert (
            reconciliation_tier(Decimal("20.00"), Decimal("20.00"))
            is StrengthTier.PROOF
        )

    def test_moderate_mismatch_is_strong(self) -> None:
        # 5% off -> within the moderate band
        assert (
            reconciliation_tier(Decimal("21.00"), Decimal("20.00"))
            is StrengthTier.STRONG
        )

    def test_large_mismatch_is_weak(self) -> None:
        # 25% off -> wrong receipt
        assert (
            reconciliation_tier(Decimal("25.00"), Decimal("20.00")) is StrengthTier.WEAK
        )

    def test_zero_transaction_total_is_weak(self) -> None:
        assert reconciliation_tier(Decimal("5.00"), Decimal("0")) is StrengthTier.WEAK


class TestReceiptExtractor:
    def test_extracts_items_with_categories(self) -> None:
        reply = (
            '{"merchant": "Amazon", "currency": "GBP", "items": ['
            '{"description": "Python book", "amount": 12.00, "category_id": 5},'
            '{"description": "USB cable", "amount": 8.00, "category_id": 7}]}'
        )
        receipt = ReceiptExtractor(_FakeClient(reply)).extract(
            "order email", CATEGORIES
        )
        assert receipt.merchant == "Amazon"
        assert receipt.currency == "GBP"
        assert len(receipt.items) == 2
        assert receipt.items[0].amount == Decimal("12.00")
        assert receipt.items[0].category_id == 5
        assert receipt.items_total == Decimal("20.00")

    def test_reasoning_preamble_and_fences_tolerated(self) -> None:
        reply = (
            "Let me extract this.\n```json\n"
            '{"merchant": "X", "currency": "GBP", "items": ['
            '{"description": "thing", "amount": 5.0, "category_id": 6}]}\n```'
        )
        receipt = ReceiptExtractor(_FakeClient(reply)).extract("e", CATEGORIES)
        assert receipt.items_total == Decimal("5.0")

    def test_unparseable_reply_raises(self) -> None:
        with pytest.raises(ReceiptExtractionError):
            ReceiptExtractor(_FakeClient("no json here")).extract("e", CATEGORIES)
