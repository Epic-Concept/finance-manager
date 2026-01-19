"""CategoryRepository for maintaining category hierarchy with closure table consistency."""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from finance_api.models.category import Category, CategoryClosure
from finance_api.models.transaction import Transaction
from finance_api.models.transaction_category import TransactionCategory


class CategoryNotFoundError(Exception):
    """Raised when a category is not found."""

    pass


class CategoryHasChildrenError(Exception):
    """Raised when trying to delete a category that has children without cascade."""

    pass


class CategoryRepository:
    """Repository for category CRUD operations with closure table maintenance."""

    def __init__(self, session: Session) -> None:
        """Initialize the repository with a database session.

        Args:
            session: SQLAlchemy database session.
        """
        self._session = session

    def create(
        self,
        name: str,
        parent_id: int | None = None,
        description: str | None = None,
    ) -> Category:
        """Create a category and populate closure table entries.

        Args:
            name: The category name.
            parent_id: Optional parent category ID. None for root categories.
            description: Optional category description.

        Returns:
            The created Category.

        Raises:
            CategoryNotFoundError: If parent_id is provided but doesn't exist.
        """
        # Validate parent exists if provided
        if parent_id is not None:
            parent = self._session.get(Category, parent_id)
            if parent is None:
                raise CategoryNotFoundError(f"Parent category {parent_id} not found")

        # Create the category
        category = Category(
            name=name,
            parent_id=parent_id,
            description=description,
        )
        self._session.add(category)
        self._session.flush()  # Get the ID

        # Create closure table entries
        # 1. Self-reference (depth 0)
        self_closure = CategoryClosure(
            ancestor_id=category.id,
            descendant_id=category.id,
            depth=0,
        )
        self._session.add(self_closure)

        # 2. Copy all ancestor entries from parent if exists
        if parent_id is not None:
            # Get all ancestors of the parent (including the parent itself)
            stmt = select(CategoryClosure).where(
                CategoryClosure.descendant_id == parent_id
            )
            parent_ancestors = self._session.execute(stmt).scalars().all()

            for ancestor_entry in parent_ancestors:
                new_closure = CategoryClosure(
                    ancestor_id=ancestor_entry.ancestor_id,
                    descendant_id=category.id,
                    depth=ancestor_entry.depth + 1,
                )
                self._session.add(new_closure)

        return category

    def move(self, category_id: int, new_parent_id: int | None) -> Category:
        """Move a category to a new parent, updating all closure entries.

        Args:
            category_id: The category to move.
            new_parent_id: The new parent ID, or None to make it a root category.

        Returns:
            The moved Category.

        Raises:
            CategoryNotFoundError: If category or new parent doesn't exist.
        """
        category = self._session.get(Category, category_id)
        if category is None:
            raise CategoryNotFoundError(f"Category {category_id} not found")

        if new_parent_id is not None:
            new_parent = self._session.get(Category, new_parent_id)
            if new_parent is None:
                raise CategoryNotFoundError(f"New parent category {new_parent_id} not found")

        # Get all descendants of this category (including self)
        descendant_ids_stmt = select(CategoryClosure.descendant_id).where(
            CategoryClosure.ancestor_id == category_id
        )
        descendant_ids = [
            r for r in self._session.execute(descendant_ids_stmt).scalars().all()
        ]

        # Delete all closure entries where:
        # - descendant is in the subtree AND
        # - ancestor is NOT in the subtree
        for desc_id in descendant_ids:
            delete_stmt = (
                CategoryClosure.__table__.delete()
                .where(CategoryClosure.descendant_id == desc_id)
                .where(CategoryClosure.ancestor_id.notin_(descendant_ids))
            )
            self._session.execute(delete_stmt)

        # Create new closure entries linking to new ancestors
        if new_parent_id is not None:
            # Get all ancestors of the new parent (including itself)
            new_ancestors_stmt = select(CategoryClosure).where(
                CategoryClosure.descendant_id == new_parent_id
            )
            new_ancestors = self._session.execute(new_ancestors_stmt).scalars().all()

            # For each node in the subtree, create entries to new ancestors
            for desc_id in descendant_ids:
                # Get depth of this descendant relative to category_id
                depth_stmt = select(CategoryClosure.depth).where(
                    CategoryClosure.ancestor_id == category_id,
                    CategoryClosure.descendant_id == desc_id,
                )
                relative_depth = self._session.execute(depth_stmt).scalar_one()

                for ancestor_entry in new_ancestors:
                    new_closure = CategoryClosure(
                        ancestor_id=ancestor_entry.ancestor_id,
                        descendant_id=desc_id,
                        depth=ancestor_entry.depth + 1 + relative_depth,
                    )
                    self._session.add(new_closure)

        # Update the category's parent_id
        category.parent_id = new_parent_id

        return category

    def delete(self, category_id: int, cascade: bool = False) -> None:
        """Delete a category and its closure entries.

        Args:
            category_id: The category to delete.
            cascade: If True, also delete all descendant categories.

        Raises:
            CategoryNotFoundError: If category doesn't exist.
            CategoryHasChildrenError: If category has children and cascade is False.
        """
        category = self._session.get(Category, category_id)
        if category is None:
            raise CategoryNotFoundError(f"Category {category_id} not found")

        # Check for children
        children_stmt = select(Category).where(Category.parent_id == category_id)
        children = self._session.execute(children_stmt).scalars().all()

        if children and not cascade:
            raise CategoryHasChildrenError(
                f"Category {category_id} has {len(children)} children. Use cascade=True to delete."
            )

        if cascade:
            # Get all descendants (excluding self) ordered by depth (deepest first)
            descendants_stmt = (
                select(CategoryClosure.descendant_id)
                .where(CategoryClosure.ancestor_id == category_id)
                .where(CategoryClosure.descendant_id != category_id)
                .order_by(CategoryClosure.depth.desc())
            )
            descendant_ids = list(
                self._session.execute(descendants_stmt).scalars().all()
            )

            # Delete descendants from deepest to shallowest
            for desc_id in descendant_ids:
                # Delete closure entries
                self._session.execute(
                    CategoryClosure.__table__.delete().where(
                        (CategoryClosure.ancestor_id == desc_id)
                        | (CategoryClosure.descendant_id == desc_id)
                    )
                )
                # Delete category
                desc_category = self._session.get(Category, desc_id)
                if desc_category:
                    self._session.delete(desc_category)

        # Delete closure entries for this category
        self._session.execute(
            CategoryClosure.__table__.delete().where(
                (CategoryClosure.ancestor_id == category_id)
                | (CategoryClosure.descendant_id == category_id)
            )
        )

        # Delete the category
        self._session.delete(category)

    def get_ancestors(self, category_id: int) -> list[Category]:
        """Get all ancestors of a category (including self).

        Args:
            category_id: The category ID.

        Returns:
            List of ancestor categories ordered from root to self.

        Raises:
            CategoryNotFoundError: If category doesn't exist.
        """
        category = self._session.get(Category, category_id)
        if category is None:
            raise CategoryNotFoundError(f"Category {category_id} not found")

        stmt = (
            select(Category)
            .join(
                CategoryClosure,
                Category.id == CategoryClosure.ancestor_id,
            )
            .where(CategoryClosure.descendant_id == category_id)
            .order_by(CategoryClosure.depth.desc())
        )

        return list(self._session.execute(stmt).scalars().all())

    def get_descendants(self, category_id: int) -> list[Category]:
        """Get all descendants of a category (including self).

        Args:
            category_id: The category ID.

        Returns:
            List of descendant categories ordered by depth (self first).

        Raises:
            CategoryNotFoundError: If category doesn't exist.
        """
        category = self._session.get(Category, category_id)
        if category is None:
            raise CategoryNotFoundError(f"Category {category_id} not found")

        stmt = (
            select(Category)
            .join(
                CategoryClosure,
                Category.id == CategoryClosure.descendant_id,
            )
            .where(CategoryClosure.ancestor_id == category_id)
            .order_by(CategoryClosure.depth)
        )

        return list(self._session.execute(stmt).scalars().all())

    def get_subtree_transaction_sum(self, category_id: int) -> Decimal:
        """Sum all transactions in a category and its descendants.

        Args:
            category_id: The root category ID.

        Returns:
            Sum of all transaction amounts in the subtree. Returns 0 if no transactions.

        Raises:
            CategoryNotFoundError: If category doesn't exist.
        """
        category = self._session.get(Category, category_id)
        if category is None:
            raise CategoryNotFoundError(f"Category {category_id} not found")

        stmt = (
            select(func.coalesce(func.sum(Transaction.amount), 0))
            .select_from(Transaction)
            .join(
                TransactionCategory,
                Transaction.id == TransactionCategory.transaction_id,
            )
            .join(
                CategoryClosure,
                TransactionCategory.category_id == CategoryClosure.descendant_id,
            )
            .where(CategoryClosure.ancestor_id == category_id)
        )

        result = self._session.execute(stmt).scalar_one()
        return Decimal(result) if result is not None else Decimal("0")
