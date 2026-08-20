"""Unit tests for scheduled learner promotion (confirmations -> rules)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from finance_api.classification.evidence import Claim, StrengthTier
from finance_api.classification.policy import Decision, MerchantClass, Outcome
from finance_api.classification.review import run_learner_promotion
from finance_api.models.category import Category
from finance_api.models.classification_rule import ClassificationRule
from finance_api.models.transaction import Transaction
from finance_api.repositories.classification_decision_repository import (
    ClassificationDecisionRepository,
)


def _confirmed(session: Session, description: str, category_id: int) -> None:
    txn = Transaction(
        transaction_date=date(2026, 1, 1),
        description=description,
        amount=Decimal("-9.00"),
        currency="PLN",
    )
    session.add(txn)
    session.flush()
    rec = ClassificationDecisionRepository(session).record(
        txn.id,
        txn.amount,
        Decision(
            Outcome.AUTO_APPLY,
            Claim.single_category(category_id),
            StrengthTier.STRONG,
            "sufficient",
        ),
        MerchantClass.SINGLE_CATEGORY,
    )
    rec.confirmed = True
    session.flush()


def test_stable_confirmed_merchant_is_promoted(db_session: Session) -> None:
    db_session.add(Category(id=1, name="Groceries"))
    for i in range(3):
        _confirmed(db_session, f"ZABKA {i}", category_id=1)

    created = run_learner_promotion(db_session)

    assert created == 1
    rule = db_session.query(ClassificationRule).one()
    assert rule.name == "ZABKA"
    assert rule.category_id == 1
    assert rule.is_active is True
    assert "matches" in rule.rule_expression
    assert "ZABKA" in rule.rule_expression


def test_insufficient_support_is_not_promoted(db_session: Session) -> None:
    db_session.add(Category(id=1, name="Groceries"))
    _confirmed(db_session, "ORLEN 1", category_id=1)  # only 1 obs (< min 3)

    assert run_learner_promotion(db_session) == 0
    assert db_session.query(ClassificationRule).count() == 0


def test_promotion_is_idempotent(db_session: Session) -> None:
    db_session.add(Category(id=1, name="Groceries"))
    for i in range(3):
        _confirmed(db_session, f"ZABKA {i}", category_id=1)

    run_learner_promotion(db_session)
    created_again = run_learner_promotion(db_session)  # rule already exists

    assert created_again == 0
    assert db_session.query(ClassificationRule).count() == 1
