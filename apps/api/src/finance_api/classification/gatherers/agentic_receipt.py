"""The agentic receipt gatherer: the LLM drives the mailbox hunt.

Instead of a fixed query, the local LLM is given two tools — search_mailbox and
read_email — and composes its own searches across the household mailboxes, reads
candidate emails, identifies the actual receipt, and extracts the itemized
split. The objective reconciliation check (line items vs the charge) still sets
the evidence strength, so a wrong pick degrades honestly to review.
"""

from __future__ import annotations

import json
import logging
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from finance_api.classification.evidence import (
    Claim,
    Evidence,
    EvidenceType,
    Split,
)
from finance_api.classification.gatherer import GatherContext, Gatherer
from finance_api.classification.gatherers.llm_inference import CategoryRef
from finance_api.classification.gatherers.mailbox import (
    MailboxClient,
    RawEmail,
    merchant_terms,
    strip_html,
)
from finance_api.classification.llm import ChatFn, extract_json, run_tool_loop
from finance_api.classification.receipt import reconciliation_tier

logger = logging.getLogger(__name__)

_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search_mailbox",
        "description": (
            "Search the household mailboxes for emails matching a query within a "
            "number of days around the transaction date. Returns candidate "
            "metadata (id, mailbox, subject, sender, date)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "search terms"},
                "days": {"type": "integer", "description": "+/- days around the txn"},
            },
            "required": ["query"],
        },
    },
}

_READ_TOOL = {
    "type": "function",
    "function": {
        "name": "read_email",
        "description": "Read the full text body of a candidate email by mailbox and id.",
        "parameters": {
            "type": "object",
            "properties": {
                "mailbox": {"type": "string"},
                "id": {"type": "string"},
            },
            "required": ["mailbox", "id"],
        },
    },
}


def _system_prompt(context: GatherContext, categories: list[CategoryRef]) -> str:
    catalog = "\n".join(f"- {c.id}: {c.name}" for c in categories)
    return (
        "You find the purchase receipt for a bank transaction and extract its "
        "line items. Use search_mailbox to look across the household mailboxes "
        "(try the merchant name, sender domain, or amount; widen the days if "
        "needed) and read_email to open promising candidates. Identify the email "
        "whose order/receipt total matches the charge.\n\n"
        f"Transaction: {context.description!r}, amount {context.amount} "
        f"{context.currency}, date {context.transaction_date}.\n\n"
        f"Allowed categories (id: name):\n{catalog}\n\n"
        "When done, respond ONLY with JSON: "
        '{"found": true/false, "merchant": str, "currency": str, "items": '
        '[{"description": str, "amount": number, "category_id": int}]}. '
        'If no matching receipt exists, respond {"found": false}.'
    )


class AgenticReceiptGatherer(Gatherer):
    """Emits itemized RECEIPT evidence, with the LLM driving the mailbox search."""

    produced_types = frozenset({EvidenceType.RECEIPT})

    def __init__(
        self,
        chat_fn: ChatFn,
        mailbox_clients: list[MailboxClient],
        categories: list[CategoryRef],
        max_iterations: int = 8,
        default_days: int = 7,
    ) -> None:
        self._chat = chat_fn
        self._clients = mailbox_clients
        self._categories = categories
        self._valid_ids = {c.id for c in categories}
        self._max_iterations = max_iterations
        self._default_days = default_days

    def gather(self, context: GatherContext) -> list[Evidence]:
        cache: dict[tuple[str, str], RawEmail] = {}

        def search_mailbox(args: dict[str, Any]) -> str:
            query = str(args.get("query", ""))
            days = int(args.get("days", self._default_days))
            terms = merchant_terms(query) or query.split()
            since = context.transaction_date - timedelta(days=days)
            until = context.transaction_date + timedelta(days=days)
            candidates: list[dict[str, str]] = []
            for client in self._clients:
                for email in client.search(terms, since, until):
                    cache[(email.mailbox, email.message_id)] = email
                    candidates.append(
                        {
                            "id": email.message_id,
                            "mailbox": email.mailbox,
                            "subject": email.subject,
                            "sender": email.sender,
                            "date": email.date.isoformat(),
                        }
                    )
            return json.dumps(candidates)

        def read_email(args: dict[str, Any]) -> str:
            key = (str(args.get("mailbox", "")), str(args.get("id", "")))
            email = cache.get(key)
            if email is None:
                return "Email not found; search first."
            return strip_html(f"{email.subject}\n{email.body}")

        messages: list[dict[str, object]] = [
            {"role": "system", "content": _system_prompt(context, self._categories)},
            {"role": "user", "content": "Find and extract the receipt."},
        ]
        try:
            final = run_tool_loop(
                self._chat,
                {"search_mailbox": search_mailbox, "read_email": read_email},
                messages,
                tools=[_SEARCH_TOOL, _READ_TOOL],
                max_iterations=self._max_iterations,
            )
        except Exception as exc:  # noqa: BLE001 - gatherers degrade, never crash
            logger.warning("agentic receipt search failed: %s", exc)
            return []

        try:
            data = extract_json(final)
        except ValueError:
            return []
        if not data.get("found"):
            return []

        splits = []
        for raw in data.get("items", []):
            try:
                category_id = int(raw["category_id"])
                amount = Decimal(str(raw["amount"]))
            except (KeyError, TypeError, ValueError, InvalidOperation):
                continue
            if category_id in self._valid_ids:
                splits.append(Split(category_id=category_id, amount=amount))
        if not splits:
            return []

        items_total = sum(
            (s.amount for s in splits if s.amount is not None), Decimal("0")
        )
        tier = reconciliation_tier(items_total, context.amount)
        return [
            Evidence(
                claim=Claim.split(splits),
                evidence_type=EvidenceType.RECEIPT,
                source="receipt:agentic",
                strength=tier,
                itemized=True,
            )
        ]
