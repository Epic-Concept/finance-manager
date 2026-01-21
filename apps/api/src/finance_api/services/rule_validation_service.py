"""RuleValidationService for testing proposed rules before approval."""

import re
from dataclasses import dataclass, field
from decimal import Decimal

from finance_api.models.classification_rule import ClassificationRule
from finance_api.models.transaction import Transaction
from finance_api.repositories.classification_rule_repository import (
    ClassificationRuleRepository,
)


@dataclass
class ValidationResult:
    """Result of validating a rule against transactions."""

    pattern: str
    total_matches: int
    true_positives: int  # Matches within target cluster
    false_positives: int  # Matches outside target cluster
    precision: Decimal
    coverage: Decimal  # TP / cluster_size
    sample_true_positives: list[str] = field(default_factory=list)
    sample_false_positives: list[str] = field(default_factory=list)
    is_valid_regex: bool = True
    regex_error: str | None = None


@dataclass
class ConflictResult:
    """Result of checking for rule conflicts."""

    has_conflicts: bool
    conflicting_rules: list[ClassificationRule] = field(default_factory=list)
    overlap_counts: dict[int, int] = field(
        default_factory=dict
    )  # rule_id -> overlap count


class RuleValidationService:
    """Service for validating proposed rules before approval.

    Tests rules against all transactions to calculate precision,
    identify false positives, and detect conflicts with existing rules.
    """

    def __init__(
        self,
        rule_repository: ClassificationRuleRepository | None = None,
        max_samples: int = 5,
    ) -> None:
        """Initialize the validation service.

        Args:
            rule_repository: Repository for accessing existing rules.
            max_samples: Maximum number of sample descriptions to return.
        """
        self._rule_repository = rule_repository
        self._max_samples = max_samples

    def validate_regex(self, pattern: str) -> tuple[bool, str | None]:
        """Validate that a pattern is a valid regex.

        Args:
            pattern: The regex pattern to validate.

        Returns:
            Tuple of (is_valid, error_message).
        """
        try:
            re.compile(pattern)
            return (True, None)
        except re.error as e:
            return (False, str(e))

    def test_rule(
        self,
        pattern: str,
        all_transactions: list[Transaction],
        cluster_transaction_ids: set[int],
    ) -> ValidationResult:
        """Test a proposed rule against all transactions.

        Args:
            pattern: Regex pattern to test.
            all_transactions: List of all transactions to test against.
            cluster_transaction_ids: Set of transaction IDs in the target cluster.

        Returns:
            ValidationResult with precision metrics and samples.
        """
        # First validate the regex
        is_valid, error = self.validate_regex(pattern)
        if not is_valid:
            return ValidationResult(
                pattern=pattern,
                total_matches=0,
                true_positives=0,
                false_positives=0,
                precision=Decimal("0"),
                coverage=Decimal("0"),
                is_valid_regex=False,
                regex_error=error,
            )

        try:
            compiled = re.compile(pattern)
        except re.error as e:
            return ValidationResult(
                pattern=pattern,
                total_matches=0,
                true_positives=0,
                false_positives=0,
                precision=Decimal("0"),
                coverage=Decimal("0"),
                is_valid_regex=False,
                regex_error=str(e),
            )

        # Test against all transactions
        true_positives: list[Transaction] = []
        false_positives: list[Transaction] = []

        for txn in all_transactions:
            if not txn.description:
                continue

            if compiled.search(txn.description):
                if txn.id in cluster_transaction_ids:
                    true_positives.append(txn)
                else:
                    false_positives.append(txn)

        total_matches = len(true_positives) + len(false_positives)
        cluster_size = len(cluster_transaction_ids)

        # Calculate metrics
        precision = (
            Decimal(len(true_positives)) / Decimal(total_matches)
            if total_matches > 0
            else Decimal("0")
        )
        coverage = (
            Decimal(len(true_positives)) / Decimal(cluster_size)
            if cluster_size > 0
            else Decimal("0")
        )

        # Collect samples
        sample_tp = [
            t.description for t in true_positives[: self._max_samples] if t.description
        ]
        sample_fp = [
            t.description for t in false_positives[: self._max_samples] if t.description
        ]

        return ValidationResult(
            pattern=pattern,
            total_matches=total_matches,
            true_positives=len(true_positives),
            false_positives=len(false_positives),
            precision=precision.quantize(Decimal("0.0001")),
            coverage=coverage.quantize(Decimal("0.0001")),
            sample_true_positives=sample_tp,
            sample_false_positives=sample_fp,
        )

    def calculate_precision(self, true_positives: int, false_positives: int) -> Decimal:
        """Calculate precision from TP and FP counts.

        Args:
            true_positives: Number of true positive matches.
            false_positives: Number of false positive matches.

        Returns:
            Precision as a Decimal (0-1).
        """
        total = true_positives + false_positives
        if total == 0:
            return Decimal("0")
        return (Decimal(true_positives) / Decimal(total)).quantize(Decimal("0.0001"))

    def calculate_recall(self, true_positives: int, cluster_size: int) -> Decimal:
        """Calculate recall (coverage) from TP and cluster size.

        Args:
            true_positives: Number of true positive matches.
            cluster_size: Total size of the target cluster.

        Returns:
            Recall as a Decimal (0-1).
        """
        if cluster_size == 0:
            return Decimal("0")
        return (Decimal(true_positives) / Decimal(cluster_size)).quantize(
            Decimal("0.0001")
        )

    def sample_false_positives(
        self,
        pattern: str,
        all_transactions: list[Transaction],
        cluster_transaction_ids: set[int],
        max_samples: int | None = None,
    ) -> list[str]:
        """Get sample false positive descriptions for review.

        Args:
            pattern: Regex pattern to test.
            all_transactions: List of all transactions.
            cluster_transaction_ids: Set of transaction IDs in the target cluster.
            max_samples: Maximum number of samples to return.

        Returns:
            List of false positive transaction descriptions.
        """
        if max_samples is None:
            max_samples = self._max_samples

        try:
            compiled = re.compile(pattern)
        except re.error:
            return []

        samples: list[str] = []
        for txn in all_transactions:
            if not txn.description:
                continue
            if (
                compiled.search(txn.description)
                and txn.id not in cluster_transaction_ids
            ):
                samples.append(txn.description)
                if len(samples) >= max_samples:
                    break

        return samples

    def find_conflicts(
        self,
        pattern: str,
        all_transactions: list[Transaction],
    ) -> ConflictResult:
        """Check if a new rule overlaps with existing rules.

        Args:
            pattern: Proposed regex pattern.
            all_transactions: List of all transactions.

        Returns:
            ConflictResult with overlapping rules.
        """
        if self._rule_repository is None:
            return ConflictResult(has_conflicts=False)

        try:
            new_compiled = re.compile(pattern)
        except re.error:
            return ConflictResult(has_conflicts=False)

        # Get all active rules
        existing_rules = self._rule_repository.get_active_by_priority()

        # Find transactions that match the new pattern
        new_matches: set[int] = set()
        for txn in all_transactions:
            if txn.description and new_compiled.search(txn.description):
                new_matches.add(txn.id)

        if not new_matches:
            return ConflictResult(has_conflicts=False)

        # Check for overlap with existing rules
        conflicting: list[ClassificationRule] = []
        overlaps: dict[int, int] = {}

        for rule in existing_rules:
            # Extract pattern from rule expression
            # Rule expressions use format: description =~ "pattern"
            rule_pattern = self._extract_pattern_from_expression(rule.rule_expression)
            if not rule_pattern:
                continue

            try:
                rule_compiled = re.compile(rule_pattern)
            except re.error:
                continue

            # Count overlapping transactions
            overlap_count = 0
            for txn in all_transactions:
                if txn.id in new_matches and txn.description:
                    if rule_compiled.search(txn.description):
                        overlap_count += 1

            if overlap_count > 0:
                conflicting.append(rule)
                overlaps[rule.id] = overlap_count

        return ConflictResult(
            has_conflicts=len(conflicting) > 0,
            conflicting_rules=conflicting,
            overlap_counts=overlaps,
        )

    def _extract_pattern_from_expression(self, expression: str) -> str | None:
        """Extract regex pattern from a rule expression.

        Rule expressions use format: description =~ "pattern"

        Args:
            expression: The rule expression string.

        Returns:
            The extracted pattern or None if not found.
        """
        # Match patterns like: description =~ "(?i)pattern"
        match = re.search(r'=~\s*"([^"]+)"', expression)
        if match:
            return match.group(1)
        return None

    def test_pattern_matches(self, pattern: str, description: str) -> bool:
        """Test if a pattern matches a specific description.

        Args:
            pattern: Regex pattern to test.
            description: Transaction description to match against.

        Returns:
            True if pattern matches, False otherwise.
        """
        try:
            return bool(re.search(pattern, description))
        except re.error:
            return False
