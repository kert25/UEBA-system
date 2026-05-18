"""Tests for ML model interpretability."""

import numpy as np
import pandas as pd
import pytest

from ml.model import FEATURE_COLUMNS, AnomalyModel


@pytest.fixture
def trained_model() -> AnomalyModel:
    model = AnomalyModel()
    df = pd.DataFrame(
        {
            "hour_of_day": [10, 11, 12, 13, 14],
            "day_of_week": [1, 2, 3, 4, 5],
            "minutes_from_midnight": [600, 660, 720, 780, 840],
            "bytes_transferred": [1000, 2000, 3000, 4000, 5000],
        }
    )
    model.train(df)
    return model


class TestFeatureContributions:
    """Tests for feature contribution calculation."""

    def test_contributions_shape(self, trained_model: AnomalyModel) -> None:
        features = np.array([12, 3, 720, 3000], dtype=float)
        contribs = trained_model.get_feature_contributions(features)
        assert len(contribs) == len(FEATURE_COLUMNS)
        for name in FEATURE_COLUMNS:
            assert name in contribs

    def test_contributions_sum(self, trained_model: AnomalyModel) -> None:
        features = np.array([12, 3, 720, 3000], dtype=float)
        contribs = trained_model.get_feature_contributions(features)
        assert sum(contribs.values()) == pytest.approx(1.0, abs=0.01)

    def test_no_model(self) -> None:
        model = AnomalyModel()
        model.model = None
        features = np.array([12, 3, 720, 3000], dtype=float)
        assert model.get_feature_contributions(features) == {}

    def test_normal_record(self, trained_model: AnomalyModel) -> None:
        features = np.array([12, 3, 720, 3000], dtype=float)
        contribs = trained_model.get_feature_contributions(features)
        assert max(contribs.values()) < 0.9

    def test_extreme_record(self, trained_model: AnomalyModel) -> None:
        features = np.array([3, 0, 180, 100_000_000], dtype=float)
        contribs = trained_model.get_feature_contributions(features)
        assert sum(contribs.values()) == pytest.approx(1.0, abs=0.01)
