"""Receipt extraction and reconciliation banding (receipt-evidence-retrieval spec).

The local LLM extracts line items (and a per-item category) from a receipt
email; reconciliation banding turns "do the items sum to the charge?" into an
evidence strength tier:

- within tolerance        -> PROOF  (itemized, trustworthy split)
- moderate mismatch       -> STRONG (e.g. missing shipping/discount)
- large mismatch          -> WEAK   (probably the wrong receipt)
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from finance_api.classification.evidence import StrengthTier
from finance_api.classification.gatherers.llm_inference import CategoryRef
from finance_api.classification.llm import LLMClient, extract_json

_DEFAULT_TOLERANCE = Decimal("0.02")  # 2%
_DEFAULT_MODERATE = Decimal("0.10")  # 10%


class ReceiptExtractionError(Exception):
    """Raised when receipt content cannot be extracted into line items."""


@dataclass(frozen=True)
class LineItem:
    description: str
    amount: Decimal
    category_id: int | None = None


@dataclass(frozen=True)
class ExtractedReceipt:
    merchant: str
    currency: str
    items: tuple[LineItem, ...]

    @property
    def items_total(self) -> Decimal:
        return sum((i.amount for i in self.items), Decimal("0"))


def reconciliation_tier(
    items_total: Decimal,
    transaction_total: Decimal,
    tolerance: Decimal = _DEFAULT_TOLERANCE,
    moderate: Decimal = _DEFAULT_MODERATE,
) -> StrengthTier:
    """Map the line-item-sum vs transaction-total mismatch to a strength tier."""
    if transaction_total == 0:
        return StrengthTier.WEAK
    diff_ratio = abs(items_total - transaction_total) / abs(transaction_total)
    if diff_ratio <= tolerance:
        return StrengthTier.PROOF
    if diff_ratio <= moderate:
        return StrengthTier.STRONG
    return StrengthTier.WEAK


_SYSTEM = (
    "You extract purchase line items from a receipt/order-confirmation email. "
    "For each item, assign the single best category id from the allowed list. "
    "Respond ONLY with JSON of the form "
    '{"merchant": str, "currency": str, "items": '
    '[{"description": str, "amount": number, "category_id": int}]}.'
)


class ReceiptExtractor:
    """Extracts an itemized receipt from email content using the local LLM."""

    def __init__(self, client: LLMClient) -> None:
        self._client = client

    def _build_user_prompt(self, email_text: str, categories: list[CategoryRef]) -> str:
        catalog = "\n".join(f"- {c.id}: {c.name}" for c in categories)
        return (
            f"Allowed categories (id: name):\n{catalog}\n\n"
            f"Receipt email:\n{email_text}\n\n"
            "Extract the line items as JSON."
        )

    def extract(
        self, email_text: str, categories: list[CategoryRef]
    ) -> ExtractedReceipt:
        content = self._client.complete(
            _SYSTEM, self._build_user_prompt(email_text, categories)
        )
        try:
            data = extract_json(content)
        except ValueError as exc:
            raise ReceiptExtractionError(str(exc)) from exc

        raw_items = data.get("items")
        if not isinstance(raw_items, list) or not raw_items:
            raise ReceiptExtractionError("no items in extracted receipt")

        items: list[LineItem] = []
        for raw in raw_items:
            try:
                items.append(
                    LineItem(
                        description=str(raw["description"]),
                        amount=Decimal(str(raw["amount"])),
                        category_id=(
                            int(raw["category_id"])
                            if raw.get("category_id") is not None
                            else None
                        ),
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ReceiptExtractionError(f"malformed line item: {exc}") from exc

        return ExtractedReceipt(
            merchant=str(data.get("merchant", "")),
            currency=str(data.get("currency", "")),
            items=tuple(items),
        )
