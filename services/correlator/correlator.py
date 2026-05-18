"""Correlator logic — group anomalies into incidents."""

from __future__ import annotations

import uuid
from collections import Counter
from datetime import timedelta

from shared.models import AnomalyRecord, IncidentRecord

CORRELATION_WINDOWS = [5, 15, 60]

SEVERITY_THRESHOLDS = {
    "single": 1,
    "repeated": 2,
    "critical": 5,
}


def correlate_anomalies(anomalies: list[AnomalyRecord]) -> list[IncidentRecord]:
    """Group anomalies into incidents using sliding time windows.

    Algorithm:
      1. Sort anomalies by timestamp
      2. For each window (5/15/60 min) group anomalies per-user
      3. Apply severity escalation logic
      4. Return list of incidents
    """
    if not anomalies:
        return []

    sorted_anomalies = sorted(anomalies, key=lambda a: a.timestamp)

    incidents: list[IncidentRecord] = []
    processed_ids: set[str] = set()

    for window_minutes in CORRELATION_WINDOWS:
        window_delta = timedelta(minutes=window_minutes)

        i = 0
        while i < len(sorted_anomalies):
            window_start = sorted_anomalies[i].timestamp
            window_end = window_start + window_delta

            window_anomalies = []
            for j in range(i, len(sorted_anomalies)):
                if sorted_anomalies[j].timestamp <= window_end:
                    if sorted_anomalies[j].anomaly_id not in processed_ids:
                        window_anomalies.append(sorted_anomalies[j])
                else:
                    break

            if len(window_anomalies) >= 1:
                incident = _create_incident(window_anomalies, window_minutes)
                incidents.append(incident)
                processed_ids.update(a.anomaly_id for a in window_anomalies)

            i += 1

    return incidents


def _create_incident(anomalies: list[AnomalyRecord], window_minutes: int) -> IncidentRecord:
    """Create an IncidentRecord from a group of anomalies."""
    user_ids = list(set(a.user_id for a in anomalies))
    anomaly_count = len(anomalies)

    if anomaly_count >= SEVERITY_THRESHOLDS["critical"]:
        severity = "critical"
    elif anomaly_count >= SEVERITY_THRESHOLDS["repeated"]:
        severity = "repeated"
    else:
        severity = "single"

    all_dimensions = []
    for a in anomalies:
        all_dimensions.extend(a.dimensions)
    top_dimensions = [dim for dim, _ in Counter(all_dimensions).most_common(3)]

    timestamps = [a.timestamp for a in anomalies]

    return IncidentRecord(
        incident_id=str(uuid.uuid4()),
        user_ids=user_ids,
        anomaly_count=anomaly_count,
        severity=severity,
        window_minutes=window_minutes,
        first_seen=min(timestamps),
        last_seen=max(timestamps),
        anomaly_ids=[a.anomaly_id for a in anomalies],
        top_dimensions=top_dimensions,
        description=f"{anomaly_count} anomalies detected in {window_minutes}min window",
    )


def cross_user_correlation(
    anomalies: list[AnomalyRecord],
    window_minutes: int = 15,
) -> list[IncidentRecord]:
    """Detect coordinated attacks: different users, same IP, same time window."""
    if not anomalies:
        return []

    ip_groups: dict[str, list[AnomalyRecord]] = {}
    for a in anomalies:
        source_ip = a.source_ip if a.source_ip else "unknown"
        ip_groups.setdefault(source_ip, []).append(a)

    incidents = []
    for ip, ip_anomalies in ip_groups.items():
        unique_users = set(a.user_id for a in ip_anomalies)
        if len(unique_users) > 1:
            incident = _create_incident(ip_anomalies, window_minutes)
            incident.severity = "critical"
            incident.description = f"Cross-user correlation: {len(unique_users)} users from IP {ip}"
            incidents.append(incident)

    return incidents
