"""Feature extraction from raw events."""

from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd

from shared.models import FeatureRecord

logger = logging.getLogger(__name__)


def extract_features_from_events(events: list[dict]) -> list[FeatureRecord]:
    """Extract ML features from a list of raw event dicts.

    Features:
      - hour_of_day (0-23)
      - day_of_week (0=Mon, 6=Sun)
      - minutes_from_midnight (0-1439)
      - country_code
      - bytes_transferred

    Args:
        events: List of raw event dicts from Elasticsearch.

    Returns:
        List of FeatureRecord objects.
    """
    records: list[FeatureRecord] = []

    for event in events:
        ts = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))

        record = FeatureRecord(
            event_id=event["event_id"],
            user_id=event["user_id"],
            hour_of_day=ts.hour,
            day_of_week=ts.weekday(),
            minutes_from_midnight=ts.hour * 60 + ts.minute,
            country_code=event.get("country", "Unknown"),
            bytes_transferred=event.get("bytes_transferred", 0),
        )
        records.append(record)

    logger.info("Extracted features for %d events", len(records))
    return records


def compute_deviation_features(df_features: pd.DataFrame, profiles: dict[str, dict]) -> pd.DataFrame:
    """Add deviation-from-mean features using user profiles.

    Args:
        df_features: DataFrame with feature columns.
        profiles: Dict mapping user_id -> profile dict with avg_hour, std_hour, etc.

    Returns:
        DataFrame with added deviation columns.
    """
    deviations = []
    for _, row in df_features.iterrows():
        user = row["user_id"]
        profile = profiles.get(user, {})

        avg_hour = profile.get("avg_hour", row["hour_of_day"])
        std_hour = max(profile.get("std_hour", 1), 1)  # avoid div by zero

        deviations.append({
            "hour_deviation": abs(row["hour_of_day"] - avg_hour) / std_hour,
        })

    df_features["hour_deviation"] = [d["hour_deviation"] for d in deviations]
    return df_features


def events_to_df(records: list[FeatureRecord]) -> pd.DataFrame:
    """Convert FeatureRecord list to pandas DataFrame."""
    return pd.DataFrame([r.model_dump() for r in records])
