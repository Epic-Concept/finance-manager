"""The daily classification job.

Classifies newly-synced, not-yet-classified transactions through the engine,
persisting each decision with its splits and evidence chain. Decisions routed to
review form the review queue. Idempotent: transactions that already have a
decision are skipped, so re-running makes no new decisions.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from finance_api.classification.cold_start import (
    ColdStartBlocked,
    cold_start_should_block,
)
from finance_api.classification.cohorts import (
    CohortDiscovery,
    pending_review_transactions,
)
from finance_api.classification.engine import ClassificationEngine
from finance_api.classification.gatherer import GatherContext
from finance_api.classification.policy import Outcome
from finance_api.ledger.poster import post_decision
from finance_api.models.classification_decision import ClassificationDecision
from finance_api.models.transaction import Transaction
from finance_api.repositories.classification_decision_repository import (
    ClassificationDecisionRepository,
)


@dataclass(frozen=True)
class DailyResult:
    """Counts from a daily classification run."""

    classified: int
    auto_applied: int
    review: int


def run_daily_classification(
    session: Session,
    engine: ClassificationEngine,
    limit: int | None = None,
    *,
    allow_cold_start_review: bool = False,
) -> DailyResult:
    """Classify undecided transactions and persist their decisions.

    ``limit`` bounds how many are processed per run (useful for bounded/initial
    runs); ``None`` processes all undecided transactions.
    """
    if cold_start_should_block(session) and not allow_cold_start_review:
        raise ColdStartBlocked(
            "Offer cohort bootstrap before classify-to-review on a large residual"
        )
    repo = ClassificationDecisionRepository(session)
    stmt = (
        select(Transaction)
        .where(~exists().where(ClassificationDecision.transaction_id == Transaction.id))
        .order_by(Transaction.id)
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    undecided = list(session.scalars(stmt))

    auto_applied = 0
    review = 0
    for txn in undecided:
        context = GatherContext(
            transaction_id=txn.id,
            description=txn.description,
            amount=txn.amount,
            currency=txn.currency,
            transaction_date=txn.transaction_date,
            account_name=txn.account_name,
            merchant_name=txn.merchant_name,
        )
        outcome = engine.classify(context)
        recorded = repo.record(
            txn.id, txn.amount, outcome.decision, outcome.merchant_class
        )
        if outcome.decision.outcome == Outcome.AUTO_APPLY:
            auto_applied += 1
            post_decision(session, txn, recorded)
        else:
            review += 1

    session.commit()
    return DailyResult(
        classified=len(undecided), auto_applied=auto_applied, review=review
    )


def discover_review_cohorts(session: Session) -> int:
    """Group pending review into cohorts. Returns the number of confirmable groups."""
    pending = pending_review_transactions(session)
    return len(CohortDiscovery(pending, pending, min_size=2).proposals())
