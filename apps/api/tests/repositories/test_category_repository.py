"""Tests for CategoryRepository."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from finance_api.models.category import Category, CategoryClosure
from finance_api.models.transaction import Transaction
from finance_api.models.transaction_category import TransactionCategory
from finance_api.repositories.category_repository import (
    CategoryHasChildrenError,
    CategoryNotFoundError,
    CategoryRepository,
)


class TestCategoryRepositoryCreate:
    """Tests for CategoryRepository.create()."""

    def test_create_root_category(self, db_session: Session) -> None:
        """Test creating a root category (no parent)."""
        repo = CategoryRepository(db_session)

        category = repo.create(name="Food", description="Food expenses")
        db_session.flush()

        assert category.id is not None
        assert category.name == "Food"
        assert category.parent_id is None
        assert category.description == "Food expenses"

        # Check closure table has self-reference
        closures = (
            db_session.query(CategoryClosure)
            .filter(CategoryClosure.descendant_id == category.id)
            .all()
        )
        assert len(closures) == 1
        assert closures[0].ancestor_id == category.id
        assert closures[0].depth == 0

    def test_create_child_category(self, db_session: Session) -> None:
        """Test creating a child category with proper closure entries."""
        repo = CategoryRepository(db_session)

        # Create parent
        parent = repo.create(name="Food")
        db_session.flush()

        # Create child
        child = repo.create(name="Groceries", parent_id=parent.id)
        db_session.flush()

        assert child.parent_id == parent.id

        # Check closure table entries for child
        closures = (
            db_session.query(CategoryClosure)
            .filter(CategoryClosure.descendant_id == child.id)
            .order_by(CategoryClosure.depth)
            .all()
        )
        assert len(closures) == 2

        # Self-reference (depth 0)
        assert closures[0].ancestor_id == child.id
        assert closures[0].depth == 0

        # Parent reference (depth 1)
        assert closures[1].ancestor_id == parent.id
        assert closures[1].depth == 1

    def test_create_grandchild_category(self, db_session: Session) -> None:
        """Test creating a grandchild with all ancestor closure entries."""
        repo = CategoryRepository(db_session)

        # Create hierarchy: Food -> Groceries -> Vegetables
        food = repo.create(name="Food")
        db_session.flush()
        groceries = repo.create(name="Groceries", parent_id=food.id)
        db_session.flush()
        vegetables = repo.create(name="Vegetables", parent_id=groceries.id)
        db_session.flush()

        # Check closure entries for vegetables
        closures = (
            db_session.query(CategoryClosure)
            .filter(CategoryClosure.descendant_id == vegetables.id)
            .order_by(CategoryClosure.depth)
            .all()
        )
        assert len(closures) == 3

        # Self (depth 0)
        assert closures[0].ancestor_id == vegetables.id
        assert closures[0].depth == 0

        # Parent - Groceries (depth 1)
        assert closures[1].ancestor_id == groceries.id
        assert closures[1].depth == 1

        # Grandparent - Food (depth 2)
        assert closures[2].ancestor_id == food.id
        assert closures[2].depth == 2

    def test_create_with_invalid_parent(self, db_session: Session) -> None:
        """Test creating a category with non-existent parent raises error."""
        repo = CategoryRepository(db_session)

        with pytest.raises(CategoryNotFoundError) as exc_info:
            repo.create(name="Orphan", parent_id=9999)

        assert "9999" in str(exc_info.value)


class TestCategoryRepositoryGetAncestors:
    """Tests for CategoryRepository.get_ancestors()."""

    def test_get_ancestors_root(self, db_session: Session) -> None:
        """Test getting ancestors of a root category."""
        repo = CategoryRepository(db_session)

        root = repo.create(name="Root")
        db_session.flush()

        ancestors = repo.get_ancestors(root.id)

        assert len(ancestors) == 1
        assert ancestors[0].id == root.id

    def test_get_ancestors_nested(self, db_session: Session) -> None:
        """Test getting ancestors returns full path from root to self."""
        repo = CategoryRepository(db_session)

        # Create: Food -> Groceries -> Vegetables
        food = repo.create(name="Food")
        db_session.flush()
        groceries = repo.create(name="Groceries", parent_id=food.id)
        db_session.flush()
        vegetables = repo.create(name="Vegetables", parent_id=groceries.id)
        db_session.flush()

        ancestors = repo.get_ancestors(vegetables.id)

        # Should be ordered from root to self
        assert len(ancestors) == 3
        assert ancestors[0].name == "Food"
        assert ancestors[1].name == "Groceries"
        assert ancestors[2].name == "Vegetables"

    def test_get_ancestors_not_found(self, db_session: Session) -> None:
        """Test getting ancestors of non-existent category raises error."""
        repo = CategoryRepository(db_session)

        with pytest.raises(CategoryNotFoundError):
            repo.get_ancestors(9999)


class TestCategoryRepositoryGetDescendants:
    """Tests for CategoryRepository.get_descendants()."""

    def test_get_descendants_leaf(self, db_session: Session) -> None:
        """Test getting descendants of a leaf category."""
        repo = CategoryRepository(db_session)

        leaf = repo.create(name="Leaf")
        db_session.flush()

        descendants = repo.get_descendants(leaf.id)

        assert len(descendants) == 1
        assert descendants[0].id == leaf.id

    def test_get_descendants_nested(self, db_session: Session) -> None:
        """Test getting descendants returns entire subtree."""
        repo = CategoryRepository(db_session)

        # Create: Food -> Groceries -> Vegetables
        food = repo.create(name="Food")
        db_session.flush()
        groceries = repo.create(name="Groceries", parent_id=food.id)
        db_session.flush()
        vegetables = repo.create(name="Vegetables", parent_id=groceries.id)
        db_session.flush()

        descendants = repo.get_descendants(food.id)

        # Should be ordered by depth (self first)
        assert len(descendants) == 3
        assert descendants[0].name == "Food"
        assert descendants[1].name == "Groceries"
        assert descendants[2].name == "Vegetables"

    def test_get_descendants_not_found(self, db_session: Session) -> None:
        """Test getting descendants of non-existent category raises error."""
        repo = CategoryRepository(db_session)

        with pytest.raises(CategoryNotFoundError):
            repo.get_descendants(9999)


class TestCategoryRepositoryDelete:
    """Tests for CategoryRepository.delete()."""

    def test_delete_leaf_category(self, db_session: Session) -> None:
        """Test deleting a leaf category."""
        repo = CategoryRepository(db_session)

        category = repo.create(name="ToDelete")
        db_session.flush()
        category_id = category.id

        repo.delete(category_id)
        db_session.flush()

        # Category should be gone
        assert db_session.get(Category, category_id) is None

        # Closure entries should be gone
        closures = (
            db_session.query(CategoryClosure)
            .filter(
                (CategoryClosure.ancestor_id == category_id)
                | (CategoryClosure.descendant_id == category_id)
            )
            .all()
        )
        assert len(closures) == 0

    def test_delete_with_children_fails(self, db_session: Session) -> None:
        """Test deleting a category with children without cascade raises error."""
        repo = CategoryRepository(db_session)

        parent = repo.create(name="Parent")
        db_session.flush()
        repo.create(name="Child", parent_id=parent.id)
        db_session.flush()

        with pytest.raises(CategoryHasChildrenError):
            repo.delete(parent.id)

    def test_delete_with_cascade(self, db_session: Session) -> None:
        """Test deleting a category with cascade deletes entire subtree."""
        repo = CategoryRepository(db_session)

        # Create: Parent -> Child -> Grandchild
        parent = repo.create(name="Parent")
        db_session.flush()
        child = repo.create(name="Child", parent_id=parent.id)
        db_session.flush()
        grandchild = repo.create(name="Grandchild", parent_id=child.id)
        db_session.flush()

        parent_id = parent.id
        child_id = child.id
        grandchild_id = grandchild.id

        repo.delete(parent_id, cascade=True)
        db_session.flush()

        # All categories should be gone
        assert db_session.get(Category, parent_id) is None
        assert db_session.get(Category, child_id) is None
        assert db_session.get(Category, grandchild_id) is None

    def test_delete_not_found(self, db_session: Session) -> None:
        """Test deleting non-existent category raises error."""
        repo = CategoryRepository(db_session)

        with pytest.raises(CategoryNotFoundError):
            repo.delete(9999)


class TestCategoryRepositoryMove:
    """Tests for CategoryRepository.move()."""

    def test_move_to_new_parent(self, db_session: Session) -> None:
        """Test moving a category to a new parent."""
        repo = CategoryRepository(db_session)

        # Create: OldParent -> Child, NewParent
        old_parent = repo.create(name="OldParent")
        db_session.flush()
        new_parent = repo.create(name="NewParent")
        db_session.flush()
        child = repo.create(name="Child", parent_id=old_parent.id)
        db_session.flush()

        # Move child to new parent
        repo.move(child.id, new_parent.id)
        db_session.flush()

        # Check parent_id updated
        assert child.parent_id == new_parent.id

        # Check closure table updated
        ancestors = repo.get_ancestors(child.id)
        ancestor_names = [a.name for a in ancestors]

        assert "NewParent" in ancestor_names
        assert "OldParent" not in ancestor_names

    def test_move_to_root(self, db_session: Session) -> None:
        """Test moving a category to become a root."""
        repo = CategoryRepository(db_session)

        parent = repo.create(name="Parent")
        db_session.flush()
        child = repo.create(name="Child", parent_id=parent.id)
        db_session.flush()

        # Move child to root
        repo.move(child.id, None)
        db_session.flush()

        assert child.parent_id is None

        # Should only have self in ancestors
        ancestors = repo.get_ancestors(child.id)
        assert len(ancestors) == 1
        assert ancestors[0].id == child.id

    def test_move_not_found(self, db_session: Session) -> None:
        """Test moving non-existent category raises error."""
        repo = CategoryRepository(db_session)

        with pytest.raises(CategoryNotFoundError):
            repo.move(9999, None)

    def test_move_to_invalid_parent(self, db_session: Session) -> None:
        """Test moving to non-existent parent raises error."""
        repo = CategoryRepository(db_session)

        category = repo.create(name="Test")
        db_session.flush()

        with pytest.raises(CategoryNotFoundError):
            repo.move(category.id, 9999)


class TestCategoryRepositorySubtreeSum:
    """Tests for CategoryRepository.get_subtree_transaction_sum()."""

    def test_sum_empty(self, db_session: Session) -> None:
        """Test sum returns 0 for category with no transactions."""
        repo = CategoryRepository(db_session)

        category = repo.create(name="Empty")
        db_session.flush()

        total = repo.get_subtree_transaction_sum(category.id)

        assert total == Decimal("0")

    def test_sum_direct_transactions(self, db_session: Session) -> None:
        """Test sum includes direct transactions."""
        repo = CategoryRepository(db_session)

        category = repo.create(name="Food")
        db_session.flush()

        # Create transactions
        t1 = Transaction(
            transaction_date=date(2026, 1, 1),
            description="Grocery 1",
            amount=Decimal("50.00"),
        )
        t2 = Transaction(
            transaction_date=date(2026, 1, 2),
            description="Grocery 2",
            amount=Decimal("30.00"),
        )
        db_session.add_all([t1, t2])
        db_session.flush()

        # Link to category
        link1 = TransactionCategory(transaction_id=t1.id, category_id=category.id)
        link2 = TransactionCategory(transaction_id=t2.id, category_id=category.id)
        db_session.add_all([link1, link2])
        db_session.flush()

        total = repo.get_subtree_transaction_sum(category.id)

        assert total == Decimal("80.00")

    def test_sum_includes_descendants(self, db_session: Session) -> None:
        """Test sum includes transactions from descendant categories."""
        repo = CategoryRepository(db_session)

        # Create: Food -> Groceries
        food = repo.create(name="Food")
        db_session.flush()
        groceries = repo.create(name="Groceries", parent_id=food.id)
        db_session.flush()

        # Transaction in parent
        t1 = Transaction(
            transaction_date=date(2026, 1, 1),
            description="Restaurant",
            amount=Decimal("25.00"),
        )
        # Transaction in child
        t2 = Transaction(
            transaction_date=date(2026, 1, 2),
            description="Supermarket",
            amount=Decimal("75.00"),
        )
        db_session.add_all([t1, t2])
        db_session.flush()

        link1 = TransactionCategory(transaction_id=t1.id, category_id=food.id)
        link2 = TransactionCategory(transaction_id=t2.id, category_id=groceries.id)
        db_session.add_all([link1, link2])
        db_session.flush()

        # Sum at Food level should include both
        total = repo.get_subtree_transaction_sum(food.id)
        assert total == Decimal("100.00")

        # Sum at Groceries level should only include child transaction
        groceries_total = repo.get_subtree_transaction_sum(groceries.id)
        assert groceries_total == Decimal("75.00")

    def test_sum_not_found(self, db_session: Session) -> None:
        """Test sum for non-existent category raises error."""
        repo = CategoryRepository(db_session)

        with pytest.raises(CategoryNotFoundError):
            repo.get_subtree_transaction_sum(9999)
