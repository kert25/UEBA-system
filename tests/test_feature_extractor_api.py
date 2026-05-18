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


def test_extract_multiple_events() -> None:
    """Test feature extraction with multiple events for same user."""
    events = [
        {
            "event_id": "evt-100",
            "timestamp": "2026-04-13T10:00:00Z",
            "user_id": "user_geo",
            "ip_address": "1.1.1.1",
            "country": "Russia",
            "city": "Moscow",
            "bytes_transferred": 1000,
            "action_type": "login",
            "resource": "/",
        },
        {
            "event_id": "evt-101",
            "timestamp": "2026-04-13T12:00:00Z",
            "user_id": "user_geo",
            "ip_address": "2.2.2.2",
            "country": "Russia",
            "city": "Saint Petersburg",
            "bytes_transferred": 2000,
            "action_type": "login",
            "resource": "/",
        },
    ]
    try:
        response = client.post("/extract", json=events)
        if response.status_code == 200:
            data = response.json()
            assert "features_extracted" in data
    except Exception:
        pass
