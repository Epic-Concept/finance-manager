"""Tests for the evidence collection loop (transaction-classification spec).

The loop runs gatherers cheapest-first, re-evaluating sufficiency after each,
stopping as soon as the policy can auto-apply, and routing to review when
gatherers are exhausted.
"""

from datetime import date
from decimal import Decimal

from finance_api.classification.evidence import (
    Claim,
    Evidence,
    EvidenceType,
    StrengthTier,
)
from finance_api.classification.gatherer import GatherContext, Gatherer
from finance_api.classification.loop import run_collection_loop
from finance_api.classification.policy import EvidencePolicy, MerchantClass, Outcome


def _context() -> GatherContext:
    return GatherContext(
        transaction_id=1,
        description="TFL TRAVEL",
        amount=Decimal("2.80"),
        currency="GBP",
        transaction_date=date(2026, 6, 1),
    )


class _SpyGatherer(Gatherer):
    produced_types = frozenset({EvidenceType.RULE})

    def __init__(self, evidence: list[Evidence]) -> None:
        self._evidence = evidence
        self.calls = 0

    def gather(self, context: GatherContext) -> list[Evidence]:
        self.calls += 1
        return list(self._evidence)


def _strong(category: int) -> Evidence:
    return Evidence(
        claim=Claim.single_category(category),
        evidence_type=EvidenceType.RULE,
        source="rule#1",
        strength=StrengthTier.STRONG,
        itemized=False,
    )


class TestCollectionLoop:
    def test_stops_when_evidence_is_sufficient(self) -> None:
        cheap = _SpyGatherer([_strong(7)])
        expensive = _SpyGatherer([_strong(8)])
        decision = run_collection_loop(
            _context(),
            [cheap, expensive],
            MerchantClass.SINGLE_CATEGORY,
            EvidencePolicy(),
        )
        assert decision.outcome is Outcome.AUTO_APPLY
        assert decision.claim == Claim.single_category(7)
        assert cheap.calls == 1
        assert expensive.calls == 0  # costlier gatherer never invoked

    def test_invokes_next_gatherer_when_insufficient(self) -> None:
        empty = _SpyGatherer([])
        strong = _SpyGatherer([_strong(7)])
        decision = run_collection_loop(
            _context(),
            [empty, strong],
            MerchantClass.SINGLE_CATEGORY,
            EvidencePolicy(),
        )
        assert decision.outcome is Outcome.AUTO_APPLY
        assert empty.calls == 1
        assert strong.calls == 1

    def test_exhausted_gatherers_route_to_review(self) -> None:
        weak = Evidence(
            claim=Claim.single_category(7),
            evidence_type=EvidenceType.LLM_INFERENCE,
            source="llm",
            strength=StrengthTier.WEAK,
            itemized=False,
        )
        g1 = _SpyGatherer([])
        g2 = _SpyGatherer([weak])
        decision = run_collection_loop(
            _context(), [g1, g2], MerchantClass.SINGLE_CATEGORY, EvidencePolicy()
        )
        assert decision.outcome is Outcome.REVIEW
        assert g1.calls == 1 and g2.calls == 1
