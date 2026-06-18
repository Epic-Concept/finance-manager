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
