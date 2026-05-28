"""Locust load testing for UEBA system.

Usage:
    locust -f locustfile.py --headless -u 50 -r 5 --run-time 60s --host http://localhost:8001

Or use the convenience script:
    bash scripts/run_load_test.sh
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from uuid import uuid4

from locust import HttpUser, between, task

USERS = [f"user_{i:03d}" for i in range(100)]
COUNTRIES = [
    "Russia", "United States", "Germany", "United Kingdom",
    "China", "Japan", "France", "Brazil", "Australia", "India",
]
ACTIONS = ["login", "download", "upload", "access", "delete", "modify"]


def _generate_event() -> dict:
    """Generate a single synthetic event."""
    return {
        "event_id": str(uuid4()),
        "timestamp": (datetime.utcnow() - timedelta(seconds=random.randint(0, 3600))).isoformat() + "Z",
        "user_id": random.choice(USERS),
        "ip_address": f"{random.randint(10, 200)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}",
        "country": random.choice(COUNTRIES),
        "city": "TestCity",
        "bytes_transferred": random.randint(1_000, 500_000_000),
        "action_type": random.choice(ACTIONS),
        "resource": random.choice(["/api/data", "/api/files", "/api/admin", "/api/reports"]),
    }


class UEBAUser(HttpUser):
    """Simulates a user of the UEBA system."""

    wait_time = between(0.5, 2.0)

    def on_start(self) -> None:
        """Generate a batch of events once."""
        self.events = [_generate_event() for _ in range(100)]

    @task(3)
    def ingest_events(self) -> None:
        """POST /ingest — send batch of events."""
        events = [_generate_event() for _ in range(10)]
        with self.client.post(
            "/ingest",
            json=events,
            catch_response=True,
            name="POST /ingest (batch 10)",
        ) as resp:
            if resp.status_code not in (200, 202):
                resp.failure(f"Unexpected status: {resp.status_code}")

    @task(1)
    def get_anomalies(self) -> None:
        """GET /anomalies — fetch anomaly list from alerting service."""
        with self.client.get(
            "http://localhost:8005/anomalies",
            catch_response=True,
            name="GET /anomalies",
        ) as resp:
            if resp.status_code not in (200, 503):
                resp.failure(f"Unexpected status: {resp.status_code}")

    @task(1)
    def health_check(self) -> None:
        """GET /health — verify services are alive."""
        for port, name in [("8001", "ingestor"), ("8002", "extractor"), ("8006", "correlator")]:
            with self.client.get(
                f"http://localhost:{port}/health",
                catch_response=True,
                name=f"GET /health ({name})",
            ) as resp:
                if resp.status_code != 200:
                    resp.failure(f"{name} health check failed: {resp.status_code}")
