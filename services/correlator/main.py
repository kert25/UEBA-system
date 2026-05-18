"""Correlator Service — group anomalies into incidents."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from services.correlator.correlator import correlate_anomalies, cross_user_correlation
from shared.es_client import INDEX_ANOMALIES, INDEX_INCIDENTS, ensure_indices, get_es_client
from shared.es_health import is_es_available
from shared.models import AnomalyRecord, IncidentRecord

logger = logging.getLogger(__name__)

app = FastAPI(
    title="UEBA Correlator Service",
    description="Groups anomalies into incidents using sliding time windows",
    version="1.0.0",
)


@app.on_event("startup")
def on_startup() -> None:
    try:
        client = get_es_client()
        ensure_indices(client)
    except ConnectionError as exc:
        logger.error("Elasticsearch not available: %s", exc)


class CorrelateRequest(BaseModel):
    anomaly_ids: list[str] | None = None


@app.post("/correlate")
async def correlate(request: CorrelateRequest | None = None) -> dict[str, Any]:
    """Group anomalies into incidents."""
    if request and request.anomaly_ids:
        anomalies = await _load_anomalies_by_ids(request.anomaly_ids)
    else:
        anomalies = await _load_all_anomalies()

    incidents = correlate_anomalies(anomalies)
    cross_incidents = cross_user_correlation(anomalies)
    all_incidents = incidents + cross_incidents

    if is_es_available():
        await _save_incidents(all_incidents)

    return {
        "incidents": [i.model_dump(mode="json") for i in all_incidents],
        "total": len(all_incidents),
    }


@app.get("/incidents")
async def get_incidents(limit: int = 50) -> dict[str, Any]:
    """Get latest incidents from ES."""
    if not is_es_available():
        return {"incidents": [], "warning": "Elasticsearch unavailable"}

    client = get_es_client()
    result = client.search(
        index=INDEX_INCIDENTS,
        size=limit,
        sort=[{"first_seen": "desc"}],
    )

    incidents = [h["_source"] for h in result["hits"]["hits"]]
    return {"incidents": incidents, "total": result["hits"]["total"]["value"]}


@app.get("/health")
async def health() -> dict:
    return {
        "service": "correlator",
        "status": "healthy" if is_es_available() else "degraded",
        "elasticsearch": "connected" if is_es_available() else "disconnected",
    }


async def _load_all_anomalies() -> list[AnomalyRecord]:
    """Load all anomalies from ES."""
    client = get_es_client()
    result = client.search(index=INDEX_ANOMALIES, body={"query": {"match_all": {}}})
    return [AnomalyRecord(**hit["_source"]) for hit in result["hits"]["hits"]]


async def _load_anomalies_by_ids(anomaly_ids: list[str]) -> list[AnomalyRecord]:
    """Load anomalies by list of IDs."""
    client = get_es_client()
    result = client.search(
        index=INDEX_ANOMALIES,
        body={"query": {"terms": {"event_id": anomaly_ids}}},
    )
    return [AnomalyRecord(**hit["_source"]) for hit in result["hits"]["hits"]]


async def _save_incidents(incidents: list[IncidentRecord]) -> None:
    """Save incidents to ES."""
    client = get_es_client()
    actions = []
    for incident in incidents:
        actions.append({"index": {"_index": INDEX_INCIDENTS, "_id": incident.incident_id}})
        actions.append(incident.model_dump(mode="json"))

    if actions:
        client.bulk(operations=actions, refresh=True)
