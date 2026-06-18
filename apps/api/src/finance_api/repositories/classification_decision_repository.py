"""Repository for persisting evidence-driven classification decisions.

Persists a policy :class:`Decision` as a :class:`ClassificationDecision` with its
categorization splits (summing to the transaction total) and the supporting
evidence chain. Decisions routed to review form the review queue.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from finance_api.classification.policy import Decision, MerchantClass, Outcome
from finance_api.models.classification_decision import (
    CategorizationSplit,
    ClassificationDecision,
    DecisionEvidence,
)


class ClassificationDecisionRepository:
    """Persists classification decisions and queries the review queue."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def record(
        self,
        transaction_id: int,
        transaction_amount: Decimal,
        decision: Decision,
        merchant_class: MerchantClass,
    ) -> ClassificationDecision:
        """Persist a decision with its splits and evidence chain."""
        record = ClassificationDecision(
            transaction_id=transaction_id,
            outcome=decision.outcome.value,
            merchant_class=merchant_class.value,
            strength=int(decision.strength),
            reason=decision.reason,
        )

        # Splits: itemized claims carry their own amounts; a single-category
        # claim covers the whole transaction total. Contested / no-evidence
        # reviews have no claim and therefore no splits.
        claim = decision.claim
        if claim is not None:
            if claim.itemized:
                for split in claim.splits:
                    record.splits.append(
                        CategorizationSplit(
                            category_id=split.category_id,
                            amount=(
                                split.amount
                                if split.amount is not None
                                else Decimal("0")
                            ),
                        )
                    )
            else:
                record.splits.append(
                    CategorizationSplit(
                        category_id=claim.category_ids[0],
                        amount=transaction_amount,
                    )
                )

        for ev in decision.evidence:
            record.evidence.append(
                DecisionEvidence(
                    evidence_type=ev.evidence_type.value,
                    source=ev.source,
                    strength=int(ev.strength),
                    itemized=ev.itemized,
                )
            )

        self._session.add(record)
        self._session.flush()
        return record

    def pending_reviews(self) -> list[ClassificationDecision]:
        """Return decisions routed to review (the review queue)."""
        stmt = (
            select(ClassificationDecision)
            .where(ClassificationDecision.outcome == Outcome.REVIEW.value)
            .order_by(ClassificationDecision.id)
        )
        return list(self._session.scalars(stmt))
