"""Build and update user behavior profiles from features."""

from __future__ import annotations

import logging
from collections import Counter
from datetime import UTC, datetime

import pandas as pd

from shared.models import UserProfile

logger = logging.getLogger(__name__)


def build_profiles_from_features(features_df: pd.DataFrame) -> list[UserProfile]:
    """Build statistical profiles for each user from their feature records.

    For each user computes:
      - avg_hour, std_hour: mean and std deviation of access hour
      - avg_bytes, std_bytes: mean and std deviation of bytes transferred
      - top_countries: most frequently accessed countries

    Args:
        features_df: DataFrame with columns: user_id, hour_of_day, bytes_transferred, country_code.

    Returns:
        List of UserProfile objects, one per user.
    """
    required = {"user_id", "hour_of_day", "bytes_transferred", "country_code"}
    missing = required - set(features_df.columns)
    if missing:
        raise ValueError(f"Missing columns in features DataFrame: {missing}")

    profiles: list[UserProfile] = []

    for user_id, group in features_df.groupby("user_id"):
        hours = group["hour_of_day"].astype(float)
        bytes_vals = group["bytes_transferred"].astype(float)
        countries = group["country_code"].tolist()

        profile = UserProfile(
            user_id=user_id,
            avg_hour=round(hours.mean(), 2),
            std_hour=round(hours.std() if len(hours) > 1 else 0.0, 2),
            avg_bytes=round(bytes_vals.mean(), 2),
            std_bytes=round(bytes_vals.std() if len(bytes_vals) > 1 else 0.0, 2),
            top_countries=[c for c, _ in Counter(countries).most_common(5)],
            last_updated=datetime.now(UTC),
        )
        profiles.append(profile)

    logger.info("Built profiles for %d users", len(profiles))
    return profiles


def profiles_to_df(profiles: list[UserProfile]) -> pd.DataFrame:
    """Convert UserProfile list to pandas DataFrame."""
    return pd.DataFrame([p.model_dump(mode="json") for p in profiles])
