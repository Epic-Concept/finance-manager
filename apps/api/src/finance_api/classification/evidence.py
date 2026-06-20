"""The evidence model: typed evidence emitted by gatherers.

Implements the `evidence-model` capability. Every piece of information used in a
classification decision is a typed :class:`Evidence` object. Gatherers produce
evidence; they never make the final decision (that is the policy's job).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum, IntEnum


class StrengthTier(IntEnum):
    """Discrete, ordered evidence strength.

    Strength is expressed as tiers (not a continuous score compared to a
    threshold) so that decisions are explainable and the policy is a finite,
    testable table. Ordering: ``PROOF > STRONG > WEAK > NONE``.
    """

    NONE = 0
    WEAK = 1
    STRONG = 2
    PROOF = 3


class EvidenceType(Enum):
    """The kind of source that produced a piece of evidence."""

    RULE = "rule"
    HISTORY = "history"
    WEB_LOOKUP = "web_lookup"
    RECEIPT = "receipt"
    LLM_INFERENCE = "llm_inference"


@dataclass(frozen=True)
class Split:
    """One ``(category, amount)`` component of a categorization.

    ``amount`` is ``None`` for a single-category claim, where the amount is the
    whole transaction total and is filled in by the policy when the decision is
    applied.
    """

    category_id: int
    amount: Decimal | None = None


@dataclass(frozen=True)
class Claim:
    """A proposed categorization: one category, or an itemized split.

    Two claims are equal (and hash equal) when they describe the same
    categorization, so the policy can group evidence by the claim it supports.
    """

    splits: tuple[Split, ...]
    itemized: bool

    @classmethod
    def single_category(cls, category_id: int) -> Claim:
        """A claim assigning the whole transaction to one category."""
        return cls(splits=(Split(category_id=category_id),), itemized=False)

    @classmethod
    def split(cls, splits: list[Split]) -> Claim:
        """A claim splitting the transaction across categories (itemized)."""
        return cls(splits=tuple(splits), itemized=True)

    @property
    def category_ids(self) -> tuple[int, ...]:
        """The category ids referenced by this claim, in order."""
        return tuple(s.category_id for s in self.splits)


@dataclass(frozen=True)
class Evidence:
    """A typed piece of support for a claim.

    Gatherers emit ``Evidence`` and never decide; the policy combines evidence
    into a categorization.
    """

    claim: Claim
    evidence_type: EvidenceType
    source: str
    strength: StrengthTier
    itemized: bool
