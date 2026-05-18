"""Tests for synthetic data generation script."""

import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


class TestGenerateSyntheticLogs:
    """Tests for data generation."""

    def test_generate_returns_list(self) -> None:
        """Test that generate returns a list."""
        from generate_synthetic_logs import generate

        events = generate()
        assert isinstance(events, list)
        assert len(events) == 10_000

    def test_events_have_required_fields(self) -> None:
        """Test that generated events have all required fields."""
        from generate_synthetic_logs import generate

        events = generate()
        required = {
            "event_id",
            "timestamp",
            "user_id",
            "ip_address",
            "country",
            "city",
            "bytes_transferred",
            "action_type",
            "resource",
        }
        for event in events[:10]:
            assert required.issubset(set(event.keys()))

    def test_events_sorted_by_timestamp(self) -> None:
        """Test that events are sorted by timestamp."""
        from generate_synthetic_logs import generate

        events = generate()
        timestamps = [e["timestamp"] for e in events]
        assert timestamps == sorted(timestamps)

    def test_anomaly_ratio_approximate(self) -> None:
        """Test that anomaly ratio is approximately correct."""
        from generate_synthetic_logs import ANOMALOUS_COUNTRIES, generate

        events = generate()
        anomalous = [
            e
            for e in events
            if e["bytes_transferred"] > 500_000_000
            or e["country"] in ANOMALOUS_COUNTRIES
            or int(e["timestamp"][11:13]) < 5
        ]
        ratio = len(anomalous) / len(events)
        assert 0.01 < ratio < 0.60  # rough check
