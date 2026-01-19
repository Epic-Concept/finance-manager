"""Tests for main API endpoints."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from finance_api import __version__


def test_health_check_with_db(client: TestClient) -> None:
    """Test health check endpoint returns healthy status with database."""
    with patch("finance_api.main.check_database_health") as mock_db:
        mock_db.return_value = {"status": "connected"}
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == __version__
        assert data["database"]["status"] == "connected"


def test_health_check_without_db(client: TestClient) -> None:
    """Test health check endpoint returns degraded status without database."""
    with patch("finance_api.main.check_database_health") as mock_db:
        mock_db.return_value = {"status": "disconnected", "error": "Connection failed"}
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["database"]["status"] == "disconnected"


def test_root(client: TestClient) -> None:
    """Test root endpoint returns welcome message."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "Finance Manager API" in data["message"]
    assert data["version"] == __version__
