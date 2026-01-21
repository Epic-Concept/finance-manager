"""RulesClassificationService for deterministic transaction classification."""

import logging
from dataclasses import dataclass
from typing import Any

import rule_engine  # type: ignore[import-untyped]

from finance_api.models.classification_rule import ClassificationRule
from finance_api.models.transaction import Transaction
from finance_api.repositories.classification_rule_repository import (
    ClassificationRuleRepository,
)

logger = logging.getLogger(__name__)


@dataclass
class RuleMatch:
    """Result of a successful rule match."""

    rule: ClassificationRule
    category_id: int
    requires_disambiguation: bool


class RulesClassificationService:
    """Service for classifying transactions using deterministic rules.

    Uses the rule-engine library to evaluate expressions against transaction data.
    Rules are evaluated in priority order (lower priority value = higher priority).
    First matching rule wins.
    """

    def __init__(self, rule_repository: ClassificationRuleRepository) -> None:
        """Initialize the service with a rule repository.

        Args:
            rule_repository: Repository for accessing classification rules.
        """
        self._rule_repository = rule_repository
        self._compiled_rules: (
            list[tuple[ClassificationRule, rule_engine.Rule]] | None
        ) = None
        self._context = self._create_context()

    def _create_context(self) -> rule_engine.Context:
        """Create a rule-engine context with type definitions.

        Returns:
            A configured rule_engine.Context for transaction evaluation.
        """
        return rule_engine.Context(
            type_resolver=rule_engine.type_resolver_from_dict(
                {
                    "description": rule_engine.DataType.STRING,
                    "amount": rule_engine.DataType.FLOAT,
                    "currency": rule_engine.DataType.STRING,
                    "account_name": rule_engine.DataType.STRING,
                    "external_id": rule_engine.DataType.STRING,
                    "notes": rule_engine.DataType.STRING,
                    "transaction_date": rule_engine.DataType.STRING,
                }
            )
        )

    def _load_and_compile_rules(
        self,
    ) -> list[tuple[ClassificationRule, rule_engine.Rule]]:
        """Load rules from repository and compile them.

        Returns:
            List of tuples containing (ClassificationRule, compiled rule_engine.Rule).
        """
        db_rules = self._rule_repository.get_active_by_priority()
        compiled: list[tuple[ClassificationRule, rule_engine.Rule]] = []

        for db_rule in db_rules:
            try:
                compiled_rule = rule_engine.Rule(
                    db_rule.rule_expression, context=self._context
                )
                compiled.append((db_rule, compiled_rule))
            except rule_engine.RuleSyntaxError as e:
                # Log error but continue with other rules
                logger.warning(
                    "Failed to compile rule '%s' (id=%d): %s",
                    db_rule.name,
                    db_rule.id,
                    e,
                )

        return compiled

    def reload_rules(self) -> int:
        """Reload rules from the database and recompile.

        Call this after rules have been modified in the database.

        Returns:
            Number of successfully compiled rules.
        """
        self._compiled_rules = self._load_and_compile_rules()
        return len(self._compiled_rules)

    def _ensure_rules_loaded(self) -> list[tuple[ClassificationRule, rule_engine.Rule]]:
        """Ensure rules are loaded, loading them if necessary.

        Returns:
            List of compiled rules.
        """
        if self._compiled_rules is None:
            self._compiled_rules = self._load_and_compile_rules()
        return self._compiled_rules

    def _transaction_to_context(self, transaction: Transaction) -> dict[str, Any]:
        """Convert a Transaction to a rule-engine evaluation context.

        Args:
            transaction: The transaction to convert.

        Returns:
            Dictionary suitable for rule-engine evaluation.
        """
        return {
            "description": transaction.description or "",
            "amount": float(transaction.amount) if transaction.amount else 0.0,
            "currency": transaction.currency or "GBP",
            "account_name": transaction.account_name or "",
            "external_id": transaction.external_id or "",
            "notes": transaction.notes or "",
            "transaction_date": (
                transaction.transaction_date.isoformat()
                if transaction.transaction_date
                else ""
            ),
        }

    def classify(self, transaction: Transaction) -> RuleMatch | None:
        """Classify a transaction using rules.

        Evaluates all active rules in priority order. Returns the first match.

        Args:
            transaction: The transaction to classify.

        Returns:
            RuleMatch if a rule matched, None if no rules matched.
        """
        compiled_rules = self._ensure_rules_loaded()
        context_data = self._transaction_to_context(transaction)

        for db_rule, compiled_rule in compiled_rules:
            try:
                if compiled_rule.matches(context_data):
                    return RuleMatch(
                        rule=db_rule,
                        category_id=db_rule.category_id,
                        requires_disambiguation=db_rule.requires_disambiguation,
                    )
            except rule_engine.EngineError:
                # Evaluation error - skip this rule and continue
                continue

        return None

    def classify_batch(
        self, transactions: list[Transaction]
    ) -> dict[int, RuleMatch | None]:
        """Classify multiple transactions.

        Args:
            transactions: List of transactions to classify.

        Returns:
            Dictionary mapping transaction ID to RuleMatch (or None if no match).
        """
        results: dict[int, RuleMatch | None] = {}
        for transaction in transactions:
            results[transaction.id] = self.classify(transaction)
        return results

    def test_rule_expression(
        self, expression: str, test_data: dict[str, Any] | None = None
    ) -> tuple[bool, str | None]:
        """Test a rule expression for validity and optionally against test data.

        Args:
            expression: The rule-engine expression to test.
            test_data: Optional dictionary to test the expression against.

        Returns:
            Tuple of (is_valid, error_message). If valid and test_data provided,
            the first element indicates whether the rule matched.
        """
        try:
            compiled_rule = rule_engine.Rule(expression, context=self._context)
            if test_data is not None:
                return (compiled_rule.matches(test_data), None)
            return (True, None)
        except rule_engine.RuleSyntaxError as e:
            return (False, str(e))
        except rule_engine.EngineError as e:
            return (False, f"Evaluation error: {e}")

    def get_matching_rules(
        self, transaction: Transaction
    ) -> list[tuple[ClassificationRule, bool]]:
        """Get all rules that match a transaction (for debugging/testing).

        Unlike classify(), this returns ALL matching rules, not just the first.

        Args:
            transaction: The transaction to check.

        Returns:
            List of tuples (ClassificationRule, matched) for all rules.
        """
        compiled_rules = self._ensure_rules_loaded()
        context_data = self._transaction_to_context(transaction)
        results: list[tuple[ClassificationRule, bool]] = []

        for db_rule, compiled_rule in compiled_rules:
            try:
                matched = compiled_rule.matches(context_data)
                results.append((db_rule, matched))
            except rule_engine.EngineError:
                results.append((db_rule, False))

        return results
