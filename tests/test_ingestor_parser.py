"""Tests for the log ingestor parser."""

from datetime import datetime

import pytest

from services.log_ingestor.parser import parse_csv_events, parse_json_events


def _make_raw_event() -> dict:
    return {
        "event_id": "evt-001",
        "timestamp": "2026-04-13T14:30:00",
        "user_id": "user_001",
        "ip_address": "192.168.1.1",
        "country": "Russia",
        "city": "Moscow",
        "bytes_transferred": 10_000_000,
        "action_type": "login",
        "resource": "/api/data",
    }


class TestParseJsonEvents:
    """Tests for JSON event parser."""

    def test_parse_single_valid_event(self) -> None:
        """Test parsing a single valid event."""
        events = parse_json_events([_make_raw_event()])
        assert len(events) == 1
        assert events[0].user_id == "user_001"
        assert events[0].event_id == "evt-001"

    def test_parse_multiple_events(self) -> None:
        """Test parsing multiple events."""
        evts = [_make_raw_event() for _ in range(5)]
        events = parse_json_events(evts)
        assert len(events) == 5

    def test_parse_invalid_action_type(self) -> None:
        """Test that invalid action_type raises ValueError."""
        bad = _make_raw_event()
        bad["action_type"] = "hack"
        with pytest.raises(ValueError, match="action_type"):
            parse_json_events([bad])

    def test_parse_missing_required_field(self) -> None:
        """Test that missing required fields raise ValueError."""
        bad = _make_raw_event()
        del bad["user_id"]
        with pytest.raises(ValueError, match="user_id"):
            parse_json_events([bad])

    def test_parse_empty_list(self) -> None:
        """Test parsing empty list."""
        events = parse_json_events([])
        assert len(events) == 0

    def test_parse_auto_generates_uuid(self) -> None:
        """Test that event_id is auto-generated if not provided."""
        raw = _make_raw_event()
        del raw["event_id"]
        events = parse_json_events([raw])
        assert len(events) == 1
        assert len(events[0].event_id) == 36


class TestParseCsvEvents:
    """Tests for CSV event parser."""

    def _make_csv_string(self) -> str:
        return (
            "event_id,timestamp,user_id,ip_address,country,city,"
            "bytes_transferred,action_type,resource\n"
            "evt-001,2026-04-13T14:30:00,user_001,192.168.1.1,Russia,Moscow,"
            "10000000,login,/api/data\n"
        )

    def test_parse_valid_csv(self) -> None:
        """Test parsing valid CSV string."""
        events = parse_csv_events(self._make_csv_string())
        assert len(events) == 1
        assert events[0].user_id == "user_001"

    def test_parse_empty_csv(self) -> None:
        """Test parsing empty CSV (header only)."""
        csv_str = (
            "event_id,timestamp,user_id,ip_address,country,city,"
            "bytes_transferred,action_type,resource\n"
        )
        events = parse_csv_events(csv_str)
        assert len(events) == 0
