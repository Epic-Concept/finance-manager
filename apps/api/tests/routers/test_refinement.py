"""Integration tests for refinement router."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from finance_api.db.base import Base, import_models
from finance_api.db.session import get_db
from finance_api.main import app
from finance_api.models.refinement_session import RefinementSession
from finance_api.models.session_message import SessionMessage
from finance_api.models.session_rule_proposal import SessionRuleProposal
from finance_api.models.transaction import Transaction


@pytest.fixture
def test_engine():
    """Create a test engine with finance schema.

    Uses StaticPool to share a single connection across all threads,
    ensuring the attached 'finance' schema is available to the TestClient.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Setup the finance schema on the single pooled connection
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys=ON"))
        conn.execute(text("ATTACH DATABASE ':memory:' AS finance"))
        conn.commit()

    import_models()
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def in_memory_db(test_engine):
    """Create an in-memory database session for testing."""
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client_with_db(in_memory_db: Session, test_engine):
    """Create test client with database override."""
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


@pytest.fixture
def sample_transactions(in_memory_db: Session):
    """Create sample uncategorized transactions."""
    from datetime import date

    transactions = []
    for i in range(10):
        txn = Transaction(
            transaction_date=date(2024, 1, 15),
            description=f"TESCO STORE {i}",
            amount=-50.00,
            currency="GBP",
        )
        in_memory_db.add(txn)
        transactions.append(txn)
    in_memory_db.commit()
    return transactions


@pytest.fixture
def sample_session(in_memory_db: Session):
    """Create a sample refinement session."""
    session = RefinementSession(
        cluster_hash="abc123",
        cluster_key="TESCO",
        cluster_size=10,
        sample_descriptions='["TESCO STORE 1", "TESCO STORE 2"]',
        status="active",
    )
    in_memory_db.add(session)
    in_memory_db.commit()
    in_memory_db.refresh(session)
    return session


@pytest.fixture
def session_with_messages(in_memory_db: Session, sample_session):
    """Create a session with messages."""
    msg1 = SessionMessage(
        session_id=sample_session.id,
        role="assistant",
        content="I see 10 TESCO transactions. I propose...",
        proposed_rules_json='[{"pattern": "(?i)tesco", "category_id": 1, "category_name": "Groceries", "confidence": "high", "reasoning": "Standard pattern"}]',
    )
    in_memory_db.add(msg1)
    in_memory_db.commit()
    return sample_session


@pytest.fixture
def sample_category(in_memory_db: Session):
    """Create a sample category for testing."""
    from finance_api.models.category import Category

    category = Category(
        name="Groceries",
        description="Grocery stores",
    )
    in_memory_db.add(category)
    in_memory_db.commit()
    in_memory_db.refresh(category)
    return category


@pytest.fixture
def session_with_proposal(in_memory_db: Session, sample_session, sample_category):
    """Create a session with a proposal."""
    proposal = SessionRuleProposal(
        session_id=sample_session.id,
        proposed_pattern="(?i)tesco",
        proposed_category_id=sample_category.id,
        proposed_category_name="Groceries",
        llm_confidence="high",
        llm_reasoning="Standard pattern for TESCO stores",
        validation_matches=10,
        validation_precision=1.0,
        validation_true_positives=10,
        validation_false_positives=0,
        status="pending",
    )
    in_memory_db.add(proposal)
    in_memory_db.commit()
    in_memory_db.refresh(proposal)
    return sample_session, proposal


class TestListSessions:
    """Tests for GET /api/v1/refinement/sessions."""

    def test_list_sessions_empty(self, client_with_db):
        """Test listing sessions when none exist."""
        response = client_with_db.get("/api/v1/refinement/sessions")
        assert response.status_code == 200
        data = response.json()
        assert data["sessions"] == []
        assert data["total"] == 0

    def test_list_sessions_with_data(self, client_with_db, sample_session):
        """Test listing sessions with existing data."""
        response = client_with_db.get("/api/v1/refinement/sessions")
        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 1
        assert data["total"] == 1
        assert data["sessions"][0]["cluster_hash"] == "abc123"

    def test_list_sessions_with_status_filter(
        self, client_with_db, sample_session, in_memory_db
    ):
        """Test filtering sessions by status."""
        # Create a completed session
        completed = RefinementSession(
            cluster_hash="def456",
            cluster_key="SAINSBURY",
            cluster_size=5,
            sample_descriptions='["SAINSBURY 1"]',
            status="completed",
        )
        in_memory_db.add(completed)
        in_memory_db.commit()

        # Filter by active
        response = client_with_db.get("/api/v1/refinement/sessions?status=active")
        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 1
        assert data["sessions"][0]["status"] == "active"


class TestGetSession:
    """Tests for GET /api/v1/refinement/sessions/{session_id}."""

    def test_get_session_exists(self, client_with_db, sample_session):
        """Test getting an existing session."""
        response = client_with_db.get(
            f"/api/v1/refinement/sessions/{sample_session.id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_session.id
        assert data["cluster_hash"] == "abc123"
        assert data["cluster_key"] == "TESCO"

    def test_get_session_not_found(self, client_with_db):
        """Test getting a non-existent session."""
        response = client_with_db.get("/api/v1/refinement/sessions/9999")
        assert response.status_code == 404


class TestDeleteSession:
    """Tests for DELETE /api/v1/refinement/sessions/{session_id}."""

    def test_delete_session_exists(self, client_with_db, sample_session, in_memory_db):
        """Test deleting an existing session."""
        session_id = sample_session.id
        response = client_with_db.delete(f"/api/v1/refinement/sessions/{session_id}")
        assert response.status_code == 204

        # Verify deletion via API (avoids session cache issues)
        get_response = client_with_db.get(f"/api/v1/refinement/sessions/{session_id}")
        assert get_response.status_code == 404

    def test_delete_session_not_found(self, client_with_db):
        """Test deleting a non-existent session."""
        response = client_with_db.delete("/api/v1/refinement/sessions/9999")
        assert response.status_code == 404


class TestGetConversation:
    """Tests for GET /api/v1/refinement/sessions/{session_id}/messages."""

    def test_get_conversation_empty(self, client_with_db, sample_session):
        """Test getting conversation with no messages."""
        response = client_with_db.get(
            f"/api/v1/refinement/sessions/{sample_session.id}/messages"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == sample_session.id
        assert data["messages"] == []

    def test_get_conversation_with_messages(
        self, client_with_db, session_with_messages
    ):
        """Test getting conversation with messages."""
        response = client_with_db.get(
            f"/api/v1/refinement/sessions/{session_with_messages.id}/messages"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["messages"]) == 1
        assert data["messages"][0]["role"] == "assistant"


class TestListProposals:
    """Tests for GET /api/v1/refinement/sessions/{session_id}/proposals."""

    def test_list_proposals_empty(self, client_with_db, sample_session):
        """Test listing proposals when none exist."""
        response = client_with_db.get(
            f"/api/v1/refinement/sessions/{sample_session.id}/proposals"
        )
        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_list_proposals_with_data(self, client_with_db, session_with_proposal):
        """Test listing proposals with existing data."""
        session, proposal = session_with_proposal
        response = client_with_db.get(
            f"/api/v1/refinement/sessions/{session.id}/proposals"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["proposed_pattern"] == "(?i)tesco"


class TestAcceptProposal:
    """Tests for POST /api/v1/refinement/sessions/{session_id}/proposals/{proposal_id}/accept."""

    def test_accept_proposal_success(
        self, client_with_db, session_with_proposal, in_memory_db
    ):
        """Test accepting a proposal creates a rule."""
        session, proposal = session_with_proposal
        response = client_with_db.post(
            f"/api/v1/refinement/sessions/{session.id}/proposals/{proposal.id}/accept",
            json={},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"

    def test_accept_proposal_not_found(self, client_with_db, sample_session):
        """Test accepting a non-existent proposal."""
        response = client_with_db.post(
            f"/api/v1/refinement/sessions/{sample_session.id}/proposals/9999/accept",
            json={},
        )
        assert response.status_code == 404

    def test_accept_proposal_wrong_session(
        self, client_with_db, session_with_proposal, in_memory_db
    ):
        """Test accepting a proposal from wrong session."""
        session, proposal = session_with_proposal
        # Create another session
        other_session = RefinementSession(
            cluster_hash="other123",
            cluster_key="OTHER",
            cluster_size=5,
            sample_descriptions='["OTHER 1"]',
            status="active",
        )
        in_memory_db.add(other_session)
        in_memory_db.commit()

        response = client_with_db.post(
            f"/api/v1/refinement/sessions/{other_session.id}/proposals/{proposal.id}/accept",
            json={},
        )
        assert response.status_code == 400


class TestRejectProposal:
    """Tests for POST /api/v1/refinement/sessions/{session_id}/proposals/{proposal_id}/reject."""

    def test_reject_proposal_success(
        self, client_with_db, session_with_proposal, in_memory_db
    ):
        """Test rejecting a proposal."""
        session, proposal = session_with_proposal
        response = client_with_db.post(
            f"/api/v1/refinement/sessions/{session.id}/proposals/{proposal.id}/reject",
            json={"notes": "Pattern too broad"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"


class TestCompleteSession:
    """Tests for POST /api/v1/refinement/sessions/{session_id}/actions/complete."""

    def test_complete_session_success(
        self, client_with_db, sample_session, in_memory_db
    ):
        """Test completing a session."""
        response = client_with_db.post(
            f"/api/v1/refinement/sessions/{sample_session.id}/actions/complete"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    def test_complete_session_not_found(self, client_with_db):
        """Test completing a non-existent session."""
        response = client_with_db.post(
            "/api/v1/refinement/sessions/9999/actions/complete"
        )
        assert response.status_code == 404


class TestSkipSession:
    """Tests for POST /api/v1/refinement/sessions/{session_id}/actions/skip."""

    def test_skip_session_success(self, client_with_db, sample_session, in_memory_db):
        """Test skipping a session."""
        response = client_with_db.post(
            f"/api/v1/refinement/sessions/{sample_session.id}/actions/skip"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "skipped"


class TestListClusters:
    """Tests for GET /api/v1/refinement/clusters."""

    def test_list_clusters_no_transactions(self, client_with_db):
        """Test listing clusters with no transactions."""
        response = client_with_db.get("/api/v1/refinement/clusters")
        assert response.status_code == 200
        data = response.json()
        assert data["clusters"] == []
        assert data["total"] == 0

    def test_list_clusters_with_transactions(self, client_with_db, sample_transactions):
        """Test listing clusters with uncategorized transactions."""
        response = client_with_db.get("/api/v1/refinement/clusters?min_size=1")
        assert response.status_code == 200
        data = response.json()
        # Should have at least one cluster from the TESCO transactions
        assert data["total"] > 0
