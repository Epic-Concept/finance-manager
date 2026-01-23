"""Tests for seed_categories script and CATEGORY_HIERARCHY data structure."""

from finance_api.scripts.seed_categories import CATEGORY_HIERARCHY

# Valid values for seed data
VALID_COMMITMENT_LEVELS = {0, 1, 2, 3, 4}
VALID_FREQUENCIES = {"monthly", "weekly", "annual", "one-time", "quarterly"}


def count_categories(hierarchy: list) -> int:
    """Count total categories including nested children."""
    count = 0
    for cat in hierarchy:
        count += 1
        count += count_categories(cat.get("children", []))
    return count


def get_all_categories(hierarchy: list) -> list:
    """Flatten hierarchy into list of all category dicts."""
    categories = []
    for cat in hierarchy:
        categories.append(cat)
        categories.extend(get_all_categories(cat.get("children", [])))
    return categories


class TestCategoryHierarchyStructure:
    """Tests for CATEGORY_HIERARCHY structure validity."""

    def test_hierarchy_is_not_empty(self) -> None:
        """Test that CATEGORY_HIERARCHY has content."""
        assert len(CATEGORY_HIERARCHY) > 0

    def test_all_categories_have_name(self) -> None:
        """Test every category has a name field."""
        all_cats = get_all_categories(CATEGORY_HIERARCHY)
        for cat in all_cats:
            assert "name" in cat, f"Category missing name: {cat}"
            assert isinstance(cat["name"], str)
            assert len(cat["name"]) > 0

    def test_all_categories_have_commitment_level(self) -> None:
        """Test every category has a commitment_level field."""
        all_cats = get_all_categories(CATEGORY_HIERARCHY)
        for cat in all_cats:
            assert (
                "commitment_level" in cat
            ), f"Category {cat['name']} missing commitment_level"

    def test_all_commitment_levels_are_valid(self) -> None:
        """Test all commitment_level values are 0-4."""
        all_cats = get_all_categories(CATEGORY_HIERARCHY)
        for cat in all_cats:
            level = cat["commitment_level"]
            assert (
                level in VALID_COMMITMENT_LEVELS
            ), f"Category {cat['name']} has invalid commitment_level: {level}"

    def test_all_categories_have_frequency(self) -> None:
        """Test every category has a frequency field."""
        all_cats = get_all_categories(CATEGORY_HIERARCHY)
        for cat in all_cats:
            assert "frequency" in cat, f"Category {cat['name']} missing frequency"

    def test_all_frequencies_are_valid(self) -> None:
        """Test all frequency values are in the valid set."""
        all_cats = get_all_categories(CATEGORY_HIERARCHY)
        for cat in all_cats:
            freq = cat["frequency"]
            assert (
                freq in VALID_FREQUENCIES
            ), f"Category {cat['name']} has invalid frequency: {freq}"

    def test_children_field_is_list_or_missing(self) -> None:
        """Test children field is always a list when present."""
        all_cats = get_all_categories(CATEGORY_HIERARCHY)
        for cat in all_cats:
            if "children" in cat:
                assert isinstance(
                    cat["children"], list
                ), f"Category {cat['name']} has non-list children"


class TestCategoryHierarchyCounts:
    """Tests for expected category counts."""

    def test_total_category_count(self) -> None:
        """Test total number of categories is 117."""
        total = count_categories(CATEGORY_HIERARCHY)
        assert total == 117, f"Expected 117 categories, got {total}"

    def test_top_level_category_count(self) -> None:
        """Test number of top-level categories."""
        assert len(CATEGORY_HIERARCHY) == 29

    def test_categories_per_commitment_level(self) -> None:
        """Test distribution of categories across commitment levels."""
        all_cats = get_all_categories(CATEGORY_HIERARCHY)
        counts_per_level = dict.fromkeys(range(5), 0)

        for cat in all_cats:
            counts_per_level[cat["commitment_level"]] += 1

        # Level 0 (Survival): Housing, Utilities, Food, Healthcare, Transportation, Debt
        assert counts_per_level[0] > 15, "Should have significant survival categories"

        # Level 1 (Committed): Insurance, Communication, Dependents, Pets, Subscriptions
        assert counts_per_level[1] > 10, "Should have committed categories"

        # Level 2 (Lifestyle): Food quality, Transportation comfort, Personal care, etc.
        assert counts_per_level[2] > 15, "Should have lifestyle categories"

        # Level 3 (Discretionary): Dining, Entertainment, Hobbies, Shopping, Gifts, Travel
        assert counts_per_level[3] > 15, "Should have discretionary categories"

        # Level 4 (Future): Emergency, Retirement, Sinking Funds, Savings Goals
        assert counts_per_level[4] > 5, "Should have future/savings categories"


class TestCategoryHierarchyCommitmentLevelConsistency:
    """Tests for commitment level consistency within hierarchy."""

    def test_children_match_or_exceed_parent_commitment_level(self) -> None:
        """Children should have the same or higher commitment level as parent."""

        # This is a policy test - children shouldn't be more essential than parents
        # Actually for this hierarchy, children typically have same level as parent
        def check_children(cats: list, parent_level: int | None = None) -> None:
            for cat in cats:
                level = cat["commitment_level"]
                if parent_level is not None:
                    # In this design, children should have same commitment level
                    assert level == parent_level, (
                        f"Category {cat['name']} has different level ({level}) "
                        f"than parent ({parent_level})"
                    )
                check_children(cat.get("children", []), level)

        check_children(CATEGORY_HIERARCHY)


class TestCategoryHierarchyUniqueNames:
    """Tests for name uniqueness."""

    def test_all_category_names_unique(self) -> None:
        """Test that all category names are unique."""
        all_cats = get_all_categories(CATEGORY_HIERARCHY)
        names = [cat["name"] for cat in all_cats]
        duplicates = [name for name in names if names.count(name) > 1]

        assert (
            len(duplicates) == 0
        ), f"Duplicate category names found: {set(duplicates)}"


class TestCategoryHierarchyExpectedCategories:
    """Tests for presence of expected categories."""

    def test_survival_categories_exist(self) -> None:
        """Test key survival (level 0) categories exist."""
        all_cats = get_all_categories(CATEGORY_HIERARCHY)
        names = {cat["name"] for cat in all_cats}

        expected_survival = [
            "Housing",
            "Rent",
            "Mortgage",
            "Electricity",
            "Groceries - Basic",
            "Health Insurance",
        ]

        for expected in expected_survival:
            assert expected in names, f"Missing survival category: {expected}"

    def test_committed_categories_exist(self) -> None:
        """Test key committed (level 1) categories exist."""
        all_cats = get_all_categories(CATEGORY_HIERARCHY)
        names = {cat["name"] for cat in all_cats}

        expected_committed = [
            "Auto Insurance",
            "Mobile Phone",
            "Internet",
            "Daycare",
            "Pet Food",
        ]

        for expected in expected_committed:
            assert expected in names, f"Missing committed category: {expected}"

    def test_discretionary_categories_exist(self) -> None:
        """Test key discretionary (level 3) categories exist."""
        all_cats = get_all_categories(CATEGORY_HIERARCHY)
        names = {cat["name"] for cat in all_cats}

        expected_discretionary = [
            "Restaurants",
            "Streaming Services",
            "Movies",
            "Electronics",
            "Travel",
        ]

        for expected in expected_discretionary:
            assert expected in names, f"Missing discretionary category: {expected}"

    def test_future_categories_exist(self) -> None:
        """Test key future/savings (level 4) categories exist."""
        all_cats = get_all_categories(CATEGORY_HIERARCHY)
        names = {cat["name"] for cat in all_cats}

        expected_future = [
            "Emergency Fund",
            "401k",
            "IRA",
            "Vacation Fund",
        ]

        for expected in expected_future:
            assert expected in names, f"Missing future category: {expected}"
