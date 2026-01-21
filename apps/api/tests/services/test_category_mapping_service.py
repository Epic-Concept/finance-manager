"""Tests for CategoryMappingService."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from finance_api.models.category import Category, CategoryClosure
from finance_api.repositories.category_repository import CategoryRepository
from finance_api.services.category_mapping_service import CategoryMappingService
from finance_api.services.receipt_extraction_service import (
    ExtractedItem,
    ExtractedReceipt,
)


@pytest.fixture
def electronics_category(db_session: Session) -> Category:
    """Create an Electronics category."""
    category = Category(name="Electronics")
    db_session.add(category)
    db_session.flush()
    closure = CategoryClosure(
        ancestor_id=category.id, descendant_id=category.id, depth=0
    )
    db_session.add(closure)
    db_session.flush()
    return category


@pytest.fixture
def books_category(db_session: Session) -> Category:
    """Create a Books category."""
    category = Category(name="Books")
    db_session.add(category)
    db_session.flush()
    closure = CategoryClosure(
        ancestor_id=category.id, descendant_id=category.id, depth=0
    )
    db_session.add(closure)
    db_session.flush()
    return category


@pytest.fixture
def clothing_category(db_session: Session) -> Category:
    """Create a Clothing category."""
    category = Category(name="Clothing")
    db_session.add(category)
    db_session.flush()
    closure = CategoryClosure(
        ancestor_id=category.id, descendant_id=category.id, depth=0
    )
    db_session.add(closure)
    db_session.flush()
    return category


@pytest.fixture
def uncategorized_category(db_session: Session) -> Category:
    """Create an Uncategorized category for defaults."""
    category = Category(name="Uncategorized")
    db_session.add(category)
    db_session.flush()
    closure = CategoryClosure(
        ancestor_id=category.id, descendant_id=category.id, depth=0
    )
    db_session.add(closure)
    db_session.flush()
    return category


@pytest.fixture
def category_repo(db_session: Session) -> CategoryRepository:
    """Create a CategoryRepository instance."""
    return CategoryRepository(db_session)


@pytest.fixture
def mapping_service(category_repo: CategoryRepository) -> CategoryMappingService:
    """Create a CategoryMappingService instance."""
    return CategoryMappingService(category_repo)


class TestCategoryMappingServiceMapItem:
    """Tests for mapping individual items."""

    def test_map_item_by_hint_direct_match(
        self, mapping_service: CategoryMappingService, electronics_category: Category
    ) -> None:
        """Test mapping item by exact category hint match."""
        item = ExtractedItem(
            name="USB Cable",
            price=Decimal("9.99"),
            category_hint="Electronics",
        )

        category_id, category_name = mapping_service.map_item(item)

        assert category_id == electronics_category.id
        assert category_name == "Electronics"

    def test_map_item_by_hint_case_insensitive(
        self, mapping_service: CategoryMappingService, electronics_category: Category
    ) -> None:
        """Test mapping is case insensitive."""
        item = ExtractedItem(
            name="USB Cable",
            price=Decimal("9.99"),
            category_hint="ELECTRONICS",
        )

        category_id, _ = mapping_service.map_item(item)

        assert category_id == electronics_category.id

    def test_map_item_by_item_name_keyword(
        self, mapping_service: CategoryMappingService, books_category: Category
    ) -> None:
        """Test mapping by item name keyword when hint is missing."""
        item = ExtractedItem(
            name="Python Programming Book",
            price=Decimal("29.99"),
            category_hint=None,
        )

        category_id, category_name = mapping_service.map_item(item)

        assert category_id == books_category.id
        assert category_name == "Books"

    def test_map_item_no_match(
        self, mapping_service: CategoryMappingService, electronics_category: Category
    ) -> None:
        """Test item with no matching category."""
        item = ExtractedItem(
            name="Random Unknown Item",
            price=Decimal("50.00"),
            category_hint=None,
        )

        category_id, category_name = mapping_service.map_item(item)

        assert category_id is None
        assert category_name is None

    def test_map_item_with_default_category(
        self,
        category_repo: CategoryRepository,
        electronics_category: Category,
        uncategorized_category: Category,
    ) -> None:
        """Test using default category for unmapped items."""
        service = CategoryMappingService(
            category_repo, default_category_id=uncategorized_category.id
        )

        item = ExtractedItem(
            name="Mystery Item",
            price=Decimal("25.00"),
            category_hint=None,
        )

        category_id, category_name = service.map_item(item)

        assert category_id == uncategorized_category.id
        assert category_name == "Uncategorized"


class TestCategoryMappingServiceMapReceipt:
    """Tests for mapping entire receipts."""

    def test_map_receipt_all_items_mapped(
        self,
        mapping_service: CategoryMappingService,
        electronics_category: Category,
        books_category: Category,
    ) -> None:
        """Test mapping receipt where all items are mapped."""
        receipt = ExtractedReceipt(
            merchant="Amazon",
            order_date=date(2026, 1, 15),
            items=[
                ExtractedItem(
                    name="USB Cable", price=Decimal("9.99"), category_hint="Electronics"
                ),
                ExtractedItem(
                    name="Python Book", price=Decimal("29.99"), category_hint="Books"
                ),
            ],
            total=Decimal("39.98"),
        )

        result = mapping_service.map_receipt(receipt)

        assert len(result.mapped_items) == 2
        assert len(result.unmapped_items) == 0
        assert result.total_mapped_value == Decimal("39.98")

    def test_map_receipt_partial_mapping(
        self,
        mapping_service: CategoryMappingService,
        electronics_category: Category,
    ) -> None:
        """Test mapping receipt with some unmapped items."""
        receipt = ExtractedReceipt(
            merchant="Amazon",
            order_date=date(2026, 1, 15),
            items=[
                ExtractedItem(
                    name="USB Cable", price=Decimal("9.99"), category_hint="Electronics"
                ),
                ExtractedItem(
                    name="Mystery Item", price=Decimal("20.00"), category_hint=None
                ),
            ],
            total=Decimal("29.99"),
        )

        result = mapping_service.map_receipt(receipt)

        assert len(result.mapped_items) == 1
        assert len(result.unmapped_items) == 1
        assert result.total_mapped_value == Decimal("9.99")

    def test_map_receipt_dominant_category(
        self,
        mapping_service: CategoryMappingService,
        electronics_category: Category,
        books_category: Category,
    ) -> None:
        """Test finding dominant category by value."""
        receipt = ExtractedReceipt(
            merchant="Amazon",
            order_date=date(2026, 1, 15),
            items=[
                ExtractedItem(
                    name="Cheap Cable",
                    price=Decimal("5.00"),
                    category_hint="Electronics",
                ),
                ExtractedItem(
                    name="Expensive Book",
                    price=Decimal("50.00"),
                    category_hint="Books",
                ),
            ],
            total=Decimal("55.00"),
        )

        result = mapping_service.map_receipt(receipt)

        # Books should be dominant (50 > 5)
        assert result.dominant_category_id == books_category.id

    def test_map_receipt_handles_quantity(
        self,
        mapping_service: CategoryMappingService,
        electronics_category: Category,
    ) -> None:
        """Test that quantity is considered in total calculation."""
        receipt = ExtractedReceipt(
            merchant="Amazon",
            order_date=date(2026, 1, 15),
            items=[
                ExtractedItem(
                    name="USB Cable",
                    price=Decimal("10.00"),
                    quantity=3,
                    category_hint="Electronics",
                ),
            ],
            total=Decimal("30.00"),
        )

        result = mapping_service.map_receipt(receipt)

        assert result.total_mapped_value == Decimal("30.00")

    def test_map_receipt_empty_items(
        self, mapping_service: CategoryMappingService
    ) -> None:
        """Test mapping receipt with no items."""
        receipt = ExtractedReceipt(
            merchant="Amazon",
            order_date=date(2026, 1, 15),
            items=[],
            total=Decimal("0"),
        )

        result = mapping_service.map_receipt(receipt)

        assert len(result.mapped_items) == 0
        assert len(result.unmapped_items) == 0
        assert result.dominant_category_id is None


class TestCategoryMappingServiceValidateTotal:
    """Tests for total validation."""

    def test_validate_exact_match(
        self, mapping_service: CategoryMappingService
    ) -> None:
        """Test validation passes for exact match."""
        receipt = ExtractedReceipt(
            merchant="Amazon",
            order_date=date(2026, 1, 15),
            items=[ExtractedItem(name="Item", price=Decimal("50.00"))],
            total=Decimal("50.00"),
        )

        is_valid, diff = mapping_service.validate_total(
            receipt, Decimal("-50.00")  # Negative for purchase
        )

        assert is_valid is True
        assert diff == Decimal("0")

    def test_validate_within_tolerance(
        self, mapping_service: CategoryMappingService
    ) -> None:
        """Test validation passes within tolerance."""
        receipt = ExtractedReceipt(
            merchant="Amazon",
            order_date=date(2026, 1, 15),
            items=[ExtractedItem(name="Item", price=Decimal("50.00"))],
            total=Decimal("51.00"),  # 2% difference
        )

        is_valid, diff = mapping_service.validate_total(
            receipt, Decimal("-50.00"), tolerance=Decimal("0.05")
        )

        assert is_valid is True

    def test_validate_outside_tolerance(
        self, mapping_service: CategoryMappingService
    ) -> None:
        """Test validation fails outside tolerance."""
        receipt = ExtractedReceipt(
            merchant="Amazon",
            order_date=date(2026, 1, 15),
            items=[ExtractedItem(name="Item", price=Decimal("50.00"))],
            total=Decimal("60.00"),  # 20% difference
        )

        is_valid, diff = mapping_service.validate_total(
            receipt, Decimal("-50.00"), tolerance=Decimal("0.05")
        )

        assert is_valid is False
        assert diff > Decimal("0.05")


class TestCategoryMappingServiceReload:
    """Tests for category cache reloading."""

    def test_reload_categories(
        self, mapping_service: CategoryMappingService, electronics_category: Category
    ) -> None:
        """Test reloading category cache."""
        # Force cache load
        mapping_service._load_categories()

        count = mapping_service.reload_categories()

        assert count >= 1  # At least electronics category exists
