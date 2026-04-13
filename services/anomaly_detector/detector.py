"""Anomaly detection using the trained Isolation Forest model."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from ml.model import AnomalyModel
from shared.config import settings
from shared.models import AnomalyRecord

logger = logging.getLogger(__name__)

FEATURE_COLUMNS = ["hour_of_day", "day_of_week", "minutes_from_midnight", "bytes_transferred"]


def load_model() -> AnomalyModel:
    """Load the trained Isolation Forest model from disk."""
    model_path = Path(settings.model_path)
    if not model_path.exists():
        raise FileNotFoundError(
            f"Model not found at {model_path}. Run 'python scripts/train_model.py' first."
        )
    return AnomalyModel.load(model_path)


def detect_anomalies(
    features_df: pd.DataFrame,
    model: AnomalyModel | None = None,
    threshold: float | None = None,
) -> list[AnomalyRecord]:
    """Detect anomalies in feature records using the trained model.

    Args:
        features_df: DataFrame with feature columns.
        model: Pre-loaded model. If None, loads from disk.
        threshold: Anomaly score threshold. Defaults to settings.anomaly_threshold.

    Returns:
        List of AnomalyRecord objects for events exceeding the threshold.
    """
    if model is None:
        model = load_model()

    if threshold is None:
        threshold = settings.anomaly_threshold

    # Get anomaly scores
    scores = model.predict(features_df)

    anomalies: list[AnomalyRecord] = []
    for idx, (score, (_, row)) in enumerate(zip(scores, features_df.iterrows())):
        if score > threshold:
            # Determine which dimensions contributed to the anomaly
            dimensions = _classify_anomaly_dimensions(row, score)

            anomaly = AnomalyRecord(
                event_id=row.get("event_id", f"unknown_{idx}"),
                user_id=row.get("user_id", "unknown"),
                anomaly_score=round(float(score), 4),
                timestamp=datetime.now(timezone.utc),
                dimensions=dimensions,
                details=f"Score: {score:.4f}, Threshold: {threshold:.4f}",
            )
            anomalies.append(anomaly)

    logger.info("Detected %d anomalies out of %d events", len(anomalies), len(features_df))
    return anomalies


def _classify_anomaly_dimensions(row: pd.Series, score: float) -> list[str]:
    """Determine which detection dimensions flagged this event as anomalous."""
    dimensions: list[str] = []

    # Time dimension
    hour = row.get("hour_of_day", 12)
    if hour < 5 or hour > 21:
        dimensions.append("time")

    # Volume dimension
    bytes_val = row.get("bytes_transferred", 0)
    if bytes_val > 500_000_000:  # >500 MB
        dimensions.append("volume")

    # Geography — check country_code against typical
    country = row.get("country_code", "")
    unusual_countries = {
        "United States", "China", "Brazil", "Australia", "Nigeria",
        "North Korea", "Iran", "Germany", "United Kingdom", "Japan",
    }
    if country in unusual_countries:
        dimensions.append("geography")

    # If no specific dimension caught it, flag by score alone
    if not dimensions:
        if score > 0.8:
            dimensions = ["time", "volume", "geography"]
        else:
            dimensions = ["unknown"]

    return dimensions
