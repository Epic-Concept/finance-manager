"""Tests for RuleDiscoveryService."""

import json
from unittest.mock import MagicMock, patch

import pytest

from finance_api.models.category import Category
from finance_api.services.rule_discovery_service import (
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
