"""Tests for the alerting logic."""

from datetime import datetime

import pytest

from services.alerting.alerter import (
    _alert_history,
    mark_alert_sent,
    process_anomalies,
    send_alert_email,
    send_alert_telegram,
    should_send_alert,
)
from shared.models import AnomalyRecord


def _make_anomaly(
    score: float, user_id: str = "user_001", dimensions: list[str] | None = None
) -> AnomalyRecord:
    return AnomalyRecord(
        event_id=f"evt-{score}",
        user_id=user_id,
        anomaly_id=f"anom-{score}",
        anomaly_score=score,
        timestamp=datetime.utcnow(),
        dimensions=dimensions or ["time"],
        details="Test",
    )


@pytest.fixture(autouse=True)
def clear_alert_history() -> None:
    """Clear alert history before each test."""
    _alert_history.clear()
    yield
    _alert_history.clear()


class TestProcessAnomalies:
    """Tests for anomaly processing."""

    def test_critical_anomalies_filtered(self) -> None:
        """Test that only critical anomalies are returned."""
        anomalies = [
            _make_anomaly(0.9),
            _make_anomaly(0.5),
            _make_anomaly(0.8, user_id="user_002"),
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
        anomalies = [_make_anomaly(0.75), _make_anomaly(0.85, user_id="user_002")]
        critical = process_anomalies(anomalies, threshold=0.8)
        assert len(critical) == 1


class TestDeduplication:
    """Tests for alert deduplication."""

    def test_should_send_first_alert(self) -> None:
        assert should_send_alert(_make_anomaly(0.9)) is True

    def test_should_not_send_duplicate(self) -> None:
        anomaly = _make_anomaly(0.9)
        mark_alert_sent(anomaly)
        assert should_send_alert(anomaly) is False

    def test_different_users_not_deduped(self) -> None:
        a1 = _make_anomaly(0.9, user_id="user_001")
        a2 = _make_anomaly(0.9, user_id="user_002")
        mark_alert_sent(a1)
        assert should_send_alert(a2) is True

    def test_different_dimensions_not_deduped(self) -> None:
        a1 = _make_anomaly(0.9, dimensions=["time"])
        a2 = _make_anomaly(0.9, dimensions=["volume"])
        mark_alert_sent(a1)
        assert should_send_alert(a2) is True


class TestSendAlerts:
    """Tests for alert sending functions."""

    @pytest.mark.asyncio
    async def test_send_email_no_credentials(self) -> None:
        """Test email sending with no SMTP credentials."""
        anomaly = _make_anomaly(0.9)
        result = await send_alert_email(anomaly, email="")
        assert result is False

    @pytest.mark.asyncio
    async def test_send_telegram_no_credentials(self) -> None:
        """Test telegram sending with no token."""
        anomaly = _make_anomaly(0.9)
        result = await send_alert_telegram(anomaly, token="", chat_id="")
        assert result is False

    @pytest.mark.asyncio
    async def test_send_telegram_no_chat_id(self) -> None:
        """Test telegram sending with token but no chat_id."""
        anomaly = _make_anomaly(0.9)
        result = await send_alert_telegram(anomaly, token="fake_token", chat_id="")
        assert result is False
