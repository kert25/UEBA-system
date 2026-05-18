"""Alerting logic for detected anomalies."""

from __future__ import annotations

import logging
import os
from datetime import datetime

from shared.models import AnomalyRecord

logger = logging.getLogger(__name__)

_alert_history: dict[str, datetime] = {}
_rate_limit_minutes = int(os.getenv("ALERT_RATE_LIMIT_MINUTES", "30"))


def _dedup_key(anomaly: AnomalyRecord) -> str:
    return f"{anomaly.user_id}:{','.join(sorted(anomaly.dimensions))}"


def should_send_alert(anomaly: AnomalyRecord) -> bool:
    """Check if alert can be sent (no duplicates within rate limit window)."""
    key = _dedup_key(anomaly)
    last_sent = _alert_history.get(key)
    if last_sent is None:
        return True
    elapsed = (datetime.utcnow() - last_sent).total_seconds() / 60
    return elapsed >= _rate_limit_minutes


def mark_alert_sent(anomaly: AnomalyRecord) -> None:
    """Mark alert as sent."""
    _alert_history[_dedup_key(anomaly)] = datetime.utcnow()


def process_anomalies(
    anomalies: list[AnomalyRecord],
    threshold: float = 0.7,
) -> list[AnomalyRecord]:
    """Filter and process anomalies above the alert threshold.

    Args:
        anomalies: List of detected anomaly records.
        threshold: Minimum score to trigger an alert.

    Returns:
        List of anomalies that exceeded the threshold.
    """
    critical = [a for a in anomalies if a.anomaly_score >= threshold]

    alerted = []
    for anomaly in critical:
        if not should_send_alert(anomaly):
            logger.info("Alert deduplicated: %s", _dedup_key(anomaly))
            continue

        logger.warning(
            "CRITICAL ANOMALY: user=%s, score=%.4f, dimensions=%s, details=%s",
            anomaly.user_id,
            anomaly.anomaly_score,
            anomaly.dimensions,
            anomaly.details,
        )

        alerted.append(anomaly)
        mark_alert_sent(anomaly)

    if alerted:
        logger.info("Alerted on %d critical anomalies", len(alerted))

    return alerted


async def send_alert_email(anomaly: AnomalyRecord, email: str) -> bool:
    """Send alert via email using aiosmtplib."""
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME", "")
    password = os.getenv("SMTP_PASSWORD", "")

    if not username or not password or not email:
        logger.warning("Email credentials not configured, skipping email alert")
        return False

    subject = f"[UEBA] ANOMALY — user={anomaly.user_id}, score={anomaly.anomaly_score:.4f}"
    body = (
        f"UEBA Alert\n\n"
        f"User: {anomaly.user_id}\n"
        f"Score: {anomaly.anomaly_score:.4f}\n"
        f"Dimensions: {', '.join(anomaly.dimensions)}\n"
        f"Time: {anomaly.timestamp.isoformat()}\n"
        f"Details: {anomaly.details}\n"
        f"Top features: {', '.join(anomaly.top_features)}"
    )

    try:
        from email.message import EmailMessage

        import aiosmtplib

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = username
        msg["To"] = email
        msg.set_content(body)

        await aiosmtplib.send(
            msg,
            hostname=smtp_host,
            port=smtp_port,
            username=username,
            password=password,
            start_tls=True,
        )
        logger.info("Email alert sent to %s", email)
        return True
    except ImportError:
        logger.warning("aiosmtplib not installed, email alert skipped")
        return False
    except Exception as e:
        logger.error("Failed to send email alert: %s", e)
        return False


async def send_alert_telegram(anomaly: AnomalyRecord, token: str, chat_id: str) -> bool:
    """Send alert via Telegram Bot API."""
    if not token or not chat_id:
        logger.warning("Telegram credentials not configured, skipping Telegram alert")
        return False

    text = (
        f"🚨 *UEBA Alert*\n\n"
        f"*User:* {anomaly.user_id}\n"
        f"*Score:* {anomaly.anomaly_score:.4f}\n"
        f"*Dimensions:* {', '.join(anomaly.dimensions)}\n"
        f"*Time:* {anomaly.timestamp.isoformat()}\n"
        f"*Details:* {anomaly.details}\n"
        f"*Top features:* {', '.join(anomaly.top_features)}"
    )

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }

    try:
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10)
            response.raise_for_status()
        logger.info("Telegram alert sent to chat %s", chat_id)
        return True
    except Exception as e:
        logger.error("Failed to send Telegram alert: %s", e)
        return False
