"""Tests for ReceiptExtractionService."""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from finance_api.services.email_search_service import EmailMessage
from finance_api.services.receipt_extraction_service import (
    ExtractedItem,
    ReceiptExtractionError,
    ReceiptExtractionService,
)


@pytest.fixture
def sample_email() -> EmailMessage:
    """Create a sample email message."""
    return EmailMessage(
        message_id="<test123@amazon.co.uk>",
        subject="Your Amazon.co.uk order of USB Cable...",
        sender="no-reply@amazon.co.uk",
        recipient="test@gmail.com",
        date=datetime(2026, 1, 15, 10, 30, 0),
        body_text="""
Your order has been confirmed!

Order #123-4567890
Placed on January 15, 2026

Items:
- USB Type-C Cable (2-pack) - £9.99
- Wireless Mouse - £24.99

Subtotal: £34.98
Shipping: Free
Order Total: £34.98

Thank you for shopping with us!
""",
    )


@pytest.fixture
def multi_item_email() -> EmailMessage:
    """Create a multi-item order email."""
    return EmailMessage(
        message_id="<order456@amazon.co.uk>",
        subject="Your Amazon.co.uk order confirmation",
        sender="no-reply@amazon.co.uk",
        recipient="test@gmail.com",
        date=datetime(2026, 1, 20, 14, 0, 0),
        body_text="""
Order Confirmation

Order #789-1234567
Date: January 20, 2026

Items ordered:
1x Python Programming Book - £29.99
2x USB Flash Drive 64GB - £14.99 each
1x Desk Lamp LED - £35.00

Subtotal: £94.97
Shipping: £4.99
Order Total: £99.96
""",
    )


class TestReceiptExtractionServiceParseResponse:
    """Tests for response parsing logic."""

    def test_parse_valid_json(self) -> None:
        """Test parsing a valid JSON response."""
        service = ReceiptExtractionService(api_key="test-key")

        response = """{
            "merchant": "Amazon",
            "order_date": "2026-01-15",
            "items": [{"name": "USB Cable", "price": 9.99, "quantity": 1}],
            "shipping_cost": null,
            "total": 9.99,
            "currency": "GBP"
        }"""

        result = service._parse_response(response)

        assert result["merchant"] == "Amazon"
        assert result["total"] == 9.99

    def test_parse_json_with_markdown(self) -> None:
        """Test parsing JSON wrapped in markdown code blocks."""
        service = ReceiptExtractionService(api_key="test-key")

        response = """```json
{
    "merchant": "Amazon",
    "order_date": "2026-01-15",
    "items": [{"name": "Test", "price": 10.0}],
    "total": 10.0,
    "currency": "GBP"
}
```"""

        result = service._parse_response(response)

        assert result["merchant"] == "Amazon"

    def test_parse_invalid_json_raises_error(self) -> None:
        """Test that invalid JSON raises ReceiptExtractionError."""
        service = ReceiptExtractionService(api_key="test-key")

        with pytest.raises(ReceiptExtractionError, match="Failed to parse"):
            service._parse_response("not valid json at all")


class TestReceiptExtractionServiceValidation:
    """Tests for response validation."""

    def test_validate_valid_response(self) -> None:
        """Test validation passes for valid data."""
        service = ReceiptExtractionService(api_key="test-key")

        data = {
            "merchant": "Amazon",
            "order_date": "2026-01-15",
            "items": [{"name": "Item", "price": 10.0}],
            "total": 10.0,
            "currency": "GBP",
        }

        # Should not raise
        service._validate_response(data)

    def test_validate_missing_required_field(self) -> None:
        """Test validation fails for missing required field."""
        service = ReceiptExtractionService(api_key="test-key")

        data = {
            "merchant": "Amazon",
            # Missing order_date, items, total, currency
        }

        with pytest.raises(ReceiptExtractionError, match="Missing required field"):
            service._validate_response(data)

    def test_validate_items_not_list(self) -> None:
        """Test validation fails when items is not a list."""
        service = ReceiptExtractionService(api_key="test-key")

        data = {
            "merchant": "Amazon",
            "order_date": "2026-01-15",
            "items": "not a list",
            "total": 10.0,
            "currency": "GBP",
        }

        with pytest.raises(ReceiptExtractionError, match="Items must be a list"):
            service._validate_response(data)

    def test_validate_item_missing_name(self) -> None:
        """Test validation fails when item missing name."""
        service = ReceiptExtractionService(api_key="test-key")

        data = {
            "merchant": "Amazon",
            "order_date": "2026-01-15",
            "items": [{"price": 10.0}],  # Missing name
            "total": 10.0,
            "currency": "GBP",
        }

        with pytest.raises(ReceiptExtractionError, match="missing 'name' field"):
            service._validate_response(data)


class TestReceiptExtractionServiceConversion:
    """Tests for conversion to ExtractedReceipt."""

    def test_convert_basic_receipt(self) -> None:
        """Test basic receipt conversion."""
        service = ReceiptExtractionService(api_key="test-key")

        data = {
            "merchant": "Amazon UK",
            "order_date": "2026-01-15",
            "items": [
                {"name": "USB Cable", "price": 9.99, "quantity": 1, "category_hint": "Electronics"}
            ],
            "shipping_cost": None,
            "total": 9.99,
            "currency": "GBP",
        }

        receipt = service._convert_to_receipt(data, "raw response")

        assert receipt.merchant == "Amazon UK"
        assert receipt.order_date == date(2026, 1, 15)
        assert len(receipt.items) == 1
        assert receipt.items[0].name == "USB Cable"
        assert receipt.items[0].price == Decimal("9.99")
        assert receipt.items[0].category_hint == "Electronics"
        assert receipt.shipping_cost is None
        assert receipt.total == Decimal("9.99")
        assert receipt.currency == "GBP"

    def test_convert_with_shipping(self) -> None:
        """Test conversion with shipping cost."""
        service = ReceiptExtractionService(api_key="test-key")

        data = {
            "merchant": "Amazon",
            "order_date": "2026-01-15",
            "items": [{"name": "Item", "price": 20.0}],
            "shipping_cost": 4.99,
            "total": 24.99,
            "currency": "GBP",
        }

        receipt = service._convert_to_receipt(data, "")

        assert receipt.shipping_cost == Decimal("4.99")
        assert receipt.total == Decimal("24.99")

    def test_convert_multiple_items(self) -> None:
        """Test conversion with multiple items."""
        service = ReceiptExtractionService(api_key="test-key")

        data = {
            "merchant": "Amazon",
            "order_date": "2026-01-20",
            "items": [
                {"name": "Book", "price": 15.0, "quantity": 2, "category_hint": "Books"},
                {"name": "Cable", "price": 10.0, "quantity": 1},
            ],
            "shipping_cost": None,
            "total": 40.0,
            "currency": "GBP",
        }

        receipt = service._convert_to_receipt(data, "")

        assert len(receipt.items) == 2
        assert receipt.items[0].quantity == 2
        assert receipt.items[1].category_hint is None

    def test_confidence_calculation_exact_match(self) -> None:
        """Test confidence is high when items match total exactly."""
        service = ReceiptExtractionService(api_key="test-key")

        data = {
            "merchant": "Amazon",
            "order_date": "2026-01-15",
            "items": [
                {"name": "Item1", "price": 10.0, "quantity": 2},
                {"name": "Item2", "price": 5.0, "quantity": 1},
            ],
            "shipping_cost": 5.0,
            "total": 30.0,  # 10*2 + 5*1 + 5 = 30 exact match
            "currency": "GBP",
        }

        receipt = service._convert_to_receipt(data, "")

        # Should have high confidence (0.95) for exact match
        assert receipt.confidence_score >= Decimal("0.9")

    def test_confidence_lower_for_mismatch(self) -> None:
        """Test confidence is lower when items don't match total."""
        service = ReceiptExtractionService(api_key="test-key")

        data = {
            "merchant": "Amazon",
            "order_date": "2026-01-15",
            "items": [{"name": "Item", "price": 10.0}],
            "shipping_cost": None,
            "total": 50.0,  # Doesn't match items
            "currency": "GBP",
        }

        receipt = service._convert_to_receipt(data, "")

        # Should have lower confidence
        assert receipt.confidence_score < Decimal("0.7")


class TestReceiptExtractionServiceExtract:
    """Tests for the main extract method with mocked API."""

    def test_extract_success(self, sample_email: EmailMessage) -> None:
        """Test successful extraction with mocked API."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text="""{
                "merchant": "Amazon UK",
                "order_date": "2026-01-15",
                "items": [
                    {"name": "USB Type-C Cable (2-pack)", "price": 9.99, "quantity": 1, "category_hint": "Electronics"},
                    {"name": "Wireless Mouse", "price": 24.99, "quantity": 1, "category_hint": "Electronics"}
                ],
                "shipping_cost": null,
                "total": 34.98,
                "currency": "GBP"
            }"""
            )
        ]

        with patch("finance_api.services.receipt_extraction_service.Anthropic") as mock_client:
            instance = mock_client.return_value
            instance.messages.create.return_value = mock_response

            service = ReceiptExtractionService(api_key="test-key")
            receipt = service.extract(sample_email)

            assert receipt.merchant == "Amazon UK"
            assert len(receipt.items) == 2
            assert receipt.total == Decimal("34.98")

    def test_extract_api_failure(self, sample_email: EmailMessage) -> None:
        """Test handling of API failure."""
        with patch("finance_api.services.receipt_extraction_service.Anthropic") as mock_client:
            instance = mock_client.return_value
            instance.messages.create.side_effect = Exception("API Error")

            service = ReceiptExtractionService(api_key="test-key")

            with pytest.raises(ReceiptExtractionError, match="LLM API call failed"):
                service.extract(sample_email)


class TestReceiptExtractionServiceBatch:
    """Tests for batch extraction."""

    def test_extract_batch_mixed_results(
        self, sample_email: EmailMessage, multi_item_email: EmailMessage
    ) -> None:
        """Test batch extraction with mixed success/failure."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text="""{
                "merchant": "Amazon",
                "order_date": "2026-01-15",
                "items": [{"name": "Item", "price": 10.0}],
                "total": 10.0,
                "currency": "GBP"
            }"""
            )
        ]

        call_count = 0

        def side_effect(*args: object, **kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_response
            else:
                raise Exception("API Error")

        with patch("finance_api.services.receipt_extraction_service.Anthropic") as mock_client:
            instance = mock_client.return_value
            instance.messages.create.side_effect = side_effect

            service = ReceiptExtractionService(api_key="test-key")
            results = service.extract_batch([sample_email, multi_item_email])

            assert len(results) == 2
            # First should succeed
            assert not isinstance(results[0], ReceiptExtractionError)
            # Second should be an error
            assert isinstance(results[1], ReceiptExtractionError)
