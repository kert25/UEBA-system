"""Profile Builder microservice.

Endpoints:
  POST /build              — build profiles from provided features
  POST /build/all          — build profiles from ALL features in ES
  GET  /profile/{user_id}  — get profile for a specific user
  GET  /health             — health check
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shared.es_client import ensure_indices, get_es_client
from shared.es_client import INDEX_FEATURES, INDEX_PROFILES
from shared.models import UserProfile
from services.profile_builder.builder import build_profiles_from_features, profiles_to_df

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
async def build_profiles(features: list[dict]) -> BuildResponse:
    """Build user profiles from provided feature records."""
    import pandas as pd

    if not features:
        return BuildResponse(profiles_built=0)

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
async def build_all_profiles() -> BuildResponse:
    """Build profiles from all features currently in Elasticsearch."""
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
    client = get_es_client()
    try:
        result = client.get(index=INDEX_PROFILES, id=user_id)
        return UserProfile(**result["_source"])
    except Exception:
        return {"error": f"Profile not found for user {user_id}"}


@app.get("/health")
async def health() -> dict:
    try:
        client = get_es_client()
        return {"status": "healthy" if client.ping() else "degraded"}
    except ConnectionError:
        return {"status": "degraded", "elasticsearch": "unavailable"}
