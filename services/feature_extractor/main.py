"""Feature Extractor microservice.

Endpoints:
  POST /extract       — extract features from events and save to ES
  POST /extract/all   — extract features for ALL events in ES
  GET  /health        — health check
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from services.feature_extractor.extractor import (
    extract_features_from_events,
)
from shared.es_client import INDEX_EVENTS, INDEX_FEATURES, ensure_indices, get_es_client
from shared.es_health import is_es_available

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Feature Extractor",
    description="Extracts ML features from raw events and stores in Elasticsearch",
    version="0.1.0",
)


@app.on_event("startup")
def on_startup() -> None:
    try:
        client = get_es_client()
        ensure_indices(client)
    except ConnectionError as exc:
        logger.error("Elasticsearch not available: %s", exc)


class ExtractResponse(BaseModel):
    features_extracted: int


@app.post("/extract")
async def extract_events(events: list[dict[str, Any]]) -> ExtractResponse | dict:
    """Extract features from provided events and store in Elasticsearch."""
    if not events:
        return ExtractResponse(features_extracted=0)

    if not is_es_available():
        return {"error": "Elasticsearch unavailable", "status": "degraded"}

    features = extract_features_from_events(events)
    if not features:
        return ExtractResponse(features_extracted=0)

    client = get_es_client()
    actions = []
    for f in features:
        actions.append({"index": {"_index": INDEX_FEATURES, "_id": f.event_id}})
        actions.append(f.model_dump(mode="json"))

    if actions:
        client.bulk(operations=actions, refresh=True)

    return ExtractResponse(features_extracted=len(features))


@app.post("/extract/all")
async def extract_all_events() -> ExtractResponse | dict:
    """Extract features for all events currently in Elasticsearch."""
    if not is_es_available():
        return {"error": "Elasticsearch unavailable", "status": "degraded"}

    client = get_es_client()

    all_events = []
    scroll = client.search(index=INDEX_EVENTS, size=1000, scroll="2m")
    scroll_id = scroll["_scroll_id"]
    hits = scroll["hits"]["hits"]

    while hits:
        all_events.extend(h["_source"] for h in hits)
        scroll = client.scroll(scroll_id=scroll_id, scroll="2m")
        scroll_id = scroll["_scroll_id"]
        hits = scroll["hits"]["hits"]

    if not all_events:
        return ExtractResponse(features_extracted=0)

    features = extract_features_from_events(all_events)

    actions = []
    for f in features:
        actions.append({"index": {"_index": INDEX_FEATURES, "_id": f.event_id}})
        actions.append(f.model_dump(mode="json"))

    if actions:
        client.bulk(operations=actions, refresh=True)

    return ExtractResponse(features_extracted=len(features))


@app.get("/health")
async def health() -> dict:
    return {
        "status": "healthy" if is_es_available() else "degraded",
        "elasticsearch": "connected" if is_es_available() else "disconnected",
    }
