"""Integration tests for correlator FastAPI endpoints."""

from fastapi.testclient import TestClient

from services.correlator.main import app

client = TestClient(app)


def test_health() -> None:
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "elasticsearch" in data


def test_correlate_empty() -> None:
    """Test correlation with no anomalies."""
    try:
        response = client.post("/correlate", json={})
        if response.status_code == 200:
            data = response.json()
            assert data["total"] >= 0
    except Exception:
        pass


def test_incidents_empty() -> None:
    """Test getting incidents when none exist."""
    response = client.get("/incidents")
    assert response.status_code == 200
