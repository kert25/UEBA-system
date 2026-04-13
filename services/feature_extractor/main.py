"""Feature Extractor microservice.

Endpoints:
  POST /extract       — extract features from events and save to ES
  POST /extract/all   — extract features for ALL events in ES
  GET  /health        — health check
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shared.es_client import ensure_indices, get_es_client
from shared.es_client import INDEX_EVENTS, INDEX_FEATURES
from services.feature_extractor.extractor import (
    events_to_df,
    extract_features_from_events,
)

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
async def extract_events(events: list[dict[str, Any]]) -> ExtractResponse:
    """Extract features from provided events and store in Elasticsearch."""
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
async def extract_all_events() -> ExtractResponse:
    """Extract features for all events currently in Elasticsearch."""
    client = get_es_client()

    # Scroll through all events
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
    try:
        client = get_es_client()
        return {"status": "healthy" if client.ping() else "degraded"}
    except ConnectionError:
        return {"status": "degraded", "elasticsearch": "unavailable"}
