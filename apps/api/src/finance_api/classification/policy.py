"""The deterministic evidence policy.

Implements the decision core of the `transaction-classification` capability:
given a pile of typed :class:`Evidence`, deterministically produce a decision to
auto-apply a categorization or route to human review.

Key rules:
- Strength combines by **max, not sum** (weak evidence never accumulates into a
  higher tier).
- Two claims tied at the top tier that disagree are **contested** -> review.
- A **split** claim requires itemized ``PROOF`` evidence (the itemized invariant).
- A **splittable** merchant is never auto-applied on non-itemized evidence.
- The **required-tier table** is the tunable risk dial, kept separate from the
  tier definitions (which live in the gatherers).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from finance_api.classification.evidence import Claim, Evidence, StrengthTier


class MerchantClass(Enum):
    """How a transaction's merchant is treated by the policy."""

    SINGLE_CATEGORY = "single_category"
    SPLITTABLE = "splittable"
    UNKNOWN = "unknown"


class Outcome(Enum):
    """The two possible policy outcomes."""

    AUTO_APPLY = "auto_apply"
    REVIEW = "review"


@dataclass(frozen=True)
class Decision:
    """The result of evaluating the policy over a set of evidence."""

    outcome: Outcome
    claim: Claim | None
    strength: StrengthTier
    reason: str
    evidence: tuple[Evidence, ...] = field(default_factory=tuple)


# The required-tier table: the tunable risk dial. Keyed by
# (merchant_class, claim_is_split). These thresholds are intentionally easy to
# change; the *meaning* of each tier lives in the gatherers, not here.
DEFAULT_REQUIRED_TIER: dict[tuple[MerchantClass, bool], StrengthTier] = {
    (MerchantClass.SINGLE_CATEGORY, False): StrengthTier.STRONG,
    (MerchantClass.SINGLE_CATEGORY, True): StrengthTier.PROOF,
    (MerchantClass.UNKNOWN, False): StrengthTier.STRONG,
    (MerchantClass.UNKNOWN, True): StrengthTier.PROOF,
    (MerchantClass.SPLITTABLE, False): StrengthTier.PROOF,
    (MerchantClass.SPLITTABLE, True): StrengthTier.PROOF,
}


class EvidencePolicy:
    """Maps collected evidence to a deterministic decision."""

    def __init__(
        self,
        required_tier_table: (
            dict[tuple[MerchantClass, bool], StrengthTier] | None
        ) = None,
    ) -> None:
        self._required = dict(required_tier_table or DEFAULT_REQUIRED_TIER)

    def required_tier(
        self, merchant_class: MerchantClass, is_split: bool
    ) -> StrengthTier:
        """The tier required to auto-apply, for this context."""
        return self._required[(merchant_class, is_split)]

    def decide(
        self, evidence: list[Evidence], merchant_class: MerchantClass
    ) -> Decision:
        """Return a deterministic decision for the given evidence."""
        usable = [e for e in evidence if e.strength > StrengthTier.NONE]
        if not usable:
            return Decision(Outcome.REVIEW, None, StrengthTier.NONE, "no_evidence")

        # Group by claim; each claim's tier is the MAX of its evidence (no sum).
        by_claim: dict[Claim, list[Evidence]] = {}
        for e in usable:
            by_claim.setdefault(e.claim, []).append(e)
        claim_tier = {
            claim: max(e.strength for e in evs) for claim, evs in by_claim.items()
        }

        top = max(claim_tier.values())
        top_claims = [claim for claim, tier in claim_tier.items() if tier == top]
        if len(top_claims) > 1:
            return Decision(Outcome.REVIEW, None, top, "contested")

        winning = top_claims[0]
        supporting = tuple(by_claim[winning])
        is_split = winning.itemized

        # Itemized invariant: a split claim needs itemized PROOF evidence.
        if is_split:
            has_itemized_proof = any(
                e.strength == StrengthTier.PROOF and e.itemized for e in supporting
            )
            if not has_itemized_proof:
                return Decision(
                    Outcome.REVIEW,
                    winning,
                    top,
                    "split_requires_itemized_proof",
                    supporting,
                )

        # A splittable merchant is never auto-applied on non-itemized evidence.
        if merchant_class is MerchantClass.SPLITTABLE and not is_split:
            return Decision(
                Outcome.REVIEW, winning, top, "splittable_requires_itemized", supporting
            )

        required = self.required_tier(merchant_class, is_split)
        if top >= required:
            return Decision(Outcome.AUTO_APPLY, winning, top, "sufficient", supporting)
        return Decision(
            Outcome.REVIEW, winning, top, "insufficient_evidence", supporting
        )
