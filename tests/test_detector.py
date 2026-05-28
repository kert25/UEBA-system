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

    def test_no_distance_no_travel_flag(self) -> None:
        """Test that None distance doesn't trigger impossible travel."""
        row = pd.Series(
            {
                "hour_of_day": 12,
                "bytes_transferred": 10_000_000,
                "country_code": "Russia",
                "distance_from_previous_km": None,
                "hours_since_last_event": None,
            }
        )
        dims = _classify_anomaly_dimensions(row, score=0.5, profile=None)
        assert "impossible_travel" not in dims

    def test_zero_hours_no_flag(self) -> None:
        """Test that zero hours_since_last_event doesn't trigger flag."""
        row = pd.Series(
            {
                "hour_of_day": 12,
                "bytes_transferred": 10_000_000,
                "country_code": "Russia",
                "distance_from_previous_km": 5000,
                "hours_since_last_event": 0,
            }
        )
        dims = _classify_anomaly_dimensions(row, score=0.5, profile=None)
        assert "impossible_travel" not in dims

    def test_profile_based_time_anomaly(self) -> None:
        """Test profile-based z-score time detection."""
        row = pd.Series(
            {
                "hour_of_day": 3,
                "bytes_transferred": 10_000_000,
                "country_code": "Russia",
            }
        )
        from shared.models import UserProfile

        profile = UserProfile(
            user_id="user_001",
            avg_hour=14.0,
            std_hour=2.0,
            avg_bytes=10_000_000,
            std_bytes=5_000_000,
        )
        dims = _classify_anomaly_dimensions(row, score=0.5, profile=profile)
        assert "time" in dims

    def test_profile_based_volume_anomaly(self) -> None:
        """Test profile-based z-score volume detection."""
        row = pd.Series(
            {
                "hour_of_day": 14,
                "bytes_transferred": 500_000_000,
                "country_code": "Russia",
            }
        )
        from shared.models import UserProfile

        profile = UserProfile(
            user_id="user_001",
            avg_hour=14.0,
            std_hour=1.0,
            avg_bytes=10_000_000,
            std_bytes=5_000_000,
        )
        dims = _classify_anomaly_dimensions(row, score=0.5, profile=profile)
        assert "volume" in dims

    def test_geography_with_profile_common_country(self) -> None:
        """Test geography flagged when country not in profile."""
        row = pd.Series(
            {
                "hour_of_day": 14,
                "bytes_transferred": 10_000_000,
                "country_code": "North Korea",
            }
        )
        from shared.models import UserProfile

        profile = UserProfile(
            user_id="user_001",
            avg_hour=14.0,
            std_hour=1.0,
            avg_bytes=10_000_000,
            std_bytes=1_000_000,
            top_countries=["Russia"],
        )
        dims = _classify_anomaly_dimensions(row, score=0.5, profile=profile)
        assert "geography" in dims

    def test_zero_std_handling(self) -> None:
        """Test behavior when standard deviation is zero."""
        row = pd.Series(
            {
                "hour_of_day": 14,
                "bytes_transferred": 10_000_000,
                "country_code": "Russia",
            }
        )
        from shared.models import UserProfile

        profile = UserProfile(
            user_id="user_001",
            avg_hour=14.0,
            std_hour=0.0,
            avg_bytes=10_000_000,
            std_bytes=0.0,
        )
        dims = _classify_anomaly_dimensions(row, score=0.5, profile=profile)
        # With zero std and same values, no anomaly expected
        assert "time" not in dims
        assert "volume" not in dims
