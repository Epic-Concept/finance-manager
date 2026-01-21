"""Pytest configuration and fixtures."""

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from finance_api.db.base import Base, import_models
from finance_api.main import app

# ============================================================================
# Helper functions
# ============================================================================


def get_test_database_url() -> str | None:
    """Get database URL from environment for integration tests.

    Returns None if DATABASE_URL is not set, indicating SQL Server is not available.
    """
    return os.environ.get("DATABASE_URL")


def is_sqlserver_available() -> bool:
    """Check if SQL Server is available for integration tests."""
    url = get_test_database_url()
    if not url:
        return False

    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


# ============================================================================
# FastAPI test client
# ============================================================================


@pytest.fixture
def client() -> TestClient:
    """Create a test client."""
    return TestClient(app)


# ============================================================================
# Unit test fixtures (SQLite in-memory)
# ============================================================================


@pytest.fixture
def in_memory_db() -> Generator[Session, None, None]:
    """Create an in-memory SQLite database for unit testing.

    Uses SQLite's ATTACH DATABASE to simulate the 'finance' schema.
    This fixture is fast and doesn't require external dependencies.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def setup_sqlite(dbapi_connection, connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("ATTACH DATABASE ':memory:' AS finance")
        cursor.close()

    import_models()
    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(in_memory_db: Session) -> Session:
    """Alias for in_memory_db fixture (used by unit tests)."""
    return in_memory_db


# ============================================================================
# Integration test fixtures (SQL Server)
# ============================================================================


@pytest.fixture(scope="session")
def sqlserver_engine():
    """Create a SQL Server engine for integration tests.

    This fixture is session-scoped for efficiency - the engine is reused
    across all integration tests.
    """
    url = get_test_database_url()
    if not url:
        pytest.skip("DATABASE_URL not set - skipping SQL Server integration tests")

    engine = create_engine(url)

    # Verify connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        pytest.skip(f"Could not connect to SQL Server: {e}")

    return engine


@pytest.fixture(scope="session")
def sqlserver_setup(sqlserver_engine):
    """Set up the SQL Server schema once per test session.

    Creates the finance schema and all tables. Tables are preserved
    between tests for efficiency, but data is cleaned up per-test.
    """
    import_models()

    with sqlserver_engine.connect() as conn:
        # Create finance schema if it doesn't exist
        conn.execute(
            text(
                "IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'finance') "
                "EXEC('CREATE SCHEMA finance')"
            )
        )
        conn.commit()

    # Create all tables
    Base.metadata.create_all(bind=sqlserver_engine)

    yield sqlserver_engine

    # Teardown: drop all tables (optional - can be removed if you want to inspect)
    # Base.metadata.drop_all(bind=sqlserver_engine)


@pytest.fixture
def sqlserver_session(sqlserver_setup) -> Generator[Session, None, None]:
    """Create a SQL Server session for integration tests.

    Each test gets a fresh session with transaction rollback for isolation.
    Data is cleaned up after each test.
    """
    engine = sqlserver_setup

    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()

        # Clean up data from all tables (in correct order for FK constraints)
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM finance.rule_proposals"))
            conn.execute(text("DELETE FROM finance.transaction_categories"))
            conn.execute(text("DELETE FROM finance.category_closure"))
            conn.execute(text("DELETE FROM finance.classification_rules"))
            conn.execute(text("DELETE FROM finance.online_purchases"))
            conn.execute(text("DELETE FROM finance.transactions"))
            conn.execute(text("DELETE FROM finance.categories"))
            conn.execute(text("DELETE FROM finance.bank_sessions"))
            conn.commit()


# ============================================================================
# Skip markers for conditional test execution
# ============================================================================


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (SQLite)")
    config.addinivalue_line("markers", "integration: Integration tests (SQL Server)")


def pytest_collection_modifyitems(config: pytest.Config, items: list) -> None:
    """Automatically mark tests based on their location."""
    for item in items:
        # Mark tests in integration/ directory
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        # Mark tests in models/ and repositories/ as unit tests by default
        elif "models" in str(item.fspath) or "repositories" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
