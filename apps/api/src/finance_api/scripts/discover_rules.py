"""Interactive rule discovery CLI for building classification rules.

Multi-stage classification pipeline:
- Stage 1: High-frequency pattern detection (bank artifacts, savings round-ups)
- Stage 2: Transaction clustering with interactive refinement API
"""

import argparse
from typing import Any

from finance_api.db.session import SessionLocal
from finance_api.models.category import Category
from finance_api.models.session_rule_proposal import SessionRuleProposal
from finance_api.models.transaction import Transaction
from finance_api.models.transaction_category import TransactionCategory
from finance_api.repositories.category_repository import CategoryRepository
from finance_api.repositories.classification_rule_repository import (
    ClassificationRuleRepository,
)
from finance_api.repositories.refinement_session_repository import (
    RefinementSessionRepository,
)
from finance_api.repositories.rule_proposal_repository import RuleProposalRepository
from finance_api.services.high_frequency_analyzer import (
    HighFrequencyPattern,
    HighFrequencyPatternAnalyzer,
)
from finance_api.services.interactive_refinement_service import (
    InteractiveRefinementError,
    InteractiveRefinementService,
)
from finance_api.services.rule_discovery_service import (
    RuleDiscoveryError,
    RuleDiscoveryService,
)
from finance_api.services.rule_validation_service import ValidationResult
from finance_api.services.transaction_clustering_service import (
    TransactionCluster,
    TransactionClusteringService,
)


def get_uncategorized_transactions(db: Any) -> list[Transaction]:
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
    validation: ValidationResult,
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


def display_session_proposals(proposals: list[SessionRuleProposal]) -> None:
    """Display all pending proposals in a session."""
    pending = [p for p in proposals if p.status == "pending"]
    if not pending:
        print("\n  No pending proposals.")
        return

    print(f"\n  Pending Proposals ({len(pending)}):")
    for i, proposal in enumerate(pending, 1):
        precision = float(proposal.validation_precision or 0) * 100
        print(f"  [{i}] {proposal.proposed_pattern}")
        print(f"      → {proposal.proposed_category_name} ({proposal.llm_confidence})")
        print(
            f"      Matches: {proposal.validation_matches}, Precision: {precision:.0f}%"
        )


def get_refinement_action() -> str:
    """Get user action for interactive refinement."""
    print()
    print("Actions:")
    print("  [C]ontinue chat - send feedback to LLM")
    print("  [A]ccept proposal - accept a specific proposal")
    print("  [R]eject proposal - reject a specific proposal")
    print("  [D]one - complete this session")
    print("  [S]kip - skip this cluster for individual treatment")
    print("  [Q]uit - exit discovery")
    action = input("Action: ").strip().upper()
    return action


def select_proposal(proposals: list[SessionRuleProposal]) -> SessionRuleProposal | None:
    """Let user select a proposal by number."""
    pending = [p for p in proposals if p.status == "pending"]
    if not pending:
        print("No pending proposals to select.")
        return None

    try:
        choice = input("Enter proposal number: ").strip()
        idx = int(choice)
        if 1 <= idx <= len(pending):
            return pending[idx - 1]
    except ValueError:
        pass
    print("Invalid selection")
    return None


def display_assistant_message(content: str) -> None:
    """Display an assistant message in a formatted way."""
    print()
    print("-" * 40)
    print("LLM Response:")
    print()
    # Indent the content for readability
    for line in content.split("\n"):
        print(f"  {line}")


def find_category_by_name(categories: list[Category], name: str) -> Category | None:
    """Find a category by name (case-insensitive)."""
    name_lower = name.lower()
    for cat in categories:
        if cat.name.lower() == name_lower:
            return cat
    return None


def display_pattern(
    pattern: HighFrequencyPattern,
    pattern_num: int,
    total_patterns: int,
) -> None:
    """Display a detected high-frequency pattern."""
    print()
    print("=" * 60)
    print(f"=== Pattern #{pattern_num}/{total_patterns} ===")
    print(f'Pattern: "{pattern.phrase}"')
    print(
        f"Appears in: {pattern.transaction_count} transactions ({pattern.frequency:.1%})"
    )
    print()
    print("Sample transactions:")
    for sample in pattern.sample_descriptions:
        print(f"  - {sample}")


def display_pattern_explanation(
    explanation: str,
    suggested_category: str,
    suggested_category_id: int | None,
    confidence: str,
    reasoning: str,
) -> None:
    """Display the LLM's explanation of a pattern."""
    print()
    print("-" * 40)
    print("LLM Analysis:")
    print(f"  {explanation}")
    print()
    print(f"  Suggested category: {suggested_category}", end="")
    if suggested_category_id:
        print(f" (ID: {suggested_category_id})")
    else:
        print(" (not found in category list)")
    print(f"  Confidence: {confidence}")
    print(f"  Reasoning: {reasoning}")


def get_pattern_action() -> str:
    """Get user action for a pattern from interactive prompt."""
    print()
    print("How would you like to handle this pattern?")
    print("  [A] Assign to suggested category (create rule)")
    print("  [S] Strip from descriptions (cleaner clustering)")
    print("  [N] Do nothing (leave as-is)")
    print("  [C] Choose different category")
    print("  [Q] Quit")
    action = input("Action: ").strip().upper()
    return action


def select_category(categories: list[Category]) -> Category | None:
    """Let user select a category from the list."""
    print()
    print("Available categories:")
    for i, cat in enumerate(categories, 1):
        desc = f" - {cat.description}" if cat.description else ""
        print(f"  {i:3d}. {cat.name}{desc}")
    print()
    try:
        choice = input("Enter category number (or 0 to cancel): ").strip()
        idx = int(choice)
        if idx == 0:
            return None
        if 1 <= idx <= len(categories):
            return categories[idx - 1]
    except ValueError:
        pass
    print("Invalid selection")
    return None


def run_pattern_detection_stage(
    transactions: list[Transaction],
    categories: list[Category],
    rule_repo: ClassificationRuleRepository,
    db: Any,
    threshold: float = 0.10,
) -> tuple[set[int], list[str]]:
    """Run Stage 1: High-frequency pattern detection.

    Args:
        transactions: All uncategorized transactions.
        categories: Available categories.
        rule_repo: Repository for creating rules.
        db: Database session.
        threshold: Minimum frequency for pattern detection.

    Returns:
        Tuple of (categorized_transaction_ids, strip_patterns)
    """
    print()
    print("=" * 60)
    print("=== STAGE 1: High-Frequency Pattern Detection ===")
    print("=" * 60)
    print()

    analyzer = HighFrequencyPatternAnalyzer(threshold=threshold)
    patterns = analyzer.analyze(transactions)

    if not patterns:
        print(f"No patterns found above {threshold:.0%} threshold.")
        return set(), []

    print(f"Found {len(patterns)} high-frequency patterns")
    print()

    # Initialize LLM service for pattern explanation
    discovery_service = RuleDiscoveryService()

    categorized_ids: set[int] = set()
    strip_patterns: list[str] = []
    rules_created = 0
    patterns_stripped = 0
    patterns_ignored = 0

    for i, pattern in enumerate(patterns, 1):
        display_pattern(pattern, i, len(patterns))

        # Get LLM explanation
        print("\nAnalyzing pattern with LLM...")
        try:
            explanation = discovery_service.explain_pattern(
                pattern, categories, len(transactions)
            )
            display_pattern_explanation(
                explanation.explanation,
                explanation.suggested_category,
                explanation.suggested_category_id,
                explanation.confidence,
                explanation.reasoning,
            )
        except RuleDiscoveryError as e:
            print(f"Error getting LLM explanation: {e}")
            explanation = None

        action = get_pattern_action()

        if action == "A":
            # Assign to suggested category
            if explanation and explanation.suggested_category_id:
                category = find_category_by_name(
                    categories, explanation.suggested_category
                )
            else:
                print("No suggested category available. Please choose one.")
                category = select_category(categories)

            if category:
                # Create a rule for this pattern
                # Use case-insensitive regex that matches the phrase
                regex_pattern = f"(?i).*{pattern.phrase}.*"
                rule = rule_repo.create(
                    name=f"Pattern: {pattern.phrase[:50]}",
                    rule_expression=f'description =~ "{regex_pattern}"',
                    category_id=category.id,
                    priority=-100,  # Stage 1 rules run before Stage 2
                )
                db.commit()

                # Track categorized transactions
                matching_ids = analyzer.get_all_matching_transaction_ids(
                    pattern, transactions
                )
                categorized_ids.update(matching_ids)
                rules_created += 1

                print(f"✓ Rule created: {rule.name}")
                print(f"  Matched {len(matching_ids)} transactions → {category.name}")
            else:
                patterns_ignored += 1
                print("→ Skipped (no category selected)")

        elif action == "S":
            # Strip from descriptions
            strip_patterns.append(pattern.phrase)
            patterns_stripped += 1
            print("✓ Pattern will be stripped from descriptions during clustering")

        elif action == "N":
            # Do nothing
            patterns_ignored += 1
            print("→ Pattern ignored")

        elif action == "C":
            # Choose different category
            category = select_category(categories)
            if category:
                regex_pattern = f"(?i).*{pattern.phrase}.*"
                rule = rule_repo.create(
                    name=f"Pattern: {pattern.phrase[:50]}",
                    rule_expression=f'description =~ "{regex_pattern}"',
                    category_id=category.id,
                    priority=-100,  # Stage 1 rules run before Stage 2
                )
                db.commit()

                matching_ids = analyzer.get_all_matching_transaction_ids(
                    pattern, transactions
                )
                categorized_ids.update(matching_ids)
                rules_created += 1

                print(f"✓ Rule created: {rule.name}")
                print(f"  Matched {len(matching_ids)} transactions → {category.name}")
            else:
                patterns_ignored += 1
                print("→ Skipped (no category selected)")

        elif action == "Q":
            print("\nExiting pattern detection stage...")
            break

    print()
    print("-" * 40)
    print("Stage 1 Summary:")
    print(f"  Rules created: {rules_created}")
    print(f"  Patterns to strip: {patterns_stripped}")
    print(f"  Patterns ignored: {patterns_ignored}")
    print(f"  Transactions categorized: {len(categorized_ids)}")

    return categorized_ids, strip_patterns


def run_interactive_refinement(
    cluster: TransactionCluster,
    cluster_num: int,
    total_clusters: int,
    categories: list[Category],
    all_transactions: list[Transaction],
    session_repo: RefinementSessionRepository,
    rule_repo: ClassificationRuleRepository,
    refinement_service: InteractiveRefinementService,
    db: Any,
) -> tuple[int, int, bool]:
    """Run interactive refinement for a single cluster.

    Args:
        cluster: The transaction cluster to refine.
        cluster_num: Current cluster number.
        total_clusters: Total clusters being processed.
        categories: Available categories.
        all_transactions: All transactions for validation.
        session_repo: Repository for sessions.
        rule_repo: Repository for rules.
        refinement_service: Service for LLM interactions.
        db: Database session.

    Returns:
        Tuple of (accepted_count, rejected_count, should_quit)
    """
    display_cluster(cluster, cluster_num, total_clusters)

    # Check for existing active session
    existing_session = session_repo.get_by_cluster_hash(
        cluster.cluster_hash, active_only=True
    )
    if existing_session:
        print(f"\nResuming existing session (ID: {existing_session.id})")
        session = existing_session
        # Get existing messages for context
        messages = session_repo.get_conversation(session.id)
        if messages:
            print("\nPrevious conversation:")
            for msg in messages:
                role_label = "You" if msg.role == "user" else "LLM"
                print(f"  [{role_label}]: {msg.content[:100]}...")
    else:
        # Create new session
        print("\nCreating refinement session...")
        session = session_repo.create(
            cluster_hash=cluster.cluster_hash,
            cluster_key=cluster.cluster_key,
            cluster_size=cluster.size,
            sample_descriptions=cluster.sample_descriptions,
        )
        db.commit()

        # Get initial LLM proposal
        print("Getting initial LLM proposal...")
        try:
            response = refinement_service.start_session(cluster, categories)

            # Store assistant message
            session_repo.add_message(
                session_id=session.id,
                role="assistant",
                content=response.message,
                proposed_rules=[
                    {
                        "pattern": p.pattern,
                        "category_id": p.category_id,
                        "category_name": p.category_name,
                        "confidence": p.confidence,
                        "reasoning": p.reasoning,
                    }
                    for p in response.proposed_rules
                ],
            )

            # Run validation and store proposals
            if response.proposed_rules:
                cluster_ids = {t.id for t in cluster.transactions}
                validated = refinement_service.validate_proposals(
                    response.proposed_rules, all_transactions, cluster_ids
                )
                for proposal, validation in validated:
                    # Find category
                    category = find_category_by_name(categories, proposal.category_name)
                    session_repo.add_proposal(
                        session_id=session.id,
                        proposed_pattern=proposal.pattern,
                        proposed_category_id=category.id if category else None,
                        proposed_category_name=proposal.category_name,
                        llm_confidence=proposal.confidence,
                        llm_reasoning=proposal.reasoning,
                        validation_matches=validation.total_matches,
                        validation_precision=float(validation.precision),
                        validation_true_positives=validation.true_positives,
                        validation_false_positives=validation.false_positives,
                        sample_false_positives=validation.sample_false_positives,
                    )

                # Add validation feedback as system message
                validation_feedback = refinement_service.format_validation_feedback(
                    validated
                )
                session_repo.add_message(
                    session_id=session.id,
                    role="system",
                    content=validation_feedback,
                )

            db.commit()
            display_assistant_message(response.message)

        except InteractiveRefinementError as e:
            print(f"Error getting LLM proposal: {e}")
            return 0, 0, False

    # Interactive refinement loop
    accepted_count = 0
    rejected_count = 0

    while True:
        # Refresh session data
        session = session_repo.get(session.id)
        if not session:
            break

        proposals = session_repo.get_session_proposals(session.id)
        display_session_proposals(proposals)

        action = get_refinement_action()

        if action == "C":
            # Continue chat - send feedback
            feedback = input("Your message: ").strip()
            if not feedback:
                continue

            # Store user message
            session_repo.add_message(
                session_id=session.id,
                role="user",
                content=feedback,
            )
            db.commit()

            # Get LLM response
            print("\nGetting LLM response...")
            try:
                messages = session_repo.get_conversation(session.id)
                history = [{"role": m.role, "content": m.content} for m in messages]

                response = refinement_service.continue_session(
                    conversation_history=history,
                    user_message=feedback,
                    cluster=cluster,
                    categories=categories,
                )

                # Store assistant message
                session_repo.add_message(
                    session_id=session.id,
                    role="assistant",
                    content=response.message,
                    proposed_rules=[
                        {
                            "pattern": p.pattern,
                            "category_id": p.category_id,
                            "category_name": p.category_name,
                            "confidence": p.confidence,
                            "reasoning": p.reasoning,
                        }
                        for p in response.proposed_rules
                    ],
                )

                # Validate and store new proposals
                if response.proposed_rules:
                    cluster_ids = {t.id for t in cluster.transactions}
                    validated = refinement_service.validate_proposals(
                        response.proposed_rules, all_transactions, cluster_ids
                    )
                    for proposal, validation in validated:
                        # Check if this pattern already exists
                        existing = [
                            p
                            for p in proposals
                            if p.proposed_pattern == proposal.pattern
                        ]
                        if not existing:
                            category = find_category_by_name(
                                categories, proposal.category_name
                            )
                            session_repo.add_proposal(
                                session_id=session.id,
                                proposed_pattern=proposal.pattern,
                                proposed_category_id=category.id if category else None,
                                proposed_category_name=proposal.category_name,
                                llm_confidence=proposal.confidence,
                                llm_reasoning=proposal.reasoning,
                                validation_matches=validation.total_matches,
                                validation_precision=float(validation.precision),
                                validation_true_positives=validation.true_positives,
                                validation_false_positives=validation.false_positives,
                                sample_false_positives=validation.sample_false_positives,
                            )

                    # Add validation feedback
                    validation_feedback = refinement_service.format_validation_feedback(
                        validated
                    )
                    session_repo.add_message(
                        session_id=session.id,
                        role="system",
                        content=validation_feedback,
                    )

                db.commit()
                display_assistant_message(response.message)

            except InteractiveRefinementError as e:
                print(f"Error: {e}")

        elif action == "A":
            # Accept a proposal
            selected = select_proposal(proposals)
            if selected and selected.proposed_category_id:
                # Create the classification rule
                rule = rule_repo.create(
                    name=f"Cluster: {cluster.cluster_key[:40]}",
                    rule_expression=f'description =~ "{selected.proposed_pattern}"',
                    category_id=selected.proposed_category_id,
                    priority=0,
                )
                db.flush()
                # Link the rule to the proposal
                session_repo.accept_proposal(
                    proposal_id=selected.id,
                    final_rule_id=rule.id,
                )
                db.commit()
                accepted_count += 1
                print(f"✓ Rule created: {rule.name}")
                print(f"  Pattern: {selected.proposed_pattern}")
                print(f"  Category: {selected.proposed_category_name}")
            elif selected:
                print("Cannot accept: proposal has no category assigned")

        elif action == "R":
            # Reject a proposal
            selected = select_proposal(proposals)
            if selected:
                session_repo.reject_proposal(proposal_id=selected.id)
                db.commit()
                rejected_count += 1
                print("✗ Proposal rejected")

        elif action == "D":
            # Done - complete session
            session_repo.complete_session(session.id)
            db.commit()
            print("✓ Session completed")
            break

        elif action == "S":
            # Skip for individual treatment
            session_repo.skip_session(session.id)
            db.commit()
            print("→ Session skipped for individual treatment")
            break

        elif action == "Q":
            # Quit
            return accepted_count, rejected_count, True

    return accepted_count, rejected_count, False


def run_discovery(
    analyze_only: bool = False,
    resume: bool = False,
    min_cluster_size: int = 5,
    max_clusters: int | None = None,
    pattern_threshold: float = 0.10,
    skip_pattern_detection: bool = False,
) -> None:
    """Run the interactive rule discovery workflow.

    Args:
        analyze_only: If True, only show clustering analysis (no LLM).
        resume: If True, continue from pending proposals.
        min_cluster_size: Minimum cluster size to process.
        max_clusters: Maximum number of clusters to process.
        pattern_threshold: Minimum frequency for pattern detection (default 10%).
        skip_pattern_detection: If True, skip Stage 1 pattern detection.
    """
    db = SessionLocal()
    try:
        # Initialize services and repositories
        clustering_service = TransactionClusteringService(
            min_cluster_size=min_cluster_size
        )
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

        # === STAGE 1: Pattern Detection ===
        stage1_categorized_ids: set[int] = set()
        strip_patterns: list[str] = []

        if not skip_pattern_detection and not analyze_only:
            stage1_categorized_ids, strip_patterns = run_pattern_detection_stage(
                transactions=uncategorized,
                categories=categories,
                rule_repo=rule_repo,
                db=db,
                threshold=pattern_threshold,
            )

            # Filter out categorized transactions for Stage 2
            if stage1_categorized_ids:
                uncategorized = [
                    t for t in uncategorized if t.id not in stage1_categorized_ids
                ]
                # Also filter all_transactions so Stage 2 validation doesn't show
                # Stage 1 categorized transactions as false positives
                all_transactions = [
                    t for t in all_transactions if t.id not in stage1_categorized_ids
                ]
                print()
                print(f"Remaining uncategorized for Stage 2: {len(uncategorized)}")

        # === STAGE 2: Clustering ===
        print()
        print("=" * 60)
        print("=== STAGE 2: Transaction Clustering ===")
        print("=" * 60)
        print()

        # Update clustering service with strip patterns if any
        if strip_patterns:
            clustering_service = TransactionClusteringService(
                min_cluster_size=min_cluster_size,
                strip_patterns=strip_patterns,
            )
            print(f"Stripping {len(strip_patterns)} patterns from descriptions")
            print()

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

        # Initialize services for interactive refinement
        session_repo = RefinementSessionRepository(db)
        refinement_service = InteractiveRefinementService()

        # Process clusters with interactive refinement
        clusters_to_process = clusters[:max_clusters] if max_clusters else clusters
        total_accepted = 0
        total_rejected = 0
        completed_count = 0
        skipped_count = 0

        for i, cluster in enumerate(clusters_to_process, 1):
            # Check if we already have a completed/skipped session for this cluster
            existing_session = session_repo.get_by_cluster_hash(cluster.cluster_hash)
            if existing_session and existing_session.status in ("completed", "skipped"):
                print(f"\nSkipping cluster {cluster.cluster_key} (already processed)")
                continue

            accepted, rejected, should_quit = run_interactive_refinement(
                cluster=cluster,
                cluster_num=i,
                total_clusters=len(clusters_to_process),
                categories=categories,
                all_transactions=all_transactions,
                session_repo=session_repo,
                rule_repo=rule_repo,
                refinement_service=refinement_service,
                db=db,
            )

            total_accepted += accepted
            total_rejected += rejected

            # Get session to check final status
            final_session = session_repo.get_by_cluster_hash(cluster.cluster_hash)
            if final_session:
                if final_session.status == "completed":
                    completed_count += 1
                elif final_session.status == "skipped":
                    skipped_count += 1

            if should_quit:
                print("\nQuitting...")
                break

        print()
        print("=" * 60)
        print("=== Session Summary ===")
        print(f"Rules accepted: {total_accepted}")
        print(f"Proposals rejected: {total_rejected}")
        print(f"Clusters completed: {completed_count}")
        print(f"Clusters skipped: {skipped_count}")

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
    parser.add_argument(
        "--pattern-threshold",
        type=float,
        default=0.10,
        help="Minimum frequency for pattern detection (default: 0.10 = 10%%)",
    )
    parser.add_argument(
        "--skip-pattern-detection",
        action="store_true",
        help="Skip Stage 1 pattern detection, go directly to clustering",
    )

    args = parser.parse_args()

    run_discovery(
        analyze_only=args.analyze_only,
        resume=args.resume,
        min_cluster_size=args.min_cluster_size,
        max_clusters=args.max_clusters,
        pattern_threshold=args.pattern_threshold,
        skip_pattern_detection=args.skip_pattern_detection,
    )


if __name__ == "__main__":
    main()
