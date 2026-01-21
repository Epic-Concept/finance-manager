"""End-to-end integration tests for the classification pipeline.

These tests verify the full classification flow with real services (not mocked)
using an in-memory SQLite database.
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from finance_api.models.category import Category, CategoryClosure
from finance_api.models.transaction import Transaction
from finance_api.models.transaction_category import TransactionCategory
from finance_api.repositories.category_evidence_repository import (
    CategoryEvidenceRepository,
)
from finance_api.repositories.classification_rule_repository import (
    ClassificationRuleRepository,
)
from finance_api.services.classification_orchestrator import (
    ClassificationOrchestrator,
)
from finance_api.services.rules_classification_service import (
    RulesClassificationService,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def setup_categories(db_session: Session) -> dict[str, Category]:
    """Create a realistic category hierarchy for testing."""
    categories = {}

    # Create parent categories
    for name in ["Food", "Shopping", "Utilities", "Transport", "Entertainment"]:
        cat = Category(name=name, commitment_level=2)
        db_session.add(cat)
        db_session.flush()
        # Add closure entry
        closure = CategoryClosure(ancestor_id=cat.id, descendant_id=cat.id, depth=0)
        db_session.add(closure)
        categories[name] = cat

    # Create child categories under Food
    food_children = ["Groceries", "Restaurants", "Coffee Shops", "Takeaway"]
    for name in food_children:
        cat = Category(name=name, parent_id=categories["Food"].id, commitment_level=2)
        db_session.add(cat)
        db_session.flush()
        # Self-reference closure
        closure = CategoryClosure(ancestor_id=cat.id, descendant_id=cat.id, depth=0)
        db_session.add(closure)
        # Parent closure
        closure2 = CategoryClosure(
            ancestor_id=categories["Food"].id, descendant_id=cat.id, depth=1
        )
        db_session.add(closure2)
        categories[name] = cat

    # Create child categories under Shopping
    shopping_children = ["Electronics", "Clothing", "Home & Garden", "General"]
    for name in shopping_children:
        cat = Category(
            name=name, parent_id=categories["Shopping"].id, commitment_level=3
        )
        db_session.add(cat)
        db_session.flush()
        closure = CategoryClosure(ancestor_id=cat.id, descendant_id=cat.id, depth=0)
        db_session.add(closure)
        closure2 = CategoryClosure(
            ancestor_id=categories["Shopping"].id, descendant_id=cat.id, depth=1
        )
        db_session.add(closure2)
        categories[name] = cat

    db_session.flush()
    return categories


@pytest.fixture
def setup_rules(
    db_session: Session,
    setup_categories: dict[str, Category],
) -> list:
    """Create realistic classification rules."""
    rule_repo = ClassificationRuleRepository(db_session)
    rules = []

    # Groceries rules (high priority)
    rules.append(
        rule_repo.create(
            name="Tesco",
            rule_expression='description =~ "(?i)tesco"',
            category_id=setup_categories["Groceries"].id,
            priority=100,
        )
    )
    rules.append(
        rule_repo.create(
            name="Sainsburys",
            rule_expression='description =~ "(?i)sainsbury"',
            category_id=setup_categories["Groceries"].id,
            priority=100,
        )
    )
    rules.append(
        rule_repo.create(
            name="Asda",
            rule_expression='description =~ "(?i)asda"',
            category_id=setup_categories["Groceries"].id,
            priority=100,
        )
    )

    # Coffee shops
    rules.append(
        rule_repo.create(
            name="Starbucks",
            rule_expression='description =~ "(?i)starbucks"',
            category_id=setup_categories["Coffee Shops"].id,
            priority=90,
        )
    )
    rules.append(
        rule_repo.create(
            name="Costa Coffee",
            rule_expression='description =~ "(?i)costa"',
            category_id=setup_categories["Coffee Shops"].id,
            priority=90,
        )
    )

    # Restaurants
    rules.append(
        rule_repo.create(
            name="McDonalds",
            rule_expression='description =~ "(?i)mcdonald"',
            category_id=setup_categories["Restaurants"].id,
            priority=85,
        )
    )

    # Utilities
    rules.append(
        rule_repo.create(
            name="British Gas",
            rule_expression='description =~ "(?i)british gas"',
            category_id=setup_categories["Utilities"].id,
            priority=100,
        )
    )

    # Shopping - needs disambiguation (Amazon, eBay)
    rules.append(
        rule_repo.create(
            name="Amazon (needs disambiguation)",
            rule_expression='description =~ "(?i)amazon"',
            category_id=setup_categories["General"].id,  # Default to General
            priority=50,
            requires_disambiguation=True,
        )
    )

    db_session.flush()
    return rules


@pytest.fixture
def create_transactions(db_session: Session):
    """Factory to create test transactions."""

    def _create(
        description: str,
        amount: Decimal,
        transaction_date: date | None = None,
    ) -> Transaction:
        txn = Transaction(
            transaction_date=transaction_date or date(2026, 1, 15),
            description=description,
            amount=amount,
            currency="GBP",
        )
        db_session.add(txn)
        db_session.flush()
        return txn

    return _create


# ============================================================================
# End-to-End Integration Tests
# ============================================================================


class TestClassificationPipelineIntegration:
    """Integration tests for the full classification pipeline."""

    def test_single_transaction_rule_match(
        self,
        db_session: Session,
        setup_categories: dict[str, Category],
        setup_rules: list,
        create_transactions,
    ) -> None:
        """Test classifying a single transaction that matches a rule."""
        # Create services
        rule_repo = ClassificationRuleRepository(db_session)
        evidence_repo = CategoryEvidenceRepository(db_session)
        rules_service = RulesClassificationService(rule_repo)
        rules_service.reload_rules()

        assigned_categories: dict[int, int] = {}

        def category_updater(txn_id: int, cat_id: int) -> TransactionCategory:
            assigned_categories[txn_id] = cat_id
            link = TransactionCategory(transaction_id=txn_id, category_id=cat_id)
            db_session.add(link)
            return link

        orchestrator = ClassificationOrchestrator(
            rules_service=rules_service,
            disambiguation_service=None,
            evidence_repository=evidence_repo,
            transaction_category_updater=category_updater,
        )

        # Create test transaction
        txn = create_transactions("TESCO STORES 1234", Decimal("-45.67"))

        # Classify
        result = orchestrator.classify(txn)
        db_session.flush()

        # Verify result
        assert result.classified is True
        assert result.method == "rule"
        assert result.rule_name == "Tesco"
        assert result.category_id == setup_categories["Groceries"].id
        assert result.confidence == Decimal("1.0")

        # Verify evidence was created
        evidence = evidence_repo.get_by_transaction(txn.id)
        assert len(evidence) == 1
        assert evidence[0].evidence_type == "rule"
        assert "Tesco" in evidence[0].evidence_summary

    def test_batch_classification_mixed_results(
        self,
        db_session: Session,
        setup_categories: dict[str, Category],
        setup_rules: list,
        create_transactions,
    ) -> None:
        """Test batch classification with mixed results."""
        # Create services
        rule_repo = ClassificationRuleRepository(db_session)
        evidence_repo = CategoryEvidenceRepository(db_session)
        rules_service = RulesClassificationService(rule_repo)
        rules_service.reload_rules()

        assigned_categories: dict[int, int] = {}

        def category_updater(txn_id: int, cat_id: int) -> TransactionCategory:
            assigned_categories[txn_id] = cat_id
            return TransactionCategory(transaction_id=txn_id, category_id=cat_id)

        orchestrator = ClassificationOrchestrator(
            rules_service=rules_service,
            disambiguation_service=None,
            evidence_repository=evidence_repo,
            transaction_category_updater=category_updater,
        )

        # Create test transactions
        transactions = [
            create_transactions("TESCO STORES 1234", Decimal("-45.67")),
            create_transactions("STARBUCKS COFFEE", Decimal("-4.50")),
            create_transactions("BRITISH GAS DD", Decimal("-120.00")),
            create_transactions("UNKNOWN MERCHANT ABC", Decimal("-25.00")),
            create_transactions("MCDONALDS LONDON", Decimal("-8.99")),
        ]

        # Classify batch
        results = orchestrator.classify_batch(transactions)

        # Verify results
        assert len(results) == 5

        # Tesco -> Groceries
        assert results[transactions[0].id].classified is True
        assert (
            results[transactions[0].id].category_id == setup_categories["Groceries"].id
        )

        # Starbucks -> Coffee Shops
        assert results[transactions[1].id].classified is True
        assert (
            results[transactions[1].id].category_id
            == setup_categories["Coffee Shops"].id
        )

        # British Gas -> Utilities
        assert results[transactions[2].id].classified is True
        assert (
            results[transactions[2].id].category_id == setup_categories["Utilities"].id
        )

        # Unknown -> not classified
        assert results[transactions[3].id].classified is False
        assert results[transactions[3].id].method == "unclassified"

        # McDonalds -> Restaurants
        assert results[transactions[4].id].classified is True
        assert (
            results[transactions[4].id].category_id
            == setup_categories["Restaurants"].id
        )

    def test_classification_statistics(
        self,
        db_session: Session,
        setup_categories: dict[str, Category],
        setup_rules: list,
        create_transactions,
    ) -> None:
        """Test classification statistics gathering."""
        # Create services
        rule_repo = ClassificationRuleRepository(db_session)
        evidence_repo = CategoryEvidenceRepository(db_session)
        rules_service = RulesClassificationService(rule_repo)
        rules_service.reload_rules()

        orchestrator = ClassificationOrchestrator(
            rules_service=rules_service,
            disambiguation_service=None,
            evidence_repository=evidence_repo,
        )

        # Create transactions with different outcomes
        transactions = [
            create_transactions("TESCO STORES", Decimal("-50.00")),
            create_transactions("SAINSBURYS LOCAL", Decimal("-30.00")),
            create_transactions("STARBUCKS", Decimal("-5.00")),
            create_transactions("RANDOM SHOP 123", Decimal("-15.00")),
            create_transactions("UNKNOWN VENDOR XYZ", Decimal("-20.00")),
        ]

        # Classify
        results = orchestrator.classify_batch(transactions)
        stats = orchestrator.get_classification_statistics(results)

        # Verify statistics
        assert stats["total"] == 5
        assert stats["classified"] == 3  # Tesco, Sainsburys, Starbucks
        assert stats["unclassified"] == 2  # Random, Unknown
        assert stats["by_rule"] == 3
        assert stats["by_ai"] == 0

    def test_idempotency_skip_already_classified(
        self,
        db_session: Session,
        setup_categories: dict[str, Category],
        setup_rules: list,
        create_transactions,
    ) -> None:
        """Test that already classified transactions are skipped."""
        # Create services
        rule_repo = ClassificationRuleRepository(db_session)
        evidence_repo = CategoryEvidenceRepository(db_session)
        rules_service = RulesClassificationService(rule_repo)
        rules_service.reload_rules()

        # Create transaction and pre-classify it
        txn = create_transactions("TESCO STORES", Decimal("-50.00"))
        pre_assigned = TransactionCategory(
            transaction_id=txn.id,
            category_id=setup_categories["Electronics"].id,  # "Wrong" category
        )
        db_session.add(pre_assigned)
        db_session.flush()
        db_session.refresh(txn)

        orchestrator = ClassificationOrchestrator(
            rules_service=rules_service,
            disambiguation_service=None,
            evidence_repository=evidence_repo,
        )

        # Classify without force
        result = orchestrator.classify(txn, force=False)

        # Should return existing category, not reclassify
        assert result.method == "existing"
        assert result.category_id == setup_categories["Electronics"].id

    def test_force_reclassification(
        self,
        db_session: Session,
        setup_categories: dict[str, Category],
        setup_rules: list,
        create_transactions,
    ) -> None:
        """Test force reclassification overrides existing category."""
        # Create services
        rule_repo = ClassificationRuleRepository(db_session)
        evidence_repo = CategoryEvidenceRepository(db_session)
        rules_service = RulesClassificationService(rule_repo)
        rules_service.reload_rules()

        assigned_categories: dict[int, int] = {}

        def category_updater(txn_id: int, cat_id: int) -> TransactionCategory:
            assigned_categories[txn_id] = cat_id
            return TransactionCategory(transaction_id=txn_id, category_id=cat_id)

        # Create transaction and pre-classify it with wrong category
        txn = create_transactions("TESCO STORES", Decimal("-50.00"))
        pre_assigned = TransactionCategory(
            transaction_id=txn.id,
            category_id=setup_categories["Electronics"].id,  # Wrong category
        )
        db_session.add(pre_assigned)
        db_session.flush()
        db_session.refresh(txn)

        orchestrator = ClassificationOrchestrator(
            rules_service=rules_service,
            disambiguation_service=None,
            evidence_repository=evidence_repo,
            transaction_category_updater=category_updater,
        )

        # Classify with force=True
        result = orchestrator.classify(txn, force=True)

        # Should reclassify to correct category
        assert result.method == "rule"
        assert result.category_id == setup_categories["Groceries"].id
        assert assigned_categories[txn.id] == setup_categories["Groceries"].id

    def test_rule_priority_ordering(
        self,
        db_session: Session,
        setup_categories: dict[str, Category],
        setup_rules: list,  # Use pre-configured rules
        create_transactions,
    ) -> None:
        """Test that lower priority value rules are evaluated first."""
        rule_repo = ClassificationRuleRepository(db_session)
        evidence_repo = CategoryEvidenceRepository(db_session)
        rules_service = RulesClassificationService(rule_repo)
        rules_service.reload_rules()

        orchestrator = ClassificationOrchestrator(
            rules_service=rules_service,
            disambiguation_service=None,
            evidence_repository=evidence_repo,
        )

        # Test 1: Starbucks matches "Starbucks" rule at priority 90
        txn1 = create_transactions("STARBUCKS COFFEE", Decimal("-4.00"))
        result1 = orchestrator.classify(txn1)
        assert result1.classified is True
        assert result1.rule_name == "Starbucks"

        # Test 2: Costa matches "Costa Coffee" rule at priority 90
        txn2 = create_transactions("COSTA COFFEE SHOP", Decimal("-3.50"))
        result2 = orchestrator.classify(txn2)
        assert result2.classified is True
        assert result2.rule_name == "Costa Coffee"

        # Test 3: Tesco has higher priority (100) - should match
        txn3 = create_transactions("TESCO METRO", Decimal("-25.00"))
        result3 = orchestrator.classify(txn3)
        assert result3.classified is True
        assert result3.rule_name == "Tesco"
        assert result3.category_id == setup_categories["Groceries"].id

    def test_disambiguation_flag_without_service(
        self,
        db_session: Session,
        setup_categories: dict[str, Category],
        setup_rules: list,  # Includes Amazon rule with requires_disambiguation=True
        create_transactions,
    ) -> None:
        """Test transaction requiring disambiguation when no service available."""
        rule_repo = ClassificationRuleRepository(db_session)
        evidence_repo = CategoryEvidenceRepository(db_session)
        rules_service = RulesClassificationService(rule_repo)
        rules_service.reload_rules()

        assigned_categories: dict[int, int] = {}

        def category_updater(txn_id: int, cat_id: int) -> TransactionCategory:
            assigned_categories[txn_id] = cat_id
            return TransactionCategory(transaction_id=txn_id, category_id=cat_id)

        orchestrator = ClassificationOrchestrator(
            rules_service=rules_service,
            disambiguation_service=None,  # No disambiguation service
            evidence_repository=evidence_repo,
            transaction_category_updater=category_updater,
        )

        # Amazon transaction (requires disambiguation)
        txn = create_transactions("AMAZON.CO.UK ORDER", Decimal("-99.99"))

        result = orchestrator.classify(txn)

        # Should fall back to rule category with lower confidence
        assert result.classified is True
        assert result.method == "rule_with_disambiguation"
        assert result.needs_disambiguation is True
        assert result.confidence == Decimal("0.7")
        # Uses the General category from the Amazon rule
        assert result.category_id == setup_categories["General"].id


class TestRulesServiceIntegration:
    """Integration tests for RulesClassificationService."""

    def test_rule_reload_picks_up_new_rules(
        self,
        db_session: Session,
        setup_categories: dict[str, Category],
    ) -> None:
        """Test that reload_rules picks up newly created rules."""
        rule_repo = ClassificationRuleRepository(db_session)
        rules_service = RulesClassificationService(rule_repo)

        # Initially no rules
        rules_service.reload_rules()

        txn = Transaction(
            transaction_date=date(2026, 1, 15),
            description="TESCO STORES",
            amount=Decimal("-50.00"),
        )
        db_session.add(txn)
        db_session.flush()

        # Should not match any rule
        match = rules_service.classify(txn)
        assert match is None

        # Add a rule
        rule_repo.create(
            name="Tesco",
            rule_expression='description =~ "(?i)tesco"',
            category_id=setup_categories["Groceries"].id,
        )
        db_session.flush()

        # Reload rules
        rules_service.reload_rules()

        # Now should match
        match = rules_service.classify(txn)
        assert match is not None
        assert match.rule.name == "Tesco"
        assert match.category_id == setup_categories["Groceries"].id

    def test_deactivated_rules_not_loaded(
        self,
        db_session: Session,
        setup_categories: dict[str, Category],
    ) -> None:
        """Test that deactivated rules are not loaded."""
        rule_repo = ClassificationRuleRepository(db_session)
        rules_service = RulesClassificationService(rule_repo)

        # Create an active rule
        rule = rule_repo.create(
            name="Tesco",
            rule_expression='description =~ "(?i)tesco"',
            category_id=setup_categories["Groceries"].id,
        )
        db_session.flush()

        rules_service.reload_rules()

        txn = Transaction(
            transaction_date=date(2026, 1, 15),
            description="TESCO STORES",
            amount=Decimal("-50.00"),
        )
        db_session.add(txn)
        db_session.flush()

        # Should match
        assert rules_service.classify(txn) is not None

        # Deactivate the rule using the repository method
        rule_repo.deactivate(rule.id)
        db_session.flush()
        rules_service.reload_rules()

        # Should not match now
        assert rules_service.classify(txn) is None
