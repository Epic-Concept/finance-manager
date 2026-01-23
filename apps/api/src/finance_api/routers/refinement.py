"""FastAPI router for interactive refinement endpoints."""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from finance_api.db.session import get_db
from finance_api.models.transaction import Transaction
from finance_api.repositories.category_repository import CategoryRepository
from finance_api.repositories.classification_rule_repository import (
    ClassificationRuleRepository,
)
from finance_api.repositories.refinement_session_repository import (
    RefinementSessionNotFoundError,
    RefinementSessionRepository,
    SessionProposalNotFoundError,
)
from finance_api.schemas.refinement import (
    ClusterListResponse,
    ClusterResponse,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
    ProposalActionRequest,
    ProposalResponse,
    ProposedRuleResponse,
    SessionCreate,
    SessionListResponse,
    SessionResponse,
    ValidationResultResponse,
)
from finance_api.services.interactive_refinement_service import (
    InteractiveRefinementService,
)
from finance_api.services.transaction_clustering_service import (
    TransactionCluster,
    TransactionClusteringService,
)

router = APIRouter()


def get_session_repo(
    db: Session = Depends(get_db),  # noqa: B008
) -> RefinementSessionRepository:
    """Get refinement session repository."""
    return RefinementSessionRepository(db)


def get_category_repo(
    db: Session = Depends(get_db),  # noqa: B008
) -> CategoryRepository:
    """Get category repository."""
    return CategoryRepository(db)


def get_rule_repo(
    db: Session = Depends(get_db),  # noqa: B008
) -> ClassificationRuleRepository:
    """Get classification rule repository."""
    return ClassificationRuleRepository(db)


def get_refinement_service() -> InteractiveRefinementService:
    """Get interactive refinement service."""
    return InteractiveRefinementService()


def get_clustering_service() -> TransactionClusteringService:
    """Get transaction clustering service."""
    return TransactionClusteringService()


# --- Session Endpoints ---


@router.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    request: SessionCreate,
    db: Annotated[Session, Depends(get_db)],
    session_repo: Annotated[RefinementSessionRepository, Depends(get_session_repo)],
    category_repo: Annotated[CategoryRepository, Depends(get_category_repo)],
    refinement_service: Annotated[
        InteractiveRefinementService, Depends(get_refinement_service)
    ],
    clustering_service: Annotated[
        TransactionClusteringService, Depends(get_clustering_service)
    ],
) -> SessionResponse:
    """Create a new refinement session for a cluster.

    If an active session already exists for the cluster, returns that session.
    """
    # Check for existing active session
    existing = session_repo.get_by_cluster_hash(request.cluster_hash, active_only=True)
    if existing:
        return _session_to_response(existing)

    # Get uncategorized transactions and cluster them
    uncategorized = list(
        db.query(Transaction).filter(Transaction.assigned_category_id.is_(None)).all()
    )

    if not uncategorized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No uncategorized transactions available",
        )

    clusters = clustering_service.cluster_transactions(uncategorized)

    # Find the requested cluster
    cluster = next(
        (c for c in clusters if c.cluster_hash == request.cluster_hash),
        None,
    )
    if cluster is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cluster {request.cluster_hash} not found",
        )

    # Create session
    session = session_repo.create(
        cluster_hash=cluster.cluster_hash,
        cluster_key=cluster.cluster_key,
        cluster_size=len(cluster.transactions),
        sample_descriptions=cluster.sample_descriptions,
    )

    # Get categories and generate initial proposal
    categories = category_repo.get_all_leaf_categories()

    response = refinement_service.start_session(cluster, categories)

    # Store initial assistant message
    proposed_rules_data = [
        {
            "pattern": r.pattern,
            "category_id": r.category_id,
            "category_name": r.category_name,
            "confidence": r.confidence,
            "reasoning": r.reasoning,
        }
        for r in response.proposals
    ]
    session_repo.add_message(
        session.id,
        "assistant",
        response.message,
        proposed_rules=proposed_rules_data,
    )

    # Store proposals and validate them
    all_transactions = list(db.query(Transaction).all())
    cluster_ids = {t.id for t in cluster.transactions}

    for rule in response.proposals:
        proposal = session_repo.add_proposal(
            session_id=session.id,
            proposed_pattern=rule.pattern,
            proposed_category_id=rule.category_id,
            proposed_category_name=rule.category_name,
            llm_confidence=rule.confidence,
            llm_reasoning=rule.reasoning,
        )

        # Validate proposal
        validation_results = refinement_service.validate_proposals(
            [rule], all_transactions, cluster_ids
        )
        if validation_results:
            _, validation = validation_results[0]
            session_repo.update_proposal_validation(
                proposal.id,
                matches=validation.total_matches,
                true_positives=validation.true_positives,
                false_positives=validation.false_positives,
                precision=validation.precision,
                coverage=validation.coverage,
                false_positives_json=(
                    json.dumps(validation.sample_false_positives)
                    if validation.sample_false_positives
                    else None
                ),
            )

    # Add validation feedback as system message
    if response.proposals:
        validation_results = refinement_service.validate_proposals(
            response.proposals, all_transactions, cluster_ids
        )
        feedback = refinement_service.format_validation_feedback(validation_results)
        session_repo.add_message(session.id, "system", feedback)

    db.commit()

    return _session_to_response(session_repo.get_with_relations(session.id))


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    session_repo: Annotated[RefinementSessionRepository, Depends(get_session_repo)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    skip: int = 0,
    limit: int = 20,
) -> SessionListResponse:
    """List refinement sessions with optional filtering."""
    sessions = session_repo.get_all(status=status_filter)
    total = len(sessions)
    sessions = sessions[skip : skip + limit]

    return SessionListResponse(
        sessions=[_session_to_response(s) for s in sessions],
        total=total,
    )


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: int,
    session_repo: Annotated[RefinementSessionRepository, Depends(get_session_repo)],
) -> SessionResponse:
    """Get session details."""
    try:
        session = session_repo.get_with_relations(session_id)
        return _session_to_response(session)
    except RefinementSessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        ) from None


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: int,
    db: Annotated[Session, Depends(get_db)],
    session_repo: Annotated[RefinementSessionRepository, Depends(get_session_repo)],
) -> None:
    """Delete/cancel a refinement session."""
    try:
        session_repo.delete_session(session_id)
        db.commit()
    except RefinementSessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        ) from None


# --- Message Endpoints ---


@router.post("/sessions/{session_id}/messages", response_model=MessageResponse)
async def send_message(
    session_id: int,
    request: MessageCreate,
    db: Annotated[Session, Depends(get_db)],
    session_repo: Annotated[RefinementSessionRepository, Depends(get_session_repo)],
    category_repo: Annotated[CategoryRepository, Depends(get_category_repo)],
    refinement_service: Annotated[
        InteractiveRefinementService, Depends(get_refinement_service)
    ],
    clustering_service: Annotated[
        TransactionClusteringService, Depends(get_clustering_service)
    ],
) -> MessageResponse:
    """Send a message and get LLM response with proposals."""
    try:
        session = session_repo.get_with_relations(session_id)
    except RefinementSessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        ) from None

    if session.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session is {session.status}, cannot send messages",
        )

    # Store user message
    session_repo.add_message(session_id, "user", request.content)

    # Build conversation history
    messages = session_repo.get_conversation(session_id)
    history = [
        {"role": m.role, "content": m.content} for m in messages if m.role != "system"
    ]

    # Reconstruct cluster
    cluster = TransactionCluster(
        cluster_key=session.cluster_key,
        cluster_hash=session.cluster_hash,
        transactions=[],  # We don't need actual transactions for LLM
        sample_descriptions=json.loads(session.sample_descriptions),
    )

    # Get categories and continue conversation
    categories = category_repo.get_all_leaf_categories()
    response = refinement_service.continue_session(
        history, request.content, cluster, categories
    )

    # Store assistant response
    proposed_rules_data = [
        {
            "pattern": r.pattern,
            "category_id": r.category_id,
            "category_name": r.category_name,
            "confidence": r.confidence,
            "reasoning": r.reasoning,
        }
        for r in response.proposals
    ]
    assistant_msg = session_repo.add_message(
        session_id,
        "assistant",
        response.message,
        proposed_rules=proposed_rules_data,
    )

    # Store new proposals if any
    if response.proposals:
        # Get transactions for validation
        all_transactions = list(db.query(Transaction).all())
        uncategorized = [t for t in all_transactions if t.assigned_category_id is None]
        clusters = clustering_service.cluster_transactions(uncategorized)
        cluster_full = next(
            (c for c in clusters if c.cluster_hash == session.cluster_hash),
            None,
        )
        cluster_ids = (
            {t.id for t in cluster_full.transactions} if cluster_full else set()
        )

        for rule in response.proposals:
            proposal = session_repo.add_proposal(
                session_id=session_id,
                proposed_pattern=rule.pattern,
                proposed_category_id=rule.category_id,
                proposed_category_name=rule.category_name,
                llm_confidence=rule.confidence,
                llm_reasoning=rule.reasoning,
            )

            # Validate
            validation_results = refinement_service.validate_proposals(
                [rule], all_transactions, cluster_ids
            )
            if validation_results:
                _, validation = validation_results[0]
                session_repo.update_proposal_validation(
                    proposal.id,
                    matches=validation.total_matches,
                    true_positives=validation.true_positives,
                    false_positives=validation.false_positives,
                    precision=validation.precision,
                    coverage=validation.coverage,
                    false_positives_json=(
                        json.dumps(validation.sample_false_positives)
                        if validation.sample_false_positives
                        else None
                    ),
                )

        # Add validation feedback
        validation_results = refinement_service.validate_proposals(
            response.proposals, all_transactions, cluster_ids
        )
        feedback = refinement_service.format_validation_feedback(validation_results)
        session_repo.add_message(session_id, "system", feedback)

    db.commit()

    return _message_to_response(assistant_msg)


@router.get("/sessions/{session_id}/messages", response_model=ConversationResponse)
async def get_conversation(
    session_id: int,
    session_repo: Annotated[RefinementSessionRepository, Depends(get_session_repo)],
) -> ConversationResponse:
    """Get full conversation history."""
    try:
        messages = session_repo.get_conversation(session_id)
        return ConversationResponse(
            session_id=session_id,
            messages=[_message_to_response(m) for m in messages],
        )
    except RefinementSessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        ) from None


# --- Proposal Endpoints ---


@router.get("/sessions/{session_id}/proposals", response_model=list[ProposalResponse])
async def list_proposals(
    session_id: int,
    session_repo: Annotated[RefinementSessionRepository, Depends(get_session_repo)],
    category_repo: Annotated[CategoryRepository, Depends(get_category_repo)],
) -> list[ProposalResponse]:
    """List all proposals in a session."""
    try:
        proposals = session_repo.get_session_proposals(session_id)
        return [_proposal_to_response(p, category_repo) for p in proposals]
    except RefinementSessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        ) from None


@router.post(
    "/sessions/{session_id}/proposals/{proposal_id}/accept",
    response_model=ProposalResponse,
)
async def accept_proposal(
    session_id: int,
    proposal_id: int,
    request: ProposalActionRequest,
    db: Annotated[Session, Depends(get_db)],
    session_repo: Annotated[RefinementSessionRepository, Depends(get_session_repo)],
    category_repo: Annotated[CategoryRepository, Depends(get_category_repo)],
    rule_repo: Annotated[ClassificationRuleRepository, Depends(get_rule_repo)],
) -> ProposalResponse:
    """Accept a proposal and create a classification rule."""
    try:
        proposal = session_repo.get_proposal(proposal_id)
    except SessionProposalNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposal {proposal_id} not found",
        ) from None

    if proposal.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Proposal does not belong to this session",
        )

    if proposal.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Proposal is already {proposal.status}",
        )

    # Create classification rule from proposal
    rule = rule_repo.create(
        name=f"Rule from proposal {proposal_id}",
        rule_expression=f'description =~ "{proposal.proposed_pattern}"',
        category_id=proposal.proposed_category_id,
        priority=100,
    )
    db.flush()

    # Mark proposal as accepted with the rule reference
    session_repo.accept_proposal(
        proposal_id=proposal_id,
        final_rule_id=rule.id,
    )
    db.commit()

    return _proposal_to_response(session_repo.get_proposal(proposal_id), category_repo)


@router.post(
    "/sessions/{session_id}/proposals/{proposal_id}/reject",
    response_model=ProposalResponse,
)
async def reject_proposal(
    session_id: int,
    proposal_id: int,
    request: ProposalActionRequest,
    db: Annotated[Session, Depends(get_db)],
    session_repo: Annotated[RefinementSessionRepository, Depends(get_session_repo)],
    category_repo: Annotated[CategoryRepository, Depends(get_category_repo)],
) -> ProposalResponse:
    """Reject a proposal."""
    try:
        proposal = session_repo.get_proposal(proposal_id)
    except SessionProposalNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposal {proposal_id} not found",
        ) from None

    if proposal.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Proposal does not belong to this session",
        )

    if proposal.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Proposal is already {proposal.status}",
        )

    session_repo.reject_proposal(proposal_id)
    db.commit()

    return _proposal_to_response(session_repo.get_proposal(proposal_id), category_repo)


# --- Action Endpoints ---


@router.post("/sessions/{session_id}/actions/complete", response_model=SessionResponse)
async def complete_session(
    session_id: int,
    db: Annotated[Session, Depends(get_db)],
    session_repo: Annotated[RefinementSessionRepository, Depends(get_session_repo)],
) -> SessionResponse:
    """Mark session as completed."""
    try:
        session_repo.complete_session(session_id)
        db.commit()
        return _session_to_response(session_repo.get_with_relations(session_id))
    except RefinementSessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        ) from None


@router.post("/sessions/{session_id}/actions/skip", response_model=SessionResponse)
async def skip_session(
    session_id: int,
    db: Annotated[Session, Depends(get_db)],
    session_repo: Annotated[RefinementSessionRepository, Depends(get_session_repo)],
) -> SessionResponse:
    """Skip session for individual treatment."""
    try:
        session_repo.skip_session(session_id)
        db.commit()
        return _session_to_response(session_repo.get_with_relations(session_id))
    except RefinementSessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        ) from None


# --- Cluster Endpoints ---


@router.get("/clusters", response_model=ClusterListResponse)
async def list_clusters(
    db: Annotated[Session, Depends(get_db)],
    session_repo: Annotated[RefinementSessionRepository, Depends(get_session_repo)],
    clustering_service: Annotated[
        TransactionClusteringService, Depends(get_clustering_service)
    ],
    min_size: int = Query(default=3, ge=1),
) -> ClusterListResponse:
    """List clusters available for refinement."""
    # Get uncategorized transactions (those without a TransactionCategory link)
    from finance_api.models.transaction_category import TransactionCategory

    uncategorized = list(
        db.query(Transaction)
        .outerjoin(
            TransactionCategory, Transaction.id == TransactionCategory.transaction_id
        )
        .filter(TransactionCategory.id.is_(None))
        .all()
    )

    if not uncategorized:
        return ClusterListResponse(clusters=[], total=0)

    # Cluster transactions
    clusters = clustering_service.cluster_transactions(uncategorized)

    # Filter by minimum size
    clusters = [c for c in clusters if len(c.transactions) >= min_size]

    # Get active sessions for each cluster
    responses = []
    for cluster in clusters:
        active_session = session_repo.get_by_cluster_hash(
            cluster.cluster_hash, active_only=True
        )
        responses.append(
            ClusterResponse(
                cluster_hash=cluster.cluster_hash,
                cluster_key=cluster.cluster_key,
                size=len(cluster.transactions),
                sample_descriptions=cluster.sample_descriptions,
                has_active_session=active_session is not None,
                active_session_id=active_session.id if active_session else None,
            )
        )

    return ClusterListResponse(clusters=responses, total=len(responses))


# --- Helper Functions ---


def _session_to_response(session) -> SessionResponse:
    """Convert session model to response schema."""
    return SessionResponse(
        id=session.id,
        cluster_hash=session.cluster_hash,
        cluster_key=session.cluster_key,
        cluster_size=session.cluster_size,
        sample_descriptions=json.loads(session.sample_descriptions),
        status=session.status,
        created_at=session.created_at,
        updated_at=session.updated_at,
        completed_at=session.completed_at,
        message_count=len(session.messages) if hasattr(session, "messages") else 0,
        proposal_count=len(session.proposals) if hasattr(session, "proposals") else 0,
    )


def _message_to_response(message) -> MessageResponse:
    """Convert message model to response schema."""
    proposed_rules = None
    if message.proposed_rules_json:
        rules_data = json.loads(message.proposed_rules_json)
        proposed_rules = [
            ProposedRuleResponse(
                pattern=r["pattern"],
                category_id=r["category_id"],
                category_name=r["category_name"],
                confidence=r["confidence"],
                reasoning=r["reasoning"],
            )
            for r in rules_data
        ]

    return MessageResponse(
        id=message.id,
        role=message.role,
        content=message.content,
        proposed_rules=proposed_rules,
        created_at=message.created_at,
    )


def _proposal_to_response(
    proposal, category_repo: CategoryRepository
) -> ProposalResponse:
    """Convert proposal model to response schema."""
    # Get category name
    category_name = proposal.proposed_category_name
    if not category_name and proposal.proposed_category_id:
        try:
            category = category_repo.get(proposal.proposed_category_id)
            category_name = category.name
        except Exception:
            category_name = "Unknown"

    # Build validation response if available
    validation = None
    if proposal.validation_matches is not None:
        false_positives_list = []
        if proposal.validation_false_positives_json:
            false_positives_list = json.loads(proposal.validation_false_positives_json)

        validation = ValidationResultResponse(
            total_matches=proposal.validation_matches,
            true_positives=proposal.validation_true_positives or 0,
            false_positives=proposal.validation_false_positives or 0,
            precision=proposal.validation_precision or 0,
            coverage=proposal.validation_coverage or 0,
            sample_true_positives=[],
            sample_false_positives=false_positives_list,
            is_valid_regex=True,
            regex_error=None,
        )

    return ProposalResponse(
        id=proposal.id,
        proposed_pattern=proposal.proposed_pattern,
        proposed_category_id=proposal.proposed_category_id,
        proposed_category_name=category_name or "Unknown",
        llm_confidence=proposal.llm_confidence,
        llm_reasoning=proposal.llm_reasoning,
        validation=validation,
        status=proposal.status,
        created_at=proposal.created_at,
        reviewed_at=proposal.reviewed_at,
    )
