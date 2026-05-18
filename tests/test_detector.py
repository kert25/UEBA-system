"""Tests for anomaly detector logic."""

import pandas as pd

from services.anomaly_detector.detector import _classify_anomaly_dimensions


class TestClassifyAnomalyDimensions:
    """Tests for anomaly dimension classification."""

    def test_time_anomaly(self) -> None:
        """Test that night hours are flagged as time anomaly."""
        row = pd.Series(
            {"hour_of_day": 2, "bytes_transferred": 10_000_000, "country_code": "Russia"}
        )
        dims = _classify_anomaly_dimensions(row, score=0.5, profile=None)
        assert "time" in dims

    def test_volume_anomaly(self) -> None:
        """Test that large transfers are flagged as volume anomaly."""
        row = pd.Series(
            {"hour_of_day": 14, "bytes_transferred": 1_000_000_000, "country_code": "Russia"}
        )
        dims = _classify_anomaly_dimensions(row, score=0.5, profile=None)
        assert "volume" in dims

    def test_geography_anomaly(self) -> None:
        """Test that unusual countries are flagged."""
        row = pd.Series(
            {"hour_of_day": 14, "bytes_transferred": 10_000_000, "country_code": "North Korea"}
        )
        dims = _classify_anomaly_dimensions(row, score=0.5, profile=None)
        assert "geography" not in dims

    def test_no_profile_fallback(self) -> None:
        """Test fallback behavior when profile is None."""
        row = pd.Series(
            {"hour_of_day": 12, "bytes_transferred": 10_000_000, "country_code": "Russia"}
        )
        dims = _classify_anomaly_dimensions(row, score=0.5, profile=None)
        assert dims == []

    def test_impossible_travel(self) -> None:
        """Test impossible travel detection."""
        row = pd.Series(
            {
                "hour_of_day": 12,
                "bytes_transferred": 10_000_000,
                "country_code": "Russia",
                "distance_from_previous_km": 5000,
                "hours_since_last_event": 1,
            }
        )
        dims = _classify_anomaly_dimensions(row, score=0.5, profile=None)
        assert "impossible_travel" in dims

    def test_normal_travel(self) -> None:
        """Test normal travel is not flagged."""
        row = pd.Series(
            {
                "hour_of_day": 12,
                "bytes_transferred": 10_000_000,
                "country_code": "Russia",
                "distance_from_previous_km": 500,
                "hours_since_last_event": 5,
            }
        )
        dims = _classify_anomaly_dimensions(row, score=0.5, profile=None)
        assert "impossible_travel" not in dims
