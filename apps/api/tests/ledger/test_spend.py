"""Spend totals exclude transfers."""

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from finance_api.ledger.poster import post_decision
from finance_api.ledger.spend import spend_total
from finance_api.models.category import Category
from finance_api.models.classification_decision import (
    CategorizationSplit,
    ClassificationDecision,
)
from finance_api.models.transaction import Transaction


def test_spend_excludes_transfers(db_session: Session) -> None:
    groceries = Category(name="Groceries")
    parent = Category(name="Internal Transfer")
    db_session.add_all([groceries, parent])
    db_session.flush()
    child = Category(name="Self Transfer", parent_id=parent.id)
    db_session.add(child)
    db_session.flush()

    spend = Transaction(
        transaction_date=date(2026, 6, 1),
        description="TESCO",
        amount=Decimal("-10.00"),
        currency="GBP",
        account_name="Current",
    )
    xfer = Transaction(
        transaction_date=date(2026, 6, 1),
        description="TO SAVINGS",
        amount=Decimal("-50.00"),
        currency="GBP",
        account_name="Current",
    )
    db_session.add_all([spend, xfer])
    db_session.flush()

    d1 = ClassificationDecision(
        transaction_id=spend.id,
        outcome="auto_apply",
        merchant_class="unknown",
        strength=3,
        reason="sufficient",
        confirmed=True,
    )
    d2 = ClassificationDecision(
        transaction_id=xfer.id,
        outcome="auto_apply",
        merchant_class="unknown",
        strength=3,
        reason="sufficient",
        confirmed=True,
    )
    db_session.add_all([d1, d2])
    db_session.flush()
    db_session.add(
        CategorizationSplit(
            decision_id=d1.id, category_id=groceries.id, amount=spend.amount
        )
    )
    db_session.add(
        CategorizationSplit(decision_id=d2.id, category_id=child.id, amount=xfer.amount)
    )
    db_session.flush()
    db_session.refresh(d1)
    db_session.refresh(d2)
    post_decision(db_session, spend, d1)
    post_decision(db_session, xfer, d2)

    total = spend_total(db_session)
    assert total.amount_minor == 100000  # £10 spend only
