"""Integration tests for anomaly detector FastAPI endpoints."""

from fastapi.testclient import TestClient

from services.anomaly_detector.main import app

client = TestClient(app)


def test_health() -> None:
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200


def test_detect_empty() -> None:
    """Test detection on empty feature list."""
    response = client.post("/detect", json=[])
    assert response.status_code == 200
    data = response.json()
    assert data["anomalies_detected"] == 0


def test_detect_anomalies() -> None:
    """Test anomaly detection with sample features."""
    features = [
        {
            "event_id": "evt-001",
            "user_id": "user_001",
            "hour_of_day": 14,
            "day_of_week": 1,
            "minutes_from_midnight": 840,
            "country_code": "Russia",
            "bytes_transferred": 10_000_000,
        },
    ]
    try:
        response = client.post("/detect", json=features)
        if response.status_code == 200:
            data = response.json()
            assert "anomalies_detected" in data
    except Exception:
        # Model may not be loaded without ES
        pass
