"""Tests for the alerting logic."""

from datetime import datetime

from shared.models import AnomalyRecord
from services.alerting.alerter import process_anomalies


def _make_anomaly(score: float) -> AnomalyRecord:
    return AnomalyRecord(
        event_id="evt-001",
        user_id="user_001",
        anomaly_score=score,
        timestamp=datetime.utcnow(),
        dimensions=["time"],
        details="Test",
    )


class TestProcessAnomalies:
    """Tests for anomaly processing."""

    def test_critical_anomalies_filtered(self) -> None:
        """Test that only critical anomalies are returned."""
        anomalies = [
            _make_anomaly(0.9),  # above default threshold 0.7
            _make_anomaly(0.5),  # below
            _make_anomaly(0.8),  # above
        ]
        critical = process_anomalies(anomalies, threshold=0.7)
        assert len(critical) == 2

    def test_empty_list(self) -> None:
        """Test processing empty list."""
        critical = process_anomalies([])
        assert len(critical) == 0

    def test_all_below_threshold(self) -> None:
        """Test when all anomalies are below threshold."""
        anomalies = [_make_anomaly(0.3), _make_anomaly(0.6)]
        critical = process_anomalies(anomalies, threshold=0.7)
        assert len(critical) == 0

    def test_custom_threshold(self) -> None:
        """Test with custom threshold."""
        anomalies = [_make_anomaly(0.75), _make_anomaly(0.85)]
        critical = process_anomalies(anomalies, threshold=0.8)
        assert len(critical) == 1
