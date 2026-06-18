"""Shadow-mode runner (task 7.3).

Runs the classification engine over historical transactions with no side
effects and reports what *would* happen: auto-apply vs review (by reason) and
parity against the existing category assignments. This is the evidence gate
before the legacy classification path is removed (task 9.2).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Protocol

from finance_api.classification.engine import EngineOutcome
from finance_api.classification.gatherer import GatherContext
from finance_api.classification.policy import Outcome


class _Engine(Protocol):
    def classify(self, context: GatherContext) -> EngineOutcome: ...


@dataclass(frozen=True)
class ShadowItem:
    """A historical transaction to replay, with its existing category (if any)."""

    context: GatherContext
    current_category_id: int | None = None


@dataclass
class ShadowReport:
    total: int = 0
    auto_applied: int = 0
    review: int = 0
    by_reason: dict[str, int] = field(default_factory=dict)
    parity_total: int = 0
    parity_matches: int = 0

    @property
    def parity_rate(self) -> float:
        return self.parity_matches / self.parity_total if self.parity_total else 0.0


def run_shadow(engine: _Engine, items: Iterable[ShadowItem]) -> ShadowReport:
    """Replay items through the engine and summarize outcomes + parity."""
    report = ShadowReport()
    for item in items:
        report.total += 1
        outcome = engine.classify(item.context)
        decision = outcome.decision
        report.by_reason[decision.reason] = report.by_reason.get(decision.reason, 0) + 1

        if decision.outcome is Outcome.AUTO_APPLY:
            report.auto_applied += 1
            # Parity only makes sense for single-category auto-applies with a
            # known existing category to compare against.
            claim = decision.claim
            if (
                item.current_category_id is not None
                and claim is not None
                and not claim.itemized
            ):
                report.parity_total += 1
                if claim.category_ids[0] == item.current_category_id:
                    report.parity_matches += 1
        else:
            report.review += 1

    return report
