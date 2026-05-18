"""Pydantic v2 models for event validation."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class EventIngest(BaseModel):
    """Raw event as received by the log ingestor."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime
    user_id: str
    ip_address: str
    country: str
    city: str
    bytes_transferred: int = Field(ge=0)
    action_type: str
    resource: str = Field(default="/")
    latitude: float | None = None
    longitude: float | None = None

    @field_validator("action_type")
    @classmethod
    def validate_action_type(cls, v: str) -> str:
        """Ensure action_type is one of the allowed values."""
        allowed = {"login", "download", "upload", "access", "delete", "modify"}
        if v not in allowed:
            raise ValueError(f"action_type must be one of {allowed}, got '{v}'")
        return v


class EventDocument(EventIngest):
    """Event as stored in Elasticsearch (extends EventIngest with metadata)."""

    indexed_at: datetime = Field(default_factory=datetime.utcnow)


class FeatureRecord(BaseModel):
    """Extracted features for a single event."""

    event_id: str
    user_id: str
    hour_of_day: int = Field(ge=0, le=23)
    day_of_week: int = Field(ge=0, le=6)
    minutes_from_midnight: int = Field(ge=0, le=1439)
    country_code: str
    bytes_transferred: int = Field(ge=0)
    is_anomaly: bool = Field(default=False)
    latitude: float | None = None
    longitude: float | None = None
    distance_from_previous_km: float | None = None
    hours_since_last_event: float | None = None


class UserProfile(BaseModel):
    """Statistical profile for a single user."""

    user_id: str
    avg_hour: float
    std_hour: float
    avg_bytes: float
    std_bytes: float
    top_countries: list[str] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class AnomalyRecord(BaseModel):
    """Record of a detected anomaly."""

    event_id: str
    user_id: str
    anomaly_id: str = Field(default_factory=lambda: str(uuid4()))
    anomaly_score: float = Field(ge=0.0, le=1.0)
    timestamp: datetime
    dimensions: list[str]  # e.g. ["time", "geography", "volume"]
    details: str = ""
    source_ip: str = ""
    feature_contributions: dict[str, float] = Field(default_factory=dict)
    top_features: list[str] = Field(default_factory=list)


class AnomalyStats(BaseModel):
    """Aggregated anomaly statistics."""

    total_events: int
    total_anomalies: int
    anomaly_rate: float
    top_anomalous_users: list[dict[str, Any]] = Field(default_factory=list)


class IncidentRecord(BaseModel):
    """Grouped incident from multiple anomalies."""

    model_config = {"from_attributes": True}

    incident_id: str
    user_ids: list[str]
    anomaly_count: int
    severity: str  # "single", "repeated", "critical"
    window_minutes: int
    first_seen: datetime
    last_seen: datetime
    anomaly_ids: list[str]
    top_dimensions: list[str]
    description: str = ""


AnomalyStats.model_rebuild()
