"""Tests for the feature extractor."""

import pandas as pd

from services.feature_extractor.extractor import (
    events_to_df,
    extract_features_from_events,
)


def _make_raw_event(hour: int = 14, country: str = "Russia", bytes_val: int = 10_000_000) -> dict:
    return {
        "event_id": "evt-001",
        "timestamp": f"2026-04-13T{hour:02d}:30:00Z",
        "user_id": "user_001",
        "ip_address": "192.168.1.1",
        "country": country,
        "city": "Moscow",
        "bytes_transferred": bytes_val,
        "action_type": "login",
        "resource": "/api/data",
    }


class TestExtractFeatures:
    """Tests for feature extraction."""

    def test_extract_hour(self) -> None:
        """Test that hour is correctly extracted."""
        events = [_make_raw_event(hour=10)]
        features = extract_features_from_events(events)
        assert features[0].hour_of_day == 10

    def test_extract_day_of_week(self) -> None:
        """Test day of week extraction (2026-04-13 is Monday = 0)."""
        events = [_make_raw_event()]
        features = extract_features_from_events(events)
        assert features[0].day_of_week == 0  # Monday

    def test_extract_minutes_from_midnight(self) -> None:
        """Test minutes_from_midnight calculation."""
        events = [_make_raw_event(hour=14)]  # 14:30
        features = extract_features_from_events(events)
        assert features[0].minutes_from_midnight == 14 * 60 + 30

    def test_extract_bytes(self) -> None:
        """Test bytes_transferred extraction."""
        events = [_make_raw_event(bytes_val=50_000_000)]
        features = extract_features_from_events(events)
        assert features[0].bytes_transferred == 50_000_000

    def test_extract_multiple_events(self) -> None:
        """Test extracting features from multiple events."""
        events = [
            _make_raw_event(hour=9),
            _make_raw_event(hour=15),
            _make_raw_event(hour=21),
        ]
        features = extract_features_from_events(events)
        assert len(features) == 3
        assert features[0].hour_of_day == 9
        assert features[1].hour_of_day == 15

    def test_events_to_df(self) -> None:
        """Test conversion to DataFrame."""
        events = [_make_raw_event()]
        features = extract_features_from_events(events)
        df = events_to_df(features)
        assert isinstance(df, pd.DataFrame)
        assert "hour_of_day" in df.columns
        assert len(df) == 1

    def test_extract_features_with_geo(self) -> None:
        """Test that geo coordinates are extracted."""
        events = [_make_raw_event(country="Russia", hour=14)]
        features = extract_features_from_events(events)
        assert features[0].latitude == 55.7558
        assert features[0].longitude == 37.6173
        assert features[0].distance_from_previous_km is None

    def test_extract_features_distance(self) -> None:
        """Test haversine distance between consecutive events."""
        events = [
            _make_raw_event(country="Russia", hour=14),
            _make_raw_event(country="United States", hour=15),
        ]
        features = extract_features_from_events(events)
        assert features[0].distance_from_previous_km is None
        assert features[1].distance_from_previous_km is not None
        assert features[1].distance_from_previous_km > 0

    def test_extract_unknown_country(self) -> None:
        """Test extraction with unknown country."""
        events = [_make_raw_event(country="Atlantis")]
        features = extract_features_from_events(events)
        assert features[0].latitude == 0.0
        assert features[0].longitude == 0.0


class TestComputeDeviationFeatures:
    """Tests for deviation features computation."""

    def test_basic_deviation(self) -> None:
        """Test basic deviation features calculation."""
        from services.feature_extractor.extractor import compute_deviation_features

        df = pd.DataFrame(
            {
                "user_id": ["user_001", "user_002"],
                "hour_of_day": [14, 3],
                "bytes_transferred": [10_000_000, 500_000_000],
            }
        )
        profiles = {
            "user_001": {
                "avg_hour": 12,
                "std_hour": 2,
                "avg_bytes": 5_000_000,
                "std_bytes": 2_000_000,
            },
            "user_002": {
                "avg_hour": 14,
                "std_hour": 1,
                "avg_bytes": 10_000_000,
                "std_bytes": 5_000_000,
            },
        }
        result = compute_deviation_features(df, profiles)
        assert "hour_deviation" in result.columns
        assert "bytes_deviation" in result.columns
        assert result["hour_deviation"].iloc[0] >= 0
        assert result["bytes_deviation"].iloc[0] >= 0

    def test_no_profile_fallback(self) -> None:
        """Test fallback when no profile exists."""
        from services.feature_extractor.extractor import compute_deviation_features

        df = pd.DataFrame(
            {
                "user_id": ["no_such_user"],
                "hour_of_day": [10],
                "bytes_transferred": [1_000_000],
            }
        )
        result = compute_deviation_features(df, {})
        assert result["hour_deviation"].iloc[0] == 0.0
        assert result["bytes_deviation"].iloc[0] == 0.0
