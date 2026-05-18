"""ML module for anomaly detection using Isolation Forest."""

from __future__ import annotations

import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

FEATURE_COLUMNS = [
    "hour_of_day",
    "day_of_week",
    "minutes_from_midnight",
    "bytes_transferred",
]


class AnomalyModel:
    """Wrapper around scikit-learn Isolation Forest for UEBA anomaly detection.

    Usage::

        model = AnomalyModel()
        model.train(df_normal)        # train on normal-only data
        model.save("models/model.joblib")

        model = AnomalyModel.load("models/model.joblib")
        scores = model.predict(df_features)
    """

    def __init__(
        self,
        contamination: float = 0.05,
        random_state: int = 42,
        n_estimators: int = 100,
    ) -> None:
        self.contamination = contamination
        self.random_state = random_state
        self.n_estimators = n_estimators

        self.scaler = StandardScaler()
        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=self.random_state,
        )
        self._is_fitted = False

    # ─── Training ────────────────────────────────────────────────────────

    def train(self, df: pd.DataFrame) -> None:
        """Fit the scaler and train Isolation Forest on normal data only.

        Args:
            df: DataFrame with feature columns (FEATURE_COLUMNS).
        """
        X = self._extract_features(df)
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        self._is_fitted = True
        logger.info(
            "Model trained on %d samples with %d features",
            len(df),
            len(FEATURE_COLUMNS),
        )

    # ─── Prediction ──────────────────────────────────────────────────────

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """Return anomaly scores for each row (higher = more anomalous).

        Args:
            df: DataFrame with feature columns.

        Returns:
            Array of anomaly scores in [0, 1].  Scores > 0.5 are typically anomalous.
        """
        if not self._is_fitted:
            raise RuntimeError("Model must be trained before prediction. Call .train() first.")

        X = self._extract_features(df)
        X_scaled = self.scaler.transform(X)

        # decision_function: lower = more anomalous (can be negative)
        raw_scores = self.model.decision_function(X_scaled)

        # Convert to [0, 1] where 1 = most anomalous
        # Isolation Forest: decision_function returns negative for anomalies
        # We negate so positive = anomalous, then sigmoid-like normalize
        scores = -raw_scores
        scores = (scores - scores.min()) / (scores.max() - scores.min() + 1e-8)
        return scores

    def predict_labels(self, df: pd.DataFrame) -> np.ndarray:
        """Return binary labels: 1 = anomaly, 0 = normal."""
        if not self._is_fitted:
            raise RuntimeError("Model must be trained before prediction.")

        X = self._extract_features(df)
        X_scaled = self.scaler.transform(X)
        # Isolation Forest returns -1 for anomalies, 1 for normal
        labels = self.model.predict(X_scaled)
        return (labels == -1).astype(int)

    # ─── Persistence ─────────────────────────────────────────────────────

    def save(self, path: str | Path) -> None:
        """Serialize model, scaler, and fitted flag to disk."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "model": self.model,
                "scaler": self.scaler,
                "is_fitted": self._is_fitted,
                "contamination": self.contamination,
                "random_state": self.random_state,
                "n_estimators": self.n_estimators,
            },
            path,
        )
        logger.info("Model saved to %s", path)

    @classmethod
    def load(cls, path: str | Path) -> AnomalyModel:
        """Deserialize a previously saved model."""
        data = joblib.load(path)
        instance = cls(
            contamination=data["contamination"],
            random_state=data["random_state"],
            n_estimators=data["n_estimators"],
        )
        instance.model = data["model"]
        instance.scaler = data["scaler"]
        instance._is_fitted = data["is_fitted"]
        logger.info("Model loaded from %s", path)
        return instance

    # ─── Internal ────────────────────────────────────────────────────────

    @staticmethod
    def _extract_features(df: pd.DataFrame) -> pd.DataFrame:
        """Extract only the feature columns needed for ML."""
        missing = [c for c in FEATURE_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(f"Missing feature columns: {missing}")
        return df[FEATURE_COLUMNS]

    def get_feature_contributions(self, features_array: np.ndarray) -> dict[str, float]:
        """Estimate each feature's contribution to the anomaly score.

        Uses a permutation-based approach: replace each feature with its median
        value and measure the change in score.

        Args:
            features_array: 1D array of feature values (length = len(FEATURE_COLUMNS)).

        Returns:
            Dict mapping feature name to normalized contribution (sum ≈ 1.0).
        """
        if self.model is None:
            return {}

        base_score = self.model.score_samples(features_array.reshape(1, -1))[0]

        contributions = {}
        for i, name in enumerate(FEATURE_COLUMNS):
            perturbed = features_array.copy()
            median_val = np.median(
                self.scaler.data_min_ if hasattr(self.scaler, "data_min_") else 0
            )
            perturbed[i] = median_val
            perturbed_score = self.model.score_samples(perturbed.reshape(1, -1))[0]
            contributions[name] = abs(perturbed_score - base_score)

        total = sum(contributions.values())
        if total > 0:
            contributions = {k: round(v / total, 3) for k, v in contributions.items()}

        return contributions
