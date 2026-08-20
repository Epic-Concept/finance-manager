"""Cohort review grouping and skip/confirm."""

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from finance_api.classification.cold_start import (
    ColdStartBlocked,
    cold_start_should_block,
)
from finance_api.classification.daily import run_daily_classification
from finance_api.classification.engine import EngineOutcome
from finance_api.classification.evidence import StrengthTier
from finance_api.classification.gatherer import GatherContext
from finance_api.classification.policy import Decision, MerchantClass, Outcome
from finance_api.db.base import Base, import_models
from finance_api.db.session import get_db
from finance_api.main import app
from finance_api.models.category import Category
from finance_api.models.classification_decision import ClassificationDecision
from finance_api.models.classification_rule import ClassificationRule
from finance_api.models.transaction import Transaction


def _engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys=ON"))
        conn.execute(text("ATTACH DATABASE ':memory:' AS finance"))
        conn.commit()
    import_models()
    Base.metadata.create_all(bind=engine)
    return engine


def test_forty_seven_tesco_are_one_cohort() -> None:
    engine = _engine()
    SessionLocal = sessionmaker(bind=engine)
    session: Session = SessionLocal()
    session.add(Category(id=1, name="Groceries"))
    for i in range(47):
        txn = Transaction(
            transaction_date=date(2026, 1, 1),
            description=f"TESCO STORES {i}",
            amount=Decimal("-12.00"),
            currency="GBP",
            account_name="Current",
        )
        session.add(txn)
        session.flush()
        session.add(
            ClassificationDecision(
                transaction_id=txn.id,
                outcome="review",
                merchant_class="unknown",
                strength=0,
                reason="no_evidence",
                confirmed=False,
            )
        )
    session.commit()

    def override():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    try:
        client = TestClient(app)
        listed = client.get("/api/v1/cohorts")
        assert listed.status_code == 200
        body = listed.json()
        assert len(body["items"]) == 1
        assert body["items"][0]["size"] == 47
        cohort_id = body["items"][0]["cohort_id"]
        stats = client.get("/api/v1/stats")
        assert stats.status_code == 200
        assert stats.json()["pending_cohorts"] == 1

        skipped = client.post(
            f"/api/v1/cohorts/{cohort_id}/resolve", json={"action": "skip"}
        )
        assert skipped.status_code == 200
        assert skipped.json()["resolved"] == 0
        # skip is idempotent: cohort still listed (in-memory skip is per request)
        listed_again = client.get("/api/v1/cohorts").json()
        assert len(listed_again["items"]) == 1
    finally:
        app.dependency_overrides.clear()
        session.close()


def test_confirm_cohort_mints_rule_and_resolves() -> None:
    engine = _engine()
    SessionLocal = sessionmaker(bind=engine)
    session: Session = SessionLocal()
    session.add(Category(id=1, name="Groceries"))
    for i in range(3):
        txn = Transaction(
            transaction_date=date(2026, 1, 1),
            description=f"TESCO STORES {i}",
            amount=Decimal("-12.00"),
            currency="GBP",
            account_name="Current",
        )
        session.add(txn)
        session.flush()
        session.add(
            ClassificationDecision(
                transaction_id=txn.id,
                outcome="review",
                merchant_class="unknown",
                strength=0,
                reason="no_evidence",
                confirmed=False,
            )
        )
    session.commit()

    def override():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    try:
        client = TestClient(app)
        listed = client.get("/api/v1/cohorts").json()
        assert len(listed["items"]) == 1
        cohort_id = listed["items"][0]["cohort_id"]
        confirmed = client.post(
            f"/api/v1/cohorts/{cohort_id}/resolve",
            json={"action": "confirm", "category_id": 1},
        )
        assert confirmed.status_code == 200
        assert confirmed.json()["resolved"] == 3
        assert client.get("/api/v1/cohorts").json()["items"] == []
    finally:
        app.dependency_overrides.clear()
        check = SessionLocal()
        rules = list(check.scalars(select(ClassificationRule)))
        assert len(rules) == 1
        assert "matches" in rules[0].rule_expression
        check.close()
        session.close()


def test_cold_start_blocks_large_residual_without_rules() -> None:
    engine = _engine()
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    for i in range(50):
        session.add(
            Transaction(
                transaction_date=date(2026, 1, 1),
                description=f"X {i}",
                amount=Decimal("-1.00"),
                currency="GBP",
            )
        )
    session.commit()
    assert cold_start_should_block(session) is True

    class _Engine:
        def classify(self, context: GatherContext) -> EngineOutcome:
            return EngineOutcome(
                decision=Decision(
                    Outcome.REVIEW, None, StrengthTier.NONE, "no_evidence"
                ),
                merchant_class=MerchantClass.UNKNOWN,
            )

    try:
        run_daily_classification(session, _Engine())  # type: ignore[arg-type]
        raise AssertionError("expected ColdStartBlocked")
    except ColdStartBlocked:
        pass
    session.close()
