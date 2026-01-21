"""Batch classification script with coverage reporting."""

import argparse
from datetime import datetime

from sqlalchemy import func

from finance_api.db.session import SessionLocal
from finance_api.models.category import Category
from finance_api.models.transaction import Transaction
from finance_api.models.transaction_category import TransactionCategory
from finance_api.repositories.classification_rule_repository import (
    ClassificationRuleRepository,
)
from finance_api.services.rules_classification_service import RulesClassificationService


def get_coverage_stats(db) -> dict:  # type: ignore[no-untyped-def, type-arg]
    """Get coverage statistics for transactions."""
    total = db.query(func.count(Transaction.id)).scalar()
    categorized = (
        db.query(func.count(TransactionCategory.id))
        .filter(TransactionCategory.category_id.isnot(None))
        .scalar()
    )
    uncategorized = total - categorized

    return {
        "total": total,
        "categorized": categorized,
        "uncategorized": uncategorized,
        "coverage_percentage": (categorized / total * 100) if total > 0 else 0,
    }


def get_category_distribution(db) -> list[dict]:  # type: ignore[no-untyped-def, type-arg]
    """Get distribution of transactions by category."""
    results = (
        db.query(
            Category.name,
            func.count(TransactionCategory.id).label("count"),
        )
        .join(TransactionCategory, TransactionCategory.category_id == Category.id)
        .group_by(Category.name)
        .order_by(func.count(TransactionCategory.id).desc())
        .all()
    )

    return [{"category": r[0], "count": r[1]} for r in results]


def print_stats_report(db) -> None:  # type: ignore[no-untyped-def]
    """Print a coverage statistics report."""
    stats = get_coverage_stats(db)
    distribution = get_category_distribution(db)

    print()
    print("=" * 60)
    print("=== Transaction Classification Report ===")
    print()
    print(f"Total transactions: {stats['total']}")
    print(f"Categorized: {stats['categorized']} ({stats['coverage_percentage']:.1f}%)")
    print(f"Uncategorized: {stats['uncategorized']}")
    print()

    if distribution:
        print("Category Distribution:")
        print("-" * 40)
        for item in distribution[:15]:
            print(f"  {item['category']}: {item['count']}")
        if len(distribution) > 15:
            print(f"  ... and {len(distribution) - 15} more categories")
    print()


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


def run_classification(
    stats_only: bool = False,
    dry_run: bool = False,
    limit: int | None = None,
) -> None:
    """Run batch classification.

    Args:
        stats_only: Only show statistics, don't classify.
        dry_run: Show what would be classified without saving.
        limit: Maximum number of transactions to classify.
    """
    db = SessionLocal()
    try:
        if stats_only:
            print_stats_report(db)
            return

        # Initialize services
        rule_repo = ClassificationRuleRepository(db)
        classification_service = RulesClassificationService(rule_repo)

        # Get uncategorized transactions
        uncategorized = get_uncategorized_transactions(db)

        if not uncategorized:
            print("No uncategorized transactions to process.")
            print_stats_report(db)
            return

        if limit:
            uncategorized = uncategorized[:limit]

        print()
        print("=== Batch Classification ===")
        print()
        print(f"Processing {len(uncategorized)} uncategorized transactions...")
        if dry_run:
            print("(DRY RUN - no changes will be saved)")
        print()

        # Classify transactions
        results = classification_service.classify_batch(uncategorized)

        # Count results
        matched = sum(1 for r in results.values() if r is not None)
        unmatched = len(results) - matched

        print(f"Matched by rules: {matched}")
        print(f"No match: {unmatched}")

        if not dry_run and matched > 0:
            # Apply classifications
            for txn_id, match in results.items():
                if match is None:
                    continue

                # Check if already has a category assignment
                existing = (
                    db.query(TransactionCategory)
                    .filter(TransactionCategory.transaction_id == txn_id)
                    .first()
                )

                if existing:
                    # Update existing
                    existing.category_id = match.category_id
                    existing.classification_source = "rule"
                    existing.classification_rule_id = match.rule.id
                    existing.updated_at = datetime.utcnow()
                else:
                    # Create new
                    txn_cat = TransactionCategory(
                        transaction_id=txn_id,
                        category_id=match.category_id,
                        classification_source="rule",
                        classification_rule_id=match.rule.id,
                    )
                    db.add(txn_cat)

            db.commit()
            print()
            print(f"Applied {matched} classifications.")

        print()
        print_stats_report(db)

        if dry_run and matched > 0:
            print("Sample matches (first 10):")
            print("-" * 60)
            count = 0
            for txn_id, match in results.items():
                if match is None or count >= 10:
                    continue

                txn = db.query(Transaction).get(txn_id)
                if txn:
                    print(f"  {txn.description[:50]}")
                    print(f"    → Rule: {match.rule.name}")
                    print(f"    → Category ID: {match.category_id}")
                    print()
                count += 1

    finally:
        db.close()


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Batch classification of transactions using rules"
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only show coverage statistics",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be classified without saving",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of transactions to classify",
    )

    args = parser.parse_args()

    run_classification(
        stats_only=args.stats_only,
        dry_run=args.dry_run,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
