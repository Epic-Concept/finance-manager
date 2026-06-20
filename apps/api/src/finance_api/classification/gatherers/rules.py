"""The rule gatherer: deterministic description-matching fast-path.

A rule is a regex over the transaction description mapped to a category. A
matched approved rule is the cheapest, highest-trust evidence (non-itemized
``PROOF``). Rules are evaluated in priority order; the first match wins, so rule
precedence is deterministic. Invalid patterns are skipped rather than fatal.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Protocol

from finance_api.classification.evidence import (
    Claim,
    Evidence,
    EvidenceType,
    StrengthTier,
)
from finance_api.classification.gatherer import GatherContext, Gatherer

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RulePattern:
    """A description-matching rule: a regex mapped to a category."""

    pattern: str
    category_id: int
    name: str


class RuleSource(Protocol):
    """Supplies active rules in priority order (highest priority first)."""

    def active_rules(self) -> list[RulePattern]: ...


class RuleGatherer(Gatherer):
    """Emits PROOF evidence for the highest-priority rule matching the description."""

    produced_types = frozenset({EvidenceType.RULE})

    def __init__(self, source: RuleSource) -> None:
        self._source = source

    def gather(self, context: GatherContext) -> list[Evidence]:
        description = context.description or ""
        for rule in self._source.active_rules():
            try:
                matched = re.search(rule.pattern, description) is not None
            except re.error as exc:
                logger.warning("skipping invalid rule '%s': %s", rule.name, exc)
                continue
            if matched:
                return [
                    Evidence(
                        claim=Claim.single_category(rule.category_id),
                        evidence_type=EvidenceType.RULE,
                        source=f"rule:{rule.name}",
                        strength=StrengthTier.PROOF,
                        itemized=False,
                    )
                ]
        return []
