"""Interactive rule discovery CLI for building classification rules."""

import argparse
import json

from finance_api.db.session import SessionLocal
from finance_api.models.category import Category
from finance_api.models.transaction import Transaction
from finance_api.models.transaction_category import TransactionCategory
from finance_api.repositories.category_repository import CategoryRepository
from finance_api.repositories.classification_rule_repository import (
    ClassificationRuleRepository,
)
from finance_api.repositories.rule_proposal_repository import RuleProposalRepository
from finance_api.services.rule_discovery_service import (
    RuleDiscoveryError,
    RuleDiscoveryService,
)
from finance_api.services.rule_validation_service import RuleValidationService
from finance_api.services.transaction_clustering_service import (
    TransactionCluster,
    TransactionClusteringService,
)


def get_uncategorized_transactions(db) -> list[Transaction]:  # type: ignore[no-untyped-def]
    """Get all transactions without a category."""
    categorized_ids = (
        db.query(TransactionCategory.transaction_id)
        .filter(TransactionCategory.category_id.isnot(None))
        .all()
    )
    categorized_id_set = {r[0] for r in categorized_ids}

    all_txns = db.query(Transaction).all()
    return [t for t in all_txns if t.id not in categorized_id_set]


def display_cluster(
    cluster: TransactionCluster, cluster_num: int, total_clusters: int
) -> None:
    """Display cluster information."""
    print()
    print("=" * 60)
    print(
        f"=== Cluster #{cluster_num}/{total_clusters}: {cluster.size} transactions ==="
    )
    print(f"Cluster key: {cluster.cluster_key}")
    print()
    print("Sample descriptions:")
    for sample in cluster.sample_descriptions:
        print(f"  - {sample}")


def display_proposal(
    pattern: str,
    category_name: str,
    confidence: str,
    reasoning: str,
    validation,  # type: ignore[no-untyped-def]
) -> None:
    """Display the LLM proposal and validation results."""
    print()
    print("-" * 40)
    print("LLM Proposal:")
    print(f"  Pattern: {pattern}")
    print(f"  Category: {category_name}")
    print(f"  Confidence: {confidence}")
    print(f"  Reasoning: {reasoning}")
    print()
    print("Validation Results:")
    print(f"  Matches: {validation.total_matches}")
    print(f"  True Positives: {validation.true_positives}")
    print(f"  False Positives: {validation.false_positives}")
    print(f"  Precision: {float(validation.precision) * 100:.1f}%")
    print(f"  Coverage: {float(validation.coverage) * 100:.1f}%")

    if validation.sample_false_positives:
        print()
        print("Sample False Positives:")
        for fp in validation.sample_false_positives[:3]:
            print(f"  - {fp}")


def get_user_action() -> str:
    """Get user action from interactive prompt."""
    print()
    action = input("[A]ccept  [M]odify  [R]eject  [S]kip  [Q]uit: ").strip().upper()
    return action


def get_modified_pattern() -> str:
    """Get a modified pattern from the user."""
    return input("Enter modified pattern: ").strip()


def find_category_by_name(categories: list[Category], name: str) -> Category | None:
    """Find a category by name (case-insensitive)."""
    name_lower = name.lower()
    for cat in categories:
        if cat.name.lower() == name_lower:
            return cat
    return None


def run_discovery(
    analyze_only: bool = False,
    resume: bool = False,
    min_cluster_size: int = 5,
    max_clusters: int | None = None,
) -> None:
    """Run the interactive rule discovery workflow.

    Args:
        analyze_only: If True, only show clustering analysis (no LLM).
        resume: If True, continue from pending proposals.
        min_cluster_size: Minimum cluster size to process.
        max_clusters: Maximum number of clusters to process.
    """
    db = SessionLocal()
    try:
        # Initialize services and repositories
        clustering_service = TransactionClusteringService(
            min_cluster_size=min_cluster_size
        )
        validation_service = RuleValidationService()
        category_repo = CategoryRepository(db)
        rule_repo = ClassificationRuleRepository(db)
        proposal_repo = RuleProposalRepository(db)

        # Get all transactions and categories
        all_transactions = list(db.query(Transaction).all())
        uncategorized = get_uncategorized_transactions(db)
        categories = category_repo.get_all()

        print()
        print("=== Transaction Rule Discovery ===")
        print()
        print(f"Total transactions: {len(all_transactions)}")
        print(f"Uncategorized: {len(uncategorized)}")
        print(f"Categories available: {len(categories)}")
        print()

        if resume:
            # Resume from pending proposals
            pending = proposal_repo.get_pending_proposals()
            if not pending:
                print("No pending proposals to resume.")
                return

            print(f"Found {len(pending)} pending proposals to review.")
            # TODO: Implement resume workflow
            print("Resume workflow not yet implemented.")
            return

        # Cluster uncategorized transactions
        print("Clustering transactions...")
        clusters = clustering_service.cluster_transactions(uncategorized)
        stats = clustering_service.get_cluster_statistics(clusters, len(uncategorized))

        print(f"Found {stats.total_clusters} clusters")
        print(f"Coverage: {stats.coverage_percentage:.1f}%")
        print(f"Largest cluster: {stats.largest_cluster_size} transactions")
        print(f"Average cluster size: {stats.average_cluster_size:.1f}")

        if analyze_only:
            print()
            print("=== Cluster Analysis ===")
            for i, cluster in enumerate(clusters[:20], 1):
                print(f"\n{i}. {cluster.cluster_key}: {cluster.size} transactions")
                for sample in cluster.sample_descriptions[:3]:
                    print(f"   - {sample}")
            return

        # Initialize LLM service
        discovery_service = RuleDiscoveryService()

        # Process clusters
        clusters_to_process = clusters[:max_clusters] if max_clusters else clusters
        accepted_count = 0
        rejected_count = 0
        skipped_count = 0

        for i, cluster in enumerate(clusters_to_process, 1):
            # Check if we already have a proposal for this cluster
            existing = proposal_repo.get_by_cluster_hash(cluster.cluster_hash)
            if existing and existing.status in ("accepted", "rejected"):
                print(f"\nSkipping cluster {cluster.cluster_key} (already processed)")
                continue

            display_cluster(cluster, i, len(clusters_to_process))

            # Get LLM proposal
            print("\nProposing rule via LLM...")
            try:
                proposal_result = discovery_service.propose_rule(cluster, categories)
            except RuleDiscoveryError as e:
                print(f"Error: {e}")
                continue

            # Find the category
            category = find_category_by_name(categories, proposal_result.category_name)
            if not category:
                print(f"Warning: Category '{proposal_result.category_name}' not found")
                continue

            # Validate the rule
            cluster_ids = {t.id for t in cluster.transactions}
            validation = validation_service.test_rule(
                proposal_result.pattern, all_transactions, cluster_ids
            )

            if not validation.is_valid_regex:
                print(f"Invalid regex: {validation.regex_error}")
                continue

            display_proposal(
                proposal_result.pattern,
                proposal_result.category_name,
                proposal_result.confidence,
                proposal_result.reasoning,
                validation,
            )

            # Store proposal
            db_proposal = proposal_repo.create(
                cluster_hash=cluster.cluster_hash,
                cluster_size=cluster.size,
                sample_descriptions=json.dumps(cluster.sample_descriptions),
                proposed_pattern=proposal_result.pattern,
                proposed_category_id=category.id,
                llm_confidence=proposal_result.confidence,
                llm_reasoning=proposal_result.reasoning,
                validation_matches=validation.total_matches,
                validation_precision=validation.precision,
                validation_false_positives=(
                    json.dumps(validation.sample_false_positives)
                    if validation.sample_false_positives
                    else None
                ),
            )
            db.commit()

            # Get user action
            action = get_user_action()

            if action == "A":
                # Accept - create classification rule
                rule = rule_repo.create(
                    name=f"Auto: {cluster.cluster_key}",
                    rule_expression=f'description =~ "{proposal_result.pattern}"',
                    category_id=category.id,
                )
                proposal_repo.update_status(
                    db_proposal.id, "accepted", final_rule_id=rule.id
                )
                db.commit()
                accepted_count += 1
                print(f"✓ Rule created: {rule.name}")

            elif action == "M":
                # Modify pattern
                new_pattern = get_modified_pattern()
                if new_pattern:
                    # Re-validate with new pattern
                    new_validation = validation_service.test_rule(
                        new_pattern, all_transactions, cluster_ids
                    )
                    if new_validation.is_valid_regex:
                        display_proposal(
                            new_pattern,
                            proposal_result.category_name,
                            "modified",
                            "User-modified pattern",
                            new_validation,
                        )
                        confirm = input("Accept modified rule? [y/N]: ").strip().upper()
                        if confirm == "Y":
                            rule = rule_repo.create(
                                name=f"Auto: {cluster.cluster_key}",
                                rule_expression=f'description =~ "{new_pattern}"',
                                category_id=category.id,
                            )
                            proposal_repo.update_pattern(db_proposal.id, new_pattern)
                            proposal_repo.update_status(
                                db_proposal.id,
                                "modified",
                                final_rule_id=rule.id,
                                reviewer_notes="Pattern modified by user",
                            )
                            db.commit()
                            accepted_count += 1
                            print(f"✓ Modified rule created: {rule.name}")
                        else:
                            skipped_count += 1
                    else:
                        print(f"Invalid pattern: {new_validation.regex_error}")
                        skipped_count += 1

            elif action == "R":
                # Reject
                reason = input("Rejection reason (optional): ").strip()
                proposal_repo.update_status(
                    db_proposal.id, "rejected", reviewer_notes=reason or None
                )
                db.commit()
                rejected_count += 1
                print("✗ Proposal rejected")

            elif action == "S":
                # Skip (leave pending)
                skipped_count += 1
                print("→ Skipped")

            elif action == "Q":
                # Quit
                print("\nQuitting...")
                break

        print()
        print("=" * 60)
        print("=== Session Summary ===")
        print(f"Accepted: {accepted_count}")
        print(f"Rejected: {rejected_count}")
        print(f"Skipped: {skipped_count}")

    finally:
        db.close()


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Interactive rule discovery for transaction classification"
    )
    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="Only show clustering analysis, no LLM proposals",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from pending proposals",
    )
    parser.add_argument(
        "--min-cluster-size",
        type=int,
        default=5,
        help="Minimum cluster size to process (default: 5)",
    )
    parser.add_argument(
        "--max-clusters",
        type=int,
        default=None,
        help="Maximum number of clusters to process",
    )

    args = parser.parse_args()

    run_discovery(
        analyze_only=args.analyze_only,
        resume=args.resume,
        min_cluster_size=args.min_cluster_size,
        max_clusters=args.max_clusters,
    )


if __name__ == "__main__":
    main()
