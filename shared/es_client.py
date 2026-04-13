"""Elasticsearch client wrapper with index management."""

from __future__ import annotations

import logging
from typing import Any

from elasticsearch import AsyncElasticsearch, Elasticsearch

from shared.config import settings

logger = logging.getLogger(__name__)

# Index names
INDEX_EVENTS = "events"
INDEX_FEATURES = "features"
INDEX_PROFILES = "profiles"
INDEX_ANOMALIES = "anomalies"

# Default index mappings
MAPPINGS: dict[str, dict[str, Any]] = {
    INDEX_EVENTS: {
        "properties": {
            "event_id": {"type": "keyword"},
            "timestamp": {"type": "date"},
            "user_id": {"type": "keyword"},
            "ip_address": {"type": "ip"},
            "country": {"type": "keyword"},
            "city": {"type": "keyword"},
            "bytes_transferred": {"type": "long"},
            "action_type": {"type": "keyword"},
            "resource": {"type": "keyword"},
        }
    },
    INDEX_FEATURES: {
        "properties": {
            "event_id": {"type": "keyword"},
            "user_id": {"type": "keyword"},
            "hour_of_day": {"type": "integer"},
            "day_of_week": {"type": "integer"},
            "minutes_from_midnight": {"type": "integer"},
            "country_code": {"type": "keyword"},
            "bytes_transferred": {"type": "long"},
            "is_anomaly": {"type": "boolean"},
        }
    },
    INDEX_PROFILES: {
        "properties": {
            "user_id": {"type": "keyword"},
            "avg_hour": {"type": "float"},
            "std_hour": {"type": "float"},
            "avg_bytes": {"type": "float"},
            "std_bytes": {"type": "float"},
            "top_countries": {"type": "keyword"},
            "last_updated": {"type": "date"},
        }
    },
    INDEX_ANOMALIES: {
        "properties": {
            "event_id": {"type": "keyword"},
            "user_id": {"type": "keyword"},
            "anomaly_score": {"type": "float"},
            "timestamp": {"type": "date"},
            "dimensions": {"type": "keyword"},
            "details": {"type": "text"},
        }
    },
}


def get_es_client() -> Elasticsearch:
    """Create and return a synchronous Elasticsearch client."""
    client = Elasticsearch(
        hosts=[settings.elasticsearch_url],
        request_timeout=30,
    )
    if not client.ping():
        logger.error("Cannot connect to Elasticsearch at %s", settings.elasticsearch_url)
        raise ConnectionError(f"Elasticsearch not reachable at {settings.elasticsearch_url}")
    return client


def get_async_es_client() -> AsyncElasticsearch:
    """Create and return an asynchronous Elasticsearch client."""
    client = AsyncElasticsearch(
        hosts=[settings.elasticsearch_url],
        request_timeout=30,
    )
    return client


def ensure_indices(client: Elasticsearch | None = None) -> None:
    """Create indices with mappings if they do not exist."""
    if client is None:
        client = get_es_client()

    for index_name, mapping in MAPPINGS.items():
        if not client.indices.exists(index=index_name):
            client.indices.create(index=index_name, mappings=mapping)
            logger.info("Created index: %s", index_name)
        else:
            logger.debug("Index already exists: %s", index_name)
