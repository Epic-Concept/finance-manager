"""CategoryMappingService for mapping extracted items to categories."""

from dataclasses import dataclass
from decimal import Decimal

from finance_api.models.category import Category
from finance_api.repositories.category_repository import CategoryRepository
from finance_api.services.receipt_extraction_service import (
    ExtractedItem,
    ExtractedReceipt,
)


@dataclass
class MappedItem:
    """An extracted item mapped to a category."""

    item: ExtractedItem
    category_id: int
    category_name: str


@dataclass
class MappingResult:
    """Result of mapping receipt items to categories."""

    mapped_items: list[MappedItem]
    unmapped_items: list[ExtractedItem]
    total_mapped_value: Decimal
    dominant_category_id: int | None


# Mapping from category hints to likely category name patterns
CATEGORY_HINT_MAPPINGS: dict[str, list[str]] = {
    "electronics": ["electronics", "tech", "computer", "phone", "gadget"],
    "books": ["books", "reading", "literature", "education"],
    "clothing": ["clothing", "apparel", "fashion", "wear"],
    "home & garden": ["home", "garden", "furniture", "decor", "household"],
    "toys & games": ["toys", "games", "play", "children"],
    "beauty": ["beauty", "cosmetics", "personal care", "skincare"],
    "sports": ["sports", "fitness", "outdoor", "exercise"],
    "food & groceries": ["food", "groceries", "grocery", "supermarket"],
    "office supplies": ["office", "stationery", "supplies"],
    "pet supplies": ["pet", "animal"],
}


class CategoryMappingService:
    """Service for mapping extracted receipt items to categories.

    Uses category hints from extraction and fuzzy matching against
    existing categories in the database.
    """

    def __init__(
        self,
        category_repository: CategoryRepository,
        default_category_id: int | None = None,
    ) -> None:
        """Initialize the service.

        Args:
            category_repository: Repository for category access.
            default_category_id: Default category for unmapped items (optional).
        """
        self._category_repo = category_repository
        self._default_category_id = default_category_id
        self._category_cache: dict[str, Category] | None = None

    def _load_categories(self) -> dict[str, Category]:
        """Load all categories and index by lowercase name.

        Returns:
            Dictionary mapping lowercase names to Category objects.
        """
        if self._category_cache is None:
            all_categories = self._category_repo.get_all()
            self._category_cache = {cat.name.lower(): cat for cat in all_categories}
        return self._category_cache

    def reload_categories(self) -> int:
        """Reload category cache.

        Returns:
            Number of categories loaded.
        """
        self._category_cache = None
        return len(self._load_categories())

    def _normalize_hint(self, hint: str | None) -> str:
        """Normalize a category hint for matching.

        Args:
            hint: Raw category hint from extraction.

        Returns:
            Normalized lowercase hint.
        """
        if not hint:
            return ""
        return hint.lower().strip()

    def _find_category_by_hint(self, hint: str | None) -> Category | None:
        """Find a category matching the given hint.

        Args:
            hint: Category hint from extraction.

        Returns:
            Matching Category or None.
        """
        categories = self._load_categories()
        normalized_hint = self._normalize_hint(hint)

        if not normalized_hint:
            return None

        # Direct match
        if normalized_hint in categories:
            return categories[normalized_hint]

        # Check hint mappings
        for hint_key, patterns in CATEGORY_HINT_MAPPINGS.items():
            if normalized_hint == hint_key or any(
                p in normalized_hint for p in patterns
            ):
                # Find matching category by patterns
                for pattern in patterns:
                    for cat_name, category in categories.items():
                        if pattern in cat_name:
                            return category

        # Partial match on category names
        for cat_name, category in categories.items():
            if normalized_hint in cat_name or cat_name in normalized_hint:
                return category

        return None

    def _find_category_by_item_name(self, item_name: str) -> Category | None:
        """Try to find a category based on item name keywords.

        Args:
            item_name: Item name/description.

        Returns:
            Matching Category or None.
        """
        categories = self._load_categories()
        name_lower = item_name.lower()

        # Common item keywords to category mappings
        keyword_mappings = {
            "book": ["books"],
            "cable": ["electronics"],
            "charger": ["electronics"],
            "phone": ["electronics"],
            "laptop": ["electronics", "computer"],
            "keyboard": ["electronics", "computer"],
            "mouse": ["electronics", "computer"],
            "shirt": ["clothing"],
            "pants": ["clothing"],
            "shoes": ["clothing", "footwear"],
            "toy": ["toys"],
            "game": ["toys", "games"],
        }

        for keyword, patterns in keyword_mappings.items():
            if keyword in name_lower:
                for pattern in patterns:
                    for cat_name, category in categories.items():
                        if pattern in cat_name:
                            return category

        return None

    def map_item(self, item: ExtractedItem) -> tuple[int | None, str | None]:
        """Map a single item to a category.

        Args:
            item: Extracted item to map.

        Returns:
            Tuple of (category_id, category_name) or (None, None) if not mapped.
        """
        # Try category hint first
        category = self._find_category_by_hint(item.category_hint)

        # Fall back to item name matching
        if category is None:
            category = self._find_category_by_item_name(item.name)

        # Use default if configured
        if category is None and self._default_category_id is not None:
            try:
                category = self._category_repo.get(self._default_category_id)
            except Exception:
                category = None

        if category:
            return (category.id, category.name)
        return (None, None)

    def map_receipt(self, receipt: ExtractedReceipt) -> MappingResult:
        """Map all items in a receipt to categories.

        Args:
            receipt: Extracted receipt with items.

        Returns:
            MappingResult with mapped and unmapped items.
        """
        mapped: list[MappedItem] = []
        unmapped: list[ExtractedItem] = []
        total_value = Decimal("0")
        category_totals: dict[int, Decimal] = {}

        for item in receipt.items:
            category_id, category_name = self.map_item(item)

            if category_id is not None and category_name is not None:
                mapped.append(
                    MappedItem(
                        item=item, category_id=category_id, category_name=category_name
                    )
                )
                item_value = item.price * item.quantity
                total_value += item_value
                category_totals[category_id] = (
                    category_totals.get(category_id, Decimal("0")) + item_value
                )
            else:
                unmapped.append(item)

        # Find dominant category (highest total value)
        dominant_id = None
        if category_totals:
            dominant_id = max(category_totals, key=lambda k: category_totals[k])

        return MappingResult(
            mapped_items=mapped,
            unmapped_items=unmapped,
            total_mapped_value=total_value,
            dominant_category_id=dominant_id,
        )

    def validate_total(
        self,
        receipt: ExtractedReceipt,
        transaction_amount: Decimal,
        tolerance: Decimal = Decimal("0.05"),
    ) -> tuple[bool, Decimal]:
        """Validate that receipt total matches transaction amount.

        Args:
            receipt: Extracted receipt.
            transaction_amount: Transaction amount (typically negative for purchases).
            tolerance: Allowed difference as decimal (0.05 = 5%).

        Returns:
            Tuple of (is_valid, difference_ratio).
        """
        # Transaction amounts are usually negative for purchases
        txn_abs = abs(transaction_amount)
        receipt_total = abs(receipt.total)

        if txn_abs == 0:
            return (False, Decimal("1"))

        diff_ratio = abs(receipt_total - txn_abs) / txn_abs

        return (diff_ratio <= tolerance, diff_ratio)
