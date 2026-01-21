"""ClassificationOrchestrator for coordinating transaction classification."""

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from fastapi import BackgroundTasks

from finance_api.models.transaction import Transaction
from finance_api.models.transaction_category import TransactionCategory
from finance_api.repositories.category_evidence_repository import (
    CategoryEvidenceRepository,
)
from finance_api.services.ai_disambiguation_service import (
    AIDisambiguationService,
)
from finance_api.services.rules_classification_service import (
    RuleMatch,
    RulesClassificationService,
)


@dataclass
class ClassificationResult:
    """Result of transaction classification."""

    transaction_id: int
    classified: bool
    category_id: int | None
    method: str  # 'rule', 'rule_with_disambiguation', 'ai', 'manual', 'pending'
    rule_name: str | None = None
    confidence: Decimal | None = None
    needs_disambiguation: bool = False
    error_message: str | None = None


class ClassificationOrchestrator:
    """Orchestrates the transaction classification pipeline.

    Coordinates:
    1. Rules-based classification (first pass)
    2. AI disambiguation for flagged transactions (background)
    3. Final category assignment

    Flow:
    - Rule match without disambiguation → Direct assignment
    - Rule match with disambiguation flag → Queue for AI disambiguation
    - No rule match → Queue for AI disambiguation
    """

    def __init__(
        self,
        rules_service: RulesClassificationService,
        disambiguation_service: AIDisambiguationService | None,
        evidence_repository: CategoryEvidenceRepository,
        transaction_category_updater: (
            Callable[[int, int], TransactionCategory] | None
        ) = None,
    ) -> None:
        """Initialize the orchestrator.

        Args:
            rules_service: Service for rules-based classification.
            disambiguation_service: Service for AI disambiguation (optional).
            evidence_repository: Repository for evidence records.
            transaction_category_updater: Callback to assign category to transaction.
        """
        self._rules_service = rules_service
        self._disambiguation_service = disambiguation_service
        self._evidence_repo = evidence_repository
        self._category_updater = transaction_category_updater

    def _assign_category(self, transaction_id: int, category_id: int) -> None:
        """Assign a category to a transaction.

        Args:
            transaction_id: The transaction ID.
            category_id: The category ID to assign.
        """
        if self._category_updater:
            self._category_updater(transaction_id, category_id)

    def _is_already_classified(self, transaction: Transaction) -> bool:
        """Check if a transaction is already classified.

        Args:
            transaction: The transaction to check.

        Returns:
            True if transaction already has a category assigned.
        """
        return transaction.category_link is not None

    def classify(
        self,
        transaction: Transaction,
        force: bool = False,
        background_tasks: BackgroundTasks | None = None,
    ) -> ClassificationResult:
        """Classify a single transaction.

        Args:
            transaction: The transaction to classify.
            force: If True, reclassify even if already classified.
            background_tasks: FastAPI BackgroundTasks for async disambiguation.

        Returns:
            ClassificationResult with outcome.
        """
        # Idempotency check
        if not force and self._is_already_classified(transaction):
            return ClassificationResult(
                transaction_id=transaction.id,
                classified=True,
                category_id=(
                    transaction.category_link.category_id
                    if transaction.category_link
                    else None
                ),
                method="existing",
            )

        # Step 1: Try rules-based classification
        rule_match = self._rules_service.classify(transaction)

        if rule_match is not None:
            if not rule_match.requires_disambiguation:
                # Direct assignment
                self._assign_category(transaction.id, rule_match.category_id)

                # Store rule evidence for audit trail
                self._evidence_repo.create(
                    transaction_id=transaction.id,
                    item_description=transaction.description or "Transaction",
                    item_price=transaction.amount,
                    item_currency=transaction.currency or "GBP",
                    item_quantity=1,
                    category_id=rule_match.category_id,
                    evidence_type="rule",
                    evidence_summary=(
                        f"Matched rule '{rule_match.rule.name}': "
                        f"{rule_match.rule.rule_expression}"
                    ),
                    confidence_score=Decimal("1.0"),
                )

                return ClassificationResult(
                    transaction_id=transaction.id,
                    classified=True,
                    category_id=rule_match.category_id,
                    method="rule",
                    rule_name=rule_match.rule.name,
                    confidence=Decimal("1.0"),
                )
            else:
                # Rule matched but needs AI disambiguation
                if self._disambiguation_service and background_tasks:
                    background_tasks.add_task(
                        self._run_disambiguation_background,
                        transaction,
                        rule_match,
                    )
                    return ClassificationResult(
                        transaction_id=transaction.id,
                        classified=False,
                        category_id=rule_match.category_id,  # Provisional category
                        method="pending",
                        rule_name=rule_match.rule.name,
                        needs_disambiguation=True,
                    )
                elif self._disambiguation_service:
                    # Run synchronously
                    return self._classify_with_disambiguation(transaction, rule_match)
                else:
                    # No disambiguation service - use rule category as best effort
                    self._assign_category(transaction.id, rule_match.category_id)
                    return ClassificationResult(
                        transaction_id=transaction.id,
                        classified=True,
                        category_id=rule_match.category_id,
                        method="rule_with_disambiguation",
                        rule_name=rule_match.rule.name,
                        confidence=Decimal("0.7"),
                        needs_disambiguation=True,
                    )

        # No rule match - try AI disambiguation
        if self._disambiguation_service:
            if background_tasks:
                background_tasks.add_task(
                    self._run_disambiguation_background,
                    transaction,
                    None,
                )
                return ClassificationResult(
                    transaction_id=transaction.id,
                    classified=False,
                    category_id=None,
                    method="pending",
                    needs_disambiguation=True,
                )
            else:
                return self._classify_with_disambiguation(transaction, None)

        # No classification possible
        return ClassificationResult(
            transaction_id=transaction.id,
            classified=False,
            category_id=None,
            method="unclassified",
            error_message="No matching rules and no disambiguation service available",
        )

    def _classify_with_disambiguation(
        self,
        transaction: Transaction,
        rule_match: RuleMatch | None,
    ) -> ClassificationResult:
        """Classify using AI disambiguation.

        Args:
            transaction: The transaction to classify.
            rule_match: Optional rule match that flagged disambiguation.

        Returns:
            ClassificationResult with outcome.
        """
        if not self._disambiguation_service:
            return ClassificationResult(
                transaction_id=transaction.id,
                classified=False,
                category_id=rule_match.category_id if rule_match else None,
                method="unclassified",
                error_message="Disambiguation service not available",
            )

        result = self._disambiguation_service.disambiguate(transaction)

        if result.success and result.dominant_category_id:
            self._assign_category(transaction.id, result.dominant_category_id)
            return ClassificationResult(
                transaction_id=transaction.id,
                classified=True,
                category_id=result.dominant_category_id,
                method="ai",
                confidence=result.confidence_score,
            )
        elif result.dominant_category_id:
            # Partial success - has category but low confidence
            self._assign_category(transaction.id, result.dominant_category_id)
            return ClassificationResult(
                transaction_id=transaction.id,
                classified=True,
                category_id=result.dominant_category_id,
                method="ai",
                confidence=result.confidence_score,
                error_message=result.error_message,
            )
        elif rule_match:
            # Fall back to rule category
            self._assign_category(transaction.id, rule_match.category_id)
            return ClassificationResult(
                transaction_id=transaction.id,
                classified=True,
                category_id=rule_match.category_id,
                method="rule_with_disambiguation",
                rule_name=rule_match.rule.name,
                confidence=Decimal("0.5"),
                error_message=result.error_message,
            )
        else:
            return ClassificationResult(
                transaction_id=transaction.id,
                classified=False,
                category_id=None,
                method="unclassified",
                error_message=result.error_message,
            )

    def _run_disambiguation_background(
        self,
        transaction: Transaction,
        rule_match: RuleMatch | None,
    ) -> None:
        """Run disambiguation in background (for BackgroundTasks).

        Args:
            transaction: The transaction to classify.
            rule_match: Optional rule match that flagged disambiguation.
        """
        # Note: In production, this would need proper session/transaction management
        self._classify_with_disambiguation(transaction, rule_match)

    def classify_batch(
        self,
        transactions: list[Transaction],
        force: bool = False,
        background_tasks: BackgroundTasks | None = None,
    ) -> dict[int, ClassificationResult]:
        """Classify multiple transactions.

        Args:
            transactions: List of transactions to classify.
            force: If True, reclassify even if already classified.
            background_tasks: FastAPI BackgroundTasks for async disambiguation.

        Returns:
            Dictionary mapping transaction ID to ClassificationResult.
        """
        results: dict[int, ClassificationResult] = {}

        for transaction in transactions:
            results[transaction.id] = self.classify(
                transaction,
                force=force,
                background_tasks=background_tasks,
            )

        return results

    def get_classification_statistics(
        self, results: dict[int, ClassificationResult]
    ) -> dict[str, int]:
        """Get statistics from classification results.

        Args:
            results: Dictionary of classification results.

        Returns:
            Dictionary with counts by method.
        """
        stats: dict[str, int] = {
            "total": len(results),
            "classified": 0,
            "unclassified": 0,
            "pending": 0,
            "by_rule": 0,
            "by_ai": 0,
            "existing": 0,
        }

        for result in results.values():
            if result.classified:
                stats["classified"] += 1
            elif result.method == "pending":
                stats["pending"] += 1
            else:
                stats["unclassified"] += 1

            if result.method == "rule":
                stats["by_rule"] += 1
            elif result.method == "ai":
                stats["by_ai"] += 1
            elif result.method == "existing":
                stats["existing"] += 1

        return stats
