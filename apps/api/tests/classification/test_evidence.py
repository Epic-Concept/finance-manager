"""Tests for the evidence model (evidence-model spec)."""

from decimal import Decimal

from finance_api.classification.evidence import (
    Claim,
    Evidence,
    EvidenceType,
    Split,
    StrengthTier,
)


class TestStrengthTier:
    def test_tiers_are_ordered_proof_highest(self) -> None:
        assert (
            StrengthTier.PROOF
            > StrengthTier.STRONG
            > StrengthTier.WEAK
            > StrengthTier.NONE
        )


class TestClaim:
    def test_single_category_claim_is_not_itemized(self) -> None:
        claim = Claim.single_category(category_id=5)
        assert claim.itemized is False
        assert claim.category_ids == (5,)

    def test_split_claim_is_itemized(self) -> None:
        claim = Claim.split(
            [
                Split(category_id=1, amount=Decimal("12.00")),
                Split(category_id=2, amount=Decimal("8.00")),
            ]
        )
        assert claim.itemized is True
        assert claim.category_ids == (1, 2)

    def test_claims_with_same_categorization_are_equal(self) -> None:
        assert Claim.single_category(5) == Claim.single_category(5)

    def test_claims_with_different_categories_are_not_equal(self) -> None:
        assert Claim.single_category(5) != Claim.single_category(6)

    def test_claim_is_hashable_for_grouping(self) -> None:
        seen = {Claim.single_category(5), Claim.single_category(5)}
        assert len(seen) == 1


class TestEvidence:
    def test_evidence_carries_required_fields(self) -> None:
        ev = Evidence(
            claim=Claim.single_category(5),
            evidence_type=EvidenceType.RULE,
            source="rule#42",
            strength=StrengthTier.PROOF,
            itemized=False,
        )
        assert ev.claim.category_ids == (5,)
        assert ev.evidence_type is EvidenceType.RULE
        assert ev.source == "rule#42"
        assert ev.strength is StrengthTier.PROOF
        assert ev.itemized is False

    def test_bare_llm_inference_is_weak(self) -> None:
        ev = Evidence(
            claim=Claim.single_category(5),
            evidence_type=EvidenceType.LLM_INFERENCE,
            source="model@gb10",
            strength=StrengthTier.WEAK,
            itemized=False,
        )
        assert ev.strength is StrengthTier.WEAK
