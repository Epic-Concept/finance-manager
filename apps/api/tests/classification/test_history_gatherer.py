"""Tests for the history gatherer.

History strength is consistency-based, but STRONG requires at least one
human-confirmed outcome so the system never entrenches its own prior auto-applies
(the self-confirmation guard from the classification-learning spec).
"""

from datetime import date
from decimal import Decimal

from finance_api.classification.evidence import EvidenceType, StrengthTier
from finance_api.classification.gatherer import GatherContext
from finance_api.classification.gatherers.history import (
    HistoryGatherer,
    HistoryOutcome,
)


class _FakeHistorySource:
    def __init__(self, outcomes: list[HistoryOutcome]) -> None:
        self._outcomes = outcomes

    def outcomes_for(self, description: str) -> list[HistoryOutcome]:
        return list(self._outcomes)


def _context() -> GatherContext:
    return GatherContext(
        transaction_id=1,
        description="GREGGS 123",
        amount=Decimal("4.10"),
        currency="GBP",
        transaction_date=date(2026, 6, 1),
    )


def _outcomes(category: int, n: int, human: bool) -> list[HistoryOutcome]:
    return [
        HistoryOutcome(category_id=category, human_confirmed=human) for _ in range(n)
    ]


class TestHistoryGatherer:
    def test_consistent_human_confirmed_history_is_strong(self) -> None:
        gatherer = HistoryGatherer(
            _FakeHistorySource(_outcomes(8, 3, human=True)), strong_min_count=3
        )
        evidence = gatherer.gather(_context())
        assert len(evidence) == 1
        ev = evidence[0]
        assert ev.evidence_type is EvidenceType.HISTORY
        assert ev.strength is StrengthTier.STRONG
        assert ev.claim.category_ids == (8,)
        assert ev.itemized is False

    def test_consistent_but_never_human_confirmed_is_weak(self) -> None:
        gatherer = HistoryGatherer(
            _FakeHistorySource(_outcomes(8, 5, human=False)), strong_min_count=3
        )
        evidence = gatherer.gather(_context())
        assert evidence[0].strength is StrengthTier.WEAK

    def test_too_few_outcomes_is_weak(self) -> None:
        gatherer = HistoryGatherer(
            _FakeHistorySource(_outcomes(8, 2, human=True)), strong_min_count=3
        )
        assert gatherer.gather(_context())[0].strength is StrengthTier.WEAK

    def test_mixed_categories_is_weak_for_dominant(self) -> None:
        outcomes = _outcomes(8, 3, human=True) + _outcomes(9, 1, human=True)
        gatherer = HistoryGatherer(_FakeHistorySource(outcomes), strong_min_count=3)
        ev = gatherer.gather(_context())[0]
        assert ev.strength is StrengthTier.WEAK
        assert ev.claim.category_ids == (8,)

    def test_no_history_emits_nothing(self) -> None:
        gatherer = HistoryGatherer(_FakeHistorySource([]))
        assert gatherer.gather(_context()) == []
