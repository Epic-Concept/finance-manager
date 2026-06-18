"""Tests for the deterministic evidence policy (transaction-classification spec)."""

from decimal import Decimal

from finance_api.classification.evidence import (
    Claim,
    Evidence,
    EvidenceType,
    Split,
    StrengthTier,
)
from finance_api.classification.policy import (
    EvidencePolicy,
    MerchantClass,
    Outcome,
)


def _ev(
    claim: Claim,
    strength: StrengthTier,
    etype: EvidenceType = EvidenceType.RULE,
    itemized: bool = False,
    source: str = "src",
) -> Evidence:
    return Evidence(
        claim=claim,
        evidence_type=etype,
        source=source,
        strength=strength,
        itemized=itemized,
    )


SPLIT_CLAIM = Claim.split([Split(1, Decimal("12.00")), Split(2, Decimal("8.00"))])


class TestSingleCategory:
    def test_strong_single_category_auto_applies(self) -> None:
        policy = EvidencePolicy()
        d = policy.decide(
            [_ev(Claim.single_category(5), StrengthTier.STRONG, EvidenceType.HISTORY)],
            MerchantClass.SINGLE_CATEGORY,
        )
        assert d.outcome is Outcome.AUTO_APPLY
        assert d.claim == Claim.single_category(5)

    def test_weak_single_category_goes_to_review(self) -> None:
        policy = EvidencePolicy()
        d = policy.decide(
            [
                _ev(
                    Claim.single_category(5),
                    StrengthTier.WEAK,
                    EvidenceType.LLM_INFERENCE,
                )
            ],
            MerchantClass.SINGLE_CATEGORY,
        )
        assert d.outcome is Outcome.REVIEW


class TestSplittable:
    def test_reconciling_receipt_auto_applies_split(self) -> None:
        policy = EvidencePolicy()
        d = policy.decide(
            [_ev(SPLIT_CLAIM, StrengthTier.PROOF, EvidenceType.RECEIPT, itemized=True)],
            MerchantClass.SPLITTABLE,
        )
        assert d.outcome is Outcome.AUTO_APPLY
        assert d.claim is SPLIT_CLAIM

    def test_splittable_without_itemized_proof_goes_to_review(self) -> None:
        policy = EvidencePolicy()
        d = policy.decide(
            [_ev(Claim.single_category(5), StrengthTier.STRONG, EvidenceType.HISTORY)],
            MerchantClass.SPLITTABLE,
        )
        assert d.outcome is Outcome.REVIEW

    def test_split_claim_below_proof_goes_to_review(self) -> None:
        # An itemized claim that is only STRONG (e.g. receipt didn't reconcile)
        policy = EvidencePolicy()
        d = policy.decide(
            [
                _ev(
                    SPLIT_CLAIM,
                    StrengthTier.STRONG,
                    EvidenceType.RECEIPT,
                    itemized=True,
                )
            ],
            MerchantClass.SPLITTABLE,
        )
        assert d.outcome is Outcome.REVIEW


class TestCombination:
    def test_strongest_evidence_governs(self) -> None:
        policy = EvidencePolicy()
        proof_receipt = _ev(
            SPLIT_CLAIM, StrengthTier.PROOF, EvidenceType.RECEIPT, itemized=True
        )
        weak_web = _ev(
            Claim.single_category(9), StrengthTier.WEAK, EvidenceType.WEB_LOOKUP
        )
        d = policy.decide([weak_web, proof_receipt], MerchantClass.SPLITTABLE)
        assert d.outcome is Outcome.AUTO_APPLY
        assert d.claim is SPLIT_CLAIM

    def test_weak_evidence_does_not_accumulate_into_proof(self) -> None:
        policy = EvidencePolicy()
        claim = Claim.single_category(5)
        many_weak = [
            _ev(claim, StrengthTier.WEAK, EvidenceType.LLM_INFERENCE, source=f"s{i}")
            for i in range(5)
        ]
        d = policy.decide(many_weak, MerchantClass.SINGLE_CATEGORY)
        assert d.outcome is Outcome.REVIEW
        assert d.strength is StrengthTier.WEAK


class TestContested:
    def test_top_tier_disagreement_is_contested_review(self) -> None:
        policy = EvidencePolicy()
        a = _ev(Claim.single_category(5), StrengthTier.STRONG, EvidenceType.HISTORY)
        b = _ev(Claim.single_category(6), StrengthTier.STRONG, EvidenceType.HISTORY)
        d = policy.decide([a, b], MerchantClass.SINGLE_CATEGORY)
        assert d.outcome is Outcome.REVIEW
        assert d.reason == "contested"

    def test_lower_tier_disagreement_does_not_contest(self) -> None:
        policy = EvidencePolicy()
        strong = _ev(
            Claim.single_category(5), StrengthTier.STRONG, EvidenceType.HISTORY
        )
        weak_other = _ev(
            Claim.single_category(6), StrengthTier.WEAK, EvidenceType.LLM_INFERENCE
        )
        d = policy.decide([strong, weak_other], MerchantClass.SINGLE_CATEGORY)
        assert d.outcome is Outcome.AUTO_APPLY
        assert d.claim == Claim.single_category(5)


class TestNoEvidence:
    def test_no_evidence_goes_to_review(self) -> None:
        policy = EvidencePolicy()
        d = policy.decide([], MerchantClass.UNKNOWN)
        assert d.outcome is Outcome.REVIEW
        assert d.strength is StrengthTier.NONE


class TestItemizedInvariant:
    def test_non_itemized_evidence_cannot_auto_apply_a_split(self) -> None:
        # A split-shaped claim asserted only by non-itemized WEAK evidence.
        policy = EvidencePolicy()
        d = policy.decide(
            [
                _ev(
                    SPLIT_CLAIM,
                    StrengthTier.WEAK,
                    EvidenceType.LLM_INFERENCE,
                    itemized=False,
                )
            ],
            MerchantClass.SPLITTABLE,
        )
        assert d.outcome is Outcome.REVIEW


class TestDeterminism:
    def test_same_evidence_yields_same_decision(self) -> None:
        policy = EvidencePolicy()
        evidence = [
            _ev(Claim.single_category(5), StrengthTier.STRONG, EvidenceType.HISTORY)
        ]
        d1 = policy.decide(list(evidence), MerchantClass.SINGLE_CATEGORY)
        d2 = policy.decide(list(evidence), MerchantClass.SINGLE_CATEGORY)
        assert d1 == d2
