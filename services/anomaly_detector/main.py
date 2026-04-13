"""Anomaly Detector microservice.

Endpoints:
  POST /detect       — detect anomalies in provided features
  POST /detect/all   — detect anomalies for ALL features in ES
  GET  /health       — health check
"""

from __future__ import annotations

import logging

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shared.es_client import ensure_indices, get_es_client
from shared.es_client import INDEX_FEATURES, INDEX_ANOMALIES
from services.anomaly_detector.detector import detect_anomalies, load_model

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Anomaly Detector",
    description="Detects anomalies in user behavior using Isolation Forest",
    version="0.1.0",
)

# Cache loaded model
_model = None


@app.on_event("startup")
def on_startup() -> None:
    global _model
    try:
        client = get_es_client()
        ensure_indices(client)
    except ConnectionError as exc:
        logger.error("Elasticsearch not available: %s", exc)

    try:
        _model = load_model()
        logger.info("ML model loaded successfully")
    except FileNotFoundError as exc:
        logger.warning("ML model not loaded: %s", exc)


class DetectResponse(BaseModel):
    anomalies_detected: int


@app.post("/detect")
async def detect(features: list[dict]) -> DetectResponse:
    """Detect anomalies in provided feature records."""
    global _model

    if not features:
        return DetectResponse(anomalies_detected=0)

    df = pd.DataFrame(features)
    anomalies = detect_anomalies(df, model=_model)

    if anomalies:
        client = get_es_client()
        actions = []
        for a in anomalies:
            actions.append({"index": {"_index": INDEX_ANOMALIES, "_id": a.event_id}})
            actions.append(a.model_dump(mode="json"))
        client.bulk(operations=actions, refresh=True)

    return DetectResponse(anomalies_detected=len(anomalies))


@app.post("/detect/all")
async def detect_all() -> DetectResponse:
    """Detect anomalies for all features in Elasticsearch."""
    global _model

    client = get_es_client()

    all_features = []
    scroll = client.search(index=INDEX_FEATURES, size=1000, scroll="2m")
    scroll_id = scroll["_scroll_id"]
    hits = scroll["hits"]["hits"]

    while hits:
        all_features.extend(h["_source"] for h in hits)
        scroll = client.scroll(scroll_id=scroll_id, scroll="2m")
        scroll_id = scroll["_scroll_id"]
        hits = scroll["hits"]["hits"]

    if not all_features:
        return DetectResponse(anomalies_detected=0)

    df = pd.DataFrame(all_features)
    anomalies = detect_anomalies(df, model=_model)

    if anomalies:
        actions = []
        for a in anomalies:
            actions.append({"index": {"_index": INDEX_ANOMALIES, "_id": a.event_id}})
            actions.append(a.model_dump(mode="json"))
        client.bulk(operations=actions, refresh=True)

    return DetectResponse(anomalies_detected=len(anomalies))


@app.get("/health")
async def health() -> dict:
    try:
        client = get_es_client()
        es_ok = client.ping()
    except ConnectionError:
        es_ok = False

    return {
        "status": "healthy" if (es_ok and _model is not None) else "degraded",
        "model_loaded": _model is not None,
        "elasticsearch": "connected" if es_ok else "unavailable",
    }
