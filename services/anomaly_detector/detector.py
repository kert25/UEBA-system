"""Anomaly detection using the trained Isolation Forest model."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from ml.model import AnomalyModel
from shared.config import settings
from shared.es_client import INDEX_PROFILES, get_es_client
from shared.models import AnomalyRecord, UserProfile

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


def _load_user_profile(user_id: str) -> UserProfile | None:
    """Load user profile from ES. Return None if not found."""
    try:
        client = get_es_client()
        result = client.get(index=INDEX_PROFILES, id=user_id, ignore=404)
        if result.get("found"):
            return UserProfile(**result["_source"])
        return None
    except Exception:
        return None


def _check_impossible_travel(row: pd.Series) -> bool:
    """Check for impossible travel based on distance and time.

    Max speed: ~900 km/h (Boeing 737 cruise).
    If distance > 1000 km and time < 2 hours → impossible_travel.
    """
    distance = row.get("distance_from_previous_km")
    hours = row.get("hours_since_last_event")

    if distance is None or hours is None or hours == 0:
        return False

    max_speed_kmh = 900
    min_time_hours = distance / max_speed_kmh
    return hours < (min_time_hours + 0.5)


def _classify_anomaly_dimensions(
    row: pd.Series,
    score: float,
    profile: UserProfile | None,
) -> list[str]:
    """Classify anomaly dimensions based on z-score from user profile."""
    dimensions: list[str] = []

    if profile is None:
        if row.get("hour_of_day", 12) < 5 or row.get("hour_of_day", 12) > 21:
            dimensions.append("time")
        if row.get("bytes_transferred", 0) > 500_000_000:
            dimensions.append("volume")
        if _check_impossible_travel(row):
            dimensions.append("impossible_travel")
        return dimensions

    hour = row.get("hour_of_day", 12)
    if profile.std_hour > 0:
        z_hour = abs(hour - profile.avg_hour) / profile.std_hour
    else:
        z_hour = abs(hour - profile.avg_hour)
    if z_hour > 2.0:
        dimensions.append("time")

    bytes_val = row.get("bytes_transferred", 0)
    if profile.std_bytes > 0:
        z_bytes = abs(bytes_val - profile.avg_bytes) / profile.std_bytes
    else:
        z_bytes = abs(bytes_val - profile.avg_bytes) / max(profile.avg_bytes, 1)
    if z_bytes > 2.0:
        dimensions.append("volume")

    if _check_impossible_travel(row):
        dimensions.append("impossible_travel")
    elif profile.top_countries and row.get("country_code", "") not in profile.top_countries:
        dimensions.append("geography")

    return dimensions


def _compute_feature_contributions(
    model: AnomalyModel,
    row: pd.Series,
) -> tuple[dict[str, float], list[str]]:
    """Compute per-feature contribution to anomaly score."""
    feature_names = ["hour_of_day", "day_of_week", "minutes_from_midnight", "bytes_transferred"]
    feature_values = np.array([row.get(f, 0) for f in feature_names], dtype=float)

    try:
        contributions = model.get_feature_contributions(feature_values)
    except Exception:
        contributions = {name: 1.0 / len(feature_names) for name in feature_names}

    top_features = sorted(contributions, key=contributions.get, reverse=True)[:3]
    return contributions, top_features


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

    scores = model.predict(features_df)

    anomalies: list[AnomalyRecord] = []
    for idx, (score, (_, row)) in enumerate(zip(scores, features_df.iterrows())):
        is_anomaly = score > threshold
        is_impossible = _check_impossible_travel(row)

        if is_anomaly or is_impossible:
            user_id = row.get("user_id", "unknown")
            profile = _load_user_profile(user_id)

            dimensions = _classify_anomaly_dimensions(row, score, profile)
            contributions, top_features = _compute_feature_contributions(model, row)

            final_score = max(float(score), 0.8) if is_impossible and not is_anomaly else float(score)

            anomaly = AnomalyRecord(
                event_id=row.get("event_id", f"unknown_{idx}"),
                user_id=user_id,
                anomaly_score=round(final_score, 4),
                timestamp=datetime.now(UTC),
                dimensions=dimensions,
                details=f"Score: {score:.4f}, Threshold: {threshold:.4f}",
                feature_contributions=contributions,
                top_features=top_features,
            )
            anomalies.append(anomaly)

    logger.info("Detected %d anomalies out of %d events", len(anomalies), len(features_df))
    return anomalies
