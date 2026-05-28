"""Edge-case tests for anomaly detector (covering remaining gaps)."""

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from ml.model import AnomalyModel
from services.anomaly_detector.detector import (
    _compute_feature_contributions,
    _load_user_profile,
    load_model,
)


def _make_test_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_id": ["evt-001"],
            "user_id": ["user_001"],
            "hour_of_day": [14],
            "day_of_week": [1],
            "minutes_from_midnight": [840],
            "country_code": ["Russia"],
            "bytes_transferred": [10_000_000],
        }
    )


class TestLoadModel:
    """Tests for model loading edge cases."""

    def test_load_model_file_not_found(self) -> None:
        """Test that load_model raises when model file is missing."""
        with patch("services.anomaly_detector.detector.settings") as mock_settings:
            mock_settings.model_path = "/nonexistent/path/model.joblib"
            with pytest.raises(FileNotFoundError, match="Model not found"):
                load_model()

    def test_load_model_success(self) -> None:
        """Test successful model loading."""
        df = _make_test_df()
        model = AnomalyModel(contamination=0.05, random_state=42)
        model.train(df)

        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as f:
            model.save(f.name)

        with patch("services.anomaly_detector.detector.settings") as mock_settings:
            mock_settings.model_path = f.name
            loaded = load_model()
            assert loaded is not None
            assert loaded._is_fitted


class TestLoadUserProfile:
    """Tests for user profile loading."""

    def test_load_user_profile_not_found(self) -> None:
        """Test when profile is not found (returns None)."""
        mock_client = MagicMock()
        mock_client.get.return_value = {"found": False}

        with patch("services.anomaly_detector.detector.get_es_client", return_value=mock_client):
            result = _load_user_profile("nonexistent")
            assert result is None

    def test_load_user_profile_error_returns_none(self) -> None:
        """Test that ES error returns None gracefully."""
        mock_client = MagicMock()
        mock_client.get.side_effect = Exception("ES connection error")

        with patch("services.anomaly_detector.detector.get_es_client", return_value=mock_client):
            result = _load_user_profile("user_001")
            assert result is None


class TestComputeFeatureContributions:
    """Tests for feature contributions computation."""

    def test_contributions_error_fallback(self) -> None:
        """Test fallback when get_feature_contributions raises."""
        model = MagicMock()
        model.get_feature_contributions.side_effect = Exception("Error")

        row = pd.Series(
            {
                "hour_of_day": 14,
                "day_of_week": 1,
                "minutes_from_midnight": 840,
                "bytes_transferred": 10_000_000,
            }
        )
        contributions, top_features = _compute_feature_contributions(model, row)
        assert len(contributions) == 4
        assert len(top_features) == 3
        assert abs(sum(contributions.values()) - 1.0) < 0.01

    def test_contributions_success(self) -> None:
        """Test successful contribution computation."""
        model = MagicMock()
        model.get_feature_contributions.return_value = {
            "hour_of_day": 0.5,
            "day_of_week": 0.2,
            "minutes_from_midnight": 0.2,
            "bytes_transferred": 0.1,
        }

        row = pd.Series(
            {
                "hour_of_day": 3,
                "day_of_week": 6,
                "minutes_from_midnight": 180,
                "bytes_transferred": 500_000_000,
            }
        )
        contributions, top_features = _compute_feature_contributions(model, row)
        assert contributions["hour_of_day"] == 0.5
        assert top_features[0] == "hour_of_day"


class TestDetectAnomalies:
    """Tests for the detect_anomalies function."""

    def _make_model(self) -> AnomalyModel:
        df = _make_test_df()
        df2 = pd.concat([df] * 50, ignore_index=True)
        df2["hour_of_day"] = np.random.randint(9, 18, 50)
        model = AnomalyModel(contamination=0.05, random_state=42)
        model.train(df2)
        return model

    def test_detect_normal_no_anomalies(self) -> None:
        """Test detection with normal data returns no anomalies."""
        from services.anomaly_detector.detector import detect_anomalies

        model = self._make_model()
        df = pd.DataFrame(
            {
                "event_id": ["evt-001"],
                "user_id": ["user_001"],
                "hour_of_day": [14],
                "day_of_week": [1],
                "minutes_from_midnight": [840],
                "country_code": ["Russia"],
                "bytes_transferred": [10_000_000],
            }
        )
        result = detect_anomalies(df, model=model, threshold=0.99)
        assert len(result) == 0

    def test_detect_with_impossible_travel(self) -> None:
        """Test detection where impossible travel triggers anomaly even with low score."""
        from services.anomaly_detector.detector import detect_anomalies

        model = self._make_model()
        df = pd.DataFrame(
            {
                "event_id": ["evt-impossible"],
                "user_id": ["user_001"],
                "hour_of_day": [14],
                "day_of_week": [1],
                "minutes_from_midnight": [840],
                "country_code": ["Russia"],
                "bytes_transferred": [10_000_000],
                "distance_from_previous_km": [7500],
                "hours_since_last_event": [0.5],
            }
        )
        with patch("services.anomaly_detector.detector._load_user_profile", return_value=None):
            result = detect_anomalies(df, model=model, threshold=0.99)
            assert len(result) >= 1
            assert "impossible_travel" in result[0].dimensions
