"""Integration tests for the review router."""

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from finance_api.classification.evidence import StrengthTier
from finance_api.classification.policy import Decision, MerchantClass, Outcome
from finance_api.db.base import Base, import_models
from finance_api.db.session import get_db
from finance_api.main import app
from finance_api.models.category import Category
from finance_api.models.transaction import Transaction
from finance_api.repositories.classification_decision_repository import (
    ClassificationDecisionRepository,
)


@pytest.fixture
def test_engine():
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


@pytest.fixture
def client_with_db(test_engine):
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def _seed_review(test_engine) -> int:
    TestingSessionLocal = sessionmaker(bind=test_engine)
    session: Session = TestingSessionLocal()
    session.add(Category(id=1, name="Groceries"))
    txn = Transaction(
        transaction_date=date(2026, 1, 1),
        description="MYSTERY MERCHANT",
        amount=Decimal("-30.00"),
        currency="PLN",
    )
    session.add(txn)
    session.flush()
    rec = ClassificationDecisionRepository(session).record(
        txn.id,
        txn.amount,
        Decision(Outcome.REVIEW, None, StrengthTier.NONE, "no_evidence"),
        MerchantClass.UNKNOWN,
    )
    decision_id = rec.id
    session.commit()
    session.close()
    return decision_id


def test_list_then_resolve(client_with_db, test_engine) -> None:
    decision_id = _seed_review(test_engine)

    listed = client_with_db.get("/api/v1/reviews")
    assert listed.status_code == 200
    body = listed.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["description"] == "MYSTERY MERCHANT"

    resolved = client_with_db.post(
        f"/api/v1/reviews/{decision_id}/resolve", json={"category_id": 1}
    )
    assert resolved.status_code == 200
    assert resolved.json()["confirmed"] is True

    # queue is now empty
    assert client_with_db.get("/api/v1/reviews").json()["items"] == []


def test_resolve_missing_decision_404(client_with_db, test_engine) -> None:
    resp = client_with_db.post("/api/v1/reviews/999/resolve", json={"category_id": 1})
    assert resp.status_code == 404
