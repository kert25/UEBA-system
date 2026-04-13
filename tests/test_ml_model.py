"""Tests for the ML anomaly detection model."""

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml.model import AnomalyModel, FEATURE_COLUMNS


def _make_normal_df(n: int = 100) -> pd.DataFrame:
    """Create a DataFrame with normal-looking features."""
    return pd.DataFrame(
        {
            "event_id": [f"evt-{i}" for i in range(n)],
            "user_id": [f"user_{i % 10:03d}" for i in range(n)],
            "hour_of_day": np.random.randint(9, 18, n),
            "day_of_week": np.random.randint(0, 5, n),
            "minutes_from_midnight": np.random.randint(540, 1080, n),
            "country_code": ["Russia"] * n,
            "bytes_transferred": np.random.randint(1_000_000, 50_000_000, n),
        }
    )


def _make_anomalous_df() -> pd.DataFrame:
    """Create a DataFrame with clearly anomalous features."""
    return pd.DataFrame(
        {
            "event_id": ["anom-1"],
            "user_id": ["user_001"],
            "hour_of_day": [2],  # 2 AM
            "day_of_week": [6],  # Sunday
            "minutes_from_midnight": [120],
            "country_code": ["North Korea"],
            "bytes_transferred": [2_000_000_000],  # 2 GB
        }
    )


class TestAnomalyModel:
    """Tests for AnomalyModel class."""

    def test_train_and_predict(self) -> None:
        """Test basic training and prediction."""
        df = _make_normal_df(200)
        model = AnomalyModel(contamination=0.05, random_state=42)
        model.train(df)

        scores = model.predict(df)
        assert len(scores) == 200
        assert scores.min() >= 0.0
        assert scores.max() <= 1.0

    def test_predict_anomalous(self) -> None:
        """Test that anomalous data is scored differently from normal."""
        df_normal = _make_normal_df(500)
        model = AnomalyModel(contamination=0.05, random_state=42)
        model.train(df_normal)

        df_anomalous = _make_anomalous_df()
        labels = model.predict_labels(df_anomalous)
        # The anomalous event should be detected as anomaly (label=1)
        assert labels[0] == 1

    def test_predict_labels(self) -> None:
        """Test binary label prediction."""
        df = _make_normal_df(200)
        model = AnomalyModel(contamination=0.05, random_state=42)
        model.train(df)

        labels = model.predict_labels(df)
        assert set(labels.flatten()).issubset({0, 1})

    def test_model_not_fitted_raises(self) -> None:
        """Test that prediction without training raises RuntimeError."""
        model = AnomalyModel()
        df = _make_normal_df(10)
        with pytest.raises(RuntimeError, match="trained"):
            model.predict(df)

    def test_save_and_load(self) -> None:
        """Test model serialization and deserialization."""
        df = _make_normal_df(100)
        model = AnomalyModel(contamination=0.05, random_state=42)
        model.train(df)

        with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as f:
            model.save(f.name)
            loaded = AnomalyModel.load(f.name)

        # Predictions should match
        df_test = _make_normal_df(10)
        scores_orig = model.predict(df_test)
        scores_loaded = loaded.predict(df_test)
        np.testing.assert_array_almost_equal(scores_orig, scores_loaded)

    def test_missing_feature_columns_raises(self) -> None:
        """Test that missing feature columns raise ValueError."""
        df = pd.DataFrame({"hour_of_day": [10]})  # missing other columns
        model = AnomalyModel()
        model.train(_make_normal_df(100))
        with pytest.raises(ValueError, match="Missing feature columns"):
            model.predict(df)

    def test_save_creates_directory(self) -> None:
        """Test that save() creates parent directories."""
        df = _make_normal_df(50)
        model = AnomalyModel()
        model.train(df)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nested" / "dir" / "model.joblib"
            model.save(path)
            assert path.exists()
