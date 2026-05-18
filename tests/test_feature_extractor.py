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
