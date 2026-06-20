"""The LLM-inference gatherer: a bare guess from the description alone.

This is the weakest gatherer: it asks the local LLM to pick the best category
for a transaction description with no receipt or history. Its evidence is always
``WEAK`` and non-itemized, so it can never on its own auto-apply anything beyond
what the policy's required-tier table permits.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from finance_api.classification.evidence import (
    Claim,
    Evidence,
    EvidenceType,
    StrengthTier,
)
from finance_api.classification.gatherer import GatherContext, Gatherer
from finance_api.classification.llm import LLMClient, extract_json

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a personal-finance transaction classifier. Given a bank "
    "transaction description and a list of allowed categories, choose the single "
    'best category. Respond ONLY with JSON of the form {"category_id": <int>}. '
    "If unsure, choose the closest category."
)


@dataclass(frozen=True)
class CategoryRef:
    """A category the LLM may choose from."""

    id: int
    name: str


class LLMInferenceGatherer(Gatherer):
    """Emits a single WEAK guess for the best-matching category."""

    produced_types = frozenset({EvidenceType.LLM_INFERENCE})

    def __init__(self, client: LLMClient, categories: list[CategoryRef]) -> None:
        self._client = client
        self._categories = categories
        self._valid_ids = {c.id for c in categories}

    def _build_user_prompt(self, description: str) -> str:
        catalog = "\n".join(f"- {c.id}: {c.name}" for c in self._categories)
        return (
            f"Transaction description: {description}\n\n"
            f"Allowed categories (id: name):\n{catalog}\n\n"
            'Respond ONLY with {"category_id": <int>}.'
        )

    def gather(self, context: GatherContext) -> list[Evidence]:
        description = context.description or ""
        try:
            content = self._client.complete(
                _SYSTEM, self._build_user_prompt(description)
            )
        except Exception as exc:  # noqa: BLE001 - gatherers degrade, never crash
            logger.warning("LLM inference call failed: %s", exc)
            return []

        try:
            data = extract_json(content)
        except ValueError:
            return []

        category_id = data.get("category_id")
        if not isinstance(category_id, int) or category_id not in self._valid_ids:
            return []

        return [
            Evidence(
                claim=Claim.single_category(category_id),
                evidence_type=EvidenceType.LLM_INFERENCE,
                source="llm:inference",
                strength=StrengthTier.WEAK,
                itemized=False,
            )
        ]
