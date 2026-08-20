"""Compose a production ``ClassificationEngine`` from configuration.

Always wires the cheap DB-backed gatherers (rules, history). The expensive
agentic gatherers are added only when their backend is configured:

- LLM inference   -> requires the local LLM gateway (``litellm_api_key``)
- web lookup      -> requires the LLM gateway **and** Brave (``brave_api_key``)
- agentic receipt -> requires the LLM gateway **and** Gmail IMAP credentials

so the engine runs with whatever backends are available and degrades cleanly.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from finance_api.classification.db_sources import DbHistorySource, DbRuleSource
from finance_api.classification.engine import (
    ClassificationEngine,
    KeywordMerchantClassifier,
)
from finance_api.classification.gatherer import Gatherer
from finance_api.classification.gatherers.agentic_receipt import AgenticReceiptGatherer
from finance_api.classification.gatherers.history import HistoryGatherer
from finance_api.classification.gatherers.llm_inference import (
    CategoryRef,
    LLMInferenceGatherer,
)
from finance_api.classification.gatherers.mailbox import MultiMailboxSource
from finance_api.classification.gatherers.receipt import ReceiptGatherer
from finance_api.classification.gatherers.rules import RuleGatherer
from finance_api.classification.gatherers.web_lookup import WebLookupGatherer
from finance_api.classification.llm import LiteLLMClient
from finance_api.classification.mailbox_factory import build_mailbox_clients
from finance_api.classification.policy import EvidencePolicy
from finance_api.classification.receipt import ReceiptExtractor
from finance_api.classification.web_search import BraveWebSearch
from finance_api.core.config import Settings
from finance_api.core.config import settings as default_settings
from finance_api.models.category import Category

# Merchants known to sell mixed baskets, so a single category needs itemized proof.
DEFAULT_SPLITTABLE_KEYWORDS = [
    "BIEDRONKA",
    "LIDL",
    "AUCHAN",
    "CARREFOUR",
    "KAUFLAND",
    "ZABKA",
    "ALLEGRO",
    "AMAZON",
]


def _load_categories(session: Session) -> list[CategoryRef]:
    return [
        CategoryRef(id=c.id, name=c.name) for c in session.scalars(select(Category))
    ]


def build_gatherers(
    session: Session, settings: Settings = default_settings
) -> list[Gatherer]:
    """Build the configured gatherer list (cheap first)."""
    gatherers: list[Gatherer] = [
        RuleGatherer(DbRuleSource(session)),
        HistoryGatherer(DbHistorySource(session)),
    ]

    categories: list[CategoryRef] | None = None

    def cats() -> list[CategoryRef]:
        nonlocal categories
        if categories is None:
            categories = _load_categories(session)
        return categories

    def _llm() -> LiteLLMClient:
        return LiteLLMClient(
            base_url=settings.litellm_base_url,
            api_key=settings.litellm_api_key,
            model=settings.litellm_model,
            max_tokens=settings.litellm_max_tokens,
            timeout=settings.litellm_timeout_seconds,
        )

    if settings.litellm_api_key:
        gatherers.append(LLMInferenceGatherer(_llm(), cats()))

        if settings.brave_api_key:
            web = BraveWebSearch(
                api_key=settings.brave_api_key, base_url=settings.brave_base_url
            )
            gatherers.append(WebLookupGatherer(_llm().chat, web, cats()))

        mailbox_clients = build_mailbox_clients(session, settings)
        if mailbox_clients:
            mailbox_source = MultiMailboxSource(mailbox_clients)
            gatherers.append(
                ReceiptGatherer(mailbox_source, ReceiptExtractor(_llm()), cats())
            )
            gatherers.append(
                AgenticReceiptGatherer(_llm().chat, mailbox_clients, cats())
            )

    return gatherers


def build_engine(
    session: Session, settings: Settings = default_settings
) -> ClassificationEngine:
    """Build a ready-to-run engine wired to the configured backends."""
    return ClassificationEngine(
        gatherers=build_gatherers(session, settings),
        policy=EvidencePolicy(),
        merchant_classifier=KeywordMerchantClassifier(DEFAULT_SPLITTABLE_KEYWORDS),
    )
