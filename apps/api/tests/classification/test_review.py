"""Unit tests for the review service (list / resolve / confirm)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from finance_api.classification.evidence import StrengthTier
from finance_api.classification.policy import Decision, MerchantClass, Outcome
from finance_api.classification.review import ReviewService
from finance_api.models.category import Category
from finance_api.models.classification_decision import ClassificationDecision
from finance_api.models.transaction import Transaction
from finance_api.repositories.classification_decision_repository import (
    ClassificationDecisionRepository,
)


def _seed_review(session: Session, description: str = "MYSTERY MERCHANT") -> int:
    session.add(Category(id=1, name="Groceries"))
    session.add(Category(id=2, name="Self Transfer"))
    txn = Transaction(
        transaction_date=date(2026, 1, 1),
        description=description,
        amount=Decimal("-30.00"),
        currency="PLN",
    )
    session.add(txn)
    session.flush()
    decision = Decision(Outcome.REVIEW, None, StrengthTier.NONE, "no_evidence")
    rec = ClassificationDecisionRepository(session).record(
        txn.id, txn.amount, decision, MerchantClass.UNKNOWN
    )
    return rec.id


def test_list_pending_returns_review_items(db_session: Session) -> None:
    _seed_review(db_session)

    items = ReviewService(db_session).list_pending()

    assert len(items) == 1
    assert items[0].description == "MYSTERY MERCHANT"
    assert items[0].reason == "no_evidence"


def test_resolve_applies_category_and_leaves_queue(db_session: Session) -> None:
    decision_id = _seed_review(db_session)
    svc = ReviewService(db_session)

    svc.resolve(decision_id, category_id=1)

    assert svc.list_pending() == []  # left the queue
    rec = db_session.get(ClassificationDecision, decision_id)
    assert rec.confirmed is True
    assert rec.outcome == Outcome.AUTO_APPLY.value
    assert [s.category_id for s in rec.splits] == [1]


def test_mark_internal_transfer(db_session: Session) -> None:
    decision_id = _seed_review(db_session)
    svc = ReviewService(db_session)

    svc.resolve(decision_id, category_id=2)  # Self Transfer

    rec = db_session.get(ClassificationDecision, decision_id)
    assert [s.category_id for s in rec.splits] == [2]
    assert rec.confirmed is True
