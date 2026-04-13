"""Parser for JSON and CSV log ingestion."""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime
from typing import Any

from shared.models import EventIngest

logger = logging.getLogger(__name__)


def parse_json_events(data: list[dict[str, Any]]) -> list[EventIngest]:
    """Parse a list of JSON event dicts into validated EventIngest models.

    Args:
        data: List of raw event dicts from JSON payload.

    Returns:
        List of validated EventIngest objects.

    Raises:
        ValueError: If any event fails validation.
    """
    events: list[EventIngest] = []
    errors: list[str] = []

    for i, raw in enumerate(data):
        try:
            event = EventIngest(**raw)
            events.append(event)
        except Exception as exc:
            errors.append(f"Event {i}: {exc}")

    if errors:
        logger.warning("Parse errors: %s", errors[:5])
        if len(errors) > len(events):
            raise ValueError(f"Too many parse errors: {errors[:10]}")

    logger.info("Parsed %d valid events from JSON", len(events))
    return events


def parse_csv_events(data: str) -> list[EventIngest]:
    """Parse CSV-formatted string into validated EventIngest models.

    Args:
        data: CSV string with header row.

    Returns:
        List of validated EventIngest objects.
    """
    reader = csv.DictReader(io.StringIO(data))
    raw_events: list[dict[str, Any]] = []

    for row in reader:
        # Convert types
        if "bytes_transferred" in row:
            try:
                row["bytes_transferred"] = int(row["bytes_transferred"])
            except (ValueError, TypeError):
                continue

        if "timestamp" in row:
            # Ensure ISO format
            try:
                datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
            except (ValueError, TypeError):
                continue

        raw_events.append(row)

    return parse_json_events(raw_events)
