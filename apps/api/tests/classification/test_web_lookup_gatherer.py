"""Tests for the agentic web-lookup gatherer (task 5.1).

For an unknown merchant, the LLM researches it via a web_search tool and
concludes a category. A confident, single-category merchant (e.g. Seeed Studio,
which sells only electronics) yields STRONG evidence; anything ambiguous is WEAK.
Tested with an injected fake chat function and fake web search (no network).
"""

import json
from datetime import date
from decimal import Decimal

from finance_api.classification.evidence import EvidenceType, StrengthTier
from finance_api.classification.gatherer import GatherContext
from finance_api.classification.gatherers.llm_inference import CategoryRef
from finance_api.classification.gatherers.web_lookup import (
    SearchResult,
    WebLookupGatherer,
)

CATEGORIES = [
    CategoryRef(1, "Groceries"),
    CategoryRef(3, "Electronics & Hardware"),
    CategoryRef(9, "Eating Out"),
]


class _FakeWebSearch:
    def __init__(self, results: list[SearchResult]) -> None:
        self._results = results
        self.queries: list[str] = []

    def search(self, query: str) -> list[SearchResult]:
        self.queries.append(query)
        return list(self._results)


def _scripted_chat(*messages_out):
    """Return a chat_fn that yields the given assistant messages in order."""
    responses = iter(messages_out)

    def chat(messages, tools):
        return next(responses)

    return chat


def _tool_call(name: str, args: dict):
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "c1",
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(args)},
            }
        ],
    }


def _final(payload: dict):
    return {"role": "assistant", "content": json.dumps(payload), "tool_calls": None}


def _context() -> GatherContext:
    return GatherContext(
        transaction_id=1,
        description="SEEED STUDIO SHENZHEN",
        amount=Decimal("48.00"),
        currency="GBP",
        transaction_date=date(2026, 6, 6),
    )


SEEED_RESULTS = [
    SearchResult(
        title="Seeed Studio",
        url="https://seeedstudio.com",
        snippet="Seeed Studio sells open-source hardware, electronics modules and IoT devices.",
    )
]


class TestWebLookupGatherer:
    def test_confident_single_category_merchant_is_strong(self) -> None:
        web = _FakeWebSearch(SEEED_RESULTS)
        chat = _scripted_chat(
            _tool_call("web_search", {"query": "Seeed Studio"}),
            _final(
                {
                    "category_id": 3,
                    "single_category_merchant": True,
                    "confidence": "high",
                }
            ),
        )
        gatherer = WebLookupGatherer(chat, web, CATEGORIES)
        evidence = gatherer.gather(_context())
        assert len(evidence) == 1
        ev = evidence[0]
        assert ev.evidence_type is EvidenceType.WEB_LOOKUP
        assert ev.strength is StrengthTier.STRONG
        assert ev.claim.category_ids == (3,)
        assert web.queries  # the agent actually searched

    def test_low_confidence_is_weak(self) -> None:
        chat = _scripted_chat(
            _final(
                {
                    "category_id": 3,
                    "single_category_merchant": True,
                    "confidence": "low",
                }
            )
        )
        gatherer = WebLookupGatherer(chat, _FakeWebSearch([]), CATEGORIES)
        assert gatherer.gather(_context())[0].strength is StrengthTier.WEAK

    def test_multi_category_merchant_is_weak(self) -> None:
        chat = _scripted_chat(
            _final(
                {
                    "category_id": 3,
                    "single_category_merchant": False,
                    "confidence": "high",
                }
            )
        )
        gatherer = WebLookupGatherer(chat, _FakeWebSearch([]), CATEGORIES)
        assert gatherer.gather(_context())[0].strength is StrengthTier.WEAK

    def test_category_not_in_set_emits_nothing(self) -> None:
        chat = _scripted_chat(
            _final(
                {
                    "category_id": 999,
                    "single_category_merchant": True,
                    "confidence": "high",
                }
            )
        )
        gatherer = WebLookupGatherer(chat, _FakeWebSearch([]), CATEGORIES)
        assert gatherer.gather(_context()) == []

    def test_unparseable_final_emits_nothing(self) -> None:
        chat = _scripted_chat(
            {"role": "assistant", "content": "no idea", "tool_calls": None}
        )
        gatherer = WebLookupGatherer(chat, _FakeWebSearch([]), CATEGORIES)
        assert gatherer.gather(_context()) == []
