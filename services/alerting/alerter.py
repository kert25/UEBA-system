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


async def send_alert_telegram(anomaly: AnomalyRecord, token: str, chat_id: str) -> bool:
    """Send alert via Telegram Bot API."""
    if not token or not chat_id:
        logger.warning("Telegram credentials not configured, skipping Telegram alert")
        return False

    score_pct = anomaly.anomaly_score * 100
    time_str = anomaly.timestamp.strftime("%d %b %Y, %H:%M:%S")

    text = (
        f"🚨 <b>UEBA Alert</b>\n\n"
        f"<b>User:</b> {anomaly.user_id}\n"
        f"<b>Anomaly score:</b> {anomaly.anomaly_score:.4f} ({score_pct:.1f}%) — "
        f"степень отклонения от нормального поведения. "
        f"0% = норма, 100% = критическая аномалия. Порог оповещения: 70%.\n"
        f"<b>Triggered dimensions:</b> {', '.join(anomaly.dimensions)}\n"
        f"<b>Time:</b> {time_str}\n"
        f"<b>Details:</b> {anomaly.details}\n"
        f"<b>Top features:</b> {', '.join(anomaly.top_features)} — "
        f"признаки, которые внесли наибольший вклад в детекцию аномалии"
    )

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
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
