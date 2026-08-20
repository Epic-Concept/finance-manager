"""Cohort review API: group pending decisions, confirm/skip as a group."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from finance_api.classification.cel import CelEvaluator, activation_from_transaction
from finance_api.classification.cohorts import (
    CohortDiscovery,
    CohortProposal,
    pending_review_transactions,
)
from finance_api.classification.review import ReviewService
from finance_api.db.session import get_db

router = APIRouter()


class CohortResponse(BaseModel):
    cohort_id: str
    stage: str
    cluster_key: str
    expression: str
    transaction_ids: list[int]
    sample_descriptions: list[str]
    labelled_false_positives: int
    source: str
    size: int


class CohortListResponse(BaseModel):
    items: list[CohortResponse]
    singletons: list[int]


class ResolveCohortRequest(BaseModel):
    action: str  # confirm | skip
    category_id: int | None = None
    expression: str | None = None


class ResolveCohortResponse(BaseModel):
    cohort_id: str
    action: str
    resolved: int


def _to_response(proposal: CohortProposal) -> CohortResponse:
    return CohortResponse(
        cohort_id=proposal.cohort_id,
        stage=proposal.stage,
        cluster_key=proposal.cluster_key,
        expression=proposal.expression,
        transaction_ids=list(proposal.transaction_ids),
        sample_descriptions=list(proposal.sample_descriptions),
        labelled_false_positives=proposal.labelled_false_positives,
        source=proposal.source,
        size=len(proposal.transaction_ids),
    )


@router.get("", response_model=CohortListResponse)
def list_cohorts(db: Annotated[Session, Depends(get_db)]) -> CohortListResponse:
    pending = pending_review_transactions(db)
    discovery = CohortDiscovery(pending, pending, min_size=2)
    proposals = discovery.proposals()
    leftovers = discovery.leftovers()
    return CohortListResponse(
        items=[_to_response(p) for p in proposals],
        singletons=[int(t.id) for t in leftovers],
    )


@router.post("/{cohort_id}/resolve", response_model=ResolveCohortResponse)
def resolve_cohort(
    cohort_id: str,
    payload: ResolveCohortRequest,
    db: Annotated[Session, Depends(get_db)],
) -> ResolveCohortResponse:
    pending = pending_review_transactions(db)
    discovery = CohortDiscovery(pending, pending, min_size=2)
    proposals = {p.cohort_id: p for p in discovery.proposals()}
    proposal = proposals.get(cohort_id)
    if proposal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="cohort not found"
        )
    if payload.action == "skip":
        discovery.skip(proposal)
        db.commit()
        return ResolveCohortResponse(cohort_id=cohort_id, action="skip", resolved=0)

    if payload.action not in {"confirm", "change"} or payload.category_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="confirm/change requires category_id",
        )

    expression = payload.expression or proposal.expression
    discovery.confirm(db, proposal, payload.category_id)
    evaluator = CelEvaluator()
    review = ReviewService(db)
    resolved = 0
    pending_by_txn = {item.transaction_id: item for item in review.list_pending()}
    id_set = set(proposal.transaction_ids)
    for txn in pending:
        if txn.id not in id_set:
            continue
        if evaluator.matches(expression, activation_from_transaction(txn)) is not True:
            continue
        item = pending_by_txn.get(txn.id)
        if item is None:
            continue
        review.resolve(item.decision_id, payload.category_id)
        resolved += 1
    db.commit()
    return ResolveCohortResponse(
        cohort_id=cohort_id, action=payload.action, resolved=resolved
    )
