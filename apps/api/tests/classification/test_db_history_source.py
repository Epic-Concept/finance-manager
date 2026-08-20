"""Unit tests for DbHistorySource (prior outcomes per merchant from decisions)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from finance_api.classification.db_sources import DbHistorySource
from finance_api.classification.evidence import Claim, StrengthTier
from finance_api.classification.policy import Decision, MerchantClass, Outcome
from finance_api.models.category import Category
from finance_api.models.transaction import Transaction
from finance_api.repositories.classification_decision_repository import (
    ClassificationDecisionRepository,
)


def _cat(session: Session, category_id: int) -> None:
    if session.get(Category, category_id) is None:
        session.add(Category(id=category_id, name=f"cat-{category_id}"))
        session.flush()


def _txn(session: Session, description: str) -> Transaction:
    txn = Transaction(
        transaction_date=date(2026, 1, 1),
        description=description,
        amount=Decimal("-20.00"),
        currency="PLN",
    )
    session.add(txn)
    session.flush()
    return txn


def _record(
    session: Session, txn: Transaction, category_id: int, confirmed: bool
) -> None:
    _cat(session, category_id)
    repo = ClassificationDecisionRepository(session)
    decision = Decision(
        outcome=Outcome.AUTO_APPLY,
        claim=Claim.single_category(category_id),
        strength=StrengthTier.STRONG,
        reason="sufficient",
    )
    rec = repo.record(txn.id, txn.amount, decision, MerchantClass.SINGLE_CATEGORY)
    rec.confirmed = confirmed
    session.flush()


def test_prior_confirmed_category_surfaces_as_history(db_session: Session) -> None:
    txn = _txn(db_session, "BIEDRONKA 1234 WARSZAWA")
    _record(db_session, txn, category_id=7, confirmed=True)

    outcomes = DbHistorySource(db_session).outcomes_for("BIEDRONKA 0099 KRAKOW")

    assert len(outcomes) == 1
    assert outcomes[0].category_id == 7
    assert outcomes[0].human_confirmed is True


def test_unrelated_merchant_returns_nothing(db_session: Session) -> None:
    txn = _txn(db_session, "BIEDRONKA 1234")
    _record(db_session, txn, category_id=7, confirmed=True)

    assert DbHistorySource(db_session).outcomes_for("ORLEN STACJA") == []


def test_multiple_priors_for_same_merchant(db_session: Session) -> None:
    for desc, cat in [("ZABKA 1", 3), ("ZABKA 2", 3), ("ZABKA 3", 5)]:
        _record(db_session, _txn(db_session, desc), category_id=cat, confirmed=False)

    outcomes = DbHistorySource(db_session).outcomes_for("ZABKA 9")

    assert sorted(o.category_id for o in outcomes) == [3, 3, 5]
    assert all(o.human_confirmed is False for o in outcomes)
