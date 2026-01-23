"""Tests for RuleValidationService."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from finance_api.models.classification_rule import ClassificationRule
from finance_api.models.transaction import Transaction
from finance_api.services.rule_validation_service import (
    RuleValidationService,
)


def create_mock_transaction(id: int, description: str) -> Transaction:
    """Create a mock Transaction for testing."""
    txn = MagicMock(spec=Transaction)
    txn.id = id
    txn.description = description
    txn.amount = Decimal("-10.00")
    txn.transaction_date = date(2024, 1, 1)
    return txn


class TestValidateRegex:
    """Tests for regex validation."""

    def test_valid_regex(self) -> None:
        """Test validating a valid regex."""
        service = RuleValidationService()

        is_valid, error = service.validate_regex(r"(?i)tesco")

        assert is_valid is True
        assert error is None

    def test_invalid_regex(self) -> None:
        """Test validating an invalid regex."""
        service = RuleValidationService()

        is_valid, error = service.validate_regex(r"(?i)tesco[")

        assert is_valid is False
        assert error is not None

    def test_complex_valid_regex(self) -> None:
        """Test validating a complex but valid regex."""
        service = RuleValidationService()

        is_valid, _ = service.validate_regex(r"(?i)(tesco|sainsbury|asda)\s*\w+")

        assert is_valid is True

    def test_empty_pattern(self) -> None:
        """Test validating an empty pattern."""
        service = RuleValidationService()

        is_valid, _ = service.validate_regex("")

        assert is_valid is True  # Empty is valid regex


class TestTestRule:
    """Tests for rule testing."""

    def test_perfect_precision(self) -> None:
        """Test rule with 100% precision."""
        service = RuleValidationService()
        transactions = [
            create_mock_transaction(1, "TESCO STORES 1234"),
            create_mock_transaction(2, "TESCO EXPRESS"),
            create_mock_transaction(3, "AMAZON UK"),
        ]
        cluster_ids = {1, 2}

        result = service.test_rule(r"(?i)tesco", transactions, cluster_ids)

        assert result.true_positives == 2
        assert result.false_positives == 0
        assert result.precision == Decimal("1.0000")
        assert result.coverage == Decimal("1.0000")

    def test_with_false_positives(self) -> None:
        """Test rule that has false positives."""
        service = RuleValidationService()
        transactions = [
            create_mock_transaction(1, "TESCO STORES"),
            create_mock_transaction(2, "TESCO EXPRESS"),
            create_mock_transaction(3, "TESCO BANK"),  # Not in cluster
        ]
        cluster_ids = {1, 2}  # Only stores and express

        result = service.test_rule(r"(?i)tesco", transactions, cluster_ids)

        assert result.true_positives == 2
        assert result.false_positives == 1
        assert result.total_matches == 3
        # Precision = 2/3 = 0.6667
        assert result.precision == Decimal("0.6667")

    def test_partial_coverage(self) -> None:
        """Test rule with partial coverage."""
        service = RuleValidationService()
        transactions = [
            create_mock_transaction(1, "TESCO STORES"),
            create_mock_transaction(2, "TESCO EXPRESS"),
            create_mock_transaction(3, "SAINSBURY"),  # In cluster but not matched
        ]
        cluster_ids = {1, 2, 3}

        result = service.test_rule(r"(?i)tesco", transactions, cluster_ids)

        assert result.true_positives == 2
        assert result.coverage == Decimal("0.6667")  # 2/3

    def test_invalid_regex_returns_zero(self) -> None:
        """Test that invalid regex returns zero precision."""
        service = RuleValidationService()
        transactions = [create_mock_transaction(1, "TESCO")]
        cluster_ids = {1}

        result = service.test_rule(r"(?i)tesco[", transactions, cluster_ids)

        assert result.is_valid_regex is False
        assert result.regex_error is not None
        assert result.total_matches == 0

    def test_no_matches(self) -> None:
        """Test rule that matches nothing."""
        service = RuleValidationService()
        transactions = [
            create_mock_transaction(1, "AMAZON UK"),
            create_mock_transaction(2, "NETFLIX"),
        ]
        cluster_ids = {1, 2}

        result = service.test_rule(r"(?i)tesco", transactions, cluster_ids)

        assert result.total_matches == 0
        assert result.precision == Decimal("0")

    def test_collects_sample_true_positives(self) -> None:
        """Test that sample true positives are collected."""
        service = RuleValidationService(max_samples=2)
        transactions = [
            create_mock_transaction(1, "TESCO STORES"),
            create_mock_transaction(2, "TESCO EXPRESS"),
            create_mock_transaction(3, "TESCO EXTRA"),
        ]
        cluster_ids = {1, 2, 3}

        result = service.test_rule(r"(?i)tesco", transactions, cluster_ids)

        assert len(result.sample_true_positives) == 2

    def test_collects_sample_false_positives(self) -> None:
        """Test that sample false positives are collected."""
        service = RuleValidationService(max_samples=2)
        transactions = [
            create_mock_transaction(1, "TESCO STORES"),  # In cluster
            create_mock_transaction(2, "TESCO BANK"),  # Not in cluster
            create_mock_transaction(3, "TESCO MOBILE"),  # Not in cluster
            create_mock_transaction(4, "TESCO INSURANCE"),  # Not in cluster
        ]
        cluster_ids = {1}

        result = service.test_rule(r"(?i)tesco", transactions, cluster_ids)

        assert len(result.sample_false_positives) == 2

    def test_handles_none_description(self) -> None:
        """Test handling of transactions with None description."""
        service = RuleValidationService()
        txn1 = create_mock_transaction(1, "TESCO")
        txn2 = create_mock_transaction(2, "")
        txn2.description = None
        transactions = [txn1, txn2]
        cluster_ids = {1, 2}

        result = service.test_rule(r"(?i)tesco", transactions, cluster_ids)

        assert result.true_positives == 1


class TestCalculatePrecision:
    """Tests for precision calculation."""

    def test_perfect_precision(self) -> None:
        """Test 100% precision calculation."""
        service = RuleValidationService()

        precision = service.calculate_precision(10, 0)

        assert precision == Decimal("1.0000")

    def test_zero_precision(self) -> None:
        """Test 0% precision calculation."""
        service = RuleValidationService()

        precision = service.calculate_precision(0, 10)

        assert precision == Decimal("0.0000")

    def test_mixed_precision(self) -> None:
        """Test mixed precision calculation."""
        service = RuleValidationService()

        precision = service.calculate_precision(3, 1)

        assert precision == Decimal("0.7500")

    def test_no_matches_returns_zero(self) -> None:
        """Test that no matches returns zero precision."""
        service = RuleValidationService()

        precision = service.calculate_precision(0, 0)

        assert precision == Decimal("0")


class TestCalculateRecall:
    """Tests for recall calculation."""

    def test_full_recall(self) -> None:
        """Test 100% recall calculation."""
        service = RuleValidationService()

        recall = service.calculate_recall(10, 10)

        assert recall == Decimal("1.0000")

    def test_partial_recall(self) -> None:
        """Test partial recall calculation."""
        service = RuleValidationService()

        recall = service.calculate_recall(5, 10)

        assert recall == Decimal("0.5000")

    def test_empty_cluster_returns_zero(self) -> None:
        """Test that empty cluster returns zero recall."""
        service = RuleValidationService()

        recall = service.calculate_recall(0, 0)

        assert recall == Decimal("0")


class TestSampleFalsePositives:
    """Tests for false positive sampling."""

    def test_returns_samples(self) -> None:
        """Test that samples are returned."""
        service = RuleValidationService()
        transactions = [
            create_mock_transaction(1, "TESCO STORES"),
            create_mock_transaction(2, "TESCO BANK"),
            create_mock_transaction(3, "TESCO MOBILE"),
        ]
        cluster_ids = {1}

        samples = service.sample_false_positives(
            r"(?i)tesco", transactions, cluster_ids
        )

        assert len(samples) == 2
        assert "TESCO BANK" in samples
        assert "TESCO MOBILE" in samples

    def test_limits_samples(self) -> None:
        """Test that samples are limited."""
        service = RuleValidationService()
        transactions = [create_mock_transaction(i, f"TESCO {i}") for i in range(10)]
        cluster_ids: set[int] = set()  # None in cluster

        samples = service.sample_false_positives(
            r"(?i)tesco", transactions, cluster_ids, max_samples=3
        )

        assert len(samples) == 3

    def test_invalid_regex_returns_empty(self) -> None:
        """Test that invalid regex returns empty list."""
        service = RuleValidationService()
        transactions = [create_mock_transaction(1, "TESCO")]
        cluster_ids: set[int] = set()

        samples = service.sample_false_positives(
            r"(?i)tesco[", transactions, cluster_ids
        )

        assert samples == []


class TestFindConflicts:
    """Tests for conflict detection."""

    def test_no_conflicts_without_repository(self) -> None:
        """Test that no conflicts are found without repository."""
        service = RuleValidationService(rule_repository=None)
        transactions = [create_mock_transaction(1, "TESCO")]

        result = service.find_conflicts(r"(?i)tesco", transactions)

        assert result.has_conflicts is False

    def test_detects_overlapping_rule(self) -> None:
        """Test detection of overlapping rules."""
        mock_repo = MagicMock()
        existing_rule = MagicMock(spec=ClassificationRule)
        existing_rule.id = 1
        existing_rule.rule_expression = 'description =~ "(?i)tesco"'
        mock_repo.get_active_by_priority.return_value = [existing_rule]

        service = RuleValidationService(rule_repository=mock_repo)
        transactions = [
            create_mock_transaction(1, "TESCO STORES"),
            create_mock_transaction(2, "TESCO EXPRESS"),
        ]

        result = service.find_conflicts(r"(?i)tesco", transactions)

        assert result.has_conflicts is True
        assert len(result.conflicting_rules) == 1
        assert result.overlap_counts[1] == 2

    def test_no_overlap(self) -> None:
        """Test no conflict when rules don't overlap."""
        mock_repo = MagicMock()
        existing_rule = MagicMock(spec=ClassificationRule)
        existing_rule.id = 1
        existing_rule.rule_expression = 'description =~ "(?i)amazon"'
        mock_repo.get_active_by_priority.return_value = [existing_rule]

        service = RuleValidationService(rule_repository=mock_repo)
        transactions = [
            create_mock_transaction(1, "TESCO STORES"),
        ]

        result = service.find_conflicts(r"(?i)tesco", transactions)

        assert result.has_conflicts is False

    def test_invalid_pattern_returns_no_conflicts(self) -> None:
        """Test that invalid pattern returns no conflicts."""
        mock_repo = MagicMock()
        mock_repo.get_active_by_priority.return_value = []

        service = RuleValidationService(rule_repository=mock_repo)
        transactions = [create_mock_transaction(1, "TESCO")]

        result = service.find_conflicts(r"(?i)tesco[", transactions)

        assert result.has_conflicts is False


class TestExtractPatternFromExpression:
    """Tests for pattern extraction from rule expressions."""

    def test_extracts_simple_pattern(self) -> None:
        """Test extracting simple pattern."""
        service = RuleValidationService()

        pattern = service._extract_pattern_from_expression('description =~ "(?i)tesco"')

        assert pattern == "(?i)tesco"

    def test_extracts_complex_pattern(self) -> None:
        """Test extracting complex pattern."""
        service = RuleValidationService()

        pattern = service._extract_pattern_from_expression(
            'description =~ "(?i)(tesco|sainsbury)"'
        )

        assert pattern == "(?i)(tesco|sainsbury)"

    def test_returns_none_for_invalid_expression(self) -> None:
        """Test returning None for expression without pattern."""
        service = RuleValidationService()

        pattern = service._extract_pattern_from_expression("amount > 100")

        assert pattern is None


class TestTestPatternMatches:
    """Tests for pattern matching utility."""

    def test_matching_pattern(self) -> None:
        """Test pattern that matches."""
        service = RuleValidationService()

        result = service.test_pattern_matches(r"(?i)tesco", "TESCO STORES")

        assert result is True

    def test_non_matching_pattern(self) -> None:
        """Test pattern that doesn't match."""
        service = RuleValidationService()

        result = service.test_pattern_matches(r"(?i)amazon", "TESCO STORES")

        assert result is False

    def test_invalid_pattern_returns_false(self) -> None:
        """Test that invalid pattern returns False."""
        service = RuleValidationService()

        result = service.test_pattern_matches(r"(?i)tesco[", "TESCO")

        assert result is False
