"""Tests for the LLM-inference gatherer (transaction-classification spec).

A bare LLM guess from the description alone is always WEAK and non-itemized.
The gatherer is tested with an injected fake client (no network).
"""

from datetime import date
from decimal import Decimal

from finance_api.classification.evidence import EvidenceType, StrengthTier
from finance_api.classification.gatherer import GatherContext
from finance_api.classification.gatherers.llm_inference import (
    CategoryRef,
    LLMInferenceGatherer,
)


class _FakeClient:
    def __init__(self, reply: str) -> None:
        self._reply = reply
        self.calls = 0

    def complete(self, system: str, user: str) -> str:
        self.calls += 1
        return self._reply


CATEGORIES = [CategoryRef(5, "Groceries"), CategoryRef(7, "Transport")]


def _context() -> GatherContext:
    return GatherContext(
        transaction_id=1,
        description="GREGGS 123",
        amount=Decimal("4.10"),
        currency="GBP",
        transaction_date=date(2026, 6, 1),
    )


class TestLLMInferenceGatherer:
    def test_valid_guess_emits_one_weak_evidence(self) -> None:
        gatherer = LLMInferenceGatherer(_FakeClient('{"category_id": 5}'), CATEGORIES)
        evidence = gatherer.gather(_context())
        assert len(evidence) == 1
        ev = evidence[0]
        assert ev.evidence_type is EvidenceType.LLM_INFERENCE
        assert ev.strength is StrengthTier.WEAK
        assert ev.itemized is False
        assert ev.claim.category_ids == (5,)

    def test_reasoning_preamble_and_fences_are_tolerated(self) -> None:
        reply = '\n\nHere is the answer:\n```json\n{"category_id": 7}\n```'
        gatherer = LLMInferenceGatherer(_FakeClient(reply), CATEGORIES)
        assert gatherer.gather(_context())[0].claim.category_ids == (7,)

    def test_category_not_in_allowed_set_emits_nothing(self) -> None:
        gatherer = LLMInferenceGatherer(_FakeClient('{"category_id": 999}'), CATEGORIES)
        assert gatherer.gather(_context()) == []

    def test_unparseable_reply_emits_nothing(self) -> None:
        gatherer = LLMInferenceGatherer(_FakeClient("I am not sure."), CATEGORIES)
        assert gatherer.gather(_context()) == []

    def test_client_error_emits_nothing(self) -> None:
        class _Boom:
            def complete(self, system: str, user: str) -> str:
                raise RuntimeError("endpoint down")

        gatherer = LLMInferenceGatherer(_Boom(), CATEGORIES)
        assert gatherer.gather(_context()) == []
