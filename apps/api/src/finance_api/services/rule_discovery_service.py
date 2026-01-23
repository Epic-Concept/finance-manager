"""RuleDiscoveryService for LLM-powered rule proposal generation."""

import json
from dataclasses import dataclass
from typing import Any

from anthropic import Anthropic

from finance_api.models.category import Category
from finance_api.services.high_frequency_analyzer import HighFrequencyPattern
from finance_api.services.transaction_clustering_service import TransactionCluster


@dataclass
class PatternExplanation:
    """LLM's explanation of a detected high-frequency pattern."""

    explanation: str  # What this pattern means
    suggested_category: str  # Suggested category name
    suggested_category_id: int | None  # Category ID if matched
    confidence: str  # high/medium/low
    reasoning: str  # Why this category
    raw_response: str  # Raw LLM response


@dataclass
class RuleProposalResult:
    """Result from LLM rule proposal."""

    pattern: str
    category_name: str
    confidence: str  # high/medium/low
    reasoning: str
    raw_response: str


class RuleDiscoveryError(Exception):
    """Raised when rule discovery fails."""

    pass


RULE_PROPOSAL_PROMPT = """You are a transaction classification expert. Your task is to propose a regex pattern that will match transactions from a specific merchant or category.

Given these sample transaction descriptions from a cluster of similar items:

{sample_descriptions}

And this category hierarchy (ID: Name - Description):
{category_list}

Propose a classification rule:
1. A regex pattern (Python re syntax) that matches these transactions
2. The most appropriate category from the list above
3. Your confidence level (high/medium/low)
4. Brief reasoning for your choices

Important guidelines for the regex pattern:
- Use (?i) at the start for case-insensitive matching
- Keep patterns simple and focused on the merchant/company name
- Avoid overly broad patterns that might match unrelated transactions
- Consider common variations in how the merchant appears

Respond in this exact JSON format (no other text):
{{
    "pattern": "(?i)merchant_pattern",
    "category_name": "Exact category name from the list",
    "confidence": "high|medium|low",
    "reasoning": "Brief explanation of why this pattern and category are appropriate"
}}

JSON response:"""


PATTERN_EXPLANATION_PROMPT = """You are a financial transaction analyst. A pattern has been detected that appears in many transactions from a personal bank account.

Pattern: "{pattern}"
Appears in {count} transactions ({frequency:.1%} of all transactions)

Sample transactions containing this pattern:
{samples}

Available categories:
{categories}

Please analyze this pattern and explain:
1. What does this pattern mean? (Is it a bank feature like savings round-up, automatic transfer, merchant name, etc.)
2. What category should transactions with this pattern be assigned to?
3. Why is this the appropriate category?

Respond in this exact JSON format (no other text):
{{
    "explanation": "Brief explanation of what this pattern represents",
    "suggested_category": "Exact category name from the list",
    "confidence": "high|medium|low",
    "reasoning": "Why this category is appropriate"
}}

JSON response:"""


REFINEMENT_PROMPT = """You are a transaction classification expert. A previous rule proposal was rejected, and you need to propose an improved version.

Original cluster samples:
{sample_descriptions}

Previous proposed pattern: {previous_pattern}
Previous proposed category: {previous_category}
Rejection reason: {rejection_reason}

Category hierarchy (ID: Name - Description):
{category_list}

Please propose an improved rule that addresses the rejection reason. Consider:
- Making the pattern more specific to avoid false positives
- Choosing a more accurate category
- Adding word boundaries or additional constraints to the pattern

Respond in this exact JSON format (no other text):
{{
    "pattern": "(?i)improved_pattern",
    "category_name": "Exact category name from the list",
    "confidence": "high|medium|low",
    "reasoning": "Brief explanation of the improvements made"
}}

JSON response:"""


class RuleDiscoveryService:
    """Service for discovering classification rules using LLM.

    Takes transaction clusters and uses Claude to propose regex patterns
    and category assignments for rule creation.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-opus-4-5-20251101",
        temperature: float = 0.0,
    ) -> None:
        """Initialize the service.

        Args:
            api_key: Anthropic API key. If None, uses ANTHROPIC_API_KEY env var.
            model: Claude model to use for rule proposals.
            temperature: Temperature for LLM responses (0.0 for deterministic).
        """
        self._client = Anthropic(api_key=api_key)
        self._model = model
        self._temperature = temperature

    def _format_categories(self, categories: list[Category]) -> str:
        """Format categories for the prompt.

        Args:
            categories: List of Category objects.

        Returns:
            Formatted string of categories.
        """
        lines = []
        for cat in categories:
            # Include ID and name, with description if available
            line = f"- {cat.id}: {cat.name}"
            if hasattr(cat, "description") and cat.description:
                line += f" - {cat.description}"
            lines.append(line)
        return "\n".join(lines)

    def _format_samples(self, samples: list[str]) -> str:
        """Format sample descriptions for the prompt.

        Args:
            samples: List of sample transaction descriptions.

        Returns:
            Formatted string of samples.
        """
        return "\n".join(f"- {sample}" for sample in samples)

    def _parse_response(self, response_text: str) -> dict[str, Any]:
        """Parse the LLM response as JSON.

        Args:
            response_text: Raw LLM response.

        Returns:
            Parsed JSON dictionary.

        Raises:
            RuleDiscoveryError: If response is not valid JSON.
        """
        text = response_text.strip()

        # Handle potential markdown code blocks
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            return json.loads(text)  # type: ignore[no-any-return]
        except json.JSONDecodeError as e:
            raise RuleDiscoveryError(
                f"Failed to parse LLM response as JSON: {e}\nResponse: {text}"
            ) from e

    def _validate_response(self, data: dict[str, Any]) -> None:
        """Validate the response structure.

        Args:
            data: Parsed JSON data.

        Raises:
            RuleDiscoveryError: If required fields are missing.
        """
        required_fields = ["pattern", "category_name", "confidence", "reasoning"]
        for field in required_fields:
            if field not in data:
                raise RuleDiscoveryError(f"Missing required field: {field}")

        if data["confidence"] not in ("high", "medium", "low"):
            raise RuleDiscoveryError(
                f"Invalid confidence level: {data['confidence']}. "
                "Must be high, medium, or low."
            )

    def propose_rule(
        self,
        cluster: TransactionCluster,
        categories: list[Category],
    ) -> RuleProposalResult:
        """Propose a classification rule for a transaction cluster.

        Args:
            cluster: The transaction cluster to create a rule for.
            categories: List of available categories.

        Returns:
            RuleProposalResult with the proposed pattern and category.

        Raises:
            RuleDiscoveryError: If rule proposal fails.
        """
        prompt = RULE_PROPOSAL_PROMPT.format(
            sample_descriptions=self._format_samples(cluster.sample_descriptions),
            category_list=self._format_categories(categories),
        )

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=1024,
                temperature=self._temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            response_text = response.content[0].text  # type: ignore[union-attr]
        except Exception as e:
            raise RuleDiscoveryError(f"LLM API call failed: {e}") from e

        data = self._parse_response(response_text)
        self._validate_response(data)

        return RuleProposalResult(
            pattern=str(data["pattern"]),
            category_name=str(data["category_name"]),
            confidence=str(data["confidence"]),
            reasoning=str(data["reasoning"]),
            raw_response=response_text,
        )

    def refine_rule(
        self,
        cluster: TransactionCluster,
        categories: list[Category],
        previous_pattern: str,
        previous_category: str,
        rejection_reason: str,
    ) -> RuleProposalResult:
        """Refine a rejected rule proposal.

        Args:
            cluster: The transaction cluster.
            categories: List of available categories.
            previous_pattern: The previously proposed pattern.
            previous_category: The previously proposed category.
            rejection_reason: Why the previous proposal was rejected.

        Returns:
            RuleProposalResult with the refined pattern and category.

        Raises:
            RuleDiscoveryError: If refinement fails.
        """
        prompt = REFINEMENT_PROMPT.format(
            sample_descriptions=self._format_samples(cluster.sample_descriptions),
            previous_pattern=previous_pattern,
            previous_category=previous_category,
            rejection_reason=rejection_reason,
            category_list=self._format_categories(categories),
        )

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=1024,
                temperature=self._temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            response_text = response.content[0].text  # type: ignore[union-attr]
        except Exception as e:
            raise RuleDiscoveryError(f"LLM API call failed: {e}") from e

        data = self._parse_response(response_text)
        self._validate_response(data)

        return RuleProposalResult(
            pattern=str(data["pattern"]),
            category_name=str(data["category_name"]),
            confidence=str(data["confidence"]),
            reasoning=str(data["reasoning"]),
            raw_response=response_text,
        )

    def propose_rules_batch(
        self,
        clusters: list[TransactionCluster],
        categories: list[Category],
    ) -> list[RuleProposalResult | RuleDiscoveryError]:
        """Propose rules for multiple clusters.

        Args:
            clusters: List of transaction clusters.
            categories: List of available categories.

        Returns:
            List of RuleProposalResult or RuleDiscoveryError for each cluster.
        """
        results: list[RuleProposalResult | RuleDiscoveryError] = []
        for cluster in clusters:
            try:
                results.append(self.propose_rule(cluster, categories))
            except RuleDiscoveryError as e:
                results.append(e)
        return results

    def explain_pattern(
        self,
        pattern: HighFrequencyPattern,
        categories: list[Category],
        total_transactions: int,
    ) -> PatternExplanation:
        """Ask LLM to explain a detected high-frequency pattern.

        Args:
            pattern: The detected pattern to explain.
            categories: List of available categories.
            total_transactions: Total number of transactions for frequency calculation.

        Returns:
            PatternExplanation with the LLM's analysis.

        Raises:
            RuleDiscoveryError: If explanation fails.
        """
        prompt = PATTERN_EXPLANATION_PROMPT.format(
            pattern=pattern.phrase,
            count=pattern.transaction_count,
            frequency=pattern.frequency,
            samples=self._format_samples(pattern.sample_descriptions),
            categories=self._format_categories(categories),
        )

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=1024,
                temperature=self._temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            response_text = response.content[0].text  # type: ignore[union-attr]
        except Exception as e:
            raise RuleDiscoveryError(f"LLM API call failed: {e}") from e

        data = self._parse_response(response_text)

        # Validate required fields
        required_fields = ["explanation", "suggested_category", "confidence", "reasoning"]
        for field in required_fields:
            if field not in data:
                raise RuleDiscoveryError(f"Missing required field: {field}")

        if data["confidence"] not in ("high", "medium", "low"):
            raise RuleDiscoveryError(
                f"Invalid confidence level: {data['confidence']}. "
                "Must be high, medium, or low."
            )

        # Try to match category name to ID
        suggested_category_id: int | None = None
        suggested_category_name = str(data["suggested_category"])
        for cat in categories:
            if cat.name.lower() == suggested_category_name.lower():
                suggested_category_id = cat.id
                break

        return PatternExplanation(
            explanation=str(data["explanation"]),
            suggested_category=suggested_category_name,
            suggested_category_id=suggested_category_id,
            confidence=str(data["confidence"]),
            reasoning=str(data["reasoning"]),
            raw_response=response_text,
        )

    @property
    def model(self) -> str:
        """Return the model being used."""
        return self._model
