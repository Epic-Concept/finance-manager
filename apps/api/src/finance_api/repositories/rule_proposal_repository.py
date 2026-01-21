"""RuleProposalRepository for managing rule proposals."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from finance_api.models.rule_proposal import RuleProposal


class RuleProposalNotFoundError(Exception):
    """Raised when a rule proposal is not found."""

    pass


class RuleProposalRepository:
    """Repository for rule proposal CRUD operations."""

    def __init__(self, session: Session) -> None:
        """Initialize the repository with a database session.

        Args:
            session: SQLAlchemy database session.
        """
        self._session = session

    def create(
        self,
        cluster_hash: str,
        cluster_size: int,
        sample_descriptions: str,
        proposed_pattern: str | None = None,
        proposed_category_id: int | None = None,
        llm_confidence: str | None = None,
        llm_reasoning: str | None = None,
        validation_matches: int | None = None,
        validation_precision: Decimal | None = None,
        validation_false_positives: str | None = None,
        status: str = "pending",
    ) -> RuleProposal:
        """Create a new rule proposal.

        Args:
            cluster_hash: Unique hash identifying the transaction cluster.
            cluster_size: Number of transactions in the cluster.
            sample_descriptions: JSON array of sample transaction descriptions.
            proposed_pattern: Regex pattern proposed by LLM.
            proposed_category_id: Target category ID.
            llm_confidence: LLM's confidence level (high/medium/low).
            llm_reasoning: LLM's reasoning for the proposal.
            validation_matches: Total transactions matching the pattern.
            validation_precision: Precision metric (0-1).
            validation_false_positives: JSON array of false positive descriptions.
            status: Proposal status (pending/accepted/rejected/modified).

        Returns:
            The created RuleProposal.
        """
        proposal = RuleProposal(
            cluster_hash=cluster_hash,
            cluster_size=cluster_size,
            sample_descriptions=sample_descriptions,
            proposed_pattern=proposed_pattern,
            proposed_category_id=proposed_category_id,
            llm_confidence=llm_confidence,
            llm_reasoning=llm_reasoning,
            validation_matches=validation_matches,
            validation_precision=validation_precision,
            validation_false_positives=validation_false_positives,
            status=status,
        )
        self._session.add(proposal)
        self._session.flush()
        return proposal

    def get(self, proposal_id: int) -> RuleProposal:
        """Get a rule proposal by ID.

        Args:
            proposal_id: The proposal ID.

        Returns:
            The RuleProposal.

        Raises:
            RuleProposalNotFoundError: If proposal doesn't exist.
        """
        proposal = self._session.get(RuleProposal, proposal_id)
        if proposal is None:
            raise RuleProposalNotFoundError(f"Rule proposal {proposal_id} not found")
        return proposal

    def get_by_status(self, status: str) -> list[RuleProposal]:
        """Get all proposals with a specific status.

        Args:
            status: The status to filter by (pending/accepted/rejected/modified).

        Returns:
            List of RuleProposals with the specified status.
        """
        stmt = (
            select(RuleProposal)
            .where(RuleProposal.status == status)
            .order_by(RuleProposal.created_at.desc())
        )
        return list(self._session.execute(stmt).scalars().all())

    def get_pending_proposals(self) -> list[RuleProposal]:
        """Get all pending proposals for resume functionality.

        Returns:
            List of pending RuleProposals ordered by creation date.
        """
        return self.get_by_status("pending")

    def get_by_cluster_hash(self, cluster_hash: str) -> RuleProposal | None:
        """Get a proposal by cluster hash to avoid duplicates.

        Args:
            cluster_hash: The cluster hash to search for.

        Returns:
            The RuleProposal if found, None otherwise.
        """
        stmt = select(RuleProposal).where(RuleProposal.cluster_hash == cluster_hash)
        return self._session.execute(stmt).scalars().first()

    def get_all(self) -> list[RuleProposal]:
        """Get all rule proposals.

        Returns:
            List of all RuleProposals.
        """
        stmt = select(RuleProposal).order_by(RuleProposal.created_at.desc())
        return list(self._session.execute(stmt).scalars().all())

    def update_status(
        self,
        proposal_id: int,
        status: str,
        reviewer_notes: str | None = None,
        final_rule_id: int | None = None,
    ) -> RuleProposal:
        """Update the status of a proposal.

        Args:
            proposal_id: The proposal ID.
            status: New status (pending/accepted/rejected/modified).
            reviewer_notes: Optional notes from the reviewer.
            final_rule_id: Optional ID of the created classification rule.

        Returns:
            The updated RuleProposal.

        Raises:
            RuleProposalNotFoundError: If proposal doesn't exist.
        """
        proposal = self.get(proposal_id)
        proposal.status = status
        proposal.reviewed_at = datetime.utcnow()

        if reviewer_notes is not None:
            proposal.reviewer_notes = reviewer_notes
        if final_rule_id is not None:
            proposal.final_rule_id = final_rule_id

        return proposal

    def update_validation(
        self,
        proposal_id: int,
        validation_matches: int,
        validation_precision: Decimal,
        validation_false_positives: str | None = None,
    ) -> RuleProposal:
        """Update validation results for a proposal.

        Args:
            proposal_id: The proposal ID.
            validation_matches: Total transactions matching the pattern.
            validation_precision: Precision metric (0-1).
            validation_false_positives: JSON array of false positive descriptions.

        Returns:
            The updated RuleProposal.

        Raises:
            RuleProposalNotFoundError: If proposal doesn't exist.
        """
        proposal = self.get(proposal_id)
        proposal.validation_matches = validation_matches
        proposal.validation_precision = validation_precision
        if validation_false_positives is not None:
            proposal.validation_false_positives = validation_false_positives
        return proposal

    def update_pattern(
        self,
        proposal_id: int,
        proposed_pattern: str,
        proposed_category_id: int | None = None,
    ) -> RuleProposal:
        """Update the proposed pattern (for modification workflow).

        Args:
            proposal_id: The proposal ID.
            proposed_pattern: The new regex pattern.
            proposed_category_id: Optional new category ID.

        Returns:
            The updated RuleProposal.

        Raises:
            RuleProposalNotFoundError: If proposal doesn't exist.
        """
        proposal = self.get(proposal_id)
        proposal.proposed_pattern = proposed_pattern
        if proposed_category_id is not None:
            proposal.proposed_category_id = proposed_category_id
        return proposal

    def delete(self, proposal_id: int) -> None:
        """Delete a rule proposal.

        Args:
            proposal_id: The proposal ID.

        Raises:
            RuleProposalNotFoundError: If proposal doesn't exist.
        """
        proposal = self.get(proposal_id)
        self._session.delete(proposal)

    def count_by_status(self) -> dict[str, int]:
        """Get count of proposals grouped by status.

        Returns:
            Dictionary mapping status to count.
        """
        all_proposals = self.get_all()
        counts: dict[str, int] = {
            "pending": 0,
            "accepted": 0,
            "rejected": 0,
            "modified": 0,
        }
        for proposal in all_proposals:
            if proposal.status in counts:
                counts[proposal.status] += 1
        return counts
