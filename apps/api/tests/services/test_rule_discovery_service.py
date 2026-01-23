"""Tests for RuleDiscoveryService."""

import json
from unittest.mock import MagicMock, patch

import pytest

from finance_api.models.category import Category
from finance_api.services.high_frequency_analyzer import HighFrequencyPattern
from finance_api.services.rule_discovery_service import (
    PatternExplanation,
    RuleDiscoveryError,
    RuleDiscoveryService,
)
from finance_api.services.transaction_clustering_service import TransactionCluster


def create_mock_category(id: int, name: str, description: str = "") -> Category:
    """Create a mock Category for testing."""
    cat = MagicMock(spec=Category)
    cat.id = id
    cat.name = name
    cat.description = description
    return cat


def create_mock_cluster(
    cluster_key: str, samples: list[str], size: int = 10
) -> TransactionCluster:
    """Create a mock TransactionCluster for testing."""
    return TransactionCluster(
        cluster_key=cluster_key,
        cluster_hash=f"hash_{cluster_key}",
        transactions=[],
        sample_descriptions=samples,
    )


class TestFormatCategories:
    """Tests for category formatting."""

    def test_formats_categories(self) -> None:
        """Test formatting categories for prompt."""
        service = RuleDiscoveryService()
        categories = [
            create_mock_category(1, "Groceries", "Food shopping"),
            create_mock_category(2, "Entertainment", "Movies, games"),
        ]

        result = service._format_categories(categories)

        assert "1: Groceries - Food shopping" in result
        assert "2: Entertainment - Movies, games" in result

    def test_handles_no_description(self) -> None:
        """Test formatting category without description."""
        service = RuleDiscoveryService()
        cat = create_mock_category(1, "Groceries")
        cat.description = None

        result = service._format_categories([cat])

        assert "1: Groceries" in result


class TestFormatSamples:
    """Tests for sample formatting."""

    def test_formats_samples(self) -> None:
        """Test formatting sample descriptions."""
        service = RuleDiscoveryService()
        samples = ["TESCO STORES 1234", "TESCO EXPRESS"]

        result = service._format_samples(samples)

        assert "- TESCO STORES 1234" in result
        assert "- TESCO EXPRESS" in result


class TestParseResponse:
    """Tests for response parsing."""

    def test_parses_valid_json(self) -> None:
        """Test parsing valid JSON response."""
        service = RuleDiscoveryService()
        response = json.dumps({
            "pattern": "(?i)tesco",
            "category_name": "Groceries",
            "confidence": "high",
            "reasoning": "All Tesco transactions",
        })

        result = service._parse_response(response)

        assert result["pattern"] == "(?i)tesco"
        assert result["category_name"] == "Groceries"

    def test_handles_markdown_code_blocks(self) -> None:
        """Test parsing JSON wrapped in markdown code blocks."""
        service = RuleDiscoveryService()
        response = """```json
{
    "pattern": "(?i)tesco",
    "category_name": "Groceries",
    "confidence": "high",
    "reasoning": "All Tesco transactions"
}
```"""

        result = service._parse_response(response)

        assert result["pattern"] == "(?i)tesco"

    def test_raises_on_invalid_json(self) -> None:
        """Test error raised on invalid JSON."""
        service = RuleDiscoveryService()

        with pytest.raises(RuleDiscoveryError) as exc_info:
            service._parse_response("not valid json")

        assert "Failed to parse LLM response" in str(exc_info.value)


class TestValidateResponse:
    """Tests for response validation."""

    def test_validates_complete_response(self) -> None:
        """Test validation of complete response."""
        service = RuleDiscoveryService()
        data = {
            "pattern": "(?i)tesco",
            "category_name": "Groceries",
            "confidence": "high",
            "reasoning": "Test reasoning",
        }

        # Should not raise
        service._validate_response(data)

    def test_raises_on_missing_field(self) -> None:
        """Test error on missing required field."""
        service = RuleDiscoveryService()
        data = {
            "pattern": "(?i)tesco",
            "category_name": "Groceries",
            # Missing confidence and reasoning
        }

        with pytest.raises(RuleDiscoveryError) as exc_info:
            service._validate_response(data)

        assert "Missing required field" in str(exc_info.value)

    def test_raises_on_invalid_confidence(self) -> None:
        """Test error on invalid confidence level."""
        service = RuleDiscoveryService()
        data = {
            "pattern": "(?i)tesco",
            "category_name": "Groceries",
            "confidence": "very_high",  # Invalid
            "reasoning": "Test",
        }

        with pytest.raises(RuleDiscoveryError) as exc_info:
            service._validate_response(data)

        assert "Invalid confidence level" in str(exc_info.value)


class TestProposeRule:
    """Tests for rule proposal."""

    @patch("finance_api.services.rule_discovery_service.Anthropic")
    def test_proposes_rule_successfully(self, mock_anthropic_class: MagicMock) -> None:
        """Test successful rule proposal."""
        # Set up mock response
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps({
                    "pattern": "(?i)tesco",
                    "category_name": "Groceries",
                    "confidence": "high",
                    "reasoning": "All transactions are from Tesco supermarket",
                })
            )
        ]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client

        service = RuleDiscoveryService()
        cluster = create_mock_cluster(
            "TESCO", ["TESCO STORES 1234", "TESCO EXPRESS"]
        )
        categories = [create_mock_category(1, "Groceries")]

        result = service.propose_rule(cluster, categories)

        assert result.pattern == "(?i)tesco"
        assert result.category_name == "Groceries"
        assert result.confidence == "high"
        assert "Tesco" in result.reasoning

    @patch("finance_api.services.rule_discovery_service.Anthropic")
    def test_handles_api_error(self, mock_anthropic_class: MagicMock) -> None:
        """Test handling of API error."""
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API error")
        mock_anthropic_class.return_value = mock_client

        service = RuleDiscoveryService()
        cluster = create_mock_cluster("TESCO", ["TESCO"])
        categories = [create_mock_category(1, "Groceries")]

        with pytest.raises(RuleDiscoveryError) as exc_info:
            service.propose_rule(cluster, categories)

        assert "LLM API call failed" in str(exc_info.value)

    @patch("finance_api.services.rule_discovery_service.Anthropic")
    def test_handles_invalid_response(self, mock_anthropic_class: MagicMock) -> None:
        """Test handling of invalid LLM response."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="not json")]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client

        service = RuleDiscoveryService()
        cluster = create_mock_cluster("TESCO", ["TESCO"])
        categories = [create_mock_category(1, "Groceries")]

        with pytest.raises(RuleDiscoveryError):
            service.propose_rule(cluster, categories)


class TestRefineRule:
    """Tests for rule refinement."""

    @patch("finance_api.services.rule_discovery_service.Anthropic")
    def test_refines_rule_successfully(self, mock_anthropic_class: MagicMock) -> None:
        """Test successful rule refinement."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps({
                    "pattern": "(?i)tesco\\s+store",
                    "category_name": "Groceries",
                    "confidence": "high",
                    "reasoning": "More specific pattern to avoid TESCO BANK",
                })
            )
        ]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client

        service = RuleDiscoveryService()
        cluster = create_mock_cluster("TESCO", ["TESCO STORES 1234"])
        categories = [create_mock_category(1, "Groceries")]

        result = service.refine_rule(
            cluster,
            categories,
            previous_pattern="(?i)tesco",
            previous_category="Groceries",
            rejection_reason="Matches TESCO BANK transactions",
        )

        assert "store" in result.pattern.lower()
        assert result.category_name == "Groceries"


class TestProposeRulesBatch:
    """Tests for batch rule proposals."""

    @patch("finance_api.services.rule_discovery_service.Anthropic")
    def test_proposes_multiple_rules(self, mock_anthropic_class: MagicMock) -> None:
        """Test proposing rules for multiple clusters."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps({
                    "pattern": "(?i)test",
                    "category_name": "Test",
                    "confidence": "high",
                    "reasoning": "Test",
                })
            )
        ]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client

        service = RuleDiscoveryService()
        clusters = [
            create_mock_cluster("A", ["A1"]),
            create_mock_cluster("B", ["B1"]),
        ]
        categories = [create_mock_category(1, "Test")]

        results = service.propose_rules_batch(clusters, categories)

        assert len(results) == 2

    @patch("finance_api.services.rule_discovery_service.Anthropic")
    def test_handles_mixed_results(self, mock_anthropic_class: MagicMock) -> None:
        """Test batch with mixed success/failure."""
        mock_client = MagicMock()
        # First call succeeds, second fails
        mock_client.messages.create.side_effect = [
            MagicMock(
                content=[
                    MagicMock(
                        text=json.dumps({
                            "pattern": "(?i)test",
                            "category_name": "Test",
                            "confidence": "high",
                            "reasoning": "Test",
                        })
                    )
                ]
            ),
            Exception("API error"),
        ]
        mock_anthropic_class.return_value = mock_client

        service = RuleDiscoveryService()
        clusters = [
            create_mock_cluster("A", ["A1"]),
            create_mock_cluster("B", ["B1"]),
        ]
        categories = [create_mock_category(1, "Test")]

        results = service.propose_rules_batch(clusters, categories)

        assert len(results) == 2
        assert not isinstance(results[0], RuleDiscoveryError)
        assert isinstance(results[1], RuleDiscoveryError)


class TestModelProperty:
    """Tests for model property."""

    def test_returns_model_name(self) -> None:
        """Test that model property returns model name."""
        with patch("finance_api.services.rule_discovery_service.Anthropic"):
            service = RuleDiscoveryService(model="claude-sonnet-4-5-20250514")

        assert service.model == "claude-sonnet-4-5-20250514"


class TestConfiguration:
    """Tests for service configuration."""

    def test_default_temperature(self) -> None:
        """Test default temperature is deterministic."""
        with patch("finance_api.services.rule_discovery_service.Anthropic"):
            service = RuleDiscoveryService()

        assert service._temperature == 0.0

    def test_custom_temperature(self) -> None:
        """Test custom temperature setting."""
        with patch("finance_api.services.rule_discovery_service.Anthropic"):
            service = RuleDiscoveryService(temperature=0.7)

        assert service._temperature == 0.7


def create_mock_pattern(
    phrase: str = "TEST PATTERN",
    frequency: float = 0.15,
    transaction_count: int = 150,
) -> HighFrequencyPattern:
    """Create a mock HighFrequencyPattern for testing."""
    return HighFrequencyPattern(
        phrase=phrase,
        frequency=frequency,
        transaction_count=transaction_count,
        sample_descriptions=[f"Sample with {phrase} 1", f"Sample with {phrase} 2"],
        sample_transaction_ids=[1, 2],
    )


class TestExplainPattern:
    """Tests for pattern explanation."""

    @patch("finance_api.services.rule_discovery_service.Anthropic")
    def test_explains_pattern_successfully(
        self, mock_anthropic_class: MagicMock
    ) -> None:
        """Test successful pattern explanation."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps({
                    "explanation": "This is a bank savings round-up feature",
                    "suggested_category": "Savings",
                    "confidence": "high",
                    "reasoning": "Common bank artifact for automatic savings",
                })
            )
        ]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client

        service = RuleDiscoveryService()
        pattern = create_mock_pattern("ZAKUP PRZY KARTY")
        categories = [
            create_mock_category(1, "Groceries"),
            create_mock_category(2, "Savings"),
        ]

        result = service.explain_pattern(pattern, categories, total_transactions=1000)

        assert isinstance(result, PatternExplanation)
        assert result.explanation == "This is a bank savings round-up feature"
        assert result.suggested_category == "Savings"
        assert result.suggested_category_id == 2
        assert result.confidence == "high"
        assert "savings" in result.reasoning.lower()

    @patch("finance_api.services.rule_discovery_service.Anthropic")
    def test_handles_category_not_found(
        self, mock_anthropic_class: MagicMock
    ) -> None:
        """Test handling when suggested category is not in list."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps({
                    "explanation": "This is a subscription service",
                    "suggested_category": "Entertainment",
                    "confidence": "medium",
                    "reasoning": "Looks like streaming service",
                })
            )
        ]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client

        service = RuleDiscoveryService()
        pattern = create_mock_pattern()
        categories = [
            create_mock_category(1, "Groceries"),
            create_mock_category(2, "Savings"),
        ]

        result = service.explain_pattern(pattern, categories, total_transactions=1000)

        assert result.suggested_category == "Entertainment"
        assert result.suggested_category_id is None  # Not found

    @patch("finance_api.services.rule_discovery_service.Anthropic")
    def test_handles_api_error(self, mock_anthropic_class: MagicMock) -> None:
        """Test handling of API error."""
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API error")
        mock_anthropic_class.return_value = mock_client

        service = RuleDiscoveryService()
        pattern = create_mock_pattern()
        categories = [create_mock_category(1, "Test")]

        with pytest.raises(RuleDiscoveryError) as exc_info:
            service.explain_pattern(pattern, categories, total_transactions=1000)

        assert "LLM API call failed" in str(exc_info.value)

    @patch("finance_api.services.rule_discovery_service.Anthropic")
    def test_handles_invalid_json_response(
        self, mock_anthropic_class: MagicMock
    ) -> None:
        """Test handling of invalid JSON response."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="not valid json")]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client

        service = RuleDiscoveryService()
        pattern = create_mock_pattern()
        categories = [create_mock_category(1, "Test")]

        with pytest.raises(RuleDiscoveryError) as exc_info:
            service.explain_pattern(pattern, categories, total_transactions=1000)

        assert "Failed to parse LLM response" in str(exc_info.value)

    @patch("finance_api.services.rule_discovery_service.Anthropic")
    def test_handles_missing_fields(self, mock_anthropic_class: MagicMock) -> None:
        """Test handling of response with missing required fields."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps({
                    "explanation": "Some explanation",
                    # Missing: suggested_category, confidence, reasoning
                })
            )
        ]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client

        service = RuleDiscoveryService()
        pattern = create_mock_pattern()
        categories = [create_mock_category(1, "Test")]

        with pytest.raises(RuleDiscoveryError) as exc_info:
            service.explain_pattern(pattern, categories, total_transactions=1000)

        assert "Missing required field" in str(exc_info.value)

    @patch("finance_api.services.rule_discovery_service.Anthropic")
    def test_handles_invalid_confidence(
        self, mock_anthropic_class: MagicMock
    ) -> None:
        """Test handling of invalid confidence level."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps({
                    "explanation": "Test",
                    "suggested_category": "Test",
                    "confidence": "very_high",  # Invalid
                    "reasoning": "Test",
                })
            )
        ]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client

        service = RuleDiscoveryService()
        pattern = create_mock_pattern()
        categories = [create_mock_category(1, "Test")]

        with pytest.raises(RuleDiscoveryError) as exc_info:
            service.explain_pattern(pattern, categories, total_transactions=1000)

        assert "Invalid confidence level" in str(exc_info.value)

    @patch("finance_api.services.rule_discovery_service.Anthropic")
    def test_case_insensitive_category_matching(
        self, mock_anthropic_class: MagicMock
    ) -> None:
        """Test that category matching is case-insensitive."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps({
                    "explanation": "Test",
                    "suggested_category": "SAVINGS",  # Uppercase
                    "confidence": "high",
                    "reasoning": "Test",
                })
            )
        ]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client

        service = RuleDiscoveryService()
        pattern = create_mock_pattern()
        categories = [
            create_mock_category(1, "Groceries"),
            create_mock_category(2, "Savings"),  # Lowercase
        ]

        result = service.explain_pattern(pattern, categories, total_transactions=1000)

        assert result.suggested_category_id == 2


class TestPatternExplanationDataclass:
    """Tests for PatternExplanation dataclass."""

    def test_creates_pattern_explanation(self) -> None:
        """Test creating PatternExplanation instance."""
        explanation = PatternExplanation(
            explanation="This is a savings feature",
            suggested_category="Savings",
            suggested_category_id=5,
            confidence="high",
            reasoning="Common bank pattern",
            raw_response='{"test": "response"}',
        )

        assert explanation.explanation == "This is a savings feature"
        assert explanation.suggested_category == "Savings"
        assert explanation.suggested_category_id == 5
        assert explanation.confidence == "high"

    def test_creates_with_no_category_id(self) -> None:
        """Test creating PatternExplanation with no category ID."""
        explanation = PatternExplanation(
            explanation="Unknown pattern",
            suggested_category="Unknown",
            suggested_category_id=None,
            confidence="low",
            reasoning="Not sure",
            raw_response='{}',
        )

        assert explanation.suggested_category_id is None
