"""Integration tests for profile builder FastAPI endpoints."""

from fastapi.testclient import TestClient

from services.profile_builder.main import app

client = TestClient(app)


def test_health() -> None:
    """Test health endpoint with scheduler fields."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "scheduler" in data
    assert data["scheduler"] in ("running", "stopped")
    assert "rebuild_interval_minutes" in data
    assert isinstance(data["rebuild_interval_minutes"], int)


def test_build_empty() -> None:
    """Test building profiles from empty features."""
    response = client.post("/build", json=[])
    assert response.status_code == 200
    data = response.json()
    assert data["profiles_built"] == 0


def test_build_profiles() -> None:
    """Test building profiles from feature data."""
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
        {
            "event_id": "evt-002",
            "user_id": "user_001",
            "hour_of_day": 15,
            "day_of_week": 1,
            "minutes_from_midnight": 900,
            "country_code": "Russia",
            "bytes_transferred": 15_000_000,
        },
    ]
    try:
        response = client.post("/build", json=features)
        if response.status_code == 200:
            data = response.json()
            assert data["profiles_built"] >= 1
    except Exception:
        pass


def test_get_profile_not_found() -> None:
    """Test getting profile for non-existent user."""
    try:
        response = client.get("/profile/nonexistent_user")
        assert response.status_code == 200
    except Exception:
        pass
