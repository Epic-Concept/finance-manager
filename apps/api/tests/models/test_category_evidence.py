"""Tests for CategoryEvidence model."""

from datetime import datetime
from decimal import Decimal

from finance_api.models.category_evidence import CategoryEvidence


def test_category_evidence_creation() -> None:
    """Test CategoryEvidence can be instantiated with required fields."""
    evidence = CategoryEvidence(
        transaction_id=1,
        item_description="USB Cable",
        item_price=Decimal("9.99"),
        category_id=5,
        evidence_type="email",
    )

    assert evidence.transaction_id == 1
    assert evidence.item_description == "USB Cable"
    assert evidence.item_price == Decimal("9.99")
    assert evidence.category_id == 5
    assert evidence.evidence_type == "email"
    # Note: defaults are applied at database level, not Python level


def test_category_evidence_with_email_provenance() -> None:
    """Test CategoryEvidence with full email provenance."""
    email_datetime = datetime(2026, 1, 10, 10, 57, 21)
    evidence = CategoryEvidence(
        transaction_id=1,
        item_description="Wireless Headphones",
        item_price=Decimal("49.99"),
        item_currency="GBP",
        item_quantity=1,
        category_id=3,
        evidence_type="email",
        email_account_id=1,
        email_message_id="<abc123@amazon.co.uk>",
        email_datetime=email_datetime,
        evidence_summary="Email from Amazon UK dated 2026-01-10: Order #123-456",
    )

    assert evidence.email_account_id == 1
    assert evidence.email_message_id == "<abc123@amazon.co.uk>"
    assert evidence.email_datetime == email_datetime
    assert evidence.evidence_summary is not None


def test_category_evidence_with_ai_metadata() -> None:
    """Test CategoryEvidence with AI classification metadata."""
    evidence = CategoryEvidence(
        transaction_id=1,
        item_description="Book: Python Programming",
        item_price=Decimal("29.99"),
        category_id=7,
        evidence_type="ai_inferred",
        confidence_score=Decimal("0.9500"),
        model_used="claude-sonnet-4-5-20250514",
        raw_extraction='{"items": [{"name": "Book: Python Programming", "price": 29.99}]}',
    )

    assert evidence.evidence_type == "ai_inferred"
    assert evidence.confidence_score == Decimal("0.9500")
    assert evidence.model_used == "claude-sonnet-4-5-20250514"
    assert evidence.raw_extraction is not None


def test_category_evidence_rule_type() -> None:
    """Test CategoryEvidence with rule evidence type."""
    evidence = CategoryEvidence(
        transaction_id=1,
        item_description="Tesco Groceries",
        item_price=Decimal("85.50"),
        category_id=2,
        evidence_type="rule",
        confidence_score=Decimal("1.0000"),
        evidence_summary='Matched rule: "Groceries" (description =~ "(?i)tesco")',
    )

    assert evidence.evidence_type == "rule"
    assert evidence.confidence_score == Decimal("1.0000")


def test_category_evidence_manual_type() -> None:
    """Test CategoryEvidence with manual evidence type."""
    evidence = CategoryEvidence(
        transaction_id=1,
        item_description="Manual entry",
        item_price=Decimal("100.00"),
        category_id=1,
        evidence_type="manual",
        evidence_summary="User manually categorized this transaction",
    )

    assert evidence.evidence_type == "manual"


def test_category_evidence_shipping_item() -> None:
    """Test CategoryEvidence for shipping costs."""
    evidence = CategoryEvidence(
        transaction_id=1,
        item_description="Shipping",
        item_price=Decimal("4.99"),
        category_id=15,  # Shipping category
        evidence_type="email",
    )

    assert evidence.item_description == "Shipping"
    assert evidence.item_price == Decimal("4.99")


def test_category_evidence_multi_item_quantity() -> None:
    """Test CategoryEvidence with quantity > 1."""
    evidence = CategoryEvidence(
        transaction_id=1,
        item_description="AA Batteries (pack of 4)",
        item_price=Decimal("3.99"),
        item_quantity=2,
        category_id=8,
        evidence_type="email",
    )

    assert evidence.item_quantity == 2
    # Total value would be 3.99 * 2 = 7.98


def test_category_evidence_different_currency() -> None:
    """Test CategoryEvidence with non-default currency."""
    evidence = CategoryEvidence(
        transaction_id=1,
        item_description="Polish Product",
        item_price=Decimal("99.99"),
        item_currency="PLN",
        category_id=1,
        evidence_type="email",
    )

    assert evidence.item_currency == "PLN"


def test_category_evidence_repr() -> None:
    """Test CategoryEvidence string representation."""
    evidence = CategoryEvidence(
        id=1,
        transaction_id=5,
        item_description="A very long product description that should be truncated",
        item_price=Decimal("19.99"),
        category_id=3,
        evidence_type="email",
    )

    repr_str = repr(evidence)
    assert "id=1" in repr_str
    assert "transaction_id=5" in repr_str
    assert "..." in repr_str  # Truncation indicator


def test_category_evidence_table_name() -> None:
    """Test CategoryEvidence table configuration."""
    assert CategoryEvidence.__tablename__ == "category_evidence"
    assert CategoryEvidence.__table_args__[3]["schema"] == "finance"
