"""Tests for ClassificationRuleRepository."""

import pytest
from sqlalchemy.orm import Session

from finance_api.models.category import Category, CategoryClosure
from finance_api.repositories.classification_rule_repository import (
    ClassificationRuleNotFoundError,
    ClassificationRuleRepository,
)


@pytest.fixture
def test_category(db_session: Session) -> Category:
    """Create a test category for rules."""
    category = Category(name="Test Category")
    db_session.add(category)
    db_session.flush()

    # Add closure table entry
    closure = CategoryClosure(
        ancestor_id=category.id,
        descendant_id=category.id,
        depth=0,
    )
    db_session.add(closure)
    db_session.flush()

    return category


class TestClassificationRuleRepositoryCreate:
    """Tests for ClassificationRuleRepository.create()."""

    def test_create_simple_rule(
        self, db_session: Session, test_category: Category
    ) -> None:
        """Test creating a simple classification rule."""
        repo = ClassificationRuleRepository(db_session)

        rule = repo.create(
            name="Groceries",
            rule_expression='description =~ "(?i)tesco"',
            category_id=test_category.id,
        )
        db_session.flush()

        assert rule.id is not None
        assert rule.name == "Groceries"
        assert rule.rule_expression == 'description =~ "(?i)tesco"'
        assert rule.category_id == test_category.id
        assert rule.is_active is True

    def test_create_rule_with_priority(
        self, db_session: Session, test_category: Category
    ) -> None:
        """Test creating a rule with custom priority."""
        repo = ClassificationRuleRepository(db_session)

        rule = repo.create(
            name="High Priority",
            rule_expression='amount > 100',
            category_id=test_category.id,
            priority=5,
        )
        db_session.flush()

        assert rule.priority == 5

    def test_create_rule_requires_disambiguation(
        self, db_session: Session, test_category: Category
    ) -> None:
        """Test creating a rule that requires AI disambiguation."""
        repo = ClassificationRuleRepository(db_session)

        rule = repo.create(
            name="Amazon",
            rule_expression='description =~ "(?i)amazon"',
            category_id=test_category.id,
            requires_disambiguation=True,
        )
        db_session.flush()

        assert rule.requires_disambiguation is True


class TestClassificationRuleRepositoryGet:
    """Tests for ClassificationRuleRepository.get()."""

    def test_get_existing_rule(
        self, db_session: Session, test_category: Category
    ) -> None:
        """Test getting an existing rule by ID."""
        repo = ClassificationRuleRepository(db_session)
        created = repo.create(
            name="Test",
            rule_expression="amount < 0",
            category_id=test_category.id,
        )
        db_session.flush()

        rule = repo.get(created.id)

        assert rule.id == created.id
        assert rule.name == "Test"

    def test_get_nonexistent_rule(self, db_session: Session) -> None:
        """Test getting a non-existent rule raises error."""
        repo = ClassificationRuleRepository(db_session)

        with pytest.raises(ClassificationRuleNotFoundError):
            repo.get(9999)


class TestClassificationRuleRepositoryGetActiveByPriority:
    """Tests for ClassificationRuleRepository.get_active_by_priority()."""

    def test_get_active_rules_ordered(
        self, db_session: Session, test_category: Category
    ) -> None:
        """Test getting active rules in priority order."""
        repo = ClassificationRuleRepository(db_session)

        r1 = repo.create(
            name="Low",
            rule_expression="a",
            category_id=test_category.id,
            priority=10,
        )
        r2 = repo.create(
            name="High",
            rule_expression="b",
            category_id=test_category.id,
            priority=0,
        )
        r3 = repo.create(
            name="Mid",
            rule_expression="c",
            category_id=test_category.id,
            priority=5,
        )
        db_session.flush()

        rules = repo.get_active_by_priority()

        assert len(rules) == 3
        assert rules[0].id == r2.id  # priority 0
        assert rules[1].id == r3.id  # priority 5
        assert rules[2].id == r1.id  # priority 10

    def test_get_active_excludes_inactive(
        self, db_session: Session, test_category: Category
    ) -> None:
        """Test inactive rules are excluded."""
        repo = ClassificationRuleRepository(db_session)

        active = repo.create(
            name="Active",
            rule_expression="active",
            category_id=test_category.id,
        )
        inactive = repo.create(
            name="Inactive",
            rule_expression="inactive",
            category_id=test_category.id,
        )
        db_session.flush()

        repo.deactivate(inactive.id)
        db_session.flush()

        rules = repo.get_active_by_priority()

        assert len(rules) == 1
        assert rules[0].id == active.id


class TestClassificationRuleRepositoryGetByCategory:
    """Tests for ClassificationRuleRepository.get_by_category()."""

    def test_get_rules_for_category(
        self, db_session: Session, test_category: Category
    ) -> None:
        """Test getting rules for a specific category."""
        repo = ClassificationRuleRepository(db_session)

        # Create another category
        other_category = Category(name="Other")
        db_session.add(other_category)
        db_session.flush()

        other_closure = CategoryClosure(
            ancestor_id=other_category.id,
            descendant_id=other_category.id,
            depth=0,
        )
        db_session.add(other_closure)
        db_session.flush()

        rule1 = repo.create(
            name="Rule1",
            rule_expression="r1",
            category_id=test_category.id,
        )
        repo.create(
            name="Rule2",
            rule_expression="r2",
            category_id=other_category.id,
        )
        db_session.flush()

        rules = repo.get_by_category(test_category.id)

        assert len(rules) == 1
        assert rules[0].id == rule1.id


class TestClassificationRuleRepositoryUpdate:
    """Tests for ClassificationRuleRepository.update()."""

    def test_update_rule_expression(
        self, db_session: Session, test_category: Category
    ) -> None:
        """Test updating rule expression."""
        repo = ClassificationRuleRepository(db_session)
        rule = repo.create(
            name="Update Test",
            rule_expression="old",
            category_id=test_category.id,
        )
        db_session.flush()

        updated = repo.update(rule.id, rule_expression="new")

        assert updated.rule_expression == "new"

    def test_update_multiple_fields(
        self, db_session: Session, test_category: Category
    ) -> None:
        """Test updating multiple fields."""
        repo = ClassificationRuleRepository(db_session)
        rule = repo.create(
            name="Old Name",
            rule_expression="expr",
            category_id=test_category.id,
            priority=5,
        )
        db_session.flush()

        updated = repo.update(
            rule.id,
            name="New Name",
            priority=1,
            requires_disambiguation=True,
        )

        assert updated.name == "New Name"
        assert updated.priority == 1
        assert updated.requires_disambiguation is True


class TestClassificationRuleRepositoryActivateDeactivate:
    """Tests for activate/deactivate methods."""

    def test_deactivate_rule(
        self, db_session: Session, test_category: Category
    ) -> None:
        """Test deactivating a rule."""
        repo = ClassificationRuleRepository(db_session)
        rule = repo.create(
            name="Deactivate",
            rule_expression="d",
            category_id=test_category.id,
        )
        db_session.flush()

        assert rule.is_active is True

        repo.deactivate(rule.id)

        assert rule.is_active is False

    def test_activate_rule(
        self, db_session: Session, test_category: Category
    ) -> None:
        """Test reactivating a rule."""
        repo = ClassificationRuleRepository(db_session)
        rule = repo.create(
            name="Activate",
            rule_expression="a",
            category_id=test_category.id,
        )
        db_session.flush()

        repo.deactivate(rule.id)
        assert rule.is_active is False

        repo.activate(rule.id)
        assert rule.is_active is True


class TestClassificationRuleRepositoryDelete:
    """Tests for ClassificationRuleRepository.delete()."""

    def test_delete_rule(
        self, db_session: Session, test_category: Category
    ) -> None:
        """Test deleting a rule."""
        repo = ClassificationRuleRepository(db_session)
        rule = repo.create(
            name="Delete",
            rule_expression="del",
            category_id=test_category.id,
        )
        db_session.flush()
        rule_id = rule.id

        repo.delete(rule_id)
        db_session.flush()

        with pytest.raises(ClassificationRuleNotFoundError):
            repo.get(rule_id)

    def test_delete_nonexistent_raises_error(self, db_session: Session) -> None:
        """Test deleting non-existent rule raises error."""
        repo = ClassificationRuleRepository(db_session)

        with pytest.raises(ClassificationRuleNotFoundError):
            repo.delete(9999)
