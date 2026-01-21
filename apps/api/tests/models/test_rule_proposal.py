"""Tests for RuleProposal model."""

import json
from decimal import Decimal

from finance_api.models.rule_proposal import RuleProposal


def test_rule_proposal_creation() -> None:
    """Test RuleProposal can be instantiated with required fields."""
    proposal = RuleProposal(
        cluster_hash="abc123def456",
        cluster_size=50,
        sample_descriptions=json.dumps(["TESCO STORES 1234", "TESCO EXPRESS"]),
    )

    assert proposal.cluster_hash == "abc123def456"
    assert proposal.cluster_size == 50
    assert "TESCO STORES" in proposal.sample_descriptions


def test_rule_proposal_with_all_fields() -> None:
    """Test RuleProposal with all optional fields."""
    proposal = RuleProposal(
        cluster_hash="abc123",
        cluster_size=100,
        sample_descriptions=json.dumps(["TESCO STORES 1234"]),
        proposed_pattern="(?i)tesco",
        proposed_category_id=5,
        llm_confidence="high",
        llm_reasoning="All transactions appear to be Tesco supermarket purchases",
        validation_matches=95,
        validation_precision=Decimal("0.9800"),
        validation_false_positives=json.dumps(["TESCO BANK PAYMENT"]),
        status="pending",
    )

    assert proposal.proposed_pattern == "(?i)tesco"
    assert proposal.proposed_category_id == 5
    assert proposal.llm_confidence == "high"
    assert proposal.validation_matches == 95
    assert proposal.validation_precision == Decimal("0.9800")


def test_rule_proposal_status_pending() -> None:
    """Test RuleProposal with default pending status."""
    proposal = RuleProposal(
        cluster_hash="pending123",
        cluster_size=10,
        sample_descriptions="[]",
        status="pending",
    )

    assert proposal.status == "pending"


def test_rule_proposal_status_accepted() -> None:
    """Test RuleProposal with accepted status."""
    proposal = RuleProposal(
        cluster_hash="accepted123",
        cluster_size=10,
        sample_descriptions="[]",
        status="accepted",
        final_rule_id=42,
    )

    assert proposal.status == "accepted"
    assert proposal.final_rule_id == 42


def test_rule_proposal_status_rejected() -> None:
    """Test RuleProposal with rejected status."""
    proposal = RuleProposal(
        cluster_hash="rejected123",
        cluster_size=10,
        sample_descriptions="[]",
        status="rejected",
        reviewer_notes="Too many false positives",
    )

    assert proposal.status == "rejected"
    assert proposal.reviewer_notes == "Too many false positives"


def test_rule_proposal_status_modified() -> None:
    """Test RuleProposal with modified status."""
    proposal = RuleProposal(
        cluster_hash="modified123",
        cluster_size=10,
        sample_descriptions="[]",
        status="modified",
        reviewer_notes="Pattern adjusted to be more specific",
    )

    assert proposal.status == "modified"


def test_rule_proposal_with_reviewer_notes() -> None:
    """Test RuleProposal with reviewer notes."""
    proposal = RuleProposal(
        cluster_hash="notes123",
        cluster_size=10,
        sample_descriptions="[]",
        reviewer_notes="Adjusted pattern from '(?i)tesco' to '(?i)tesco\\s+store'",
    )

    assert "Adjusted pattern" in proposal.reviewer_notes


def test_rule_proposal_validation_precision() -> None:
    """Test RuleProposal with various precision values."""
    proposal_perfect = RuleProposal(
        cluster_hash="perfect123",
        cluster_size=100,
        sample_descriptions="[]",
        validation_precision=Decimal("1.0000"),
    )
    assert proposal_perfect.validation_precision == Decimal("1.0000")

    proposal_low = RuleProposal(
        cluster_hash="low123",
        cluster_size=100,
        sample_descriptions="[]",
        validation_precision=Decimal("0.5000"),
    )
    assert proposal_low.validation_precision == Decimal("0.5000")


def test_rule_proposal_sample_descriptions_json() -> None:
    """Test RuleProposal stores sample descriptions as JSON."""
    samples = [
        "TESCO STORES 1234",
        "TESCO EXPRESS",
        "TESCO EXTRA",
    ]
    proposal = RuleProposal(
        cluster_hash="json123",
        cluster_size=len(samples),
        sample_descriptions=json.dumps(samples),
    )

    parsed = json.loads(proposal.sample_descriptions)
    assert len(parsed) == 3
    assert "TESCO STORES 1234" in parsed


def test_rule_proposal_false_positives_json() -> None:
    """Test RuleProposal stores false positives as JSON."""
    false_positives = ["TESCO BANK PAYMENT", "TESCO MOBILE"]
    proposal = RuleProposal(
        cluster_hash="fp123",
        cluster_size=50,
        sample_descriptions="[]",
        validation_false_positives=json.dumps(false_positives),
    )

    parsed = json.loads(proposal.validation_false_positives)
    assert len(parsed) == 2


def test_rule_proposal_repr() -> None:
    """Test RuleProposal string representation."""
    proposal = RuleProposal(
        id=1,
        cluster_hash="abc123def456abc123def456abc123def456abc123def456abc123def456abc1",
        cluster_size=50,
        sample_descriptions="[]",
        status="pending",
    )

    result = repr(proposal)
    assert "RuleProposal" in result
    assert "id=1" in result
    assert "abc123de..." in result  # truncated hash
    assert "pending" in result


def test_rule_proposal_table_name() -> None:
    """Test RuleProposal table configuration."""
    assert RuleProposal.__tablename__ == "rule_proposals"
    assert RuleProposal.__table_args__[2]["schema"] == "finance"


def test_rule_proposal_confidence_levels() -> None:
    """Test RuleProposal with different confidence levels."""
    high = RuleProposal(
        cluster_hash="high123",
        cluster_size=10,
        sample_descriptions="[]",
        llm_confidence="high",
    )
    assert high.llm_confidence == "high"

    medium = RuleProposal(
        cluster_hash="medium123",
        cluster_size=10,
        sample_descriptions="[]",
        llm_confidence="medium",
    )
    assert medium.llm_confidence == "medium"

    low = RuleProposal(
        cluster_hash="low123",
        cluster_size=10,
        sample_descriptions="[]",
        llm_confidence="low",
    )
    assert low.llm_confidence == "low"
