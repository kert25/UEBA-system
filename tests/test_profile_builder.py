"""Tests for the profile builder."""

import pandas as pd

from services.profile_builder.builder import build_profiles_from_features


def _make_features_df(users: list[str] | None = None) -> pd.DataFrame:
    """Create a features DataFrame for testing."""
    if users is None:
        users = ["user_001"] * 10

    records = []
    for i, user in enumerate(users):
        records.append(
            {
                "event_id": f"evt-{i}",
                "user_id": user,
                "hour_of_day": 10 + (i % 8),  # 10-17
                "day_of_week": i % 5,
                "minutes_from_midnight": 600 + (i % 8) * 60,
                "country_code": "Russia",
                "bytes_transferred": 10_000_000 + i * 1_000_000,
            }
        )
    return pd.DataFrame(records)


class TestBuildProfiles:
    """Tests for profile building."""

    def test_single_user_profile(self) -> None:
        """Test building profile for a single user."""
        df = _make_features_df()
        profiles = build_profiles_from_features(df)
        assert len(profiles) == 1
        assert profiles[0].user_id == "user_001"
        assert 10 <= profiles[0].avg_hour <= 17

    def test_multiple_users(self) -> None:
        """Test building profiles for multiple users."""
        users = ["user_001"] * 5 + ["user_002"] * 5
        df = _make_features_df(users)
        profiles = build_profiles_from_features(df)
        assert len(profiles) == 2

    def test_profile_stats(self) -> None:
        """Test that profile contains expected statistics."""
        df = _make_features_df()
        profiles = build_profiles_from_features(df)
        profile = profiles[0]

        assert profile.avg_hour > 0
        assert profile.std_hour >= 0
        assert profile.avg_bytes > 0
        assert profile.std_bytes >= 0
        assert len(profile.top_countries) > 0

    def test_top_countries(self) -> None:
        """Test top countries list."""
        records = []
        countries = ["Russia"] * 5 + ["Belarus"] * 3
        for i, country in enumerate(countries):
            records.append(
                {
                    "event_id": f"evt-{i}",
                    "user_id": "user_001",
                    "hour_of_day": 12,
                    "day_of_week": 1,
                    "minutes_from_midnight": 720,
                    "country_code": country,
                    "bytes_transferred": 10_000_000,
                }
            )
        df = pd.DataFrame(records)
        profiles = build_profiles_from_features(df)
        assert profiles[0].top_countries[0] == "Russia"

    def test_missing_columns_raises(self) -> None:
        """Test that missing columns raise ValueError."""
        import pytest

        bad_df = pd.DataFrame({"user_id": ["user_001"]})
        with pytest.raises(ValueError, match="Missing columns"):
            build_profiles_from_features(bad_df)
