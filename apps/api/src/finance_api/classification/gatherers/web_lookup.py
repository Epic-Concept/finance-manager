"""The agentic web-lookup gatherer (task 5.1).

For a merchant the rules/history don't know, the local LLM researches it with a
``web_search`` tool (agentic loop) and concludes a category. The key payoff:
many merchants sell exactly one class of goods (e.g. Seeed Studio = electronics),
so a confident single-category finding resolves the category without a receipt.

Evidence strength is conservative: only a *confident* finding about a
*single-category* merchant is STRONG (enough to auto-apply for an unknown
merchant); everything else is WEAK (a suggestion for review). The web search
backend is injected behind ``WebSearch`` (a search API or MCP server adapter).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from finance_api.classification.evidence import (
    Claim,
    Evidence,
    EvidenceType,
    StrengthTier,
)
from finance_api.classification.gatherer import GatherContext, Gatherer
from finance_api.classification.gatherers.llm_inference import CategoryRef
from finance_api.classification.llm import ChatFn, extract_json, run_tool_loop

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You identify the spending category for a bank transaction whose merchant is "
    "unknown. Use the web_search tool to research what the merchant sells. Then "
    'respond ONLY with JSON: {"category_id": <int from the allowed list>, '
    '"single_category_merchant": <true if the merchant sells essentially one '
    'class of goods>, "confidence": "high"|"medium"|"low"}.'
)

_WEB_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the web for information about a merchant.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
}


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str


class WebSearch(Protocol):
    """A web search backend (search API or MCP server adapter)."""

    def search(self, query: str) -> list[SearchResult]: ...


class WebLookupGatherer(Gatherer):
    """Researches an unknown merchant on the web to infer its category."""

    produced_types = frozenset({EvidenceType.WEB_LOOKUP})

    def __init__(
        self,
        chat_fn: ChatFn,
        web_search: WebSearch,
        categories: list[CategoryRef],
        max_iterations: int = 4,
    ) -> None:
        self._chat = chat_fn
        self._web = web_search
        self._categories = categories
        self._valid_ids = {c.id for c in categories}
        self._max_iterations = max_iterations

    def _run_search(self, args: dict[str, object]) -> str:
        query = str(args.get("query", ""))
        results = self._web.search(query)
        if not results:
            return "No results."
        return "\n".join(f"- {r.title}: {r.snippet} ({r.url})" for r in results)

    def _build_user_prompt(self, description: str) -> str:
        catalog = "\n".join(f"- {c.id}: {c.name}" for c in self._categories)
        return (
            f"Merchant (from bank description): {description}\n\n"
            f"Allowed categories (id: name):\n{catalog}"
        )

    def gather(self, context: GatherContext) -> list[Evidence]:
        messages: list[dict[str, object]] = [
            {"role": "system", "content": _SYSTEM},
            {
                "role": "user",
                "content": self._build_user_prompt(context.description or ""),
            },
        ]
        try:
            final = run_tool_loop(
                self._chat,
                {"web_search": self._run_search},
                messages,
                tools=[_WEB_SEARCH_TOOL],
                max_iterations=self._max_iterations,
            )
        except Exception as exc:  # noqa: BLE001 - gatherers degrade, never crash
            logger.warning("web lookup failed: %s", exc)
            return []

        try:
            data = extract_json(final)
        except ValueError:
            return []

        category_id = data.get("category_id")
        if not isinstance(category_id, int) or category_id not in self._valid_ids:
            return []

        confident = str(data.get("confidence", "")).lower() == "high"
        single_category = bool(data.get("single_category_merchant", False))
        strength = (
            StrengthTier.STRONG if confident and single_category else StrengthTier.WEAK
        )

        return [
            Evidence(
                claim=Claim.single_category(category_id),
                evidence_type=EvidenceType.WEB_LOOKUP,
                source="web_lookup",
                strength=strength,
                itemized=False,
            )
        ]
