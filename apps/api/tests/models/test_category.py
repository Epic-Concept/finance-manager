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
