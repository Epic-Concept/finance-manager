"""Tests for RulesClassificationService."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from finance_api.models.category import Category, CategoryClosure
from finance_api.models.transaction import Transaction
from finance_api.repositories.classification_rule_repository import (
    ClassificationRuleRepository,
)
from finance_api.services.rules_classification_service import (
    RulesClassificationService,
)


@pytest.fixture
def groceries_category(db_session: Session) -> Category:
    """Create a groceries category."""
    category = Category(name="Groceries")
    db_session.add(category)
    db_session.flush()

    closure = CategoryClosure(
        ancestor_id=category.id,
        descendant_id=category.id,
        depth=0,
    )
    db_session.add(closure)
    db_session.flush()
    return category


@pytest.fixture
def online_shopping_category(db_session: Session) -> Category:
    """Create an online shopping category."""
    category = Category(name="Online Shopping")
    db_session.add(category)
    db_session.flush()

    closure = CategoryClosure(
        ancestor_id=category.id,
        descendant_id=category.id,
        depth=0,
    )
    db_session.add(closure)
    db_session.flush()
    return category


@pytest.fixture
def mortgage_category(db_session: Session) -> Category:
    """Create a mortgage category."""
    category = Category(name="Mortgage")
    db_session.add(category)
    db_session.flush()

    closure = CategoryClosure(
        ancestor_id=category.id,
        descendant_id=category.id,
        depth=0,
    )
    db_session.add(closure)
    db_session.flush()
    return category


@pytest.fixture
def rule_repo(db_session: Session) -> ClassificationRuleRepository:
    """Create a ClassificationRuleRepository instance."""
    return ClassificationRuleRepository(db_session)


@pytest.fixture
def service(rule_repo: ClassificationRuleRepository) -> RulesClassificationService:
    """Create a RulesClassificationService instance."""
    return RulesClassificationService(rule_repo)


class TestRulesClassificationServiceBasic:
    """Basic tests for RulesClassificationService."""

    def test_no_rules_returns_none(
        self, service: RulesClassificationService, db_session: Session
    ) -> None:
        """Test that classification returns None when no rules exist."""
        transaction = Transaction(
            transaction_date=date(2026, 1, 15),
            description="TESCO STORES",
            amount=Decimal("-45.00"),
            currency="GBP",
        )
        db_session.add(transaction)
        db_session.flush()

        result = service.classify(transaction)

        assert result is None

    def test_simple_description_match(
        self,
        service: RulesClassificationService,
        rule_repo: ClassificationRuleRepository,
        groceries_category: Category,
        db_session: Session,
    ) -> None:
        """Test matching a transaction by description regex."""
        rule_repo.create(
            name="Tesco Groceries",
            rule_expression='description =~ "(?i)tesco"',
            category_id=groceries_category.id,
            priority=0,
        )
        db_session.flush()
        service.reload_rules()

        transaction = Transaction(
            transaction_date=date(2026, 1, 15),
            description="TESCO STORES 1234",
            amount=Decimal("-45.00"),
            currency="GBP",
        )
        db_session.add(transaction)
        db_session.flush()

        result = service.classify(transaction)

        assert result is not None
        assert result.category_id == groceries_category.id
        assert result.requires_disambiguation is False

    def test_case_insensitive_match(
        self,
        service: RulesClassificationService,
        rule_repo: ClassificationRuleRepository,
        groceries_category: Category,
        db_session: Session,
    ) -> None:
        """Test case-insensitive regex matching."""
        rule_repo.create(
            name="Tesco",
            rule_expression='description =~ "(?i)tesco"',
            category_id=groceries_category.id,
        )
        db_session.flush()
        service.reload_rules()

        transaction = Transaction(
            transaction_date=date(2026, 1, 15),
            description="tesco express",
            amount=Decimal("-10.00"),
            currency="GBP",
        )
        db_session.add(transaction)
        db_session.flush()

        result = service.classify(transaction)

        assert result is not None
        assert result.category_id == groceries_category.id


class TestRulesClassificationServicePriority:
    """Tests for rule priority ordering."""

    def test_priority_first_match_wins(
        self,
        service: RulesClassificationService,
        rule_repo: ClassificationRuleRepository,
        groceries_category: Category,
        online_shopping_category: Category,
        db_session: Session,
    ) -> None:
        """Test that higher priority rule (lower number) wins."""
        # Lower priority number = higher priority
        rule_repo.create(
            name="All Purchases",
            rule_expression="amount < 0",
            category_id=online_shopping_category.id,
            priority=10,  # Lower priority
        )
        rule_repo.create(
            name="Tesco",
            rule_expression='description =~ "(?i)tesco"',
            category_id=groceries_category.id,
            priority=0,  # Higher priority
        )
        db_session.flush()
        service.reload_rules()

        transaction = Transaction(
            transaction_date=date(2026, 1, 15),
            description="TESCO STORES",
            amount=Decimal("-45.00"),
            currency="GBP",
        )
        db_session.add(transaction)
        db_session.flush()

        result = service.classify(transaction)

        # Should match Tesco rule (priority 0) not All Purchases (priority 10)
        assert result is not None
        assert result.category_id == groceries_category.id

    def test_inactive_rules_skipped(
        self,
        service: RulesClassificationService,
        rule_repo: ClassificationRuleRepository,
        groceries_category: Category,
        online_shopping_category: Category,
        db_session: Session,
    ) -> None:
        """Test that inactive rules are not evaluated."""
        rule = rule_repo.create(
            name="Tesco",
            rule_expression='description =~ "(?i)tesco"',
            category_id=groceries_category.id,
            priority=0,
        )
        rule_repo.create(
            name="Fallback",
            rule_expression="amount < 0",
            category_id=online_shopping_category.id,
            priority=10,
        )
        db_session.flush()

        # Deactivate the high-priority rule
        rule_repo.deactivate(rule.id)
        db_session.flush()
        service.reload_rules()

        transaction = Transaction(
            transaction_date=date(2026, 1, 15),
            description="TESCO STORES",
            amount=Decimal("-45.00"),
            currency="GBP",
        )
        db_session.add(transaction)
        db_session.flush()

        result = service.classify(transaction)

        # Should match fallback rule since Tesco is inactive
        assert result is not None
        assert result.category_id == online_shopping_category.id


class TestRulesClassificationServiceComplexRules:
    """Tests for complex rule expressions."""

    def test_amount_comparison(
        self,
        service: RulesClassificationService,
        rule_repo: ClassificationRuleRepository,
        groceries_category: Category,
        db_session: Session,
    ) -> None:
        """Test rules with amount comparisons."""
        rule_repo.create(
            name="Large Purchases",
            rule_expression="amount < -100",
            category_id=groceries_category.id,
        )
        db_session.flush()
        service.reload_rules()

        small_txn = Transaction(
            transaction_date=date(2026, 1, 15),
            description="Small purchase",
            amount=Decimal("-50.00"),
            currency="GBP",
        )
        large_txn = Transaction(
            transaction_date=date(2026, 1, 15),
            description="Large purchase",
            amount=Decimal("-150.00"),
            currency="GBP",
        )
        db_session.add_all([small_txn, large_txn])
        db_session.flush()

        small_result = service.classify(small_txn)
        large_result = service.classify(large_txn)

        assert small_result is None
        assert large_result is not None
        assert large_result.category_id == groceries_category.id

    def test_combined_conditions(
        self,
        service: RulesClassificationService,
        rule_repo: ClassificationRuleRepository,
        mortgage_category: Category,
        db_session: Session,
    ) -> None:
        """Test rules with AND conditions."""
        rule_repo.create(
            name="Joint Account Mortgage",
            rule_expression='account_name == "Joint Account" and description =~ "(?i)mortgage"',
            category_id=mortgage_category.id,
        )
        db_session.flush()
        service.reload_rules()

        matching_txn = Transaction(
            transaction_date=date(2026, 1, 15),
            description="MORTGAGE PAYMENT",
            amount=Decimal("-1500.00"),
            currency="GBP",
            account_name="Joint Account",
        )
        non_matching_txn = Transaction(
            transaction_date=date(2026, 1, 15),
            description="MORTGAGE PAYMENT",
            amount=Decimal("-1500.00"),
            currency="GBP",
            account_name="Personal Account",
        )
        db_session.add_all([matching_txn, non_matching_txn])
        db_session.flush()

        matching_result = service.classify(matching_txn)
        non_matching_result = service.classify(non_matching_txn)

        assert matching_result is not None
        assert matching_result.category_id == mortgage_category.id
        assert non_matching_result is None

    def test_or_conditions_in_regex(
        self,
        service: RulesClassificationService,
        rule_repo: ClassificationRuleRepository,
        groceries_category: Category,
        db_session: Session,
    ) -> None:
        """Test rules with OR patterns in regex."""
        rule_repo.create(
            name="UK Groceries",
            rule_expression='description =~ "(?i)(tesco|sainsbury|asda|lidl|aldi)"',
            category_id=groceries_category.id,
        )
        db_session.flush()
        service.reload_rules()

        tesco_txn = Transaction(
            transaction_date=date(2026, 1, 15),
            description="TESCO STORES",
            amount=Decimal("-45.00"),
            currency="GBP",
        )
        sainsbury_txn = Transaction(
            transaction_date=date(2026, 1, 15),
            description="Sainsbury's Local",
            amount=Decimal("-30.00"),
            currency="GBP",
        )
        amazon_txn = Transaction(
            transaction_date=date(2026, 1, 15),
            description="AMAZON.CO.UK",
            amount=Decimal("-99.00"),
            currency="GBP",
        )
        db_session.add_all([tesco_txn, sainsbury_txn, amazon_txn])
        db_session.flush()

        tesco_result = service.classify(tesco_txn)
        sainsbury_result = service.classify(sainsbury_txn)
        amazon_result = service.classify(amazon_txn)

        assert tesco_result is not None
        assert sainsbury_result is not None
        assert amazon_result is None


class TestRulesClassificationServiceDisambiguation:
    """Tests for disambiguation flag handling."""

    def test_requires_disambiguation_flag(
        self,
        service: RulesClassificationService,
        rule_repo: ClassificationRuleRepository,
        online_shopping_category: Category,
        db_session: Session,
    ) -> None:
        """Test that requires_disambiguation is propagated."""
        rule_repo.create(
            name="Amazon",
            rule_expression='description =~ "(?i)amazon"',
            category_id=online_shopping_category.id,
            requires_disambiguation=True,
        )
        db_session.flush()
        service.reload_rules()

        transaction = Transaction(
            transaction_date=date(2026, 1, 15),
            description="AMAZON.CO.UK",
            amount=Decimal("-59.99"),
            currency="GBP",
        )
        db_session.add(transaction)
        db_session.flush()

        result = service.classify(transaction)

        assert result is not None
        assert result.category_id == online_shopping_category.id
        assert result.requires_disambiguation is True


class TestRulesClassificationServiceBatch:
    """Tests for batch classification."""

    def test_classify_batch(
        self,
        service: RulesClassificationService,
        rule_repo: ClassificationRuleRepository,
        groceries_category: Category,
        online_shopping_category: Category,
        db_session: Session,
    ) -> None:
        """Test classifying multiple transactions."""
        rule_repo.create(
            name="Groceries",
            rule_expression='description =~ "(?i)tesco"',
            category_id=groceries_category.id,
        )
        rule_repo.create(
            name="Online",
            rule_expression='description =~ "(?i)amazon"',
            category_id=online_shopping_category.id,
        )
        db_session.flush()
        service.reload_rules()

        txn1 = Transaction(
            transaction_date=date(2026, 1, 15),
            description="TESCO STORES",
            amount=Decimal("-45.00"),
            currency="GBP",
        )
        txn2 = Transaction(
            transaction_date=date(2026, 1, 16),
            description="AMAZON.CO.UK",
            amount=Decimal("-99.00"),
            currency="GBP",
        )
        txn3 = Transaction(
            transaction_date=date(2026, 1, 17),
            description="UNKNOWN MERCHANT",
            amount=Decimal("-50.00"),
            currency="GBP",
        )
        db_session.add_all([txn1, txn2, txn3])
        db_session.flush()

        results = service.classify_batch([txn1, txn2, txn3])

        assert len(results) == 3
        assert results[txn1.id] is not None
        assert results[txn1.id].category_id == groceries_category.id
        assert results[txn2.id] is not None
        assert results[txn2.id].category_id == online_shopping_category.id
        assert results[txn3.id] is None


class TestRulesClassificationServiceTestRule:
    """Tests for rule expression testing."""

    def test_valid_expression(
        self, service: RulesClassificationService
    ) -> None:
        """Test validating a correct expression."""
        is_valid, error = service.test_rule_expression('description =~ "(?i)test"')

        assert is_valid is True
        assert error is None

    def test_invalid_expression(
        self, service: RulesClassificationService
    ) -> None:
        """Test validating an invalid expression."""
        is_valid, error = service.test_rule_expression("invalid syntax here!!!")

        assert is_valid is False
        assert error is not None

    def test_expression_against_data(
        self, service: RulesClassificationService
    ) -> None:
        """Test evaluating expression against test data."""
        test_data = {
            "description": "TESCO STORES",
            "amount": -45.0,
            "currency": "GBP",
            "account_name": "",
            "external_id": "",
            "notes": "",
            "transaction_date": "2026-01-15",
        }

        matches, error = service.test_rule_expression(
            'description =~ "(?i)tesco"', test_data
        )
        not_matches, _ = service.test_rule_expression(
            'description =~ "(?i)amazon"', test_data
        )

        assert matches is True
        assert error is None
        assert not_matches is False


class TestRulesClassificationServiceGetMatchingRules:
    """Tests for get_matching_rules debug method."""

    def test_get_all_matching_rules(
        self,
        service: RulesClassificationService,
        rule_repo: ClassificationRuleRepository,
        groceries_category: Category,
        online_shopping_category: Category,
        db_session: Session,
    ) -> None:
        """Test getting all matching rules for a transaction."""
        rule_repo.create(
            name="Tesco",
            rule_expression='description =~ "(?i)tesco"',
            category_id=groceries_category.id,
            priority=0,
        )
        rule_repo.create(
            name="All Expenses",
            rule_expression="amount < 0",
            category_id=online_shopping_category.id,
            priority=10,
        )
        rule_repo.create(
            name="Amazon",
            rule_expression='description =~ "(?i)amazon"',
            category_id=online_shopping_category.id,
            priority=5,
        )
        db_session.flush()
        service.reload_rules()

        transaction = Transaction(
            transaction_date=date(2026, 1, 15),
            description="TESCO STORES",
            amount=Decimal("-45.00"),
            currency="GBP",
        )
        db_session.add(transaction)
        db_session.flush()

        matching_rules = service.get_matching_rules(transaction)

        # Should return all rules with their match status
        assert len(matching_rules) == 3

        # Find results by rule name
        results_by_name = {rule.name: matched for rule, matched in matching_rules}
        assert results_by_name["Tesco"] is True
        assert results_by_name["All Expenses"] is True  # amount < 0
        assert results_by_name["Amazon"] is False


class TestRulesClassificationServiceReload:
    """Tests for rule reloading."""

    def test_reload_rules(
        self,
        service: RulesClassificationService,
        rule_repo: ClassificationRuleRepository,
        groceries_category: Category,
        online_shopping_category: Category,
        db_session: Session,
    ) -> None:
        """Test that reload_rules picks up new rules."""
        # Create initial rule
        rule_repo.create(
            name="Tesco",
            rule_expression='description =~ "(?i)tesco"',
            category_id=groceries_category.id,
        )
        db_session.flush()
        service.reload_rules()

        transaction = Transaction(
            transaction_date=date(2026, 1, 15),
            description="AMAZON.CO.UK",
            amount=Decimal("-99.00"),
            currency="GBP",
        )
        db_session.add(transaction)
        db_session.flush()

        # Should not match initially
        result1 = service.classify(transaction)
        assert result1 is None

        # Add Amazon rule
        rule_repo.create(
            name="Amazon",
            rule_expression='description =~ "(?i)amazon"',
            category_id=online_shopping_category.id,
        )
        db_session.flush()

        # Still shouldn't match (cache not refreshed)
        result2 = service.classify(transaction)
        assert result2 is None

        # After reload, should match
        service.reload_rules()
        result3 = service.classify(transaction)
        assert result3 is not None
        assert result3.category_id == online_shopping_category.id

    def test_reload_returns_count(
        self,
        service: RulesClassificationService,
        rule_repo: ClassificationRuleRepository,
        groceries_category: Category,
        db_session: Session,
    ) -> None:
        """Test that reload_rules returns the count of compiled rules."""
        rule_repo.create(
            name="Rule 1",
            rule_expression='description =~ "test1"',
            category_id=groceries_category.id,
        )
        rule_repo.create(
            name="Rule 2",
            rule_expression='description =~ "test2"',
            category_id=groceries_category.id,
        )
        rule_repo.create(
            name="Rule 3",
            rule_expression='description =~ "test3"',
            category_id=groceries_category.id,
        )
        db_session.flush()

        count = service.reload_rules()

        assert count == 3
