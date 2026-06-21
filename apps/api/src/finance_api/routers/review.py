"""FastAPI router for the classification review queue."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from finance_api.classification.review import ReviewService
from finance_api.db.session import get_db
from finance_api.schemas.review import (
    EvidenceResponse,
    ResolveRequest,
    ResolveResponse,
    ReviewItemResponse,
    ReviewListResponse,
)

router = APIRouter()


@router.get("", response_model=ReviewListResponse)
def list_reviews(db: Annotated[Session, Depends(get_db)]) -> ReviewListResponse:
    """List pending review items with their proposed categorization and evidence."""
    items = ReviewService(db).list_pending()
    return ReviewListResponse(
        items=[
            ReviewItemResponse(
                decision_id=item.decision_id,
                transaction_id=item.transaction_id,
                description=item.description,
                amount=item.amount,
                proposed_category_id=item.proposed_category_id,
                strength=item.strength,
                reason=item.reason,
                evidence=[
                    EvidenceResponse(
                        evidence_type=e.evidence_type,
                        source=e.source,
                        strength=e.strength,
                    )
                    for e in item.evidence
                ],
            )
            for item in items
        ]
    )


@router.post("/{decision_id}/resolve", response_model=ResolveResponse)
def resolve_review(
    decision_id: int,
    payload: ResolveRequest,
    db: Annotated[Session, Depends(get_db)],
) -> ResolveResponse:
    """Resolve a review (confirm / reclassify / mark internal-transfer)."""
    try:
        decision = ReviewService(db).resolve(decision_id, payload.category_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    db.commit()
    return ResolveResponse(
        decision_id=decision.id,
        confirmed=decision.confirmed,
        category_id=payload.category_id,
    )
