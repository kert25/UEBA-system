"""Feature extraction from raw events."""

from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd

from shared.geo_data import get_coordinates, haversine
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
      - latitude, longitude (from country/city lookup)
      - distance_from_previous_km (haversine distance)
      - hours_since_last_event

    Args:
        events: List of raw event dicts from Elasticsearch.

    Returns:
        List of FeatureRecord objects.
    """
    records: list[FeatureRecord] = []

    # Group events by user_id to compute distance/time since last event
    user_last_event: dict[str, tuple[float, float, datetime]] = {}

    # Sort events by timestamp to ensure correct ordering
    sorted_events = sorted(events, key=lambda e: e.get("timestamp", ""))

    for event in sorted_events:
        ts = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
        user_id = event["user_id"]
        country = event.get("country", "Unknown")
        city = event.get("city", "")

        lat, lon = get_coordinates(country, city if city else None)

        distance_km = None
        hours_since = None

        if user_id in user_last_event:
            prev_lat, prev_lon, prev_ts = user_last_event[user_id]
            distance_km = round(haversine(prev_lat, prev_lon, lat, lon), 2)
            hours_since = round((ts - prev_ts).total_seconds() / 3600, 4)

        user_last_event[user_id] = (lat, lon, ts)

        record = FeatureRecord(
            event_id=event["event_id"],
            user_id=user_id,
            hour_of_day=ts.hour,
            day_of_week=ts.weekday(),
            minutes_from_midnight=ts.hour * 60 + ts.minute,
            country_code=country,
            bytes_transferred=event.get("bytes_transferred", 0),
            latitude=lat,
            longitude=lon,
            distance_from_previous_km=distance_km,
            hours_since_last_event=hours_since,
        )
        records.append(record)

    logger.info("Extracted features for %d events", len(records))
    return records


def compute_deviation_features(
    df_features: pd.DataFrame, profiles: dict[str, dict]
) -> pd.DataFrame:
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
        std_hour = max(profile.get("std_hour", 1), 1)

        avg_bytes = profile.get("avg_bytes", row["bytes_transferred"])
        std_bytes = max(profile.get("std_bytes", 1), 1)

        deviations.append(
            {
                "hour_deviation": abs(row["hour_of_day"] - avg_hour) / std_hour,
                "bytes_deviation": abs(row["bytes_transferred"] - avg_bytes) / std_bytes,
            }
        )

    df_features["hour_deviation"] = [d["hour_deviation"] for d in deviations]
    df_features["bytes_deviation"] = [d["bytes_deviation"] for d in deviations]
    return df_features


def events_to_df(records: list[FeatureRecord]) -> pd.DataFrame:
    """Convert FeatureRecord list to pandas DataFrame."""
    return pd.DataFrame([r.model_dump() for r in records])
