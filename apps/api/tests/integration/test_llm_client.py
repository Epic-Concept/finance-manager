"""Integration test for the local LLM client against the litellm gateway.

Skips unless a litellm API key is configured and the endpoint is reachable, so
the suite still runs offline.
"""

from datetime import date
from decimal import Decimal

import httpx
import pytest

from finance_api.classification.gatherer import GatherContext
from finance_api.classification.gatherers.llm_inference import (
    CategoryRef,
    LLMInferenceGatherer,
)
from finance_api.classification.llm import LiteLLMClient, extract_json
from finance_api.core.config import settings


@pytest.fixture(scope="module")
def live_client() -> LiteLLMClient:
    if not settings.litellm_api_key:
        pytest.skip("LITELLM_API_KEY not configured")
    client = LiteLLMClient()
    try:
        client.complete("Reply with JSON only.", 'Output {"ok": true}')
    except (httpx.HTTPError, KeyError) as exc:
        pytest.skip(f"litellm endpoint not reachable: {exc}")
    return client


def test_client_returns_parseable_json(live_client: LiteLLMClient) -> None:
    content = live_client.complete(
        "You output only JSON.",
        'Output exactly {"category_id": 5} and nothing else.',
    )
    data = extract_json(content)
    assert data.get("category_id") == 5


def test_receipt_extraction_against_live_model(live_client: LiteLLMClient) -> None:
    from finance_api.classification.receipt import ReceiptExtractor

    email = (
        "Your Amazon.co.uk order is confirmed.\n"
        "Order #203-9988\n"
        "1x Python Crash Course (Book) - GBP 24.99\n"
        "1x USB-C Cable 2m - GBP 9.99\n"
        "Order Total: GBP 34.98\n"
    )
    categories = [
        CategoryRef(5, "Books"),
        CategoryRef(7, "Electronics"),
        CategoryRef(9, "Groceries"),
    ]
    receipt = ReceiptExtractor(live_client).extract(email, categories)
    assert len(receipt.items) >= 1
    assert receipt.items_total > 0
    # every assigned category must be one of the allowed ids (or None)
    assert all(
        i.category_id in {5, 7, 9} or i.category_id is None for i in receipt.items
    )


def test_brave_search_live() -> None:
    from finance_api.classification.web_search import BraveWebSearch

    if not settings.brave_api_key:
        pytest.skip("BRAVE_API_KEY not configured")
    results = BraveWebSearch().search("Seeed Studio electronics")
    assert results, "expected Brave results"
    assert results[0].title and results[0].url


def test_web_lookup_end_to_end_brave_plus_qwen(live_client: LiteLLMClient) -> None:
    """Full real path: Brave web search + qwen agentic loop, no stubs."""
    from finance_api.classification.gatherers.web_lookup import WebLookupGatherer
    from finance_api.classification.web_search import BraveWebSearch

    if not settings.brave_api_key:
        pytest.skip("BRAVE_API_KEY not configured")

    categories = [
        CategoryRef(1, "Groceries"),
        CategoryRef(3, "Electronics & Hardware"),
        CategoryRef(9, "Eating Out"),
    ]
    gatherer = WebLookupGatherer(live_client.chat, BraveWebSearch(), categories)
    context = GatherContext(
        transaction_id=1,
        description="SEEED STUDIO SHENZHEN",
        amount=Decimal("48.00"),
        currency="GBP",
        transaction_date=date(2026, 6, 6),
    )
    evidence = gatherer.gather(context)
    # Real research should resolve Seeed -> Electronics (id 3).
    assert evidence and evidence[0].claim.category_ids == (3,)


def test_inference_gatherer_against_live_model(live_client: LiteLLMClient) -> None:
    """Real qwen drives the tool loop over stubbed Seeed search results."""
    from finance_api.classification.gatherers.web_lookup import (
        SearchResult,
        WebLookupGatherer,
    )

    class _StubSearch:
        def search(self, query: str) -> list[SearchResult]:
            return [
                SearchResult(
                    title="Seeed Studio",
                    url="https://seeedstudio.com",
                    snippet=(
                        "Seeed Studio is an electronics hardware company selling "
                        "open-source dev boards, sensors and IoT modules. Only hardware."
                    ),
                )
            ]

    categories = [
        CategoryRef(1, "Groceries"),
        CategoryRef(3, "Electronics & Hardware"),
        CategoryRef(9, "Eating Out"),
    ]
    gatherer = WebLookupGatherer(live_client.chat, _StubSearch(), categories)
    context = GatherContext(
        transaction_id=1,
        description="SEEED STUDIO SHENZHEN",
        amount=Decimal("48.00"),
        currency="GBP",
        transaction_date=date(2026, 6, 6),
    )
    evidence = gatherer.gather(context)
    # The model should research and land on Electronics (3); if confident +
    # single-category it is STRONG, otherwise WEAK -- but it must pick id 3.
    assert evidence == [] or evidence[0].claim.category_ids == (3,)


def test_inference_gatherer_against_live_model(live_client: LiteLLMClient) -> None:
    categories = [
        CategoryRef(5, "Groceries"),
        CategoryRef(7, "Transport"),
        CategoryRef(9, "Eating Out"),
    ]
    gatherer = LLMInferenceGatherer(live_client, categories)
    context = GatherContext(
        transaction_id=1,
        description="TESCO STORES 2911 LONDON",
        amount=Decimal("23.40"),
        currency="GBP",
        transaction_date=date(2026, 6, 1),
    )
    evidence = gatherer.gather(context)
    # The model should pick a valid category; gatherer guarantees WEAK if it does.
    assert evidence == [] or (
        evidence[0].claim.category_ids[0] in {5, 7, 9}
        and evidence[0].strength.name == "WEAK"
    )
