"""Tests for correlator logic."""

from datetime import datetime, timedelta

from services.correlator.correlator import (
    correlate_anomalies,
    cross_user_correlation,
)
from shared.models import AnomalyRecord


def _make_anomaly(event_id: str, user_id: str, ts: datetime, source_ip: str = "") -> AnomalyRecord:
    return AnomalyRecord(
        event_id=event_id,
        user_id=user_id,
        anomaly_score=0.8,
        timestamp=ts,
        dimensions=["time"],
        source_ip=source_ip,
    )


class TestCorrelateAnomalies:
    """Tests for anomaly correlation."""

    def test_empty(self) -> None:
        assert correlate_anomalies([]) == []

    def test_single_anomaly(self) -> None:
        ts = datetime(2026, 5, 18, 10, 0)
        anomalies = [_make_anomaly("a1", "user_1", ts)]
        incidents = correlate_anomalies(anomalies)
        assert len(incidents) >= 1
        assert incidents[0].severity == "single"

    def test_three_in_window(self) -> None:
        ts = datetime(2026, 5, 18, 10, 0)
        anomalies = [
            _make_anomaly("a1", "user_1", ts),
            _make_anomaly("a2", "user_1", ts + timedelta(minutes=1)),
            _make_anomaly("a3", "user_1", ts + timedelta(minutes=2)),
        ]
        incidents = correlate_anomalies(anomalies)
        assert any(i.severity == "repeated" for i in incidents)

    def test_six_in_window(self) -> None:
        ts = datetime(2026, 5, 18, 10, 0)
        anomalies = [_make_anomaly(f"a{i}", "user_1", ts + timedelta(minutes=i)) for i in range(6)]
        incidents = correlate_anomalies(anomalies)
        assert any(i.severity == "critical" for i in incidents)

    def test_outside_window(self) -> None:
        ts = datetime(2026, 5, 18, 10, 0)
        anomalies = [
            _make_anomaly("a1", "user_1", ts),
            _make_anomaly("a2", "user_1", ts + timedelta(hours=2)),
        ]
        incidents = correlate_anomalies(anomalies)
        singles = [i for i in incidents if i.severity == "single"]
        assert len(singles) >= 2

    def test_mixed_users(self) -> None:
        ts = datetime(2026, 5, 18, 10, 0)
        anomalies = [
            _make_anomaly("a1", "user_1", ts),
            _make_anomaly("a2", "user_2", ts + timedelta(minutes=1)),
        ]
        incidents = correlate_anomalies(anomalies)
        assert any("user_1" in i.user_ids and "user_2" in i.user_ids for i in incidents)

    def test_top_dimensions(self) -> None:
        ts = datetime(2026, 5, 18, 10, 0)
        anomalies = [
            AnomalyRecord(
                event_id="a1", user_id="u1", anomaly_score=0.8, timestamp=ts, dimensions=["time"]
            ),
            AnomalyRecord(
                event_id="a2",
                user_id="u1",
                anomaly_score=0.8,
                timestamp=ts + timedelta(minutes=1),
                dimensions=["volume"],
            ),
            AnomalyRecord(
                event_id="a3",
                user_id="u1",
                anomaly_score=0.8,
                timestamp=ts + timedelta(minutes=2),
                dimensions=["time"],
            ),
        ]
        incidents = correlate_anomalies(anomalies)
        assert any("time" in i.top_dimensions for i in incidents)


class TestCrossUserCorrelation:
    """Tests for cross-user IP correlation."""

    def test_same_ip_different_users(self) -> None:
        ts = datetime(2026, 5, 18, 10, 0)
        anomalies = [
            _make_anomaly("a1", "user_1", ts, source_ip="10.0.0.1"),
            _make_anomaly("a2", "user_2", ts + timedelta(minutes=5), source_ip="10.0.0.1"),
        ]
        incidents = cross_user_correlation(anomalies)
        assert len(incidents) >= 1
        assert incidents[0].severity == "critical"

    def test_different_ips(self) -> None:
        ts = datetime(2026, 5, 18, 10, 0)
        anomalies = [
            _make_anomaly("a1", "user_1", ts, source_ip="10.0.0.1"),
            _make_anomaly("a2", "user_2", ts + timedelta(minutes=5), source_ip="10.0.0.2"),
        ]
        incidents = cross_user_correlation(anomalies)
        assert len(incidents) == 0

    def test_empty(self) -> None:
        assert cross_user_correlation([]) == []
