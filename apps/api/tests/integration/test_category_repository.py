"""Integration tests for CategoryRepository with SQL Server."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from finance_api.models.category import Category
from finance_api.models.transaction import Transaction
from finance_api.models.transaction_category import TransactionCategory
from finance_api.repositories.category_repository import CategoryRepository


@pytest.mark.integration
class TestCategoryRepositoryIntegration:
    """Integration tests for CategoryRepository against SQL Server."""

    def test_create_root_category(self, sqlserver_session: Session) -> None:
        """Test creating a root category creates self-referential closure entry."""
        repo = CategoryRepository(sqlserver_session)

        category = repo.create(name="Root Category")
        sqlserver_session.flush()

        assert category.id is not None
        assert category.name == "Root Category"
        assert category.parent_id is None

        # Verify closure table has self-reference
        ancestors = repo.get_ancestors(category.id)
        assert len(ancestors) == 1
        assert ancestors[0].id == category.id

    def test_create_child_category_with_closure(
        self, sqlserver_session: Session
    ) -> None:
        """Test creating a child category creates proper closure entries."""
        repo = CategoryRepository(sqlserver_session)

        # Create hierarchy: Root -> Child -> Grandchild
        root = repo.create(name="Root")
        sqlserver_session.flush()

        child = repo.create(name="Child", parent_id=root.id)
        sqlserver_session.flush()

        grandchild = repo.create(name="Grandchild", parent_id=child.id)
        sqlserver_session.flush()

        # Verify grandchild has all ancestors
        ancestors = repo.get_ancestors(grandchild.id)
        ancestor_ids = [a.id for a in ancestors]

        assert len(ancestors) == 3
        assert grandchild.id in ancestor_ids
        assert child.id in ancestor_ids
        assert root.id in ancestor_ids

    def test_get_descendants(self, sqlserver_session: Session) -> None:
        """Test getting all descendants of a category."""
        repo = CategoryRepository(sqlserver_session)

        # Create hierarchy
        root = repo.create(name="Root")
        sqlserver_session.flush()

        child1 = repo.create(name="Child1", parent_id=root.id)
        child2 = repo.create(name="Child2", parent_id=root.id)
        sqlserver_session.flush()

        grandchild = repo.create(name="Grandchild", parent_id=child1.id)
        sqlserver_session.flush()

        # Root should have 4 descendants (including itself)
        descendants = repo.get_descendants(root.id)
        descendant_ids = [d.id for d in descendants]

        assert len(descendants) == 4
        assert root.id in descendant_ids
        assert child1.id in descendant_ids
        assert child2.id in descendant_ids
        assert grandchild.id in descendant_ids

    def test_move_category_updates_closure(self, sqlserver_session: Session) -> None:
        """Test moving a category updates closure table correctly."""
        repo = CategoryRepository(sqlserver_session)

        # Create initial hierarchy: Root1 -> Child, Root2
        root1 = repo.create(name="Root1")
        root2 = repo.create(name="Root2")
        sqlserver_session.flush()

        child = repo.create(name="Child", parent_id=root1.id)
        sqlserver_session.flush()

        # Verify child is under root1
        ancestors_before = repo.get_ancestors(child.id)
        ancestor_ids_before = [a.id for a in ancestors_before]
        assert root1.id in ancestor_ids_before
        assert root2.id not in ancestor_ids_before

        # Move child to root2
        repo.move(child.id, root2.id)
        sqlserver_session.flush()

        # Verify child is now under root2
        ancestors_after = repo.get_ancestors(child.id)
        ancestor_ids_after = [a.id for a in ancestors_after]
        assert root2.id in ancestor_ids_after
        assert root1.id not in ancestor_ids_after

    def test_delete_category_with_cascade(self, sqlserver_session: Session) -> None:
        """Test deleting a category with cascade removes descendants."""
        repo = CategoryRepository(sqlserver_session)

        # Create hierarchy
        root = repo.create(name="Root")
        sqlserver_session.flush()

        child = repo.create(name="Child", parent_id=root.id)
        sqlserver_session.flush()

        grandchild = repo.create(name="Grandchild", parent_id=child.id)
        sqlserver_session.flush()

        child_id = child.id
        grandchild_id = grandchild.id

        # Delete child with cascade
        repo.delete(child_id, cascade=True)
        sqlserver_session.flush()

        # Verify child and grandchild are deleted
        assert sqlserver_session.get(Category, child_id) is None
        assert sqlserver_session.get(Category, grandchild_id) is None

        # Root should still exist
        assert sqlserver_session.get(Category, root.id) is not None

    def test_delete_category_with_children_raises_error(
        self, sqlserver_session: Session
    ) -> None:
        """Test deleting a category with children raises error if not cascading."""
        from finance_api.repositories.category_repository import (
            CategoryHasChildrenError,
        )

        repo = CategoryRepository(sqlserver_session)

        # Create hierarchy: Root -> Child -> Grandchild
        root = repo.create(name="Root")
        sqlserver_session.flush()

        child = repo.create(name="Child", parent_id=root.id)
        sqlserver_session.flush()

        repo.create(name="Grandchild", parent_id=child.id)
        sqlserver_session.flush()

        child_id = child.id

        # Deleting child without cascade should raise error
        import pytest

        with pytest.raises(CategoryHasChildrenError):
            repo.delete(child_id, cascade=False)

    def test_subtree_transaction_sum(self, sqlserver_session: Session) -> None:
        """Test calculating sum of transactions in a category subtree."""
        repo = CategoryRepository(sqlserver_session)

        # Create category hierarchy
        root = repo.create(name="Expenses")
        sqlserver_session.flush()

        child = repo.create(name="Food", parent_id=root.id)
        sqlserver_session.flush()

        # Create transactions
        txn1 = Transaction(
            transaction_date=date(2026, 1, 15),
            amount=Decimal("50.00"),
            description="Groceries",
        )
        txn2 = Transaction(
            transaction_date=date(2026, 1, 15),
            amount=Decimal("25.00"),
            description="Restaurant",
        )
        txn3 = Transaction(
            transaction_date=date(2026, 1, 15),
            amount=Decimal("100.00"),
            description="Other expense",
        )
        sqlserver_session.add_all([txn1, txn2, txn3])
        sqlserver_session.flush()

        # Link transactions to categories
        link1 = TransactionCategory(transaction_id=txn1.id, category_id=child.id)
        link2 = TransactionCategory(transaction_id=txn2.id, category_id=child.id)
        link3 = TransactionCategory(transaction_id=txn3.id, category_id=root.id)
        sqlserver_session.add_all([link1, link2, link3])
        sqlserver_session.flush()

        # Sum for root should include all (50 + 25 + 100 = 175)
        root_sum = repo.get_subtree_transaction_sum(root.id)
        assert root_sum == Decimal("175.00")

        # Sum for child should be just its transactions (50 + 25 = 75)
        child_sum = repo.get_subtree_transaction_sum(child.id)
        assert child_sum == Decimal("75.00")

    def test_deeply_nested_hierarchy(self, sqlserver_session: Session) -> None:
        """Test closure table handles deep hierarchies correctly."""
        repo = CategoryRepository(sqlserver_session)

        # Create a chain of 10 categories
        categories = []
        parent_id = None

        for i in range(10):
            cat = repo.create(name=f"Level{i}", parent_id=parent_id)
            sqlserver_session.flush()
            categories.append(cat)
            parent_id = cat.id

        # Verify deepest category has all 10 ancestors
        deepest = categories[-1]
        ancestors = repo.get_ancestors(deepest.id)
        assert len(ancestors) == 10

        # Verify root has all 10 descendants
        root = categories[0]
        descendants = repo.get_descendants(root.id)
        assert len(descendants) == 10
