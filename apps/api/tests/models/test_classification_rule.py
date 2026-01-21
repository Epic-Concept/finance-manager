"""Tests for ClassificationRule model."""

from finance_api.models.classification_rule import ClassificationRule


def test_classification_rule_creation() -> None:
    """Test ClassificationRule can be instantiated with required fields."""
    rule = ClassificationRule(
        name="Amazon UK",
        rule_expression='description =~ "(?i)amazon\\.co\\.uk"',
        category_id=1,
    )

    assert rule.name == "Amazon UK"
    assert rule.rule_expression == 'description =~ "(?i)amazon\\.co\\.uk"'
    assert rule.category_id == 1
    # Note: defaults are applied at database level, not Python level


def test_classification_rule_with_all_fields() -> None:
    """Test ClassificationRule with all optional fields."""
    rule = ClassificationRule(
        name="Groceries",
        rule_expression='description =~ "(?i)(tesco|sainsbury|asda)"',
        category_id=5,
        priority=10,
        requires_disambiguation=False,
        is_active=True,
    )

    assert rule.name == "Groceries"
    assert rule.category_id == 5
    assert rule.priority == 10
    assert rule.requires_disambiguation is False
    assert rule.is_active is True


def test_classification_rule_requires_disambiguation() -> None:
    """Test ClassificationRule that requires AI disambiguation."""
    rule = ClassificationRule(
        name="Online Shopping",
        rule_expression='description =~ "(?i)amazon"',
        category_id=2,
        requires_disambiguation=True,
    )

    assert rule.requires_disambiguation is True


def test_classification_rule_inactive() -> None:
    """Test ClassificationRule can be deactivated."""
    rule = ClassificationRule(
        name="Old Rule",
        rule_expression='description == "legacy"',
        category_id=1,
        is_active=False,
    )

    assert rule.is_active is False


def test_classification_rule_complex_expression() -> None:
    """Test ClassificationRule with complex expression."""
    rule = ClassificationRule(
        name="Joint Account Mortgage",
        rule_expression='account_name == "Joint Account" and description =~ "(?i)mortgage"',
        category_id=10,
        priority=5,
    )

    assert "account_name ==" in rule.rule_expression
    assert "and" in rule.rule_expression


def test_classification_rule_repr() -> None:
    """Test ClassificationRule string representation."""
    rule = ClassificationRule(
        id=1,
        name="Test Rule",
        rule_expression='amount < 0',
        category_id=1,
        priority=5,
    )

    assert repr(rule) == "<ClassificationRule(id=1, name='Test Rule', priority=5)>"


def test_classification_rule_table_name() -> None:
    """Test ClassificationRule table configuration."""
    assert ClassificationRule.__tablename__ == "classification_rules"
    assert ClassificationRule.__table_args__[1]["schema"] == "finance"
