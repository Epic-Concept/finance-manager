"""The rule gatherer: deterministic CEL fast-path.

A rule is a CEL boolean over a typed transaction activation, mapped to a
category. A matched approved rule is the cheapest, highest-trust evidence
(non-itemized ``PROOF``). Rules are evaluated in priority order; the first
true result wins. Invalid expressions are skipped rather than fatal.

Legacy regex / ``description =~`` strings are migrated to CEL at evaluation
time so stored rules keep working through the cutover.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from finance_api.classification.cel import CelEvaluator, activation_from_context
from finance_api.classification.evidence import (
    Claim,
    Evidence,
    EvidenceType,
    StrengthTier,
)
from finance_api.classification.gatherer import GatherContext, Gatherer


@dataclass(frozen=True)
class RulePattern:
    """A CEL (or legacy regex) expression mapped to a category."""

    pattern: str
    category_id: int
    name: str
    requires_disambiguation: bool = False


class RuleSource(Protocol):
    """Supplies active rules in priority order (highest priority first)."""

    def active_rules(self) -> list[RulePattern]: ...


class RuleGatherer(Gatherer):
    """Emits PROOF evidence for the highest-priority matching CEL rule."""

    produced_types = frozenset({EvidenceType.RULE})

    def __init__(
        self, source: RuleSource, evaluator: CelEvaluator | None = None
    ) -> None:
        self._source = source
        self._evaluator = evaluator or CelEvaluator()

    def gather(self, context: GatherContext) -> list[Evidence]:
        activation = activation_from_context(context)
        for rule in self._source.active_rules():
            matched = self._evaluator.matches(rule.pattern, activation)
            if matched is None:
                continue
            if matched:
                return [
                    Evidence(
                        claim=Claim.single_category(rule.category_id),
                        evidence_type=EvidenceType.RULE,
                        source=f"rule:{rule.name}",
                        strength=StrengthTier.PROOF,
                        itemized=False,
                        requires_receipt=rule.requires_disambiguation,
                    )
                ]
        return []
