"""Interactive cold-start rule bootstrap.

Discovers CEL cohorts on stored transactions, asks the LLM to propose a
category per cohort, and walks the operator through the largest groups first
(with running coverage). Confirmed cohorts become active CEL rules; nothing
is created without confirmation.

    python -m finance_api.scripts.bootstrap_rules [--top-n 100]
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import select

from finance_api.classification.bootstrap import (
    ClusterCategoryProposer,
    build_proposals,
    proposal_coverage,
    resolve_choice,
)
from finance_api.classification.db_sources import apply_proposals
from finance_api.classification.gatherers.llm_inference import CategoryRef
from finance_api.classification.llm import LiteLLMClient
from finance_api.db.session import SessionLocal
from finance_api.models.category import Category
from finance_api.models.transaction import Transaction


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

        proposer = ClusterCategoryProposer(LiteLLMClient(), categories)
        proposals = build_proposals(transactions, proposer, top_n=args.top_n)
        coverage = proposal_coverage(proposals, total=len(transactions))
        print(
            f"{len(transactions)} transactions. "
            f"Top {coverage.cluster_count} cohorts cover "
            f"{coverage.covered}/{coverage.total} ({coverage.fraction:.0%}).\n"
            "Per cohort: [Enter]=confirm  <id>=use that category  s=skip\n"
        )

        confirmed = []
        for proposal in proposals:
            print(
                f"--- {proposal.cluster_key}  "
                f"({proposal.transaction_count} txns) ---"
            )
            for sample in proposal.sample_descriptions[:3]:
                print(f"    {sample}")
            print(f"  CEL: {proposal.suggested_pattern}")
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
