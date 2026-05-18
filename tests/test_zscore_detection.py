"""Tests for z-score based anomaly detection."""

import pandas as pd

from services.anomaly_detector.detector import _classify_anomaly_dimensions
from shared.models import UserProfile


def _make_profile(
    avg_hour: float = 14.0,
    std_hour: float = 2.0,
    avg_bytes: float = 1_000_000.0,
    std_bytes: float = 500_000.0,
    top_countries: list[str] | None = None,
) -> UserProfile:
    return UserProfile(
        user_id="test_user",
        avg_hour=avg_hour,
        std_hour=std_hour,
        avg_bytes=avg_bytes,
        std_bytes=std_bytes,
        top_countries=top_countries or ["Russia"],
    )


class TestZScoreDetection:
    """Tests for profile-dependent z-score detection."""

    def test_time_anomaly(self) -> None:
        profile = _make_profile(avg_hour=14, std_hour=2)
        row = pd.Series(
            {"hour_of_day": 3, "bytes_transferred": 1_000_000, "country_code": "Russia"}
        )
        dims = _classify_anomaly_dimensions(row, score=0.5, profile=profile)
        assert "time" in dims

    def test_normal_hour(self) -> None:
        profile = _make_profile(avg_hour=14, std_hour=2)
        row = pd.Series(
            {"hour_of_day": 15, "bytes_transferred": 1_000_000, "country_code": "Russia"}
        )
        dims = _classify_anomaly_dimensions(row, score=0.5, profile=profile)
        assert "time" not in dims

    def test_volume_anomaly(self) -> None:
        profile = _make_profile(avg_bytes=1_000_000, std_bytes=500_000)
        row = pd.Series(
            {"hour_of_day": 14, "bytes_transferred": 100_000_000, "country_code": "Russia"}
        )
        dims = _classify_anomaly_dimensions(row, score=0.5, profile=profile)
        assert "volume" in dims

    def test_normal_volume(self) -> None:
        profile = _make_profile(avg_bytes=1_000_000, std_bytes=500_000)
        row = pd.Series(
            {"hour_of_day": 14, "bytes_transferred": 1_200_000, "country_code": "Russia"}
        )
        dims = _classify_anomaly_dimensions(row, score=0.5, profile=profile)
        assert "volume" not in dims

    def test_no_profile_fallback(self) -> None:
        row = pd.Series(
            {"hour_of_day": 14, "bytes_transferred": 1_000_000, "country_code": "Russia"}
        )
        dims = _classify_anomaly_dimensions(row, score=0.5, profile=None)
        assert dims == []

    def test_zero_std_hour(self) -> None:
        profile = _make_profile(avg_hour=14, std_hour=0)
        row = pd.Series(
            {"hour_of_day": 3, "bytes_transferred": 1_000_000, "country_code": "Russia"}
        )
        dims = _classify_anomaly_dimensions(row, score=0.5, profile=profile)
        assert "time" in dims

    def test_zero_std_bytes(self) -> None:
        profile = _make_profile(avg_bytes=1_000_000, std_bytes=0)
        row = pd.Series(
            {"hour_of_day": 14, "bytes_transferred": 100_000_000, "country_code": "Russia"}
        )
        dims = _classify_anomaly_dimensions(row, score=0.5, profile=profile)
        assert "volume" in dims

    def test_geography_anomaly(self) -> None:
        profile = _make_profile(top_countries=["Russia"])
        row = pd.Series(
            {"hour_of_day": 14, "bytes_transferred": 1_000_000, "country_code": "China"}
        )
        dims = _classify_anomaly_dimensions(row, score=0.5, profile=profile)
        assert "geography" in dims

    def test_normal_geography(self) -> None:
        profile = _make_profile(top_countries=["Russia"])
        row = pd.Series(
            {"hour_of_day": 14, "bytes_transferred": 1_000_000, "country_code": "Russia"}
        )
        dims = _classify_anomaly_dimensions(row, score=0.5, profile=profile)
        assert "geography" not in dims
