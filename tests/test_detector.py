"""Tests for anomaly detector logic."""

from datetime import datetime, timezone
import pandas as pd
import pytest

from services.anomaly_detector.detector import _classify_anomaly_dimensions


class TestClassifyAnomalyDimensions:
    """Tests for anomaly dimension classification."""

    def test_time_anomaly(self) -> None:
        """Test that night hours are flagged as time anomaly."""
        row = pd.Series({"hour_of_day": 2, "bytes_transferred": 10_000_000, "country_code": "Russia"})
        dims = _classify_anomaly_dimensions(row, score=0.5)
        assert "time" in dims

    def test_volume_anomaly(self) -> None:
        """Test that large transfers are flagged as volume anomaly."""
        row = pd.Series({"hour_of_day": 14, "bytes_transferred": 1_000_000_000, "country_code": "Russia"})
        dims = _classify_anomaly_dimensions(row, score=0.5)
        assert "volume" in dims

    def test_geography_anomaly(self) -> None:
        """Test that unusual countries are flagged."""
        row = pd.Series({"hour_of_day": 14, "bytes_transferred": 10_000_000, "country_code": "North Korea"})
        dims = _classify_anomaly_dimensions(row, score=0.5)
        assert "geography" in dims

    def test_high_score_flags_all(self) -> None:
        """Test that very high scores flag all dimensions."""
        row = pd.Series({"hour_of_day": 12, "bytes_transferred": 10_000_000, "country_code": "Russia"})
        dims = _classify_anomaly_dimensions(row, score=0.9)
        assert len(dims) >= 1

    def test_normal_event_unknown(self) -> None:
        """Test that normal-looking events with moderate scores get 'unknown'."""
        row = pd.Series({"hour_of_day": 12, "bytes_transferred": 10_000_000, "country_code": "Russia"})
        dims = _classify_anomaly_dimensions(row, score=0.5)
        assert dims == ["unknown"]
