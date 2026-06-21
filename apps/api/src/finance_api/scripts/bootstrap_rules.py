"""Interactive cold-start rule bootstrap.

Clusters the stored transactions, asks the LLM to propose a category per cluster,
and walks the operator through the largest clusters first (with running coverage).
Confirmed clusters become active rules; nothing is created without confirmation.

    python -m finance_api.scripts.bootstrap_rules [--top-n 100]
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import select

from finance_api.classification.bootstrap import (
    ClusterCategoryProposer,
    cluster_coverage,
    resolve_choice,
)
from finance_api.classification.db_sources import apply_proposals
from finance_api.classification.gatherers.llm_inference import CategoryRef
from finance_api.classification.llm import LiteLLMClient
from finance_api.db.session import SessionLocal
from finance_api.models.category import Category
from finance_api.models.transaction import Transaction
from finance_api.services.transaction_clustering_service import (
    TransactionClusteringService,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap classification rules.")
    parser.add_argument("--top-n", type=int, default=100)
    args = parser.parse_args()

    session = SessionLocal()
    try:
        transactions = list(session.scalars(select(Transaction)))
        categories = [
            CategoryRef(id=c.id, name=c.name) for c in session.scalars(select(Category))
        ]
        if not categories:
            print("No categories seeded. Run seed_categories first.", file=sys.stderr)
            return 1

        clustering = TransactionClusteringService()
        clusters = clustering.cluster_transactions(transactions)
        coverage = cluster_coverage(clusters, top_n=args.top_n)
        print(
            f"{len(transactions)} transactions in {len(clusters)} clusters. "
            f"Top {coverage.cluster_count} cover {coverage.covered}/{coverage.total} "
            f"({coverage.fraction:.0%}).\n"
            "Per cluster: [Enter]=confirm  <id>=use that category  s=skip\n"
        )

        proposer = ClusterCategoryProposer(LiteLLMClient(), categories)
        confirmed = []
        for cluster in clusters[: args.top_n]:
            proposal = proposer.propose(cluster)
            print(f"--- {cluster.cluster_key}  ({cluster.size} txns) ---")
            for sample in cluster.sample_descriptions[:3]:
                print(f"    {sample}")
            print(
                f"  proposed: {proposal.proposed_category_name} "
                f"(id={proposal.proposed_category_id}, {proposal.confidence})"
            )
            category_id = resolve_choice(input("  > "), proposal.proposed_category_id)
            if category_id is not None:
                confirmed.append((proposal, category_id))

        created = apply_proposals(session, confirmed)
        session.commit()
        print(f"\nCreated {created} rules from {len(confirmed)} confirmations.")
        return 0
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        session.rollback()
        print(f"bootstrap failed: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
