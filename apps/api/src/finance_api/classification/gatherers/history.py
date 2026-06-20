"""The history gatherer: prior confirmed outcomes for a merchant.

Emits HISTORY evidence for the category a merchant has resolved to before.
Strength is consistency-based and intentionally conservative: a STRONG signal
requires unanimous outcomes, a minimum count, and at least one human-confirmed
outcome -- so the system never promotes a category purely from its own prior
auto-applied guesses (self-confirmation guard). Thresholds are constructor
parameters; the exact tier definitions are expected to be tuned later.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Protocol

from finance_api.classification.evidence import (
    Claim,
    Evidence,
    EvidenceType,
    StrengthTier,
)
from finance_api.classification.gatherer import GatherContext, Gatherer


@dataclass(frozen=True)
class HistoryOutcome:
    """A prior categorization outcome for a merchant."""

    category_id: int
    human_confirmed: bool = False


class HistorySource(Protocol):
    """Supplies prior outcomes for transactions resembling this one."""

    def outcomes_for(self, description: str) -> list[HistoryOutcome]: ...


class HistoryGatherer(Gatherer):
    """Emits HISTORY evidence for the dominant prior category of a merchant."""

    produced_types = frozenset({EvidenceType.HISTORY})

    def __init__(self, source: HistorySource, strong_min_count: int = 3) -> None:
        self._source = source
        self._strong_min_count = strong_min_count

    def gather(self, context: GatherContext) -> list[Evidence]:
        outcomes = self._source.outcomes_for(context.description or "")
        if not outcomes:
            return []

        counts = Counter(o.category_id for o in outcomes)
        dominant_category, dominant_count = counts.most_common(1)[0]
        total = len(outcomes)

        unanimous = dominant_count == total
        has_human_confirmation = any(o.human_confirmed for o in outcomes)
        is_strong = (
            unanimous and total >= self._strong_min_count and has_human_confirmation
        )
        strength = StrengthTier.STRONG if is_strong else StrengthTier.WEAK

        return [
            Evidence(
                claim=Claim.single_category(dominant_category),
                evidence_type=EvidenceType.HISTORY,
                source=f"history:{dominant_count}/{total}",
                strength=strength,
                itemized=False,
            )
        ]
