"""ClassificationRuleRepository for managing classification rules."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from finance_api.models.classification_rule import ClassificationRule


class ClassificationRuleNotFoundError(Exception):
    """Raised when a classification rule is not found."""

    pass


class ClassificationRuleRepository:
    """Repository for classification rule CRUD operations."""

    def __init__(self, session: Session) -> None:
        """Initialize the repository with a database session.

        Args:
            session: SQLAlchemy database session.
        """
        self._session = session

    def create(
        self,
        name: str,
        rule_expression: str,
        category_id: int,
        priority: int = 0,
        requires_disambiguation: bool = False,
    ) -> ClassificationRule:
        """Create a new classification rule.

        Args:
            name: Human-readable rule name.
            rule_expression: The rule-engine expression.
            category_id: Target category ID.
            priority: Evaluation priority (lower = higher priority).
            requires_disambiguation: Whether AI disambiguation is needed after match.

        Returns:
            The created ClassificationRule.
        """
        rule = ClassificationRule(
            name=name,
            rule_expression=rule_expression,
            category_id=category_id,
            priority=priority,
            requires_disambiguation=requires_disambiguation,
            is_active=True,
        )
        self._session.add(rule)
        self._session.flush()
        return rule

    def get(self, rule_id: int) -> ClassificationRule:
        """Get a classification rule by ID.

        Args:
            rule_id: The rule ID.

        Returns:
            The ClassificationRule.

        Raises:
            ClassificationRuleNotFoundError: If rule doesn't exist.
        """
        rule = self._session.get(ClassificationRule, rule_id)
        if rule is None:
            raise ClassificationRuleNotFoundError(
                f"Classification rule {rule_id} not found"
            )
        return rule

    def get_active_by_priority(self) -> list[ClassificationRule]:
        """Get all active rules ordered by priority.

        Returns:
            List of active ClassificationRules ordered by priority (lower first).
        """
        stmt = (
            select(ClassificationRule)
            .where(ClassificationRule.is_active == True)  # noqa: E712
            .order_by(ClassificationRule.priority)
        )
        return list(self._session.execute(stmt).scalars().all())

    def get_by_category(self, category_id: int) -> list[ClassificationRule]:
        """Get all rules targeting a specific category.

        Args:
            category_id: The target category ID.

        Returns:
            List of ClassificationRules for the category.
        """
        stmt = (
            select(ClassificationRule)
            .where(ClassificationRule.category_id == category_id)
            .order_by(ClassificationRule.priority)
        )
        return list(self._session.execute(stmt).scalars().all())

    def update(
        self,
        rule_id: int,
        name: str | None = None,
        rule_expression: str | None = None,
        category_id: int | None = None,
        priority: int | None = None,
        requires_disambiguation: bool | None = None,
    ) -> ClassificationRule:
        """Update a classification rule.

        Args:
            rule_id: The rule ID.
            name: New name (None to keep current).
            rule_expression: New expression (None to keep current).
            category_id: New category ID (None to keep current).
            priority: New priority (None to keep current).
            requires_disambiguation: New disambiguation flag (None to keep current).

        Returns:
            The updated ClassificationRule.

        Raises:
            ClassificationRuleNotFoundError: If rule doesn't exist.
        """
        rule = self.get(rule_id)

        if name is not None:
            rule.name = name
        if rule_expression is not None:
            rule.rule_expression = rule_expression
        if category_id is not None:
            rule.category_id = category_id
        if priority is not None:
            rule.priority = priority
        if requires_disambiguation is not None:
            rule.requires_disambiguation = requires_disambiguation

        return rule

    def activate(self, rule_id: int) -> ClassificationRule:
        """Activate a classification rule.

        Args:
            rule_id: The rule ID.

        Returns:
            The activated ClassificationRule.

        Raises:
            ClassificationRuleNotFoundError: If rule doesn't exist.
        """
        rule = self.get(rule_id)
        rule.is_active = True
        return rule

    def deactivate(self, rule_id: int) -> ClassificationRule:
        """Deactivate a classification rule.

        Args:
            rule_id: The rule ID.

        Returns:
            The deactivated ClassificationRule.

        Raises:
            ClassificationRuleNotFoundError: If rule doesn't exist.
        """
        rule = self.get(rule_id)
        rule.is_active = False
        return rule

    def delete(self, rule_id: int) -> None:
        """Delete a classification rule.

        Args:
            rule_id: The rule ID.

        Raises:
            ClassificationRuleNotFoundError: If rule doesn't exist.
        """
        rule = self.get(rule_id)
        self._session.delete(rule)
