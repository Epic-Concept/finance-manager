"""Unit tests for the daily classification job (idempotent persistence)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from finance_api.classification.daily import run_daily_classification
from finance_api.classification.engine import EngineOutcome
from finance_api.classification.evidence import Claim, StrengthTier
from finance_api.classification.gatherer import GatherContext
from finance_api.classification.policy import Decision, MerchantClass, Outcome
from finance_api.models.category import Category
from finance_api.models.classification_decision import ClassificationDecision
from finance_api.models.transaction import Transaction


class FakeEngine:
    """Auto-applies category 1 unless the description starts with REVIEW."""

    def classify(self, context: GatherContext) -> EngineOutcome:
        if context.description.startswith("REVIEW"):
            return EngineOutcome(
                decision=Decision(
                    Outcome.REVIEW, None, StrengthTier.NONE, "no_evidence"
                ),
                merchant_class=MerchantClass.UNKNOWN,
            )
        return EngineOutcome(
            decision=Decision(
                Outcome.AUTO_APPLY,
                Claim.single_category(1),
                StrengthTier.STRONG,
                "sufficient",
            ),
            merchant_class=MerchantClass.SINGLE_CATEGORY,
        )


def _seed(session: Session) -> None:
    session.add(Category(id=1, name="Groceries"))
    session.add_all(
        [
            Transaction(
                transaction_date=date(2026, 1, 1),
                description="BIEDRONKA 1",
                amount=Decimal("-10.00"),
                currency="PLN",
            ),
            Transaction(
                transaction_date=date(2026, 1, 2),
                description="REVIEW MYSTERY MERCHANT",
                amount=Decimal("-99.00"),
                currency="PLN",
            ),
        ]
    )
    session.flush()


def test_classifies_new_transactions(db_session: Session) -> None:
    _seed(db_session)

    result = run_daily_classification(db_session, FakeEngine())

    assert result.classified == 2
    assert result.auto_applied == 1
    assert result.review == 1
    assert db_session.query(ClassificationDecision).count() == 2


def test_rerun_is_idempotent(db_session: Session) -> None:
    _seed(db_session)
    run_daily_classification(db_session, FakeEngine())

    result = run_daily_classification(db_session, FakeEngine())

    assert result.classified == 0
    assert db_session.query(ClassificationDecision).count() == 2


def test_only_new_transactions_classified_on_second_run(db_session: Session) -> None:
    _seed(db_session)
    run_daily_classification(db_session, FakeEngine())

    db_session.add(
        Transaction(
            transaction_date=date(2026, 1, 3),
            description="BIEDRONKA 2",
            amount=Decimal("-5.00"),
            currency="PLN",
        )
    )
    db_session.flush()

    result = run_daily_classification(db_session, FakeEngine())
    assert result.classified == 1
    assert db_session.query(ClassificationDecision).count() == 3
