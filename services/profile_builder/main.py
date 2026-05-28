"""Profile Builder microservice.

Endpoints:
  POST /build              — build profiles from provided features
  POST /build/all          — build profiles from ALL features in ES
  GET  /profile/{user_id}  — get profile for a specific user
  GET  /health             — health check

Scheduler:
  Auto-rebuilds profiles every PROFILE_REBUILD_INTERVAL minutes (default: 60).
  Set PROFILE_REBUILD_INTERVAL=0 to disable.
"""

from __future__ import annotations

import logging
import os
from typing import Any

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

# Scheduler for auto-rebuilding profiles
_scheduler: Any | None = None
_scheduler_enabled = False

REBUILD_INTERVAL = int(os.getenv("PROFILE_REBUILD_INTERVAL", "60"))


async def _rebuild_profiles_job() -> None:
    """Background job: rebuild all profiles from ES features."""
    logger.info("Scheduler: rebuilding all profiles...")
    try:
        if not is_es_available():
            logger.warning("Scheduler: ES unavailable, skipping rebuild")
            return

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
            logger.info("Scheduler: no features found, skipping")
            return

        df = pd.DataFrame(all_features)
        profiles = build_profiles_from_features(df)

        actions = []
        for p in profiles:
            actions.append({"index": {"_index": INDEX_PROFILES, "_id": p.user_id}})
            actions.append(p.model_dump(mode="json"))

        if actions:
            client.bulk(operations=actions, refresh=True)

        logger.info("Scheduler: rebuilt %d profiles", len(profiles))
    except Exception as e:
        logger.error("Scheduler: rebuild failed: %s", e)


@app.on_event("startup")
async def on_startup() -> None:
    global _scheduler, _scheduler_enabled

    try:
        client = get_es_client()
        ensure_indices(client)
    except ConnectionError as exc:
        logger.error("Elasticsearch not available: %s", exc)

    if REBUILD_INTERVAL > 0:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        _scheduler = AsyncIOScheduler()
        _scheduler.add_job(
            _rebuild_profiles_job,
            "interval",
            minutes=REBUILD_INTERVAL,
            id="rebuild_profiles",
            replace_existing=True,
        )
        _scheduler.start()
        _scheduler_enabled = True
        logger.info("Profile auto-rebuild scheduler started (interval=%d min)", REBUILD_INTERVAL)
    else:
        logger.info("Profile auto-rebuild scheduler disabled (PROFILE_REBUILD_INTERVAL=0)")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Profile auto-rebuild scheduler stopped")


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
    es_status = "connected" if is_es_available() else "disconnected"
    scheduler_status = "running" if (_scheduler and _scheduler.running) else "stopped"
    return {
        "service": "profile-builder",
        "status": "healthy" if is_es_available() else "degraded",
        "elasticsearch": es_status,
        "scheduler": scheduler_status,
        "rebuild_interval_minutes": REBUILD_INTERVAL,
    }
