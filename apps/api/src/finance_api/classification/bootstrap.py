"""Cold-start rule bootstrap.

There is no labelled baseline, so rules are bootstrapped by clustering the real
transactions and asking the LLM to propose a category per cluster (one call per
*cluster*, not per transaction). The human reviews the proposals; confirmed ones
become deterministic rules. This turns "label 1,933 rows" into "review ~100
pre-filled cluster guesses".
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, replace

from finance_api.classification.cel import migrate_rule_expression
from finance_api.classification.cohorts import CohortDiscovery
from finance_api.classification.gatherers.llm_inference import CategoryRef
from finance_api.classification.llm import LLMClient, extract_json
from finance_api.services.transaction_clustering_service import (
    TransactionCluster,
    TransactionClusteringService,
)

_SYSTEM = (
    "You categorize a cluster of similar bank transactions. Given sample "
    "descriptions and the allowed categories, choose the single best category. "
    'Respond ONLY with JSON {"category_id": <int>, "confidence": "high"|"medium"'
    '|"low"}.'
)


@dataclass(frozen=True)
class ClusterProposal:
    """An LLM-proposed category for a transaction cluster, awaiting confirmation."""

    cluster_key: str
    transaction_count: int
    sample_descriptions: tuple[str, ...]
    proposed_category_id: int | None
    proposed_category_name: str
    confidence: str
    suggested_pattern: str


class ClusterCategoryProposer:
    """Proposes a category for a transaction cluster using the LLM."""

    def __init__(self, client: LLMClient, categories: list[CategoryRef]) -> None:
        self._client = client
        self._categories = categories
        self._by_id = {c.id: c for c in categories}

    def _build_user_prompt(self, cluster: TransactionCluster) -> str:
        catalog = "\n".join(f"- {c.id}: {c.name}" for c in self._categories)
        samples = "\n".join(f"- {s}" for s in cluster.sample_descriptions)
        return (
            f"Cluster key: {cluster.cluster_key}\n"
            f"Sample transaction descriptions:\n{samples}\n\n"
            f"Allowed categories (id: name):\n{catalog}"
        )

    def propose(self, cluster: TransactionCluster) -> ClusterProposal:
        pattern = migrate_rule_expression(f"(?i){re.escape(cluster.cluster_key)}")
        category_id: int | None = None
        confidence = "low"
        try:
            data = extract_json(
                self._client.complete(_SYSTEM, self._build_user_prompt(cluster))
            )
            raw_id = data.get("category_id")
            if isinstance(raw_id, int) and raw_id in self._by_id:
                category_id = raw_id
            confidence = str(data.get("confidence", "low"))
        except Exception:  # noqa: BLE001 - any failure leaves the proposal unresolved
            pass

        name = self._by_id[category_id].name if category_id is not None else ""
        return ClusterProposal(
            cluster_key=cluster.cluster_key,
            transaction_count=len(cluster.transactions),
            sample_descriptions=tuple(cluster.sample_descriptions),
            proposed_category_id=category_id,
            proposed_category_name=name,
            confidence=confidence,
            suggested_pattern=pattern,
        )


def build_proposals(
    transactions: Sequence[object],
    proposer: ClusterCategoryProposer,
    clustering: TransactionClusteringService | None = None,
    top_n: int = 100,
) -> list[ClusterProposal]:
    """Discover CEL cohorts and propose a category per cohort.

    Hierarchical clustering + template CEL replace first-token regex proposals.
    The LLM still only chooses a category (one call per cohort).
    """
    min_size = 2
    if clustering is not None:
        min_size = max(1, int(getattr(clustering, "_min_cluster_size", 2)))
    discovery = CohortDiscovery(
        list(transactions), list(transactions), min_size=min_size
    )
    out: list[ClusterProposal] = []
    for cohort in discovery.proposals(top_n=top_n):
        cluster = TransactionCluster(
            cluster_key=cohort.cluster_key,
            cluster_hash=cohort.cohort_id,
            transactions=[object()] * len(cohort.transaction_ids),  # type: ignore[list-item]
            sample_descriptions=list(cohort.sample_descriptions),
        )
        proposed = proposer.propose(cluster)
        out.append(replace(proposed, suggested_pattern=cohort.expression))
    return out


@dataclass(frozen=True)
class CoverageReport:
    """How many transactions the selected (top-N) clusters account for."""

    covered: int
    total: int
    cluster_count: int

    @property
    def fraction(self) -> float:
        return self.covered / self.total if self.total else 0.0


def cluster_coverage(
    clusters: Sequence[TransactionCluster], top_n: int | None = None
) -> CoverageReport:
    """Report the share of transactions covered by the largest ``top_n`` clusters.

    Lets the operator weigh labelling effort vs. coverage before confirming
    (e.g. "the top 100 clusters cover 74% of transactions").
    """
    total = sum(c.size for c in clusters)
    selected = list(clusters) if top_n is None else list(clusters)[:top_n]
    covered = sum(c.size for c in selected)
    return CoverageReport(covered=covered, total=total, cluster_count=len(selected))


def proposal_coverage(
    proposals: Sequence[ClusterProposal], total: int
) -> CoverageReport:
    """Share of the residual covered by the current cohort proposals."""
    covered = sum(p.transaction_count for p in proposals)
    return CoverageReport(
        covered=covered, total=total, cluster_count=len(proposals)
    )


def resolve_choice(raw: str, proposed_category_id: int | None) -> int | None:
    """Interpret an operator's bootstrap response into a category id (or skip).

    - blank / "y" -> confirm the proposed category
    - "s" / "n"   -> skip (no rule)
    - a number    -> override with that category id
    Returns the chosen category id, or ``None`` to skip.
    """
    choice = raw.strip().lower()
    if choice in ("s", "n", "skip"):
        return None
    if choice in ("", "y", "yes"):
        return proposed_category_id
    if choice.lstrip("-").isdigit():
        return int(choice)
    return None
