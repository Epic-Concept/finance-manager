"""RefinementSessionRepository for managing interactive refinement sessions."""

import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from finance_api.models.refinement_session import RefinementSession
from finance_api.models.session_message import SessionMessage
from finance_api.models.session_rule_proposal import SessionRuleProposal


class RefinementSessionNotFoundError(Exception):
    """Raised when a refinement session is not found."""

    pass


class SessionProposalNotFoundError(Exception):
    """Raised when a session rule proposal is not found."""

    pass


class RefinementSessionRepository:
    """Repository for refinement session CRUD operations."""

    def __init__(self, session: Session) -> None:
        """Initialize the repository with a database session.

        Args:
            session: SQLAlchemy database session.
        """
        self._session = session

    def create(
        self,
        cluster_hash: str,
        cluster_key: str,
        cluster_size: int,
        sample_descriptions: list[str],
    ) -> RefinementSession:
        """Create a new refinement session.

        Args:
            cluster_hash: Unique hash identifying the transaction cluster.
            cluster_key: Human-readable cluster key (e.g., merchant name).
            cluster_size: Number of transactions in the cluster.
            sample_descriptions: List of sample transaction descriptions.

        Returns:
            The created RefinementSession.
        """
        session = RefinementSession(
            cluster_hash=cluster_hash,
            cluster_key=cluster_key,
            cluster_size=cluster_size,
            sample_descriptions=json.dumps(sample_descriptions),
            status="active",
        )
        self._session.add(session)
        self._session.flush()
        return session

    def get(self, session_id: int) -> RefinementSession:
        """Get a refinement session by ID.

        Args:
            session_id: The session ID.

        Returns:
            The RefinementSession.

        Raises:
            RefinementSessionNotFoundError: If session doesn't exist.
        """
        session = self._session.get(RefinementSession, session_id)
        if session is None:
            raise RefinementSessionNotFoundError(
                f"Refinement session {session_id} not found"
            )
        return session

    def get_with_relations(self, session_id: int) -> RefinementSession:
        """Get a refinement session with messages and proposals loaded.

        Args:
            session_id: The session ID.

        Returns:
            The RefinementSession with relations loaded.

        Raises:
            RefinementSessionNotFoundError: If session doesn't exist.
        """
        stmt = (
            select(RefinementSession)
            .where(RefinementSession.id == session_id)
            .options(
                joinedload(RefinementSession.messages),
                joinedload(RefinementSession.proposals).joinedload(
                    SessionRuleProposal.proposed_category
                ),
            )
        )
        session = self._session.execute(stmt).unique().scalars().first()
        if session is None:
            raise RefinementSessionNotFoundError(
                f"Refinement session {session_id} not found"
            )
        return session

    def get_by_cluster_hash(
        self, cluster_hash: str, active_only: bool = True
    ) -> RefinementSession | None:
        """Get a session by cluster hash.

        Args:
            cluster_hash: The cluster hash to search for.
            active_only: If True, only return active sessions.

        Returns:
            The RefinementSession if found, None otherwise.
        """
        stmt = select(RefinementSession).where(
            RefinementSession.cluster_hash == cluster_hash
        )
        if active_only:
            stmt = stmt.where(RefinementSession.status == "active")
        return self._session.execute(stmt).scalars().first()

    def get_all(self, status: str | None = None) -> list[RefinementSession]:
        """Get all refinement sessions, optionally filtered by status.

        Args:
            status: Optional status filter (active/completed/skipped).

        Returns:
            List of RefinementSessions.
        """
        stmt = select(RefinementSession).order_by(RefinementSession.created_at.desc())
        if status is not None:
            stmt = stmt.where(RefinementSession.status == status)
        return list(self._session.execute(stmt).scalars().all())

    def add_message(
        self,
        session_id: int,
        role: str,
        content: str,
        proposed_rules: list[dict[str, Any]] | None = None,
    ) -> SessionMessage:
        """Add a message to a session's conversation.

        Args:
            session_id: The session ID.
            role: Message role (user/assistant/system).
            content: Message content.
            proposed_rules: Optional list of proposed rules (for assistant messages).

        Returns:
            The created SessionMessage.

        Raises:
            RefinementSessionNotFoundError: If session doesn't exist.
        """
        # Verify session exists
        self.get(session_id)

        message = SessionMessage(
            session_id=session_id,
            role=role,
            content=content,
            proposed_rules_json=json.dumps(proposed_rules) if proposed_rules else None,
        )
        self._session.add(message)
        self._session.flush()
        return message

    def get_conversation(self, session_id: int) -> list[SessionMessage]:
        """Get all messages in a session's conversation.

        Args:
            session_id: The session ID.

        Returns:
            List of SessionMessages ordered by creation time.

        Raises:
            RefinementSessionNotFoundError: If session doesn't exist.
        """
        # Verify session exists
        self.get(session_id)

        stmt = (
            select(SessionMessage)
            .where(SessionMessage.session_id == session_id)
            .order_by(SessionMessage.created_at)
        )
        return list(self._session.execute(stmt).scalars().all())

    def add_proposal(
        self,
        session_id: int,
        proposed_pattern: str,
        proposed_category_id: int | None,
        proposed_category_name: str,
        llm_confidence: str,
        llm_reasoning: str,
        validation_matches: int | None = None,
        validation_precision: float | None = None,
        validation_true_positives: int | None = None,
        validation_false_positives: int | None = None,
        sample_false_positives: list[str] | None = None,
    ) -> SessionRuleProposal:
        """Add a rule proposal to a session.

        Args:
            session_id: The session ID.
            proposed_pattern: The proposed regex pattern.
            proposed_category_id: The proposed category ID.
            proposed_category_name: The proposed category name.
            llm_confidence: LLM confidence level (high/medium/low).
            llm_reasoning: LLM reasoning for the proposal.
            validation_matches: Number of matches in validation.
            validation_precision: Precision of the pattern.
            validation_true_positives: Number of true positives.
            validation_false_positives: Number of false positives.
            sample_false_positives: Sample false positive descriptions.

        Returns:
            The created SessionRuleProposal.

        Raises:
            RefinementSessionNotFoundError: If session doesn't exist.
        """
        import json

        # Verify session exists
        self.get(session_id)

        proposal = SessionRuleProposal(
            session_id=session_id,
            proposed_pattern=proposed_pattern,
            proposed_category_id=proposed_category_id,
            proposed_category_name=proposed_category_name,
            llm_confidence=llm_confidence,
            llm_reasoning=llm_reasoning,
            validation_matches=validation_matches,
            validation_precision=validation_precision,
            validation_true_positives=validation_true_positives,
            validation_false_positives=validation_false_positives,
            validation_false_positives_json=(
                json.dumps(sample_false_positives) if sample_false_positives else None
            ),
            status="pending",
        )
        self._session.add(proposal)
        self._session.flush()
        return proposal

    def get_proposal(self, proposal_id: int) -> SessionRuleProposal:
        """Get a session rule proposal by ID.

        Args:
            proposal_id: The proposal ID.

        Returns:
            The SessionRuleProposal.

        Raises:
            SessionProposalNotFoundError: If proposal doesn't exist.
        """
        proposal = self._session.get(SessionRuleProposal, proposal_id)
        if proposal is None:
            raise SessionProposalNotFoundError(
                f"Session rule proposal {proposal_id} not found"
            )
        return proposal

    def get_session_proposals(self, session_id: int) -> list[SessionRuleProposal]:
        """Get all proposals in a session.

        Args:
            session_id: The session ID.

        Returns:
            List of SessionRuleProposals.

        Raises:
            RefinementSessionNotFoundError: If session doesn't exist.
        """
        # Verify session exists
        self.get(session_id)

        stmt = (
            select(SessionRuleProposal)
            .where(SessionRuleProposal.session_id == session_id)
            .order_by(SessionRuleProposal.created_at)
        )
        return list(self._session.execute(stmt).scalars().all())

    def update_proposal_validation(
        self,
        proposal_id: int,
        matches: int,
        true_positives: int,
        false_positives: int,
        precision: Decimal,
        coverage: Decimal,
        false_positives_json: str | None = None,
    ) -> SessionRuleProposal:
        """Update validation results for a proposal.

        Args:
            proposal_id: The proposal ID.
            matches: Total transactions matching the pattern.
            true_positives: Matches within the target cluster.
            false_positives: Matches outside the target cluster.
            precision: Precision metric (0-1).
            coverage: Coverage metric (0-1).
            false_positives_json: JSON array of false positive descriptions.

        Returns:
            The updated SessionRuleProposal.

        Raises:
            SessionProposalNotFoundError: If proposal doesn't exist.
        """
        proposal = self.get_proposal(proposal_id)
        proposal.validation_matches = matches
        proposal.validation_true_positives = true_positives
        proposal.validation_false_positives = false_positives
        proposal.validation_precision = precision
        proposal.validation_coverage = coverage
        if false_positives_json is not None:
            proposal.validation_false_positives_json = false_positives_json
        return proposal

    def accept_proposal(
        self, proposal_id: int, final_rule_id: int
    ) -> SessionRuleProposal:
        """Accept a proposal and link it to the created rule.

        Args:
            proposal_id: The proposal ID.
            final_rule_id: The ID of the created classification rule.

        Returns:
            The updated SessionRuleProposal.

        Raises:
            SessionProposalNotFoundError: If proposal doesn't exist.
        """
        proposal = self.get_proposal(proposal_id)
        proposal.status = "accepted"
        proposal.final_rule_id = final_rule_id
        proposal.reviewed_at = datetime.utcnow()
        return proposal

    def reject_proposal(self, proposal_id: int) -> SessionRuleProposal:
        """Reject a proposal.

        Args:
            proposal_id: The proposal ID.

        Returns:
            The updated SessionRuleProposal.

        Raises:
            SessionProposalNotFoundError: If proposal doesn't exist.
        """
        proposal = self.get_proposal(proposal_id)
        proposal.status = "rejected"
        proposal.reviewed_at = datetime.utcnow()
        return proposal

    def complete_session(self, session_id: int) -> RefinementSession:
        """Mark a session as completed.

        Args:
            session_id: The session ID.

        Returns:
            The updated RefinementSession.

        Raises:
            RefinementSessionNotFoundError: If session doesn't exist.
        """
        session = self.get(session_id)
        session.status = "completed"
        session.completed_at = datetime.utcnow()
        return session

    def skip_session(self, session_id: int) -> RefinementSession:
        """Mark a session as skipped for individual treatment.

        Args:
            session_id: The session ID.

        Returns:
            The updated RefinementSession.

        Raises:
            RefinementSessionNotFoundError: If session doesn't exist.
        """
        session = self.get(session_id)
        session.status = "skipped"
        session.completed_at = datetime.utcnow()
        return session

    def delete_session(self, session_id: int) -> None:
        """Delete a refinement session and all related data.

        Args:
            session_id: The session ID.

        Raises:
            RefinementSessionNotFoundError: If session doesn't exist.
        """
        session = self.get(session_id)
        self._session.delete(session)
