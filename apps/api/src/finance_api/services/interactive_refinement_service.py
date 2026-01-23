"""InteractiveRefinementService for multi-turn conversational rule refinement."""

import json
import re
from dataclasses import dataclass

from anthropic import Anthropic

from finance_api.models.category import Category
from finance_api.models.transaction import Transaction
from finance_api.services.rule_validation_service import (
    RuleValidationService,
    ValidationResult,
)
from finance_api.services.transaction_clustering_service import TransactionCluster


@dataclass
class ProposedRule:
    """A single rule proposed by the LLM."""

    pattern: str
    category_id: int
    category_name: str
    confidence: str  # high/medium/low
    reasoning: str


@dataclass
class RefinementResponse:
    """Response from an LLM refinement turn."""

    message: str
    proposed_rules: list[ProposedRule]
    raw_response: str


class InteractiveRefinementError(Exception):
    """Raised when interactive refinement fails."""

    pass


REFINEMENT_SYSTEM_PROMPT = """You are a transaction classification expert helping to create regex patterns for categorizing bank transactions.

## Your Task
Help the user create classification rules for a cluster of similar transactions. You may propose multiple rules if the cluster contains transactions from different merchants that should be categorized differently.

## Cluster Context
Cluster key: {cluster_key}
Cluster size: {cluster_size} transactions
Sample descriptions:
{sample_descriptions}

## Available Categories
{category_list}

## Response Format
When proposing rules, include a JSON block in your response with this format:
```json
{{
    "proposals": [
        {{
            "pattern": "(?i)regex_pattern",
            "category_id": 1,
            "category_name": "Category Name",
            "confidence": "high|medium|low",
            "reasoning": "Why this pattern and category"
        }}
    ]
}}
```

## Guidelines
1. Start by analyzing the sample descriptions and proposing initial rules
2. When the user provides feedback, refine your proposals
3. You can propose multiple rules if the cluster is "polluted" (contains different merchant types)
4. Use (?i) for case-insensitive matching
5. Be specific to avoid false positives
6. Explain your reasoning clearly

## Conversation Flow
- First turn: Analyze cluster and propose initial rule(s)
- User feedback: Refine based on validation results and user comments
- Iterate until user is satisfied

Begin by analyzing the cluster and proposing your initial rule(s)."""


class InteractiveRefinementService:
    """Service for multi-turn conversational rule refinement.

    Enables iterative LLM-assisted pattern creation with support for
    multiple rules per cluster and automatic validation injection.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-5-20250514",
        temperature: float = 0.3,
        validation_service: RuleValidationService | None = None,
    ) -> None:
        """Initialize the service.

        Args:
            api_key: Anthropic API key. If None, uses ANTHROPIC_API_KEY env var.
            model: Claude model to use for conversations.
            temperature: Temperature for LLM responses.
            validation_service: Service for validating proposed patterns.
        """
        self._client = Anthropic(api_key=api_key)
        self._model = model
        self._temperature = temperature
        self._validation_service = validation_service or RuleValidationService()

    def _build_system_prompt(
        self,
        cluster: TransactionCluster,
        categories: list[Category],
    ) -> str:
        """Build the system prompt with cluster context and categories.

        Args:
            cluster: The transaction cluster being refined.
            categories: Available categories for classification.

        Returns:
            The formatted system prompt.
        """
        # Format sample descriptions
        samples = "\n".join(f"- {desc}" for desc in cluster.sample_descriptions)

        # Format category list
        category_lines = []
        for cat in categories:
            desc = f" - {cat.description}" if cat.description else ""
            category_lines.append(f"  {cat.id}: {cat.name}{desc}")
        category_list = "\n".join(category_lines)

        return REFINEMENT_SYSTEM_PROMPT.format(
            cluster_key=cluster.cluster_key,
            cluster_size=len(cluster.transactions),
            sample_descriptions=samples,
            category_list=category_list,
        )

    def _parse_response(
        self, response_text: str, categories: list[Category]
    ) -> RefinementResponse:
        """Parse LLM response to extract proposals.

        Args:
            response_text: Raw LLM response text.
            categories: Available categories for ID lookup.

        Returns:
            Parsed RefinementResponse with proposals.
        """
        proposed_rules: list[ProposedRule] = []

        # Try to extract JSON block from response
        json_match = re.search(
            r"```json\s*(.*?)\s*```", response_text, re.DOTALL | re.IGNORECASE
        )
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                proposals = data.get("proposals", [])

                # Build category lookup
                category_by_id = {cat.id: cat for cat in categories}
                category_by_name = {cat.name.lower(): cat for cat in categories}

                for prop in proposals:
                    # Resolve category
                    category_id = prop.get("category_id")
                    category_name = prop.get("category_name", "")

                    # Try ID first, then name
                    if category_id and category_id in category_by_id:
                        cat = category_by_id[category_id]
                    elif category_name.lower() in category_by_name:
                        cat = category_by_name[category_name.lower()]
                    else:
                        # Skip proposals with invalid categories
                        continue

                    proposed_rules.append(
                        ProposedRule(
                            pattern=prop.get("pattern", ""),
                            category_id=cat.id,
                            category_name=cat.name,
                            confidence=prop.get("confidence", "medium"),
                            reasoning=prop.get("reasoning", ""),
                        )
                    )
            except json.JSONDecodeError:
                pass  # No valid JSON found, return empty proposals

        return RefinementResponse(
            message=response_text,
            proposed_rules=proposed_rules,
            raw_response=response_text,
        )

    def start_session(
        self,
        cluster: TransactionCluster,
        categories: list[Category],
    ) -> RefinementResponse:
        """Start a new refinement session with initial proposal.

        Args:
            cluster: The transaction cluster to create rules for.
            categories: Available categories for classification.

        Returns:
            Initial LLM response with proposed rules.

        Raises:
            InteractiveRefinementError: If LLM call fails.
        """
        system_prompt = self._build_system_prompt(cluster, categories)

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=2048,
                temperature=self._temperature,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": "Please analyze this cluster and propose classification rules.",
                    }
                ],
            )
            first_block = response.content[0]
            response_text = first_block.text if hasattr(first_block, "text") else ""
            return self._parse_response(response_text, categories)

        except Exception as e:
            raise InteractiveRefinementError(f"Failed to start session: {e}") from e

    def continue_session(
        self,
        conversation_history: list[dict[str, str]],
        user_message: str,
        cluster: TransactionCluster,
        categories: list[Category],
    ) -> RefinementResponse:
        """Continue a refinement session with user feedback.

        Args:
            conversation_history: Previous messages [{role, content}].
            user_message: New user message/feedback.
            cluster: The transaction cluster being refined.
            categories: Available categories for classification.

        Returns:
            LLM response with updated proposals.

        Raises:
            InteractiveRefinementError: If LLM call fails.
        """
        system_prompt = self._build_system_prompt(cluster, categories)

        # Build messages list from history
        messages = []
        for msg in conversation_history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Add new user message
        messages.append({"role": "user", "content": user_message})

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=2048,
                temperature=self._temperature,
                system=system_prompt,
                messages=messages,  # type: ignore[arg-type]
            )
            first_block = response.content[0]
            response_text = first_block.text if hasattr(first_block, "text") else ""
            return self._parse_response(response_text, categories)

        except Exception as e:
            raise InteractiveRefinementError(f"Failed to continue session: {e}") from e

    def validate_proposals(
        self,
        proposals: list[ProposedRule],
        all_transactions: list[Transaction],
        cluster_transaction_ids: set[int],
    ) -> list[tuple[ProposedRule, ValidationResult]]:
        """Validate all proposals against transactions.

        Args:
            proposals: List of proposed rules to validate.
            all_transactions: All transactions to test against.
            cluster_transaction_ids: IDs of transactions in the target cluster.

        Returns:
            List of (proposal, validation_result) tuples.
        """
        results = []
        for proposal in proposals:
            validation = self._validation_service.test_rule(
                proposal.pattern, all_transactions, cluster_transaction_ids
            )
            results.append((proposal, validation))
        return results

    def format_validation_feedback(
        self,
        validation_results: list[tuple[ProposedRule, ValidationResult]],
    ) -> str:
        """Format validation results as a system message.

        Args:
            validation_results: List of (proposal, validation) tuples.

        Returns:
            Formatted string for injection into conversation.
        """
        parts = ["**Validation Results:**\n"]

        for i, (proposal, validation) in enumerate(validation_results, 1):
            if not validation.is_valid_regex:
                parts.append(
                    f"\n**Rule {i}** (`{proposal.pattern[:50]}...`)\n"
                    f"- Error: Invalid regex - {validation.regex_error}\n"
                )
                continue

            precision_pct = float(validation.precision) * 100
            coverage_pct = float(validation.coverage) * 100

            parts.append(
                f"\n**Rule {i}** (`{proposal.pattern}`)\n"
                f"- Category: {proposal.category_name}\n"
                f"- Matches: {validation.total_matches}\n"
                f"- True positives: {validation.true_positives}\n"
                f"- False positives: {validation.false_positives}\n"
                f"- Precision: {precision_pct:.1f}%\n"
                f"- Coverage: {coverage_pct:.1f}%\n"
            )

            if validation.sample_false_positives:
                parts.append("- Sample false positives:\n")
                for fp in validation.sample_false_positives[:3]:
                    parts.append(f"  - {fp}\n")

        return "".join(parts)
