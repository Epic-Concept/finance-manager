"""Tests for the gatherer contract (evidence-model spec).

Gatherers declare the evidence types they can produce, return Evidence, and
never make the final decision.
"""

from datetime import date
from decimal import Decimal

import pytest

from finance_api.classification.evidence import (
    Claim,
    Evidence,
    EvidenceType,
    StrengthTier,
)
from finance_api.classification.gatherer import GatherContext, Gatherer


def _context() -> GatherContext:
    return GatherContext(
        transaction_id=1,
        description="TESCO STORES 1234",
        amount=Decimal("10.00"),
        currency="GBP",
        transaction_date=date(2026, 6, 1),
        account_name="Joint Current",
    )


class _FakeGatherer(Gatherer):
    produced_types = frozenset({EvidenceType.RULE})

    def gather(self, context: GatherContext) -> list[Evidence]:
        return [
            Evidence(
                claim=Claim.single_category(7),
                evidence_type=EvidenceType.RULE,
                source="rule#1",
                strength=StrengthTier.PROOF,
                itemized=False,
            )
        ]


class TestGathererContract:
    def test_gatherer_declares_produced_types(self) -> None:
        assert _FakeGatherer().produced_types == frozenset({EvidenceType.RULE})

    def test_gather_returns_only_evidence(self) -> None:
        result = _FakeGatherer().gather(_context())
        assert result and all(isinstance(e, Evidence) for e in result)

    def test_gatherer_cannot_apply_a_decision(self) -> None:
        # The contract exposes only evidence production, never decision/apply.
        assert not hasattr(Gatherer, "decide")
        assert not hasattr(Gatherer, "apply")

    def test_subclass_must_implement_gather(self) -> None:
        class Incomplete(Gatherer):
            produced_types = frozenset()

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]
