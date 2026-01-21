"""Tests for ClassificationOrchestrator."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

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
from finance_api.services.ai_disambiguation_service import (
    DisambiguationResult,
)
from finance_api.services.classification_orchestrator import (
    ClassificationOrchestrator,
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
        ancestor_id=category.id, descendant_id=category.id, depth=0
    )
    db_session.add(closure)
    db_session.flush()
    return category


@pytest.fixture
def electronics_category(db_session: Session) -> Category:
    """Create an electronics category."""
    category = Category(name="Electronics")
    db_session.add(category)
    db_session.flush()
    closure = CategoryClosure(
        ancestor_id=category.id, descendant_id=category.id, depth=0
    )
    db_session.add(closure)
    db_session.flush()
    return category


@pytest.fixture
def rule_repo(db_session: Session) -> ClassificationRuleRepository:
    """Create a ClassificationRuleRepository."""
    return ClassificationRuleRepository(db_session)


@pytest.fixture
def evidence_repo(db_session: Session) -> CategoryEvidenceRepository:
    """Create a CategoryEvidenceRepository."""
    return CategoryEvidenceRepository(db_session)


@pytest.fixture
def rules_service(rule_repo: ClassificationRuleRepository) -> RulesClassificationService:
    """Create a RulesClassificationService."""
    return RulesClassificationService(rule_repo)


@pytest.fixture
def tesco_transaction(db_session: Session) -> Transaction:
    """Create a Tesco transaction."""
    txn = Transaction(
        transaction_date=date(2026, 1, 15),
        description="TESCO STORES 1234",
        amount=Decimal("-45.00"),
        currency="GBP",
    )
    db_session.add(txn)
    db_session.flush()
    return txn


@pytest.fixture
def amazon_transaction(db_session: Session) -> Transaction:
    """Create an Amazon transaction."""
    txn = Transaction(
        transaction_date=date(2026, 1, 16),
        description="AMAZON.CO.UK ORDER",
        amount=Decimal("-99.99"),
        currency="GBP",
    )
    db_session.add(txn)
    db_session.flush()
    return txn


@pytest.fixture
def unknown_transaction(db_session: Session) -> Transaction:
    """Create an unknown merchant transaction."""
    txn = Transaction(
        transaction_date=date(2026, 1, 17),
        description="RANDOM STORE XYZ",
        amount=Decimal("-25.00"),
        currency="GBP",
    )
    db_session.add(txn)
    db_session.flush()
    return txn


class TestClassificationOrchestratorRulesOnly:
    """Tests for orchestrator with rules-only classification."""

    def test_classify_with_matching_rule(
        self,
        db_session: Session,
        rules_service: RulesClassificationService,
        rule_repo: ClassificationRuleRepository,
        evidence_repo: CategoryEvidenceRepository,
        groceries_category: Category,
        tesco_transaction: Transaction,
    ) -> None:
        """Test classification when a rule matches."""
        # Setup rule
        rule_repo.create(
            name="Tesco Groceries",
            rule_expression='description =~ "(?i)tesco"',
            category_id=groceries_category.id,
        )
        db_session.flush()
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

        result = orchestrator.classify(tesco_transaction)

        assert result.classified is True
        assert result.category_id == groceries_category.id
        assert result.method == "rule"
        assert result.rule_name == "Tesco Groceries"
        assert result.confidence == Decimal("1.0")
        assert assigned_categories[tesco_transaction.id] == groceries_category.id

    def test_rule_match_creates_evidence_record(
        self,
        db_session: Session,
        rules_service: RulesClassificationService,
        rule_repo: ClassificationRuleRepository,
        evidence_repo: CategoryEvidenceRepository,
        groceries_category: Category,
        tesco_transaction: Transaction,
    ) -> None:
        """Test that rule match creates evidence record for audit trail."""
        # Setup rule
        rule_repo.create(
            name="Tesco Groceries",
            rule_expression='description =~ "(?i)tesco"',
            category_id=groceries_category.id,
        )
        db_session.flush()
        rules_service.reload_rules()

        orchestrator = ClassificationOrchestrator(
            rules_service=rules_service,
            disambiguation_service=None,
            evidence_repository=evidence_repo,
        )

        result = orchestrator.classify(tesco_transaction)
        db_session.flush()

        assert result.classified is True
        assert result.method == "rule"

        # Verify evidence record was created
        evidence_records = evidence_repo.get_by_transaction(tesco_transaction.id)
        assert len(evidence_records) == 1

        evidence = evidence_records[0]
        assert evidence.evidence_type == "rule"
        assert evidence.category_id == groceries_category.id
        assert evidence.confidence_score == Decimal("1.0")
        assert "Tesco Groceries" in evidence.evidence_summary
        assert 'description =~ "(?i)tesco"' in evidence.evidence_summary
        assert evidence.item_price == tesco_transaction.amount

    def test_classify_no_matching_rule(
        self,
        db_session: Session,
        rules_service: RulesClassificationService,
        rule_repo: ClassificationRuleRepository,
        evidence_repo: CategoryEvidenceRepository,
        groceries_category: Category,
        unknown_transaction: Transaction,
    ) -> None:
        """Test classification when no rule matches."""
        # Setup rule that won't match
        rule_repo.create(
            name="Tesco",
            rule_expression='description =~ "(?i)tesco"',
            category_id=groceries_category.id,
        )
        db_session.flush()
        rules_service.reload_rules()

        orchestrator = ClassificationOrchestrator(
            rules_service=rules_service,
            disambiguation_service=None,
            evidence_repository=evidence_repo,
        )

        result = orchestrator.classify(unknown_transaction)

        assert result.classified is False
        assert result.category_id is None
        assert result.method == "unclassified"
        assert "No matching rules" in (result.error_message or "")

    def test_idempotency_skip_already_classified(
        self,
        db_session: Session,
        rules_service: RulesClassificationService,
        evidence_repo: CategoryEvidenceRepository,
        groceries_category: Category,
        tesco_transaction: Transaction,
    ) -> None:
        """Test that already classified transactions are skipped."""
        # Pre-assign a category
        category_link = TransactionCategory(
            transaction_id=tesco_transaction.id,
            category_id=groceries_category.id,
        )
        db_session.add(category_link)
        db_session.flush()

        # Refresh to load the relationship
        db_session.refresh(tesco_transaction)

        orchestrator = ClassificationOrchestrator(
            rules_service=rules_service,
            disambiguation_service=None,
            evidence_repository=evidence_repo,
        )

        result = orchestrator.classify(tesco_transaction)

        assert result.classified is True
        assert result.method == "existing"
        assert result.category_id == groceries_category.id

    def test_force_reclassification(
        self,
        db_session: Session,
        rules_service: RulesClassificationService,
        rule_repo: ClassificationRuleRepository,
        evidence_repo: CategoryEvidenceRepository,
        groceries_category: Category,
        electronics_category: Category,
        tesco_transaction: Transaction,
    ) -> None:
        """Test force reclassification of already classified transaction."""
        # Pre-assign wrong category
        category_link = TransactionCategory(
            transaction_id=tesco_transaction.id,
            category_id=electronics_category.id,  # Wrong category
        )
        db_session.add(category_link)
        db_session.flush()
        db_session.refresh(tesco_transaction)

        # Setup correct rule
        rule_repo.create(
            name="Tesco",
            rule_expression='description =~ "(?i)tesco"',
            category_id=groceries_category.id,
        )
        db_session.flush()
        rules_service.reload_rules()

        updated_categories: dict[int, int] = {}

        def category_updater(txn_id: int, cat_id: int) -> TransactionCategory:
            updated_categories[txn_id] = cat_id
            return TransactionCategory(transaction_id=txn_id, category_id=cat_id)

        orchestrator = ClassificationOrchestrator(
            rules_service=rules_service,
            disambiguation_service=None,
            evidence_repository=evidence_repo,
            transaction_category_updater=category_updater,
        )

        result = orchestrator.classify(tesco_transaction, force=True)

        assert result.classified is True
        assert result.method == "rule"
        assert result.category_id == groceries_category.id
        assert updated_categories[tesco_transaction.id] == groceries_category.id


class TestClassificationOrchestratorWithDisambiguation:
    """Tests for orchestrator with AI disambiguation."""

    def test_rule_with_disambiguation_flag(
        self,
        db_session: Session,
        rules_service: RulesClassificationService,
        rule_repo: ClassificationRuleRepository,
        evidence_repo: CategoryEvidenceRepository,
        electronics_category: Category,
        amazon_transaction: Transaction,
    ) -> None:
        """Test rule that requires disambiguation."""
        rule_repo.create(
            name="Amazon",
            rule_expression='description =~ "(?i)amazon"',
            category_id=electronics_category.id,
            requires_disambiguation=True,
        )
        db_session.flush()
        rules_service.reload_rules()

        # Create mock disambiguation service
        mock_disambiguation = MagicMock()
        mock_disambiguation.disambiguate.return_value = DisambiguationResult(
            transaction_id=amazon_transaction.id,
            success=True,
            dominant_category_id=electronics_category.id,
            evidence_records=[],
            confidence_score=Decimal("0.95"),
        )

        assigned: dict[int, int] = {}

        def updater(txn_id: int, cat_id: int) -> TransactionCategory:
            assigned[txn_id] = cat_id
            return TransactionCategory(transaction_id=txn_id, category_id=cat_id)

        orchestrator = ClassificationOrchestrator(
            rules_service=rules_service,
            disambiguation_service=mock_disambiguation,
            evidence_repository=evidence_repo,
            transaction_category_updater=updater,
        )

        result = orchestrator.classify(amazon_transaction)

        assert result.classified is True
        assert result.method == "ai"
        assert result.confidence == Decimal("0.95")
        mock_disambiguation.disambiguate.assert_called_once()

    def test_no_rule_uses_disambiguation(
        self,
        db_session: Session,
        rules_service: RulesClassificationService,
        rule_repo: ClassificationRuleRepository,
        evidence_repo: CategoryEvidenceRepository,
        electronics_category: Category,
        unknown_transaction: Transaction,
    ) -> None:
        """Test that transactions with no rule match go to disambiguation."""
        # No rules configured
        rules_service.reload_rules()

        mock_disambiguation = MagicMock()
        mock_disambiguation.disambiguate.return_value = DisambiguationResult(
            transaction_id=unknown_transaction.id,
            success=True,
            dominant_category_id=electronics_category.id,
            evidence_records=[],
            confidence_score=Decimal("0.85"),
        )

        assigned: dict[int, int] = {}

        def updater(txn_id: int, cat_id: int) -> TransactionCategory:
            assigned[txn_id] = cat_id
            return TransactionCategory(transaction_id=txn_id, category_id=cat_id)

        orchestrator = ClassificationOrchestrator(
            rules_service=rules_service,
            disambiguation_service=mock_disambiguation,
            evidence_repository=evidence_repo,
            transaction_category_updater=updater,
        )

        result = orchestrator.classify(unknown_transaction)

        assert result.classified is True
        assert result.method == "ai"
        assert assigned[unknown_transaction.id] == electronics_category.id

    def test_disambiguation_failure_fallback_to_rule(
        self,
        db_session: Session,
        rules_service: RulesClassificationService,
        rule_repo: ClassificationRuleRepository,
        evidence_repo: CategoryEvidenceRepository,
        electronics_category: Category,
        amazon_transaction: Transaction,
    ) -> None:
        """Test fallback to rule category when disambiguation fails."""
        rule_repo.create(
            name="Amazon",
            rule_expression='description =~ "(?i)amazon"',
            category_id=electronics_category.id,
            requires_disambiguation=True,
        )
        db_session.flush()
        rules_service.reload_rules()

        mock_disambiguation = MagicMock()
        mock_disambiguation.disambiguate.return_value = DisambiguationResult(
            transaction_id=amazon_transaction.id,
            success=False,
            dominant_category_id=None,
            evidence_records=[],
            confidence_score=Decimal("0"),
            error_message="No emails found",
        )

        assigned: dict[int, int] = {}

        def updater(txn_id: int, cat_id: int) -> TransactionCategory:
            assigned[txn_id] = cat_id
            return TransactionCategory(transaction_id=txn_id, category_id=cat_id)

        orchestrator = ClassificationOrchestrator(
            rules_service=rules_service,
            disambiguation_service=mock_disambiguation,
            evidence_repository=evidence_repo,
            transaction_category_updater=updater,
        )

        result = orchestrator.classify(amazon_transaction)

        # Should fall back to rule category
        assert result.classified is True
        assert result.method == "rule_with_disambiguation"
        assert result.category_id == electronics_category.id
        assert result.confidence == Decimal("0.5")


class TestClassificationOrchestratorBatch:
    """Tests for batch classification."""

    def test_classify_batch(
        self,
        db_session: Session,
        rules_service: RulesClassificationService,
        rule_repo: ClassificationRuleRepository,
        evidence_repo: CategoryEvidenceRepository,
        groceries_category: Category,
        electronics_category: Category,
        tesco_transaction: Transaction,
        amazon_transaction: Transaction,
        unknown_transaction: Transaction,
    ) -> None:
        """Test batch classification of multiple transactions."""
        rule_repo.create(
            name="Tesco",
            rule_expression='description =~ "(?i)tesco"',
            category_id=groceries_category.id,
        )
        rule_repo.create(
            name="Amazon",
            rule_expression='description =~ "(?i)amazon"',
            category_id=electronics_category.id,
        )
        db_session.flush()
        rules_service.reload_rules()

        orchestrator = ClassificationOrchestrator(
            rules_service=rules_service,
            disambiguation_service=None,
            evidence_repository=evidence_repo,
        )

        results = orchestrator.classify_batch(
            [tesco_transaction, amazon_transaction, unknown_transaction]
        )

        assert len(results) == 3
        assert results[tesco_transaction.id].classified is True
        assert results[amazon_transaction.id].classified is True
        assert results[unknown_transaction.id].classified is False


class TestClassificationOrchestratorStatistics:
    """Tests for classification statistics."""

    def test_get_statistics(
        self,
        db_session: Session,
        rules_service: RulesClassificationService,
        rule_repo: ClassificationRuleRepository,
        evidence_repo: CategoryEvidenceRepository,
        groceries_category: Category,
        tesco_transaction: Transaction,
        amazon_transaction: Transaction,
        unknown_transaction: Transaction,
    ) -> None:
        """Test gathering classification statistics."""
        rule_repo.create(
            name="Tesco",
            rule_expression='description =~ "(?i)tesco"',
            category_id=groceries_category.id,
        )
        db_session.flush()
        rules_service.reload_rules()

        orchestrator = ClassificationOrchestrator(
            rules_service=rules_service,
            disambiguation_service=None,
            evidence_repository=evidence_repo,
        )

        results = orchestrator.classify_batch(
            [tesco_transaction, amazon_transaction, unknown_transaction]
        )
        stats = orchestrator.get_classification_statistics(results)

        assert stats["total"] == 3
        assert stats["classified"] == 1
        assert stats["unclassified"] == 2
        assert stats["by_rule"] == 1
