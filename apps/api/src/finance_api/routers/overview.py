"""Overview stats and active CEL rules for the Quiet Ledger cockpit."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from finance_api.classification.cohorts import (
    CohortDiscovery,
    pending_review_transactions,
)
from finance_api.classification.policy import Outcome
from finance_api.db.session import get_db
from finance_api.models.classification_decision import ClassificationDecision
from finance_api.models.classification_rule import ClassificationRule
from finance_api.models.transaction import Transaction

router = APIRouter()


class StatsResponse(BaseModel):
    total_transactions: int
    decided: int
    auto_applied: int
    pending_review: int
    pending_cohorts: int
    auto_apply_rate: float
    coverage: float


class RuleResponse(BaseModel):
    id: int
    name: str
    expression: str
    category_id: int
    priority: int


class RuleListResponse(BaseModel):
    items: list[RuleResponse]


@router.get("/stats", response_model=StatsResponse)
def get_stats(db: Annotated[Session, Depends(get_db)]) -> StatsResponse:
    total = db.scalar(select(func.count()).select_from(Transaction)) or 0
    decided = db.scalar(select(func.count()).select_from(ClassificationDecision)) or 0
    auto_applied = (
        db.scalar(
            select(func.count())
            .select_from(ClassificationDecision)
            .where(ClassificationDecision.outcome == Outcome.AUTO_APPLY.value)
        )
        or 0
    )
    pending = (
        db.scalar(
            select(func.count())
            .select_from(ClassificationDecision)
            .where(ClassificationDecision.outcome == Outcome.REVIEW.value)
            .where(ClassificationDecision.confirmed.is_(False))
        )
        or 0
    )
    coverage = (int(decided) / int(total)) if total else 0.0
    rate = (int(auto_applied) / int(decided)) if decided else 0.0
    pending_txns = pending_review_transactions(db)
    pending_cohorts = len(
        CohortDiscovery(pending_txns, pending_txns, min_size=2).proposals()
    )
    return StatsResponse(
        total_transactions=int(total),
        decided=int(decided),
        auto_applied=int(auto_applied),
        pending_review=int(pending),
        pending_cohorts=pending_cohorts,
        auto_apply_rate=rate,
        coverage=coverage,
    )


@router.get("/rules", response_model=RuleListResponse)
def list_rules(db: Annotated[Session, Depends(get_db)]) -> RuleListResponse:
    stmt = (
        select(ClassificationRule)
        .where(ClassificationRule.is_active.is_(True))
        .order_by(ClassificationRule.priority, ClassificationRule.id)
    )
    items = [
        RuleResponse(
            id=rule.id,
            name=rule.name,
            expression=rule.rule_expression,
            category_id=rule.category_id,
            priority=rule.priority,
        )
        for rule in db.scalars(stmt)
    ]
    return RuleListResponse(items=items)
