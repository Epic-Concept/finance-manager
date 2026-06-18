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
from dataclasses import dataclass

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
        pattern = f"(?i){re.escape(cluster.cluster_key)}"
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
    clustering: TransactionClusteringService,
    top_n: int = 100,
) -> list[ClusterProposal]:
    """Cluster transactions and propose categories for the largest N clusters."""
    clusters = clustering.cluster_transactions(list(transactions))  # type: ignore[arg-type]
    return [proposer.propose(cluster) for cluster in clusters[:top_n]]
