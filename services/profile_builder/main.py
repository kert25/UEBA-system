"""Profile Builder microservice.

Endpoints:
  POST /build              — build profiles from provided features
  POST /build/all          — build profiles from ALL features in ES
  GET  /profile/{user_id}  — get profile for a specific user
  GET  /health             — health check
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from pydantic import BaseModel

from services.profile_builder.builder import build_profiles_from_features
from shared.es_client import INDEX_FEATURES, INDEX_PROFILES, ensure_indices, get_es_client
from shared.es_health import is_es_available
from shared.models import UserProfile

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Profile Builder",
    description="Builds statistical user profiles from extracted features",
    version="0.1.0",
)


@app.on_event("startup")
def on_startup() -> None:
    try:
        client = get_es_client()
        ensure_indices(client)
    except ConnectionError as exc:
        logger.error("Elasticsearch not available: %s", exc)


class BuildResponse(BaseModel):
    profiles_built: int


@app.post("/build")
async def build_profiles(features: list[dict]) -> BuildResponse | dict:
    """Build user profiles from provided feature records."""
    if not features:
        return BuildResponse(profiles_built=0)

    if not is_es_available():
        return {"error": "Elasticsearch unavailable", "status": "degraded"}

    import pandas as pd

    df = pd.DataFrame(features)
    profiles = build_profiles_from_features(df)

    client = get_es_client()
    actions = []
    for p in profiles:
        actions.append({"index": {"_index": INDEX_PROFILES, "_id": p.user_id}})
        actions.append(p.model_dump(mode="json"))

    if actions:
        client.bulk(operations=actions, refresh=True)

    return BuildResponse(profiles_built=len(profiles))


@app.post("/build/all")
async def build_all_profiles() -> BuildResponse | dict:
    """Build profiles from all features currently in Elasticsearch."""
    if not is_es_available():
        return {"error": "Elasticsearch unavailable", "status": "degraded"}

    import pandas as pd

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
        return BuildResponse(profiles_built=0)

    df = pd.DataFrame(all_features)
    profiles = build_profiles_from_features(df)

    actions = []
    for p in profiles:
        actions.append({"index": {"_index": INDEX_PROFILES, "_id": p.user_id}})
        actions.append(p.model_dump(mode="json"))

    if actions:
        client.bulk(operations=actions, refresh=True)

    return BuildResponse(profiles_built=len(profiles))


@app.get("/profile/{user_id}")
async def get_profile(user_id: str) -> UserProfile | dict:
    """Get the behavior profile for a specific user."""
    if not is_es_available():
        return {"error": "Elasticsearch unavailable", "status": "degraded"}

    client = get_es_client()
    try:
        result = client.get(index=INDEX_PROFILES, id=user_id)
        return UserProfile(**result["_source"])
    except Exception:
        return {"error": f"Profile not found for user {user_id}"}


@app.get("/health")
async def health() -> dict:
    return {
        "status": "healthy" if is_es_available() else "degraded",
        "elasticsearch": "connected" if is_es_available() else "disconnected",
    }
