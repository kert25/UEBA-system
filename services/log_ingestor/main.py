"""Log Ingestor microservice — FastAPI app.

Endpoints:
  POST /ingest      — ingest JSON events
  POST /ingest/csv  — ingest CSV events
  GET  /health      — health check
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, UploadFile
from pydantic import BaseModel

from services.log_ingestor.parser import parse_csv_events, parse_json_events
from shared.es_client import INDEX_EVENTS, ensure_indices, get_es_client

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Log Ingestor",
    description="Accepts and parses JSON/CSV log events, stores in Elasticsearch",
    version="0.1.0",
)


# ─── Startup ─────────────────────────────────────────────────────────────


@app.on_event("startup")
def on_startup() -> None:
    """Ensure Elasticsearch indices exist on startup."""
    try:
        client = get_es_client()
        ensure_indices(client)
        logger.info("Elasticsearch indices ready")
    except ConnectionError as exc:
        logger.error("Elasticsearch not available: %s", exc)


# ─── Endpoints ───────────────────────────────────────────────────────────


class IngestResponse(BaseModel):
    """Response schema for ingestion endpoint."""

    accepted: int
    errors: list[str] = []


@app.post("/ingest", response_model=IngestResponse)
async def ingest_json(events: list[dict[str, Any]]) -> IngestResponse:
    """Accept a batch of JSON events and store them in Elasticsearch."""
    try:
        parsed = parse_json_events(events)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not parsed:
        return IngestResponse(accepted=0, errors=["No valid events found"])

    try:
        client = get_es_client()
        actions = []
        for event in parsed:
            actions.append({"index": {"_index": INDEX_EVENTS, "_id": event.event_id}})
            actions.append(event.model_dump(mode="json"))
        if actions:
            client.bulk(operations=actions, refresh=True)
    except ConnectionError:
        logger.warning("Elasticsearch unavailable; events accepted but not persisted")

    logger.info("Ingested %d events", len(parsed))
    return IngestResponse(accepted=len(parsed))


@app.post("/ingest/csv", response_model=IngestResponse)
async def ingest_csv(file: UploadFile) -> IngestResponse:
    """Accept a CSV file and store events in Elasticsearch."""
    content = await file.read()
    text = content.decode("utf-8")

    try:
        parsed = parse_csv_events(text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not parsed:
        return IngestResponse(accepted=0, errors=["No valid events found"])

    try:
        client = get_es_client()
        actions = []
        for event in parsed:
            actions.append({"index": {"_index": INDEX_EVENTS, "_id": event.event_id}})
            actions.append(event.model_dump(mode="json"))
        if actions:
            client.bulk(operations=actions, refresh=True)
    except ConnectionError:
        logger.warning("Elasticsearch unavailable; CSV events accepted but not persisted")

    logger.info("Ingested %d events from CSV", len(parsed))
    return IngestResponse(accepted=len(parsed))


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    try:
        client = get_es_client()
        ok = client.ping()
        return {"status": "healthy", "elasticsearch": "connected" if ok else "disconnected"}
    except ConnectionError:
        return {"status": "degraded", "elasticsearch": "unavailable"}
