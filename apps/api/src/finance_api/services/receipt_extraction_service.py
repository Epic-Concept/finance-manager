"""ReceiptExtractionService for extracting order details from emails using LLM."""

import json
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from anthropic import Anthropic

from finance_api.services.email_search_service import EmailMessage


@dataclass
class ExtractedItem:
    """An item extracted from a receipt email."""

    name: str
    price: Decimal
    quantity: int = 1
    category_hint: str | None = None


@dataclass
class ExtractedReceipt:
    """Structured data extracted from a receipt email."""

    merchant: str
    order_date: date
    items: list[ExtractedItem] = field(default_factory=list)
    shipping_cost: Decimal | None = None
    total: Decimal = Decimal("0")
    currency: str = "GBP"
    raw_response: str = ""
    confidence_score: Decimal = Decimal("0")


EXTRACTION_PROMPT = """You are an expert at extracting structured order information from email receipts.

Analyze the following email content and extract the order details. Return your response as valid JSON.

EMAIL CONTENT:
{email_content}

Extract the following information in this exact JSON format:
{{
    "merchant": "string - the merchant/retailer name",
    "order_date": "YYYY-MM-DD - the order date from the email",
    "items": [
        {{
            "name": "string - item description",
            "price": "decimal - item price as a number",
            "quantity": "integer - quantity ordered, default 1",
            "category_hint": "string or null - suggested category based on item type (e.g., 'Electronics', 'Books', 'Clothing', 'Groceries', 'Home & Garden', etc.)"
        }}
    ],
    "shipping_cost": "decimal or null - shipping cost if any",
    "total": "decimal - order total",
    "currency": "string - 3-letter currency code (e.g., GBP, USD, EUR)"
}}

Important rules:
1. Return ONLY valid JSON, no other text
2. All prices should be positive numbers
3. If shipping is free or not listed, set shipping_cost to null
4. If you cannot extract a value, make your best reasonable estimate based on context
5. For category_hint, use common retail categories like: Electronics, Books, Clothing, Home & Garden, Toys & Games, Beauty, Sports, Food & Groceries, Office Supplies, Pet Supplies
6. Ensure the sum of (item prices * quantities) + shipping approximately equals total

JSON response:"""


class ReceiptExtractionError(Exception):
    """Raised when receipt extraction fails."""

    pass


class ReceiptExtractionService:
    """Service for extracting structured order data from receipt emails using Claude.

    Uses Claude 4.5 Sonnet to parse email content and extract structured order
    information including items, prices, and suggested categories.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-5-20250514",
    ) -> None:
        """Initialize the service.

        Args:
            api_key: Anthropic API key. If None, uses ANTHROPIC_API_KEY env var.
            model: Claude model to use for extraction.
        """
        self._client = Anthropic(api_key=api_key)
        self._model = model

    def _build_prompt(self, email: EmailMessage) -> str:
        """Build the extraction prompt for an email.

        Args:
            email: The email message to extract from.

        Returns:
            Formatted prompt string.
        """
        # Combine subject and body for context
        email_content = f"""Subject: {email.subject}
From: {email.sender}
Date: {email.date.isoformat() if email.date else 'Unknown'}

{email.body_text}"""

        return EXTRACTION_PROMPT.format(email_content=email_content)

    def _parse_response(self, response_text: str) -> dict[str, Any]:
        """Parse the LLM response as JSON.

        Args:
            response_text: Raw LLM response.

        Returns:
            Parsed JSON dictionary.

        Raises:
            ReceiptExtractionError: If response is not valid JSON.
        """
        # Try to extract JSON from the response
        text = response_text.strip()

        # Handle potential markdown code blocks
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            return json.loads(text)  # type: ignore[no-any-return]
        except json.JSONDecodeError as e:
            raise ReceiptExtractionError(f"Failed to parse LLM response as JSON: {e}") from e

    def _validate_response(self, data: dict[str, Any]) -> None:
        """Validate the extracted data structure.

        Args:
            data: Parsed JSON data.

        Raises:
            ReceiptExtractionError: If required fields are missing.
        """
        required_fields = ["merchant", "order_date", "items", "total", "currency"]
        for required_field in required_fields:
            if required_field not in data:
                raise ReceiptExtractionError(f"Missing required field: {required_field}")

        if not isinstance(data["items"], list):
            raise ReceiptExtractionError("Items must be a list")

        for i, item in enumerate(data["items"]):
            if "name" not in item:
                raise ReceiptExtractionError(f"Item {i} missing 'name' field")
            if "price" not in item:
                raise ReceiptExtractionError(f"Item {i} missing 'price' field")

    def _convert_to_receipt(
        self, data: dict[str, Any], raw_response: str
    ) -> ExtractedReceipt:
        """Convert parsed JSON to ExtractedReceipt.

        Args:
            data: Validated JSON data.
            raw_response: Original LLM response for debugging.

        Returns:
            ExtractedReceipt instance.
        """
        items = []
        for item_data in data["items"]:
            items.append(
                ExtractedItem(
                    name=str(item_data["name"]),
                    price=Decimal(str(item_data["price"])),
                    quantity=int(item_data.get("quantity", 1)),
                    category_hint=item_data.get("category_hint"),
                )
            )

        # Parse order_date
        try:
            order_date = date.fromisoformat(str(data["order_date"]))
        except ValueError:
            # Default to today if date parsing fails
            order_date = date.today()

        shipping = None
        if data.get("shipping_cost") is not None:
            shipping = Decimal(str(data["shipping_cost"]))

        # Calculate confidence based on whether items sum to total
        items_total = sum(i.price * i.quantity for i in items)
        if shipping:
            items_total += shipping

        receipt_total = Decimal(str(data["total"]))

        # Simple confidence calculation - 1.0 if within 5%, lower otherwise
        if receipt_total > 0:
            diff_ratio = abs(items_total - receipt_total) / receipt_total
            if diff_ratio <= 0.05:
                confidence = Decimal("0.95")
            elif diff_ratio <= 0.10:
                confidence = Decimal("0.85")
            elif diff_ratio <= 0.20:
                confidence = Decimal("0.70")
            else:
                confidence = Decimal("0.50")
        else:
            confidence = Decimal("0.50")

        return ExtractedReceipt(
            merchant=str(data["merchant"]),
            order_date=order_date,
            items=items,
            shipping_cost=shipping,
            total=receipt_total,
            currency=str(data.get("currency", "GBP")),
            raw_response=raw_response,
            confidence_score=confidence,
        )

    def extract(self, email: EmailMessage) -> ExtractedReceipt:
        """Extract order details from a receipt email.

        Args:
            email: The email message to extract from.

        Returns:
            ExtractedReceipt with structured order data.

        Raises:
            ReceiptExtractionError: If extraction fails.
        """
        prompt = self._build_prompt(email)

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = response.content[0].text  # type: ignore[union-attr]
        except Exception as e:
            raise ReceiptExtractionError(f"LLM API call failed: {e}") from e

        data = self._parse_response(response_text)
        self._validate_response(data)
        return self._convert_to_receipt(data, response_text)

    def extract_batch(
        self, emails: list[EmailMessage]
    ) -> list[ExtractedReceipt | ReceiptExtractionError]:
        """Extract order details from multiple emails.

        Args:
            emails: List of email messages.

        Returns:
            List of ExtractedReceipt or ReceiptExtractionError for each email.
        """
        results: list[ExtractedReceipt | ReceiptExtractionError] = []
        for email in emails:
            try:
                results.append(self.extract(email))
            except ReceiptExtractionError as e:
                results.append(e)
        return results
