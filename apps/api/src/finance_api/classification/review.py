"""Review queue service and the confirmation -> learner -> promotion loop.

A decision routed to ``REVIEW`` and not yet ``confirmed`` is a pending review.
Resolving one applies a categorization, marks it ``confirmed`` (the persisted
"human-confirmed observation"), and removes it from the queue. The scheduled
learner reads confirmed decisions and promotes stable merchants to rules, off
the classification hot path.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from finance_api.classification.learning import (
    LearningObservation,
    ShadowLearner,
    merchant_key,
)
from finance_api.classification.policy import Outcome
from finance_api.models.classification_decision import (
    CategorizationSplit,
    ClassificationDecision,
)
from finance_api.models.classification_rule import ClassificationRule
from finance_api.models.transaction import Transaction


@dataclass(frozen=True)
class EvidenceItem:
    evidence_type: str
    source: str
    strength: int


@dataclass(frozen=True)
class ReviewItem:
    """A pending review surfaced to the operator."""

    decision_id: int
    transaction_id: int
    description: str
    amount: str
    proposed_category_id: int | None
    strength: int
    reason: str
    evidence: tuple[EvidenceItem, ...]


class ReviewService:
    """Lists and resolves the review queue."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_pending(self) -> list[ReviewItem]:
        stmt = (
            select(ClassificationDecision, Transaction)
            .join(Transaction, ClassificationDecision.transaction_id == Transaction.id)
            .where(ClassificationDecision.outcome == Outcome.REVIEW.value)
            .where(ClassificationDecision.confirmed.is_(False))
            .order_by(ClassificationDecision.id)
        )
        items: list[ReviewItem] = []
        for decision, txn in self._session.execute(stmt):
            proposed = decision.splits[0].category_id if decision.splits else None
            items.append(
                ReviewItem(
                    decision_id=decision.id,
                    transaction_id=txn.id,
                    description=txn.description,
                    amount=str(txn.amount),
                    proposed_category_id=proposed,
                    strength=decision.strength,
                    reason=decision.reason,
                    evidence=tuple(
                        EvidenceItem(e.evidence_type, e.source, e.strength)
                        for e in decision.evidence
                    ),
                )
            )
        return items

    def resolve(self, decision_id: int, category_id: int) -> ClassificationDecision:
        """Apply a single-category resolution and confirm the decision.

        Covers confirm / reclassify / mark-internal-transfer (the caller chooses
        the category id). The decision leaves the queue and becomes a
        human-confirmed observation for the learner.
        """
        decision = self._session.get(ClassificationDecision, decision_id)
        if decision is None:
            raise ValueError(f"decision {decision_id} not found")
        txn = self._session.get(Transaction, decision.transaction_id)
        assert txn is not None

        decision.splits.clear()
        decision.splits.append(
            CategorizationSplit(category_id=category_id, amount=txn.amount)
        )
        decision.outcome = Outcome.AUTO_APPLY.value
        decision.confirmed = True
        self._session.flush()
        return decision

    def confirm(self, decision_id: int) -> ClassificationDecision:
        """Confirm an existing (un-corrected) decision as-is."""
        decision = self._session.get(ClassificationDecision, decision_id)
        if decision is None:
            raise ValueError(f"decision {decision_id} not found")
        decision.confirmed = True
        self._session.flush()
        return decision


def run_learner_promotion(
    session: Session, learner: ShadowLearner | None = None
) -> int:
    """Promote stable, human-confirmed merchants to active rules (off hot path).

    Reads confirmed single-category decisions, builds learner observations, and
    creates a rule for each merchant that meets the learner's stability criteria
    and is not already covered by an active rule. Returns the number created.
    """
    learner = learner or ShadowLearner()
    stmt = (
        select(ClassificationDecision, Transaction)
        .join(Transaction, ClassificationDecision.transaction_id == Transaction.id)
        .where(ClassificationDecision.confirmed.is_(True))
    )
    observations: list[LearningObservation] = []
    for decision, txn in session.execute(stmt):
        if len(decision.splits) != 1:
            continue
        observations.append(
            LearningObservation(
                merchant_key=merchant_key(txn.description),
                category_id=decision.splits[0].category_id,
                human_confirmed=True,
            )
        )

    existing = {
        rule.name
        for rule in session.scalars(
            select(ClassificationRule).where(ClassificationRule.is_active.is_(True))
        )
    }

    created = 0
    for proposal in learner.propose_rules(observations):
        if not proposal.merchant_key or proposal.merchant_key in existing:
            continue
        session.add(
            ClassificationRule(
                name=proposal.merchant_key,
                rule_expression=re.escape(proposal.merchant_key),
                category_id=proposal.category_id,
                priority=0,
                is_active=True,
            )
        )
        existing.add(proposal.merchant_key)
        created += 1
    session.flush()
    return created
