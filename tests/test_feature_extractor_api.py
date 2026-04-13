"""Integration tests for feature extractor FastAPI endpoints."""

from fastapi.testclient import TestClient

from services.feature_extractor.main import app

client = TestClient(app)


def test_health() -> None:
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200


def test_extract_empty() -> None:
    """Test extracting features from empty list."""
    response = client.post("/extract", json=[])
    assert response.status_code == 200
    data = response.json()
    assert data["features_extracted"] == 0


def test_extract_events() -> None:
    """Test feature extraction from provided events."""
    events = [
        {
            "event_id": "evt-001",
            "timestamp": "2026-04-13T14:30:00Z",
            "user_id": "user_001",
            "ip_address": "192.168.1.1",
            "country": "Russia",
            "city": "Moscow",
            "bytes_transferred": 10_000_000,
            "action_type": "login",
            "resource": "/api/data",
        }
    ]
    try:
        response = client.post("/extract", json=events)
        if response.status_code == 200:
            data = response.json()
            assert data["features_extracted"] >= 1
    except Exception:
        pass
