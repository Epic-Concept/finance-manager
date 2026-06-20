"""Exhaustive invariant sweep over the evidence policy.

Rather than enumerate every scenario by hand, sweep merchant classes, tiers,
itemized-ness and evidence multiplicity, asserting the policy's invariants hold
for every combination (transaction-classification spec).
"""

import itertools
from decimal import Decimal

import pytest

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

POLICY = EvidencePolicy()
TIERS = [StrengthTier.NONE, StrengthTier.WEAK, StrengthTier.STRONG, StrengthTier.PROOF]


def _evidence(tier: StrengthTier, itemized: bool, source: str) -> Evidence:
    if itemized:
        claim = Claim.split([Split(1, Decimal("6")), Split(2, Decimal("4"))])
    else:
        claim = Claim.single_category(1)
    return Evidence(
        claim=claim,
        evidence_type=EvidenceType.RECEIPT if itemized else EvidenceType.HISTORY,
        source=source,
        strength=tier,
        itemized=itemized,
    )


@pytest.mark.parametrize(
    "merchant_class,tier,itemized,n",
    list(itertools.product(list(MerchantClass), TIERS, [False, True], [1, 3])),
)
def test_invariants_hold_for_every_combination(
    merchant_class: MerchantClass, tier: StrengthTier, itemized: bool, n: int
) -> None:
    evidence = [_evidence(tier, itemized, f"s{i}") for i in range(n)]

    d1 = POLICY.decide(list(evidence), merchant_class)
    d2 = POLICY.decide(list(evidence), merchant_class)
    assert d1 == d2, "policy must be deterministic"

    if d1.outcome is Outcome.AUTO_APPLY:
        is_split = itemized
        # never auto-apply below the required tier
        assert tier >= POLICY.required_tier(merchant_class, is_split)
        # a split is only auto-applied with itemized PROOF
        if is_split:
            assert tier is StrengthTier.PROOF
        # a splittable merchant never auto-applies a non-itemized claim
        if merchant_class is MerchantClass.SPLITTABLE:
            assert is_split


@pytest.mark.parametrize("merchant_class", list(MerchantClass))
def test_weak_never_accumulates_to_auto_apply(merchant_class: MerchantClass) -> None:
    claim = Claim.single_category(1)
    many_weak = [
        Evidence(
            claim=claim,
            evidence_type=EvidenceType.LLM_INFERENCE,
            source=f"s{i}",
            strength=StrengthTier.WEAK,
            itemized=False,
        )
        for i in range(10)
    ]
    d = POLICY.decide(many_weak, merchant_class)
    assert d.outcome is Outcome.REVIEW
    assert d.strength is StrengthTier.WEAK


@pytest.mark.parametrize(
    "tier", [StrengthTier.WEAK, StrengthTier.STRONG, StrengthTier.PROOF]
)
@pytest.mark.parametrize("merchant_class", list(MerchantClass))
def test_top_tier_disagreement_always_contested(
    tier: StrengthTier, merchant_class: MerchantClass
) -> None:
    a = Evidence(
        claim=Claim.single_category(1),
        evidence_type=EvidenceType.HISTORY,
        source="a",
        strength=tier,
        itemized=False,
    )
    b = Evidence(
        claim=Claim.single_category(2),
        evidence_type=EvidenceType.HISTORY,
        source="b",
        strength=tier,
        itemized=False,
    )
    d = POLICY.decide([a, b], merchant_class)
    assert d.outcome is Outcome.REVIEW
    assert d.reason == "contested"
