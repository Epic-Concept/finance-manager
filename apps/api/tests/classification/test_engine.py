"""Tests for the classification engine (task 7.1).

The engine determines a merchant class (triage), runs the collection loop over
its gatherers, and returns the decision plus the merchant class used.
"""

from datetime import date
from decimal import Decimal

from finance_api.classification.engine import (
    ClassificationEngine,
    KeywordMerchantClassifier,
)
from finance_api.classification.evidence import (
    Claim,
    Evidence,
    EvidenceType,
    Split,
    StrengthTier,
)
from finance_api.classification.gatherer import GatherContext, Gatherer
from finance_api.classification.policy import EvidencePolicy, MerchantClass, Outcome


class _StaticGatherer(Gatherer):
    produced_types = frozenset({EvidenceType.RULE})

    def __init__(self, evidence: list[Evidence]) -> None:
        self._evidence = evidence

    def gather(self, context: GatherContext) -> list[Evidence]:
        return list(self._evidence)


def _ctx(description: str, amount: str = "20.00") -> GatherContext:
    return GatherContext(
        transaction_id=1,
        description=description,
        amount=Decimal(amount),
        currency="GBP",
        transaction_date=date(2026, 6, 1),
    )


def _rule_proof(category: int) -> Evidence:
    return Evidence(
        claim=Claim.single_category(category),
        evidence_type=EvidenceType.RULE,
        source="rule#1",
        strength=StrengthTier.PROOF,
        itemized=False,
    )


class TestKeywordMerchantClassifier:
    def test_known_splittable_keyword(self) -> None:
        clf = KeywordMerchantClassifier(["amazon", "allegro", "aliexpress"])
        assert clf.classify(_ctx("AMAZON MKTP")) is MerchantClass.SPLITTABLE

    def test_unknown_merchant_defaults_unknown(self) -> None:
        clf = KeywordMerchantClassifier(["amazon"])
        assert clf.classify(_ctx("CORNER CAFE")) is MerchantClass.UNKNOWN


class TestClassificationEngine:
    def test_rule_fast_path_auto_applies(self) -> None:
        engine = ClassificationEngine(
            gatherers=[_StaticGatherer([_rule_proof(7)])],
            policy=EvidencePolicy(),
            merchant_classifier=KeywordMerchantClassifier(["amazon"]),
        )
        outcome = engine.classify(_ctx("TFL TRAVEL"))
        assert outcome.decision.outcome is Outcome.AUTO_APPLY
        assert outcome.decision.claim == Claim.single_category(7)
        assert outcome.merchant_class is MerchantClass.UNKNOWN

    def test_splittable_merchant_without_itemized_goes_to_review(self) -> None:
        # A non-itemized rule claim at a splittable merchant must not auto-apply.
        engine = ClassificationEngine(
            gatherers=[_StaticGatherer([_rule_proof(7)])],
            policy=EvidencePolicy(),
            merchant_classifier=KeywordMerchantClassifier(["amazon"]),
        )
        outcome = engine.classify(_ctx("AMAZON MKTP"))
        assert outcome.merchant_class is MerchantClass.SPLITTABLE
        assert outcome.decision.outcome is Outcome.REVIEW

    def test_splittable_with_itemized_proof_auto_applies_split(self) -> None:
        split_claim = Claim.split(
            [Split(1, Decimal("12.00")), Split(2, Decimal("8.00"))]
        )
        receipt = Evidence(
            claim=split_claim,
            evidence_type=EvidenceType.RECEIPT,
            source="receipt",
            strength=StrengthTier.PROOF,
            itemized=True,
        )
        engine = ClassificationEngine(
            gatherers=[_StaticGatherer([receipt])],
            policy=EvidencePolicy(),
            merchant_classifier=KeywordMerchantClassifier(["amazon"]),
        )
        outcome = engine.classify(_ctx("AMAZON MKTP"))
        assert outcome.decision.outcome is Outcome.AUTO_APPLY
        assert outcome.decision.claim is split_claim

    def test_no_evidence_routes_to_review(self) -> None:
        engine = ClassificationEngine(
            gatherers=[_StaticGatherer([])],
            policy=EvidencePolicy(),
            merchant_classifier=KeywordMerchantClassifier([]),
        )
        outcome = engine.classify(_ctx("MYSTERY MERCHANT"))
        assert outcome.decision.outcome is Outcome.REVIEW
        assert outcome.decision.reason == "no_evidence"
