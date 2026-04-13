"""Alerting logic for detected anomalies."""

from __future__ import annotations

import logging

from shared.models import AnomalyRecord

logger = logging.getLogger(__name__)


def process_anomalies(anomalies: list[AnomalyRecord], threshold: float = 0.7) -> list[AnomalyRecord]:
    """Filter and process anomalies above the alert threshold.

    For MVP: logs critical anomalies to console.
    Future: send email / Telegram notifications.

    Args:
        anomalies: List of detected anomaly records.
        threshold: Minimum score to trigger an alert.

    Returns:
        List of anomalies that exceeded the threshold.
    """
    critical = [a for a in anomalies if a.anomaly_score >= threshold]

    for anomaly in critical:
        logger.warning(
            "CRITICAL ANOMALY: user=%s, score=%.4f, dimensions=%s, details=%s",
            anomaly.user_id,
            anomaly.anomaly_score,
            anomaly.dimensions,
            anomaly.details,
        )

    if critical:
        logger.info("Alerted on %d critical anomalies", len(critical))

    return critical


def send_alert_email(anomaly: AnomalyRecord, email: str) -> bool:
    """Stub for email alert sending.

    Args:
        anomaly: The anomaly to alert about.
        email: Recipient email address.

    Returns:
        True if alert was sent (always True for stub).
    """
    logger.info(
        "[EMAIL STUB] Would send alert to %s: user=%s, score=%.4f",
        email,
        anomaly.user_id,
        anomaly.anomaly_score,
    )
    return True


def send_alert_telegram(anomaly: AnomalyRecord, token: str, chat_id: str) -> bool:
    """Stub for Telegram alert sending.

    Args:
        anomaly: The anomaly to alert about.
        token: Telegram bot token.
        chat_id: Telegram chat ID.

    Returns:
        True if alert was sent (always True for stub).
    """
    logger.info(
        "[TELEGRAM STUB] Would send alert to chat %s: user=%s, score=%.4f",
        chat_id,
        anomaly.user_id,
        anomaly.anomaly_score,
    )
    return True
