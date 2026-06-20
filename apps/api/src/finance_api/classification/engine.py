"""The classification engine: triage + collection loop + outcome (task 7.1).

The gather/decide replacement for the old ClassificationOrchestrator. Given a
transaction context it determines a merchant class (triage), runs the
deterministic collection loop over its gatherers, and returns the decision plus
the merchant class used (needed to persist the decision).

The engine is pure (no persistence, no I/O of its own) so it can run in shadow
mode over historical transactions without side effects.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from finance_api.classification.gatherer import GatherContext, Gatherer
from finance_api.classification.loop import run_collection_loop
from finance_api.classification.policy import (
    Decision,
    EvidencePolicy,
    MerchantClass,
)


class MerchantClassifier(Protocol):
    """Triage: decide how a transaction's merchant should be treated."""

    def classify(self, context: GatherContext) -> MerchantClass: ...


class KeywordMerchantClassifier:
    """Marks merchants matching known multi-item keywords as splittable.

    A deliberately simple default; everything unmatched is ``UNKNOWN`` and left
    to the gatherers + policy. Single-category merchants are learned as rules
    over time rather than hard-coded here.
    """

    def __init__(self, splittable_keywords: Sequence[str]) -> None:
        self._splittable = [k.upper() for k in splittable_keywords]

    def classify(self, context: GatherContext) -> MerchantClass:
        description = (context.description or "").upper()
        if any(keyword in description for keyword in self._splittable):
            return MerchantClass.SPLITTABLE
        return MerchantClass.UNKNOWN


@dataclass(frozen=True)
class EngineOutcome:
    """The engine's result: the decision and the merchant class it used."""

    decision: Decision
    merchant_class: MerchantClass


class ClassificationEngine:
    """Coordinates triage, gathering, and the deterministic policy."""

    def __init__(
        self,
        gatherers: Sequence[Gatherer],
        policy: EvidencePolicy,
        merchant_classifier: MerchantClassifier,
    ) -> None:
        self._gatherers = gatherers
        self._policy = policy
        self._merchant_classifier = merchant_classifier

    def classify(self, context: GatherContext) -> EngineOutcome:
        merchant_class = self._merchant_classifier.classify(context)
        decision = run_collection_loop(
            context, self._gatherers, merchant_class, self._policy
        )
        return EngineOutcome(decision=decision, merchant_class=merchant_class)
