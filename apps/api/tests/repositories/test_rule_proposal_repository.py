"""Tests for RuleProposalRepository."""

import json
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from finance_api.models.category import Category, CategoryClosure
from finance_api.models.classification_rule import ClassificationRule
from finance_api.repositories.rule_proposal_repository import (
    RuleProposalNotFoundError,
    RuleProposalRepository,
)


@pytest.fixture
def test_category(db_session: Session) -> Category:
    """Create a test category for proposals."""
    category = Category(name="Test Category")
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
def test_rule(db_session: Session, test_category: Category) -> ClassificationRule:
    """Create a test classification rule."""
    rule = ClassificationRule(
        name="Test Rule",
        rule_expression='description =~ "(?i)test"',
        category_id=test_category.id,
    )
    db_session.add(rule)
    db_session.flush()
    return rule


class TestRuleProposalRepositoryCreate:
    """Tests for RuleProposalRepository.create()."""

    def test_create_minimal_proposal(self, db_session: Session) -> None:
        """Test creating a proposal with minimal fields."""
        repo = RuleProposalRepository(db_session)

        proposal = repo.create(
            cluster_hash="abc123",
            cluster_size=50,
            sample_descriptions=json.dumps(["TESCO STORES 1234"]),
        )
        db_session.flush()

        assert proposal.id is not None
        assert proposal.cluster_hash == "abc123"
        assert proposal.cluster_size == 50
        assert proposal.status == "pending"

    def test_create_full_proposal(
        self, db_session: Session, test_category: Category
    ) -> None:
        """Test creating a proposal with all fields."""
        repo = RuleProposalRepository(db_session)

        proposal = repo.create(
            cluster_hash="full123",
            cluster_size=100,
            sample_descriptions=json.dumps(["TESCO STORES", "TESCO EXPRESS"]),
            proposed_pattern="(?i)tesco",
            proposed_category_id=test_category.id,
            llm_confidence="high",
            llm_reasoning="All transactions appear to be Tesco purchases",
            validation_matches=95,
            validation_precision=Decimal("0.9500"),
            validation_false_positives=json.dumps(["TESCO BANK"]),
        )
        db_session.flush()

        assert proposal.proposed_pattern == "(?i)tesco"
        assert proposal.proposed_category_id == test_category.id
        assert proposal.llm_confidence == "high"
        assert proposal.validation_matches == 95
        assert proposal.validation_precision == Decimal("0.9500")

    def test_create_with_status(self, db_session: Session) -> None:
        """Test creating a proposal with explicit status."""
        repo = RuleProposalRepository(db_session)

        proposal = repo.create(
            cluster_hash="status123",
            cluster_size=10,
            sample_descriptions="[]",
            status="rejected",
        )
        db_session.flush()

        assert proposal.status == "rejected"


class TestRuleProposalRepositoryGet:
    """Tests for RuleProposalRepository.get()."""

    def test_get_existing_proposal(self, db_session: Session) -> None:
        """Test getting an existing proposal by ID."""
        repo = RuleProposalRepository(db_session)
        created = repo.create(
            cluster_hash="get123",
            cluster_size=10,
            sample_descriptions="[]",
        )
        db_session.flush()

        proposal = repo.get(created.id)

        assert proposal.id == created.id
        assert proposal.cluster_hash == "get123"

    def test_get_nonexistent_proposal(self, db_session: Session) -> None:
        """Test getting a non-existent proposal raises error."""
        repo = RuleProposalRepository(db_session)

        with pytest.raises(RuleProposalNotFoundError):
            repo.get(9999)


class TestRuleProposalRepositoryGetByStatus:
    """Tests for RuleProposalRepository.get_by_status()."""

    def test_get_pending_proposals(self, db_session: Session) -> None:
        """Test getting all pending proposals."""
        repo = RuleProposalRepository(db_session)

        repo.create(
            cluster_hash="pending1", cluster_size=10, sample_descriptions="[]"
        )
        repo.create(
            cluster_hash="pending2", cluster_size=20, sample_descriptions="[]"
        )
        repo.create(
            cluster_hash="rejected1",
            cluster_size=30,
            sample_descriptions="[]",
            status="rejected",
        )
        db_session.flush()

        pending = repo.get_by_status("pending")

        assert len(pending) == 2
        assert all(p.status == "pending" for p in pending)

    def test_get_accepted_proposals(self, db_session: Session) -> None:
        """Test getting all accepted proposals."""
        repo = RuleProposalRepository(db_session)

        repo.create(
            cluster_hash="accepted1",
            cluster_size=10,
            sample_descriptions="[]",
            status="accepted",
        )
        repo.create(
            cluster_hash="pending1", cluster_size=20, sample_descriptions="[]"
        )
        db_session.flush()

        accepted = repo.get_by_status("accepted")

        assert len(accepted) == 1
        assert accepted[0].cluster_hash == "accepted1"


class TestRuleProposalRepositoryGetPendingProposals:
    """Tests for RuleProposalRepository.get_pending_proposals()."""

    def test_get_pending_for_resume(self, db_session: Session) -> None:
        """Test getting pending proposals for resume functionality."""
        repo = RuleProposalRepository(db_session)

        repo.create(
            cluster_hash="resume1", cluster_size=10, sample_descriptions="[]"
        )
        repo.create(
            cluster_hash="resume2", cluster_size=20, sample_descriptions="[]"
        )
        repo.create(
            cluster_hash="done1",
            cluster_size=30,
            sample_descriptions="[]",
            status="accepted",
        )
        db_session.flush()

        pending = repo.get_pending_proposals()

        assert len(pending) == 2


class TestRuleProposalRepositoryGetByClusterHash:
    """Tests for RuleProposalRepository.get_by_cluster_hash()."""

    def test_get_existing_cluster(self, db_session: Session) -> None:
        """Test finding proposal by cluster hash."""
        repo = RuleProposalRepository(db_session)

        created = repo.create(
            cluster_hash="unique_cluster_hash",
            cluster_size=10,
            sample_descriptions="[]",
        )
        db_session.flush()

        found = repo.get_by_cluster_hash("unique_cluster_hash")

        assert found is not None
        assert found.id == created.id

    def test_get_nonexistent_cluster(self, db_session: Session) -> None:
        """Test finding non-existent cluster hash returns None."""
        repo = RuleProposalRepository(db_session)

        found = repo.get_by_cluster_hash("nonexistent_hash")

        assert found is None

    def test_avoids_duplicate_proposals(self, db_session: Session) -> None:
        """Test using get_by_cluster_hash to avoid duplicates."""
        repo = RuleProposalRepository(db_session)

        repo.create(
            cluster_hash="dup_hash",
            cluster_size=10,
            sample_descriptions="[]",
        )
        db_session.flush()

        existing = repo.get_by_cluster_hash("dup_hash")
        assert existing is not None

        # Should not create duplicate
        if not existing:
            repo.create(
                cluster_hash="dup_hash",
                cluster_size=10,
                sample_descriptions="[]",
            )

        all_proposals = repo.get_all()
        dup_proposals = [p for p in all_proposals if p.cluster_hash == "dup_hash"]
        assert len(dup_proposals) == 1


class TestRuleProposalRepositoryUpdateStatus:
    """Tests for RuleProposalRepository.update_status()."""

    def test_accept_proposal(
        self, db_session: Session, test_rule: ClassificationRule
    ) -> None:
        """Test accepting a proposal."""
        repo = RuleProposalRepository(db_session)
        proposal = repo.create(
            cluster_hash="accept123", cluster_size=10, sample_descriptions="[]"
        )
        db_session.flush()

        updated = repo.update_status(
            proposal.id,
            status="accepted",
            final_rule_id=test_rule.id,
        )

        assert updated.status == "accepted"
        assert updated.final_rule_id == test_rule.id
        assert updated.reviewed_at is not None

    def test_reject_proposal(self, db_session: Session) -> None:
        """Test rejecting a proposal with notes."""
        repo = RuleProposalRepository(db_session)
        proposal = repo.create(
            cluster_hash="reject123", cluster_size=10, sample_descriptions="[]"
        )
        db_session.flush()

        updated = repo.update_status(
            proposal.id,
            status="rejected",
            reviewer_notes="Too many false positives",
        )

        assert updated.status == "rejected"
        assert updated.reviewer_notes == "Too many false positives"
        assert updated.reviewed_at is not None

    def test_modify_proposal(self, db_session: Session) -> None:
        """Test marking a proposal as modified."""
        repo = RuleProposalRepository(db_session)
        proposal = repo.create(
            cluster_hash="modify123", cluster_size=10, sample_descriptions="[]"
        )
        db_session.flush()

        updated = repo.update_status(
            proposal.id,
            status="modified",
            reviewer_notes="Pattern adjusted",
        )

        assert updated.status == "modified"


class TestRuleProposalRepositoryUpdateValidation:
    """Tests for RuleProposalRepository.update_validation()."""

    def test_update_validation_results(self, db_session: Session) -> None:
        """Test updating validation results."""
        repo = RuleProposalRepository(db_session)
        proposal = repo.create(
            cluster_hash="validate123", cluster_size=100, sample_descriptions="[]"
        )
        db_session.flush()

        updated = repo.update_validation(
            proposal.id,
            validation_matches=95,
            validation_precision=Decimal("0.9500"),
            validation_false_positives=json.dumps(["FP1", "FP2"]),
        )

        assert updated.validation_matches == 95
        assert updated.validation_precision == Decimal("0.9500")
        assert "FP1" in updated.validation_false_positives

    def test_update_validation_without_false_positives(
        self, db_session: Session
    ) -> None:
        """Test updating validation without false positives."""
        repo = RuleProposalRepository(db_session)
        proposal = repo.create(
            cluster_hash="perfect123", cluster_size=100, sample_descriptions="[]"
        )
        db_session.flush()

        updated = repo.update_validation(
            proposal.id,
            validation_matches=100,
            validation_precision=Decimal("1.0000"),
        )

        assert updated.validation_matches == 100
        assert updated.validation_precision == Decimal("1.0000")


class TestRuleProposalRepositoryUpdatePattern:
    """Tests for RuleProposalRepository.update_pattern()."""

    def test_update_pattern(
        self, db_session: Session, test_category: Category
    ) -> None:
        """Test updating the proposed pattern."""
        repo = RuleProposalRepository(db_session)
        proposal = repo.create(
            cluster_hash="pattern123",
            cluster_size=10,
            sample_descriptions="[]",
            proposed_pattern="(?i)old_pattern",
        )
        db_session.flush()

        updated = repo.update_pattern(
            proposal.id,
            proposed_pattern="(?i)new_pattern",
            proposed_category_id=test_category.id,
        )

        assert updated.proposed_pattern == "(?i)new_pattern"
        assert updated.proposed_category_id == test_category.id

    def test_update_pattern_only(self, db_session: Session) -> None:
        """Test updating just the pattern without category."""
        repo = RuleProposalRepository(db_session)
        proposal = repo.create(
            cluster_hash="patternonly123",
            cluster_size=10,
            sample_descriptions="[]",
            proposed_pattern="(?i)original",
        )
        db_session.flush()

        updated = repo.update_pattern(
            proposal.id,
            proposed_pattern="(?i)updated",
        )

        assert updated.proposed_pattern == "(?i)updated"
        assert updated.proposed_category_id is None


class TestRuleProposalRepositoryDelete:
    """Tests for RuleProposalRepository.delete()."""

    def test_delete_proposal(self, db_session: Session) -> None:
        """Test deleting a proposal."""
        repo = RuleProposalRepository(db_session)
        proposal = repo.create(
            cluster_hash="delete123", cluster_size=10, sample_descriptions="[]"
        )
        db_session.flush()
        proposal_id = proposal.id

        repo.delete(proposal_id)
        db_session.flush()

        with pytest.raises(RuleProposalNotFoundError):
            repo.get(proposal_id)

    def test_delete_nonexistent_raises_error(self, db_session: Session) -> None:
        """Test deleting non-existent proposal raises error."""
        repo = RuleProposalRepository(db_session)

        with pytest.raises(RuleProposalNotFoundError):
            repo.delete(9999)


class TestRuleProposalRepositoryCountByStatus:
    """Tests for RuleProposalRepository.count_by_status()."""

    def test_count_empty(self, db_session: Session) -> None:
        """Test counting with no proposals."""
        repo = RuleProposalRepository(db_session)

        counts = repo.count_by_status()

        assert counts == {"pending": 0, "accepted": 0, "rejected": 0, "modified": 0}

    def test_count_multiple_statuses(self, db_session: Session) -> None:
        """Test counting with various statuses."""
        repo = RuleProposalRepository(db_session)

        repo.create(
            cluster_hash="p1", cluster_size=10, sample_descriptions="[]"
        )
        repo.create(
            cluster_hash="p2", cluster_size=10, sample_descriptions="[]"
        )
        repo.create(
            cluster_hash="a1",
            cluster_size=10,
            sample_descriptions="[]",
            status="accepted",
        )
        repo.create(
            cluster_hash="r1",
            cluster_size=10,
            sample_descriptions="[]",
            status="rejected",
        )
        db_session.flush()

        counts = repo.count_by_status()

        assert counts["pending"] == 2
        assert counts["accepted"] == 1
        assert counts["rejected"] == 1
        assert counts["modified"] == 0


class TestRuleProposalRepositoryGetAll:
    """Tests for RuleProposalRepository.get_all()."""

    def test_get_all_empty(self, db_session: Session) -> None:
        """Test get_all with no proposals."""
        repo = RuleProposalRepository(db_session)

        all_proposals = repo.get_all()

        assert len(all_proposals) == 0

    def test_get_all_multiple(self, db_session: Session) -> None:
        """Test get_all with multiple proposals."""
        repo = RuleProposalRepository(db_session)

        repo.create(
            cluster_hash="all1", cluster_size=10, sample_descriptions="[]"
        )
        repo.create(
            cluster_hash="all2", cluster_size=20, sample_descriptions="[]"
        )
        repo.create(
            cluster_hash="all3", cluster_size=30, sample_descriptions="[]"
        )
        db_session.flush()

        all_proposals = repo.get_all()

        assert len(all_proposals) == 3
