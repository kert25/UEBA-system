"""Alerting microservice — API for querying anomalies and statistics.

Endpoints:
  GET  /anomalies             — list all anomalies
  GET  /anomalies/{user_id}   — anomalies for a specific user
  GET  /stats                 — aggregated anomaly statistics
  POST /process               — process and alert on new anomalies
  GET  /health                — health check
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from services.alerting.alerter import process_anomalies
from shared.config import settings
from shared.es_client import (
    INDEX_ANOMALIES,
    INDEX_EVENTS,
    ensure_indices,
    get_es_client,
)
from shared.es_health import is_es_available
from shared.models import AnomalyRecord, AnomalyStats

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Alerting Dashboard",
    description="Queries anomalies and provides statistics for the UEBA system",
    version="0.1.0",
)


@app.on_event("startup")
def on_startup() -> None:
    try:
        client = get_es_client()
        ensure_indices(client)
    except ConnectionError as exc:
        logger.error("Elasticsearch not available: %s", exc)


class AnomalyList(BaseModel):
    anomalies: list[dict[str, Any]]
    total: int
    warning: str | None = None


class ProcessResponse(BaseModel):
    alerted: int


@app.get("/anomalies", response_model=AnomalyList)
async def list_anomalies(limit: int = 100, offset: int = 0) -> AnomalyList:
    """List detected anomalies with pagination."""
    if not is_es_available():
        return AnomalyList(anomalies=[], total=0, warning="Elasticsearch unavailable")

    client = get_es_client()

    result = client.search(
        index=INDEX_ANOMALIES,
        size=min(limit, 10000),
        from_=offset,
        sort=[{"anomaly_score": "desc"}],
    )

    hits = result["hits"]["hits"]
    total = result["hits"]["total"]["value"]

    anomalies = []
    for h in hits:
        source = h["_source"]
        source["_id"] = h["_id"]
        anomalies.append(source)

    return AnomalyList(anomalies=anomalies, total=total)


@app.get("/anomalies/{user_id}")
async def get_user_anomalies(user_id: str, limit: int = 50) -> AnomalyList:
    """Get anomalies for a specific user."""
    if not is_es_available():
        return AnomalyList(anomalies=[], total=0, warning="Elasticsearch unavailable")

    client = get_es_client()

    result = client.search(
        index=INDEX_ANOMALIES,
        size=limit,
        query={"term": {"user_id": user_id}},
        sort=[{"anomaly_score": "desc"}],
    )

    hits = result["hits"]["hits"]
    total = result["hits"]["total"]["value"]

    anomalies = []
    for h in hits:
        source = h["_source"]
        source["_id"] = h["_id"]
        anomalies.append(source)

    return AnomalyList(anomalies=anomalies, total=total)


@app.get("/stats")
async def get_stats() -> AnomalyStats | dict:
    """Get aggregated anomaly statistics."""
    if not is_es_available():
        return {"error": "Elasticsearch unavailable", "status": "degraded"}

    client = get_es_client()

    events_result = client.count(index=INDEX_EVENTS)
    total_events = events_result["count"]

    anomalies_result = client.count(index=INDEX_ANOMALIES)
    total_anomalies = anomalies_result["count"]

    anomaly_rate = total_anomalies / total_events if total_events > 0 else 0.0

    top_users_result = client.search(
        index=INDEX_ANOMALIES,
        size=0,
        aggs={
            "top_users": {
                "terms": {"field": "user_id", "size": 10},
                "aggs": {"avg_score": {"avg": {"field": "anomaly_score"}}},
            }
        },
    )

    top_anomalous_users = []
    for bucket in top_users_result["aggregations"]["top_users"]["buckets"]:
        top_anomalous_users.append(
            {
                "user_id": bucket["key"],
                "anomaly_count": bucket["doc_count"],
                "avg_score": round(bucket["avg_score"]["value"], 4),
            }
        )

    return AnomalyStats(
        total_events=total_events,
        total_anomalies=total_anomalies,
        anomaly_rate=round(anomaly_rate, 4),
        top_anomalous_users=top_anomalous_users,
    )


@app.post("/process")
async def process_anomaly_endpoint(anomalies: list[dict]) -> ProcessResponse:
    """Process anomalies and trigger alerts."""
    if not anomalies:
        return ProcessResponse(alerted=0)

    records = [AnomalyRecord(**a) for a in anomalies]
    critical = process_anomalies(records, threshold=settings.alert_threshold)

    for anomaly in critical:
        if settings.alert_email:
            from services.alerting.alerter import send_alert_email

            await send_alert_email(anomaly, settings.alert_email)
        if settings.alert_telegram_token and settings.alert_telegram_chat_id:
            from services.alerting.alerter import send_alert_telegram

            token = settings.alert_telegram_token
            chat = settings.alert_telegram_chat_id
            await send_alert_telegram(anomaly, token, chat)

    return ProcessResponse(alerted=len(critical))


@app.get("/health")
async def health() -> dict:
    return {
        "status": "healthy" if is_es_available() else "degraded",
        "elasticsearch": "connected" if is_es_available() else "disconnected",
    }
