"""The receipt gatherer: the agentic, holy-grail evidence path.

Pulls candidate receipt emails from household mailboxes (via an injected
``MailboxSource`` -- the real IMAP/provider adapter is wired separately),
extracts itemized line items with the local LLM, reconciles them against the
charge, and emits itemized RECEIPT evidence whose strength is set by the
reconciliation band. A plausible receipt found in more than one mailbox is
ambiguous: strength is capped (never PROOF) rather than guessing which person paid.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Protocol

from finance_api.classification.evidence import (
    Claim,
    Evidence,
    EvidenceType,
    Split,
    StrengthTier,
)
from finance_api.classification.gatherer import GatherContext, Gatherer
from finance_api.classification.gatherers.mailbox import EmailCandidate
from finance_api.classification.gatherers.mailbox_session import imap_session
from finance_api.classification.gatherers.llm_inference import CategoryRef
from finance_api.classification.receipt import (
    ReceiptExtractionError,
    ReceiptExtractor,
    reconciliation_tier,
)

logger = logging.getLogger(__name__)


class MailboxSource(Protocol):
    """Finds candidate receipt emails across household mailboxes."""

    def find_candidates(self, context: GatherContext) -> list[EmailCandidate]: ...


class ReceiptGatherer(Gatherer):
    """Emits itemized RECEIPT evidence from a matched receipt email."""

    produced_types = frozenset({EvidenceType.RECEIPT})

    def __init__(
        self,
        mailbox_source: MailboxSource,
        extractor: ReceiptExtractor,
        categories: list[CategoryRef],
        tolerance: Decimal = Decimal("0.02"),
        moderate: Decimal = Decimal("0.10"),
    ) -> None:
        self._mailbox = mailbox_source
        self._extractor = extractor
        self._categories = categories
        self._tolerance = tolerance
        self._moderate = moderate

    def gather(self, context: GatherContext) -> list[Evidence]:
        clients = getattr(self._mailbox, "clients", None)
        if clients:
            with imap_session(clients):
                return self._gather(context)
        return self._gather(context)

    def _gather(self, context: GatherContext) -> list[Evidence]:
        candidates = self._mailbox.find_candidates(context)
        if not candidates:
            return []

        best = candidates[0]
        try:
            receipt = self._extractor.extract(best.text, self._categories)
        except ReceiptExtractionError as exc:
            logger.warning("receipt extraction failed: %s", exc)
            return []

        splits = [
            Split(category_id=item.category_id, amount=item.amount)
            for item in receipt.items
            if item.category_id is not None
        ]
        if not splits:
            return []

        tier = reconciliation_tier(
            receipt.items_total, context.amount, self._tolerance, self._moderate
        )

        # Ambiguity: a plausible receipt in more than one mailbox degrades trust.
        distinct_mailboxes = {c.mailbox for c in candidates}
        if len(distinct_mailboxes) > 1 and tier is StrengthTier.PROOF:
            tier = StrengthTier.STRONG

        return [
            Evidence(
                claim=Claim.split(splits),
                evidence_type=EvidenceType.RECEIPT,
                source=f"receipt:{best.mailbox}:{best.message_id}",
                strength=tier,
                itemized=True,
            )
        ]
