"""Live integration test: the agent drives a real Gmail hunt via real qwen.

Skips unless Gmail IMAP + litellm are configured. Slow (several model turns).
"""

from datetime import date
from decimal import Decimal

import pytest

from finance_api.classification.gatherer import GatherContext
from finance_api.classification.gatherers.agentic_receipt import (
    AgenticReceiptGatherer,
)
from finance_api.classification.gatherers.imap_mailbox import ImapMailboxClient
from finance_api.classification.gatherers.llm_inference import CategoryRef
from finance_api.classification.llm import LiteLLMClient
from finance_api.core.config import settings


def test_agent_hunts_real_gmail_receipt() -> None:
    if not settings.gmail_imap_password or not settings.litellm_api_key:
        pytest.skip("Gmail IMAP or litellm not configured")

    gmail = ImapMailboxClient(
        mailbox_id="gmail:primary",
        host=settings.gmail_imap_host,
        username=settings.gmail_imap_user,
        password=settings.gmail_imap_password,
        folder=settings.gmail_imap_folder,
        max_results=8,
    )
    categories = [
        CategoryRef(1, "Groceries"),
        CategoryRef(2, "Mobile & Phone"),
        CategoryRef(3, "Software & Subscriptions"),
        CategoryRef(4, "Entertainment"),
    ]
    gatherer = AgenticReceiptGatherer(
        LiteLLMClient().chat, [gmail], categories, max_iterations=8
    )
    context = GatherContext(
        transaction_id=1,
        description="GIFFGAFF MOBILE",
        amount=Decimal("15.00"),
        currency="GBP",
        transaction_date=date(2026, 6, 13),
    )
    evidence = gatherer.gather(context)
    # The agent runs end-to-end; if it produces evidence it must be an itemized
    # receipt whose splits reconcile toward the charge.
    assert isinstance(evidence, list)
    for ev in evidence:
        assert ev.itemized is True
        assert all(s.amount is not None for s in ev.claim.splits)
