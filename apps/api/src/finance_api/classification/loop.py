"""The evidence collection loop.

Runs gatherers cheapest-first, re-evaluating the policy after each, and stops
as soon as the policy can auto-apply. If all gatherers are exhausted without a
sufficient decision, the final (review) decision is returned. Triage is simply
the first iteration of this loop, not a separate stage.
"""

from __future__ import annotations

from collections.abc import Sequence

from finance_api.classification.evidence import Evidence
from finance_api.classification.gatherer import GatherContext, Gatherer
from finance_api.classification.policy import (
    Decision,
    EvidencePolicy,
    MerchantClass,
    Outcome,
)


def run_collection_loop(
    context: GatherContext,
    gatherers: Sequence[Gatherer],
    merchant_class: MerchantClass,
    policy: EvidencePolicy,
) -> Decision:
    """Collect evidence until the policy can decide, or gatherers run out.

    Gatherers must be supplied in cheapest-first order. The loop stops invoking
    further (costlier) gatherers as soon as the policy reaches ``AUTO_APPLY``.
    """
    accumulated: list[Evidence] = []
    decision = policy.decide(accumulated, merchant_class)
    for gatherer in gatherers:
        accumulated.extend(gatherer.gather(context))
        decision = policy.decide(accumulated, merchant_class)
        if decision.outcome is Outcome.AUTO_APPLY:
            return decision
    return decision
