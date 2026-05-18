"""Elasticsearch health check and fallback utilities."""

from __future__ import annotations

import logging

from shared.es_client import get_es_client

logger = logging.getLogger(__name__)


def is_es_available() -> bool:
    """Check if Elasticsearch is reachable."""
    try:
        client = get_es_client()
        return client.ping()
    except Exception:
        return False
