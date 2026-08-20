"""Tests for household ledger posting shapes."""

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from finance_api.ledger.pockets import (
    ensure_pockets_from_transactions,
    get_or_create_pocket,
)
from finance_api.ledger.poster import post_decision
from finance_api.models.category import Category
from finance_api.models.classification_decision import (
    CategorizationSplit,
    ClassificationDecision,
)
from finance_api.models.ledger import JournalEntry, Posting
from finance_api.models.transaction import Transaction


def _txn(session: Session, amount: str, account: str = "Current") -> Transaction:
    txn = Transaction(
        transaction_date=date(2026, 6, 1),
        description="TEST",
        amount=Decimal(amount),
        currency="GBP",
        account_name=account,
    )
    session.add(txn)
    session.flush()
    return txn


def _decision(
    session: Session, txn: Transaction, splits: list[tuple[int, str]]
) -> ClassificationDecision:
    decision = ClassificationDecision(
        transaction_id=txn.id,
        outcome="auto_apply",
        merchant_class="unknown",
        strength=3,
        reason="sufficient",
        confirmed=True,
    )
    session.add(decision)
    session.flush()
    for category_id, amount in splits:
        session.add(
            CategorizationSplit(
                decision_id=decision.id,
                category_id=category_id,
                amount=Decimal(amount),
            )
        )
    session.flush()
    session.refresh(decision)
    return decision


def _sum(entry: JournalEntry) -> int:
    return sum(p.amount_minor for p in entry.postings)


class TestLedgerPosting:
    def test_spend_balances_and_debits_nominal(self, db_session: Session) -> None:
        groceries = Category(name="Groceries")
        db_session.add(groceries)
        db_session.flush()
        txn = _txn(db_session, "-42.50")
        decision = _decision(db_session, txn, [(groceries.id, "-42.50")])
        entry = post_decision(db_session, txn, decision)
        assert entry.kind == "spend"
        assert _sum(entry) == 0
        nominal = next(p for p in entry.postings if p.category_id == groceries.id)
        assert nominal.amount_minor == 425000

    def test_income_credits_nominal(self, db_session: Session) -> None:
        salary = Category(name="Salary")
        db_session.add(salary)
        db_session.flush()
        txn = _txn(db_session, "1250.00")
        decision = _decision(db_session, txn, [(salary.id, "1250.00")])
        entry = post_decision(db_session, txn, decision)
        assert entry.kind == "income"
        assert _sum(entry) == 0
        nominal = next(p for p in entry.postings if p.category_id == salary.id)
        assert nominal.amount_minor == -12500000

    def test_transfer_is_not_spend(self, db_session: Session) -> None:
        parent = Category(name="Internal Transfer")
        db_session.add(parent)
        db_session.flush()
        child = Category(name="Self Transfer", parent_id=parent.id)
        db_session.add(child)
        db_session.flush()
        txn = _txn(db_session, "-500.00", account="Current")
        decision = _decision(db_session, txn, [(child.id, "-500.00")])
        entry = post_decision(db_session, txn, decision)
        assert entry.kind == "transfer"
        assert _sum(entry) == 0
        assert all(p.category_id is None for p in entry.postings)

    def test_split_sums_to_zero(self, db_session: Session) -> None:
        groceries = Category(name="Groceries")
        household = Category(name="Household")
        db_session.add_all([groceries, household])
        db_session.flush()
        txn = _txn(db_session, "-42.50")
        decision = _decision(
            db_session, txn, [(groceries.id, "30.00"), (household.id, "12.50")]
        )
        entry = post_decision(db_session, txn, decision)
        assert entry.kind == "split"
        assert _sum(entry) == 0

    def test_reclassify_reverses_then_posts(self, db_session: Session) -> None:
        groceries = Category(name="Groceries")
        eating = Category(name="Eating Out")
        db_session.add_all([groceries, eating])
        db_session.flush()
        txn = _txn(db_session, "-10.00")
        first = _decision(db_session, txn, [(groceries.id, "-10.00")])
        post_decision(db_session, txn, first)
        second = _decision(db_session, txn, [(eating.id, "-10.00")])
        post_decision(db_session, txn, second)
        entries = list(db_session.query(JournalEntry).all())
        assert len(entries) == 3  # original, reversal, new
        assert sum(p.amount_minor for p in db_session.query(Posting).all()) == 0

    def test_ensure_pockets_from_account_names(self, db_session: Session) -> None:
        _txn(db_session, "-1.00", account="Santander Current")
        _txn(db_session, "-2.00", account="Santander Current")
        created = ensure_pockets_from_transactions(db_session)
        assert created >= 1
        pocket = get_or_create_pocket(db_session, "Santander Current")
        assert pocket.name == "Santander Current"
