"""Tests for Category and CategoryClosure models."""

from finance_api.models.category import Category, CategoryClosure


def test_category_creation() -> None:
    """Test Category can be instantiated with required fields."""
    category = Category(name="Food")

    assert category.name == "Food"
    assert category.parent_id is None
    assert category.description is None


def test_category_with_parent() -> None:
    """Test Category with parent_id."""
    category = Category(
        name="Groceries",
        parent_id=1,
        description="Weekly grocery shopping",
    )

    assert category.name == "Groceries"
    assert category.parent_id == 1
    assert category.description == "Weekly grocery shopping"


def test_category_repr() -> None:
    """Test Category string representation."""
    category = Category(id=1, name="Food")

    assert repr(category) == "<Category(id=1, name='Food')>"


def test_category_table_name() -> None:
    """Test Category table configuration."""
    assert Category.__tablename__ == "categories"
    assert Category.__table_args__["schema"] == "finance"


def test_category_closure_creation() -> None:
    """Test CategoryClosure can be instantiated."""
    closure = CategoryClosure(
        ancestor_id=1,
        descendant_id=2,
        depth=1,
    )

    assert closure.ancestor_id == 1
    assert closure.descendant_id == 2
    assert closure.depth == 1


def test_category_closure_self_reference() -> None:
    """Test CategoryClosure self-reference (depth 0)."""
    closure = CategoryClosure(
        ancestor_id=1,
        descendant_id=1,
        depth=0,
    )

    assert closure.ancestor_id == closure.descendant_id
    assert closure.depth == 0


def test_category_closure_repr() -> None:
    """Test CategoryClosure string representation."""
    closure = CategoryClosure(
        ancestor_id=1,
        descendant_id=2,
        depth=1,
    )

    assert repr(closure) == "<CategoryClosure(ancestor=1, descendant=2, depth=1)>"


def test_category_closure_table_name() -> None:
    """Test CategoryClosure table configuration."""
    assert CategoryClosure.__tablename__ == "category_closure"
    assert CategoryClosure.__table_args__[1]["schema"] == "finance"


# Tests for commitment hierarchy fields (Task 1.5)


def test_category_with_commitment_level() -> None:
    """Test Category with commitment_level field."""
    category = Category(
        name="Housing",
        commitment_level=0,  # Survival level
    )

    assert category.name == "Housing"
    assert category.commitment_level == 0


def test_category_commitment_level_all_values() -> None:
    """Test all valid commitment level values."""
    # 0=Survival, 1=Committed, 2=Lifestyle, 3=Discretionary, 4=Future
    for level in range(5):
        category = Category(name=f"Level {level}", commitment_level=level)
        assert category.commitment_level == level


def test_category_commitment_level_nullable() -> None:
    """Test commitment_level defaults to None."""
    category = Category(name="No commitment level")

    assert category.commitment_level is None


def test_category_with_frequency() -> None:
    """Test Category with frequency field."""
    category = Category(
        name="Rent",
        frequency="monthly",
    )

    assert category.name == "Rent"
    assert category.frequency == "monthly"


def test_category_frequency_values() -> None:
    """Test various frequency values."""
    frequencies = ["monthly", "weekly", "annual", "one-time", "quarterly"]
    for freq in frequencies:
        category = Category(name=f"{freq} expense", frequency=freq)
        assert category.frequency == freq


def test_category_frequency_nullable() -> None:
    """Test frequency defaults to None."""
    category = Category(name="No frequency")

    assert category.frequency is None


def test_category_is_essential_default() -> None:
    """Test is_essential defaults to None before DB persistence (server-side default)."""
    category = Category(name="Non-essential category")

    # Note: The default=False is a server-side default applied by SQLAlchemy on insert.
    # Before persistence, the value is None. After insert, the DB returns False.
    assert category.is_essential is None


def test_category_is_essential_true() -> None:
    """Test Category with is_essential set to True."""
    category = Category(
        name="Mortgage",
        is_essential=True,
    )

    assert category.name == "Mortgage"
    assert category.is_essential is True


def test_category_is_essential_false_explicit() -> None:
    """Test Category with is_essential explicitly set to False."""
    category = Category(
        name="Entertainment",
        is_essential=False,
    )

    assert category.is_essential is False


def test_category_with_all_commitment_fields() -> None:
    """Test Category with all commitment-related fields set."""
    category = Category(
        name="Rent/Mortgage",
        commitment_level=0,  # Survival
        frequency="monthly",
        is_essential=True,
        description="Primary housing expense",
    )

    assert category.name == "Rent/Mortgage"
    assert category.commitment_level == 0
    assert category.frequency == "monthly"
    assert category.is_essential is True
    assert category.description == "Primary housing expense"


def test_category_commitment_fields_with_parent() -> None:
    """Test Category commitment fields work with parent relationship."""
    category = Category(
        name="Child Category",
        parent_id=1,
        commitment_level=2,  # Lifestyle
        frequency="weekly",
        is_essential=False,
    )

    assert category.parent_id == 1
    assert category.commitment_level == 2
    assert category.frequency == "weekly"
    assert category.is_essential is False
