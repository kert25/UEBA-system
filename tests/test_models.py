"""Tests for shared Pydantic models."""

from datetime import datetime

import pytest

from shared.models import (
    AnomalyRecord,
    EventIngest,
    FeatureRecord,
    UserProfile,
)


def test_event_ingest_valid() -> None:
    """Test EventIngest with valid data."""
    event = EventIngest(
        timestamp=datetime.utcnow(),
        user_id="user_001",
        ip_address="192.168.1.1",
        country="Russia",
        city="Moscow",
        bytes_transferred=10_000_000,
        action_type="login",
        resource="/api/data",
    )
    assert event.user_id == "user_001"
    assert event.bytes_transferred == 10_000_000


def test_event_ingest_invalid_action_type() -> None:
    """Test that invalid action_type raises ValueError."""
    with pytest.raises(ValueError, match="action_type"):
        EventIngest(
            timestamp=datetime.utcnow(),
            user_id="user_001",
            ip_address="192.168.1.1",
            country="Russia",
            city="Moscow",
            bytes_transferred=10_000_000,
            action_type="hack",
            resource="/api/data",
        )


def test_event_ingest_negative_bytes() -> None:
    """Test that negative bytes_transferred raises error."""
    with pytest.raises(ValueError):
        EventIngest(
            timestamp=datetime.utcnow(),
            user_id="user_001",
            ip_address="192.168.1.1",
            country="Russia",
            city="Moscow",
            bytes_transferred=-1,
            action_type="login",
            resource="/",
        )


def test_event_ingest_auto_uuid() -> None:
    """Test that event_id is auto-generated."""
    event = EventIngest(
        timestamp=datetime.utcnow(),
        user_id="user_001",
        ip_address="192.168.1.1",
        country="Russia",
        city="Moscow",
        bytes_transferred=1,
        action_type="login",
        resource="/",
    )
    assert len(event.event_id) == 36  # UUID length


def test_feature_record_valid() -> None:
    """Test FeatureRecord with valid data."""
    rec = FeatureRecord(
        event_id="evt-1",
        user_id="user_001",
        hour_of_day=14,
        day_of_week=2,
        minutes_from_midnight=840,
        country_code="RU",
        bytes_transferred=5_000_000,
    )
    assert rec.hour_of_day == 14
    assert rec.day_of_week == 2


def test_feature_record_hour_bounds() -> None:
    """Test hour_of_day bounds."""
    with pytest.raises(ValueError):
        FeatureRecord(
            event_id="evt-1",
            user_id="u",
            hour_of_day=24,
            day_of_week=0,
            minutes_from_midnight=0,
            country_code="RU",
            bytes_transferred=0,
        )


def test_user_profile() -> None:
    """Test UserProfile creation."""
    profile = UserProfile(
        user_id="user_001",
        avg_hour=14.5,
        std_hour=2.3,
        avg_bytes=25_000_000.0,
        std_bytes=10_000_000.0,
        top_countries=["Russia", "Belarus"],
    )
    assert len(profile.top_countries) == 2
    assert profile.avg_hour == 14.5


def test_anomaly_record() -> None:
    """Test AnomalyRecord creation."""
    rec = AnomalyRecord(
        event_id="evt-1",
        user_id="user_001",
        anomaly_score=0.85,
        timestamp=datetime.utcnow(),
        dimensions=["time", "volume"],
        details="High score",
    )
    assert rec.anomaly_score == 0.85
    assert "time" in rec.dimensions
