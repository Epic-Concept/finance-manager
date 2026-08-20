"""Unit tests for the production engine factory (config-driven composition)."""

from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy.orm import Session

from finance_api.classification.engine import ClassificationEngine
from finance_api.classification.factory import build_engine, build_gatherers
from finance_api.classification.gatherers.agentic_receipt import AgenticReceiptGatherer
from finance_api.classification.gatherers.history import HistoryGatherer
from finance_api.classification.gatherers.llm_inference import LLMInferenceGatherer
from finance_api.classification.gatherers.rules import RuleGatherer
from finance_api.classification.gatherers.web_lookup import WebLookupGatherer


def _settings(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "litellm_base_url": "http://gb10:4000/v1",
        "litellm_api_key": "",
        "litellm_model": "qwen",
        "litellm_max_tokens": 2048,
        "litellm_timeout_seconds": 60.0,
        "brave_api_key": "",
        "brave_base_url": "https://brave",
        "gmail_imap_user": "",
        "gmail_imap_password": "",
        "gmail_imap_host": "imap.gmail.com",
        "gmail_imap_folder": "\\All",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _types(gatherers: list[object]) -> set[type]:
    return {type(g) for g in gatherers}


def test_minimal_config_has_only_rules_and_history(db_session: Session) -> None:
    types = _types(build_gatherers(db_session, _settings()))
    assert types == {RuleGatherer, HistoryGatherer}


def test_llm_key_adds_inference_gatherer(db_session: Session) -> None:
    types = _types(build_gatherers(db_session, _settings(litellm_api_key="k")))
    assert LLMInferenceGatherer in types
    assert WebLookupGatherer not in types  # needs brave too


def test_brave_plus_llm_adds_web_lookup(db_session: Session) -> None:
    types = _types(
        build_gatherers(db_session, _settings(litellm_api_key="k", brave_api_key="b"))
    )
    assert WebLookupGatherer in types


def test_gmail_plus_llm_adds_agentic_receipt(db_session: Session) -> None:
    types = _types(
        build_gatherers(
            db_session,
            _settings(
                litellm_api_key="k", gmail_imap_user="u", gmail_imap_password="p"
            ),
        )
    )
    assert AgenticReceiptGatherer in types


def test_build_engine_returns_engine(db_session: Session) -> None:
    engine = build_engine(db_session, _settings())
    assert isinstance(engine, ClassificationEngine)
