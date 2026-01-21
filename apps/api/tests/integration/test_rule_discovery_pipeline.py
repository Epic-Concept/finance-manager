"""Integration tests for the rule discovery CLI pipeline.

These tests verify the full rule discovery flow including:
- Batch classification with coverage reporting
- Transaction clustering
- Rule validation
- Rule proposal storage
"""

import json
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func
from sqlalchemy.orm import Session

from finance_api.models.category import Category, CategoryClosure
from finance_api.models.classification_rule import ClassificationRule
from finance_api.models.transaction import Transaction
from finance_api.models.transaction_category import TransactionCategory
from finance_api.repositories.classification_rule_repository import (
    ClassificationRuleRepository,
)
from finance_api.repositories.rule_proposal_repository import RuleProposalRepository
from finance_api.services.rule_validation_service import RuleValidationService
from finance_api.services.rules_classification_service import RulesClassificationService
from finance_api.services.transaction_clustering_service import (
    TransactionClusteringService,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def setup_categories(db_session: Session) -> dict[str, Category]:
    """Create a category hierarchy for testing."""
    categories = {}

    for name in ["Food", "Shopping", "Utilities", "Transport"]:
        cat = Category(name=name, commitment_level=2)
        db_session.add(cat)
        db_session.flush()
        closure = CategoryClosure(ancestor_id=cat.id, descendant_id=cat.id, depth=0)
        db_session.add(closure)
        categories[name] = cat

    # Create subcategories
    for name, parent in [
        ("Groceries", "Food"),
        ("Coffee", "Food"),
        ("Electronics", "Shopping"),
    ]:
        cat = Category(name=name, parent_id=categories[parent].id, commitment_level=2)
        db_session.add(cat)
        db_session.flush()
        closure = CategoryClosure(ancestor_id=cat.id, descendant_id=cat.id, depth=0)
        db_session.add(closure)
        closure2 = CategoryClosure(
            ancestor_id=categories[parent].id, descendant_id=cat.id, depth=1
        )
        db_session.add(closure2)
        categories[name] = cat

    db_session.flush()
    return categories


@pytest.fixture
def setup_transactions(db_session: Session) -> list[Transaction]:
    """Create a diverse set of transactions for testing."""
    transactions = []

    # Tesco transactions (cluster)
    for i in range(10):
        txn = Transaction(
            transaction_date=date(2026, 1, 15),
            description=f"TESCO STORES {1000 + i}",
            amount=Decimal("-45.00") - Decimal(i),
            currency="GBP",
        )
        transactions.append(txn)

    # Sainsburys transactions (cluster)
    for i in range(8):
        txn = Transaction(
            transaction_date=date(2026, 1, 16),
            description=f"SAINSBURYS LOCAL #{200 + i}",
            amount=Decimal("-30.00") - Decimal(i),
            currency="GBP",
        )
        transactions.append(txn)

    # Starbucks transactions (cluster)
    for i in range(6):
        txn = Transaction(
            transaction_date=date(2026, 1, 17),
            description=f"STARBUCKS COFFEE {i}",
            amount=Decimal("-4.50"),
            currency="GBP",
        )
        transactions.append(txn)

    # Amazon transactions (cluster - needs disambiguation)
    for i in range(5):
        txn = Transaction(
            transaction_date=date(2026, 1, 18),
            description=f"AMAZON.CO.UK ORDER {3000 + i}",
            amount=Decimal("-99.00") - Decimal(i * 10),
            currency="GBP",
        )
        transactions.append(txn)

    # Unique transactions (no cluster)
    unique_descriptions = [
        "RANDOM SHOP ABC",
        "ONE TIME PURCHASE XYZ",
        "MYSTERIOUS VENDOR 123",
    ]
    for desc in unique_descriptions:
        txn = Transaction(
            transaction_date=date(2026, 1, 19),
            description=desc,
            amount=Decimal("-25.00"),
            currency="GBP",
        )
        transactions.append(txn)

    db_session.add_all(transactions)
    db_session.flush()
    return transactions


@pytest.fixture
def setup_rules(
    db_session: Session,
    setup_categories: dict[str, Category],
) -> list[ClassificationRule]:
    """Create classification rules for testing."""
    rule_repo = ClassificationRuleRepository(db_session)
    rules = []

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
            name="Starbucks",
            rule_expression='description =~ "(?i)starbucks"',
            category_id=setup_categories["Coffee"].id,
            priority=90,
        )
    )

    db_session.flush()
    return rules


# ============================================================================
# Batch Classification Tests (classify_batch.py functions)
# ============================================================================


class TestBatchClassificationIntegration:
    """Integration tests for batch classification CLI functions."""

    def test_get_coverage_stats_all_uncategorized(
        self,
        db_session: Session,
        setup_transactions: list[Transaction],
    ) -> None:
        """Test coverage stats when no transactions are categorized."""
        total = db_session.query(func.count(Transaction.id)).scalar()
        categorized = (
            db_session.query(func.count(TransactionCategory.id))
            .filter(TransactionCategory.category_id.isnot(None))
            .scalar()
        )

        assert total == len(setup_transactions)
        assert categorized == 0

    def test_get_coverage_stats_partial_categorization(
        self,
        db_session: Session,
        setup_categories: dict[str, Category],
        setup_transactions: list[Transaction],
    ) -> None:
        """Test coverage stats with partial categorization."""
        # Categorize first 5 transactions
        for txn in setup_transactions[:5]:
            link = TransactionCategory(
                transaction_id=txn.id,
                category_id=setup_categories["Groceries"].id,
            )
            db_session.add(link)
        db_session.flush()

        total = db_session.query(func.count(Transaction.id)).scalar()
        categorized = (
            db_session.query(func.count(TransactionCategory.id))
            .filter(TransactionCategory.category_id.isnot(None))
            .scalar()
        )

        assert total == len(setup_transactions)
        assert categorized == 5
        coverage = (categorized / total * 100) if total > 0 else 0
        assert 15 < coverage < 20  # ~16% coverage

    def test_get_category_distribution(
        self,
        db_session: Session,
        setup_categories: dict[str, Category],
        setup_transactions: list[Transaction],
    ) -> None:
        """Test category distribution calculation."""
        # Assign transactions to different categories
        for i, txn in enumerate(setup_transactions[:10]):
            if i < 5:
                cat_id = setup_categories["Groceries"].id
            else:
                cat_id = setup_categories["Coffee"].id

            link = TransactionCategory(
                transaction_id=txn.id,
                category_id=cat_id,
            )
            db_session.add(link)
        db_session.flush()

        # Query distribution
        results = (
            db_session.query(
                Category.name,
                func.count(TransactionCategory.id).label("count"),
            )
            .join(TransactionCategory, TransactionCategory.category_id == Category.id)
            .group_by(Category.name)
            .order_by(func.count(TransactionCategory.id).desc())
            .all()
        )

        distribution = {r[0]: r[1] for r in results}
        assert distribution["Groceries"] == 5
        assert distribution["Coffee"] == 5

    def test_get_uncategorized_transactions(
        self,
        db_session: Session,
        setup_categories: dict[str, Category],
        setup_transactions: list[Transaction],
    ) -> None:
        """Test finding uncategorized transactions."""
        # Categorize some transactions
        for txn in setup_transactions[:10]:
            link = TransactionCategory(
                transaction_id=txn.id,
                category_id=setup_categories["Groceries"].id,
            )
            db_session.add(link)
        db_session.flush()

        # Find uncategorized
        categorized_ids = (
            db_session.query(TransactionCategory.transaction_id)
            .filter(TransactionCategory.category_id.isnot(None))
            .all()
        )
        categorized_id_set = {r[0] for r in categorized_ids}

        all_txns = db_session.query(Transaction).all()
        uncategorized = [t for t in all_txns if t.id not in categorized_id_set]

        assert len(uncategorized) == len(setup_transactions) - 10

    def test_batch_classification_with_rules(
        self,
        db_session: Session,
        setup_categories: dict[str, Category],
        setup_rules: list[ClassificationRule],
        setup_transactions: list[Transaction],
    ) -> None:
        """Test batch classification applies rules correctly."""
        rule_repo = ClassificationRuleRepository(db_session)
        classification_service = RulesClassificationService(rule_repo)
        classification_service.reload_rules()

        # Classify all transactions
        results = classification_service.classify_batch(setup_transactions)

        # Count matches
        matched = sum(1 for r in results.values() if r is not None)

        # Should match Tesco (10) + Starbucks (6) = 16
        assert matched == 16

        # Verify Tesco matches
        tesco_txns = [t for t in setup_transactions if "TESCO" in t.description]
        for txn in tesco_txns:
            assert results[txn.id] is not None
            assert results[txn.id].rule.name == "Tesco"
            assert results[txn.id].category_id == setup_categories["Groceries"].id


# ============================================================================
# Transaction Clustering Tests (discover_rules.py functions)
# ============================================================================


class TestTransactionClusteringIntegration:
    """Integration tests for transaction clustering."""

    def test_cluster_transactions_finds_groups(
        self,
        db_session: Session,
        setup_transactions: list[Transaction],
    ) -> None:
        """Test clustering finds expected transaction groups."""
        clustering_service = TransactionClusteringService(min_cluster_size=3)

        clusters = clustering_service.cluster_transactions(setup_transactions)

        # Should find clusters for Tesco, Sainsburys, Starbucks, Amazon
        cluster_keys = {c.cluster_key for c in clusters}
        assert "TESCO" in cluster_keys
        assert "SAINSBURYS" in cluster_keys
        assert "STARBUCKS" in cluster_keys
        assert "AMAZON" in cluster_keys

    def test_cluster_sizes_are_correct(
        self,
        db_session: Session,
        setup_transactions: list[Transaction],
    ) -> None:
        """Test cluster sizes match expected counts."""
        clustering_service = TransactionClusteringService(min_cluster_size=3)

        clusters = clustering_service.cluster_transactions(setup_transactions)
        cluster_sizes = {c.cluster_key: c.size for c in clusters}

        assert cluster_sizes["TESCO"] == 10
        assert cluster_sizes["SAINSBURYS"] == 8
        assert cluster_sizes["STARBUCKS"] == 6
        assert cluster_sizes["AMAZON"] == 5

    def test_cluster_statistics(
        self,
        db_session: Session,
        setup_transactions: list[Transaction],
    ) -> None:
        """Test cluster statistics calculation."""
        clustering_service = TransactionClusteringService(min_cluster_size=3)

        clusters = clustering_service.cluster_transactions(setup_transactions)
        stats = clustering_service.get_cluster_statistics(
            clusters, len(setup_transactions)
        )

        assert stats.total_clusters == 4
        assert stats.largest_cluster_size == 10
        assert stats.smallest_cluster_size == 5
        # 10 + 8 + 6 + 5 = 29 out of 32 transactions
        assert stats.clustered_transactions == 29
        assert stats.coverage_percentage > 90

    def test_cluster_sample_descriptions(
        self,
        db_session: Session,
        setup_transactions: list[Transaction],
    ) -> None:
        """Test cluster contains sample descriptions."""
        clustering_service = TransactionClusteringService(
            min_cluster_size=3, max_samples=3
        )

        clusters = clustering_service.cluster_transactions(setup_transactions)
        tesco_cluster = next(c for c in clusters if c.cluster_key == "TESCO")

        assert len(tesco_cluster.sample_descriptions) == 3
        for sample in tesco_cluster.sample_descriptions:
            assert "TESCO" in sample


# ============================================================================
# Rule Validation Tests (discover_rules.py functions)
# ============================================================================


class TestRuleValidationIntegration:
    """Integration tests for rule validation."""

    def test_validate_rule_precision(
        self,
        db_session: Session,
        setup_transactions: list[Transaction],
    ) -> None:
        """Test rule precision calculation."""
        validation_service = RuleValidationService()
        clustering_service = TransactionClusteringService(min_cluster_size=3)

        # Get Tesco cluster
        clusters = clustering_service.cluster_transactions(setup_transactions)
        tesco_cluster = next(c for c in clusters if c.cluster_key == "TESCO")
        cluster_ids = {t.id for t in tesco_cluster.transactions}

        # Test pattern
        result = validation_service.test_rule(
            pattern="(?i)tesco",
            all_transactions=setup_transactions,
            cluster_transaction_ids=cluster_ids,
        )

        assert result.is_valid_regex is True
        assert result.total_matches == 10
        assert result.true_positives == 10
        assert result.false_positives == 0
        assert result.precision == Decimal("1.0000")
        assert result.coverage == Decimal("1.0000")

    def test_validate_rule_with_false_positives(
        self,
        db_session: Session,
        setup_transactions: list[Transaction],
    ) -> None:
        """Test rule validation identifies false positives."""
        validation_service = RuleValidationService()
        clustering_service = TransactionClusteringService(min_cluster_size=3)

        # Get Tesco cluster
        clusters = clustering_service.cluster_transactions(setup_transactions)
        tesco_cluster = next(c for c in clusters if c.cluster_key == "TESCO")
        cluster_ids = {t.id for t in tesco_cluster.transactions}

        # Test overly broad pattern that matches multiple clusters
        result = validation_service.test_rule(
            pattern="(?i)stores|local",  # Matches Tesco STORES and Sainsburys LOCAL
            all_transactions=setup_transactions,
            cluster_transaction_ids=cluster_ids,
        )

        assert result.is_valid_regex is True
        assert result.true_positives == 10  # All Tesco
        assert result.false_positives == 8  # All Sainsburys
        assert result.precision < Decimal("0.6")

    def test_validate_invalid_regex(
        self,
        db_session: Session,
        setup_transactions: list[Transaction],
    ) -> None:
        """Test validation handles invalid regex."""
        validation_service = RuleValidationService()

        result = validation_service.test_rule(
            pattern="(?i)tesco[",  # Invalid regex
            all_transactions=setup_transactions,
            cluster_transaction_ids=set(),
        )

        assert result.is_valid_regex is False
        assert result.regex_error is not None


# ============================================================================
# Rule Proposal Repository Tests
# ============================================================================


class TestRuleProposalIntegration:
    """Integration tests for rule proposal storage."""

    def test_create_and_retrieve_proposal(
        self,
        db_session: Session,
        setup_categories: dict[str, Category],
    ) -> None:
        """Test creating and retrieving a rule proposal."""
        proposal_repo = RuleProposalRepository(db_session)

        proposal = proposal_repo.create(
            cluster_hash="abc123",
            cluster_size=10,
            sample_descriptions=json.dumps(["TESCO STORES 1", "TESCO STORES 2"]),
            proposed_pattern="(?i)tesco",
            proposed_category_id=setup_categories["Groceries"].id,
            llm_confidence="high",
            llm_reasoning="Common grocery store pattern",
            validation_matches=10,
            validation_precision=Decimal("1.0"),
        )
        db_session.flush()

        assert proposal.id is not None
        assert proposal.status == "pending"

        # Retrieve
        retrieved = proposal_repo.get(proposal.id)
        assert retrieved is not None
        assert retrieved.cluster_hash == "abc123"
        assert retrieved.proposed_pattern == "(?i)tesco"

    def test_update_proposal_status(
        self,
        db_session: Session,
        setup_categories: dict[str, Category],
        setup_rules: list[ClassificationRule],
    ) -> None:
        """Test updating proposal status to accepted."""
        proposal_repo = RuleProposalRepository(db_session)

        proposal = proposal_repo.create(
            cluster_hash="def456",
            cluster_size=8,
            sample_descriptions=json.dumps(["SAINSBURYS 1"]),
            proposed_pattern="(?i)sainsbury",
            proposed_category_id=setup_categories["Groceries"].id,
            llm_confidence="high",
            llm_reasoning="Grocery store",
            validation_matches=8,
            validation_precision=Decimal("1.0"),
        )
        db_session.flush()

        # Accept proposal
        proposal_repo.update_status(
            proposal.id,
            status="accepted",
            final_rule_id=setup_rules[0].id,
            reviewer_notes="Looks good",
        )
        db_session.flush()

        # Verify
        updated = proposal_repo.get(proposal.id)
        assert updated.status == "accepted"
        assert updated.final_rule_id == setup_rules[0].id
        assert updated.reviewer_notes == "Looks good"

    def test_get_pending_proposals(
        self,
        db_session: Session,
        setup_categories: dict[str, Category],
    ) -> None:
        """Test retrieving pending proposals for resume."""
        proposal_repo = RuleProposalRepository(db_session)

        # Create multiple proposals with different statuses
        for i, status in enumerate(["pending", "pending", "accepted", "rejected"]):
            p = proposal_repo.create(
                cluster_hash=f"hash{i}",
                cluster_size=5,
                sample_descriptions=json.dumps([f"Sample {i}"]),
                proposed_pattern=f"pattern{i}",
                proposed_category_id=setup_categories["Groceries"].id,
                llm_confidence="medium",
                llm_reasoning="Test",
                validation_matches=5,
                validation_precision=Decimal("0.9"),
            )
            if status != "pending":
                proposal_repo.update_status(p.id, status)
        db_session.flush()

        # Get pending
        pending = proposal_repo.get_pending_proposals()
        assert len(pending) == 2

    def test_get_by_cluster_hash_prevents_duplicates(
        self,
        db_session: Session,
        setup_categories: dict[str, Category],
    ) -> None:
        """Test cluster hash lookup prevents duplicate proposals."""
        proposal_repo = RuleProposalRepository(db_session)

        proposal_repo.create(
            cluster_hash="unique_hash_123",
            cluster_size=10,
            sample_descriptions=json.dumps(["Sample"]),
            proposed_pattern="pattern",
            proposed_category_id=setup_categories["Groceries"].id,
            llm_confidence="high",
            llm_reasoning="Test",
            validation_matches=10,
            validation_precision=Decimal("1.0"),
        )
        db_session.flush()

        # Look up by hash
        existing = proposal_repo.get_by_cluster_hash("unique_hash_123")
        assert existing is not None

        # Non-existent hash
        missing = proposal_repo.get_by_cluster_hash("non_existent")
        assert missing is None


# ============================================================================
# End-to-End Discovery Flow Tests
# ============================================================================


class TestDiscoveryFlowIntegration:
    """Integration tests for the complete discovery workflow."""

    def test_full_discovery_workflow(
        self,
        db_session: Session,
        setup_categories: dict[str, Category],
        setup_transactions: list[Transaction],
    ) -> None:
        """Test complete workflow: cluster -> validate -> store proposal."""
        # Services
        clustering_service = TransactionClusteringService(min_cluster_size=5)
        validation_service = RuleValidationService()
        proposal_repo = RuleProposalRepository(db_session)

        # Step 1: Cluster transactions
        clusters = clustering_service.cluster_transactions(setup_transactions)
        assert len(clusters) >= 2  # At least Tesco and Sainsburys

        # Step 2: For each cluster, validate a proposed pattern
        for cluster in clusters[:2]:  # Process first 2 clusters
            cluster_ids = {t.id for t in cluster.transactions}
            pattern = f"(?i){cluster.cluster_key.lower()}"

            validation = validation_service.test_rule(
                pattern=pattern,
                all_transactions=setup_transactions,
                cluster_transaction_ids=cluster_ids,
            )

            # Step 3: Store proposal if validation passes
            if validation.is_valid_regex and validation.precision >= Decimal("0.8"):
                proposal_repo.create(
                    cluster_hash=cluster.cluster_hash,
                    cluster_size=cluster.size,
                    sample_descriptions=json.dumps(cluster.sample_descriptions),
                    proposed_pattern=pattern,
                    proposed_category_id=setup_categories["Groceries"].id,
                    llm_confidence="high",
                    llm_reasoning="Auto-generated from cluster",
                    validation_matches=validation.total_matches,
                    validation_precision=validation.precision,
                )

        db_session.flush()

        # Verify proposals were created
        pending = proposal_repo.get_pending_proposals()
        assert len(pending) == 2

    def test_workflow_with_rule_creation(
        self,
        db_session: Session,
        setup_categories: dict[str, Category],
        setup_transactions: list[Transaction],
    ) -> None:
        """Test workflow through to rule creation."""
        clustering_service = TransactionClusteringService(min_cluster_size=5)
        validation_service = RuleValidationService()
        proposal_repo = RuleProposalRepository(db_session)
        rule_repo = ClassificationRuleRepository(db_session)

        # Get Tesco cluster
        clusters = clustering_service.cluster_transactions(setup_transactions)
        tesco_cluster = next(c for c in clusters if c.cluster_key == "TESCO")
        cluster_ids = {t.id for t in tesco_cluster.transactions}

        # Validate pattern
        pattern = "(?i)tesco"
        validation = validation_service.test_rule(
            pattern=pattern,
            all_transactions=setup_transactions,
            cluster_transaction_ids=cluster_ids,
        )

        # Create proposal
        proposal = proposal_repo.create(
            cluster_hash=tesco_cluster.cluster_hash,
            cluster_size=tesco_cluster.size,
            sample_descriptions=json.dumps(tesco_cluster.sample_descriptions),
            proposed_pattern=pattern,
            proposed_category_id=setup_categories["Groceries"].id,
            llm_confidence="high",
            llm_reasoning="Common grocery store",
            validation_matches=validation.total_matches,
            validation_precision=validation.precision,
        )
        db_session.flush()

        # Accept proposal and create rule
        rule = rule_repo.create(
            name=f"Auto: {tesco_cluster.cluster_key}",
            rule_expression=f'description =~ "{pattern}"',
            category_id=setup_categories["Groceries"].id,
        )
        db_session.flush()

        proposal_repo.update_status(
            proposal.id,
            status="accepted",
            final_rule_id=rule.id,
        )
        db_session.flush()

        # Verify rule works
        rules_service = RulesClassificationService(rule_repo)
        rules_service.reload_rules()

        results = rules_service.classify_batch(setup_transactions)
        tesco_matches = sum(
            1
            for txn in tesco_cluster.transactions
            if results[txn.id] is not None and results[txn.id].rule.name == rule.name
        )
        assert tesco_matches == 10
