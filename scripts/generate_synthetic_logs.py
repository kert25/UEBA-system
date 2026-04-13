"""Generate synthetic user activity logs for UEBA system training and testing.

Generates both normal and anomalous events covering three detection dimensions:
  - Time (unusual hours)
  - Geography (impossible travel, unusual countries)
  - Volume (abnormally large data transfers)

Outputs: data/synthetic_logs.json and data/synthetic_logs.csv
"""

from __future__ import annotations

import csv
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from faker import Faker

# ─── Configuration ───────────────────────────────────────────────────────────

NUM_EVENTS = 10_000
ANOMALY_RATIO = 0.05
SEED = 42
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data"

fake = Faker()
random.seed(SEED)
fake.seed_instance(SEED)

# ─── Normal behaviour patterns ───────────────────────────────────────────────

RUSSIAN_IPS = [
    "192.168.1.",
    "10.0.0.",
    "172.16.0.",
    "85.140.",
    "95.84.",
    "188.162.",
    "213.87.",
    "77.88.",
]

NORMAL_COUNTRIES = ["Russia", "Belarus", "Kazakhstan", "Armenia"]
NORMAL_CITIES = {
    "Russia": ["Moscow", "Saint Petersburg", "Novosibirsk", "Yekaterinburg", "Kazan"],
    "Belarus": ["Minsk"],
    "Kazakhstan": ["Almaty", "Astana"],
    "Armenia": ["Yerevan"],
}

ANOMALOUS_COUNTRIES = [
    "United States", "China", "Brazil", "Australia", "Nigeria",
    "North Korea", "Iran", "Germany", "United Kingdom", "Japan",
]
ANOMALOUS_CITIES = {
    "United States": ["New York", "San Francisco", "Washington"],
    "China": ["Beijing", "Shanghai"],
    "Brazil": ["Sao Paulo", "Rio de Janeiro"],
    "Australia": ["Sydney", "Melbourne"],
    "Nigeria": ["Lagos", "Abuja"],
    "North Korea": ["Pyongyang"],
    "Iran": ["Tehran"],
    "Germany": ["Berlin", "Munich"],
    "United Kingdom": ["London"],
    "Japan": ["Tokyo"],
}

USER_IDS = [f"user_{i:03d}" for i in range(1, 51)]  # 50 users
ACTION_TYPES = ["login", "download", "upload", "access", "modify"]
RESOURCES = ["/api/data", "/api/reports", "/api/files", "/dashboard", "/api/admin", "/api/export"]


def _random_ip(prefixes: list[str]) -> str:
    prefix = random.choice(prefixes)
    return f"{prefix}{random.randint(1, 254)}"


def _normal_event(user_id: str, base_date: datetime) -> dict:
    """Generate a single normal event within business hours."""
    # Business hours: 9-18 on weekdays
    day_offset = random.randint(0, 29)  # spread over a month
    hour = random.randint(9, 17)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    ts = base_date + timedelta(days=day_offset, hours=hour - 9, minutes=minute, seconds=second)

    country = random.choice(NORMAL_COUNTRIES)
    city = random.choice(NORMAL_CITIES[country])

    return {
        "event_id": str(uuid4()),
        "timestamp": ts.isoformat(),
        "user_id": user_id,
        "ip_address": _random_ip(RUSSIAN_IPS),
        "country": country,
        "city": city,
        "bytes_transferred": random.randint(1_000_000, 50_000_000),  # 1-50 MB
        "action_type": random.choice(ACTION_TYPES),
        "resource": random.choice(RESOURCES),
    }


def _anomalous_time(user_id: str, base_date: datetime) -> dict:
    """Anomalous event: login at unusual hours (midnight-5am)."""
    day_offset = random.randint(0, 29)
    hour = random.randint(0, 4)
    minute = random.randint(0, 59)
    ts = base_date + timedelta(days=day_offset, hours=hour, minutes=minute)

    country = random.choice(NORMAL_COUNTRIES)
    city = random.choice(NORMAL_CITIES[country])

    return {
        "event_id": str(uuid4()),
        "timestamp": ts.isoformat(),
        "user_id": user_id,
        "ip_address": _random_ip(RUSSIAN_IPS),
        "country": country,
        "city": city,
        "bytes_transferred": random.randint(1_000_000, 50_000_000),
        "action_type": random.choice(ACTION_TYPES),
        "resource": random.choice(RESOURCES),
    }


def _anomalous_geography(user_id: str, base_date: datetime) -> dict:
    """Anomalous event: login from unusual country (impossible travel)."""
    day_offset = random.randint(0, 29)
    hour = random.randint(9, 17)
    ts = base_date + timedelta(days=day_offset, hours=hour - 9)

    country = random.choice(ANOMALOUS_COUNTRIES)
    city = random.choice(ANOMALOUS_CITIES[country])

    return {
        "event_id": str(uuid4()),
        "timestamp": ts.isoformat(),
        "user_id": user_id,
        "ip_address": fake.ipv4(),
        "country": country,
        "city": city,
        "bytes_transferred": random.randint(1_000_000, 50_000_000),
        "action_type": "login",
        "resource": "/api/data",
    }


def _anomalous_volume(user_id: str, base_date: datetime) -> dict:
    """Anomalous event: abnormally large data transfer (>500 MB)."""
    day_offset = random.randint(0, 29)
    hour = random.randint(9, 17)
    ts = base_date + timedelta(days=day_offset, hours=hour - 9)

    country = random.choice(NORMAL_COUNTRIES)
    city = random.choice(NORMAL_CITIES[country])

    return {
        "event_id": str(uuid4()),
        "timestamp": ts.isoformat(),
        "user_id": user_id,
        "ip_address": _random_ip(RUSSIAN_IPS),
        "country": country,
        "city": city,
        "bytes_transferred": random.randint(500_000_000, 5_000_000_000),  # 500 MB - 5 GB
        "action_type": random.choice(["download", "upload", "access"]),
        "resource": random.choice(RESOURCES),
    }


def generate() -> list[dict]:
    """Generate all synthetic events."""
    base_date = datetime(2026, 3, 1, tzinfo=timezone.utc)
    num_anomalies = int(NUM_EVENTS * ANOMALY_RATIO)
    num_normal = NUM_EVENTS - num_anomalies

    events: list[dict] = []

    # Normal events
    for _ in range(num_normal):
        user = random.choice(USER_IDS)
        events.append(_normal_event(user, base_date))

    # Anomalous events — distributed across three types
    anomaly_generators = [_anomalous_time, _anomalous_geography, _anomalous_volume]
    for i in range(num_anomalies):
        user = random.choice(USER_IDS)
        gen = anomaly_generators[i % len(anomaly_generators)]
        events.append(gen(user, base_date))

    # Shuffle
    random.shuffle(events)
    # Sort by timestamp for realism
    events.sort(key=lambda e: e["timestamp"])
    return events


def save(events: list[dict]) -> None:
    """Save events to JSON and CSV files."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    json_path = OUTPUT_DIR / "synthetic_logs.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)

    csv_path = OUTPUT_DIR / "synthetic_logs.csv"
    fieldnames = list(events[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(events)


def main() -> None:
    """Entry point."""
    print(f"Generating {NUM_EVENTS} synthetic events (anomaly ratio: {ANOMALY_RATIO:.1%})...")
    events = generate()
    save(events)
    print(f"Saved to {OUTPUT_DIR / 'synthetic_logs.json'} and {OUTPUT_DIR / 'synthetic_logs.csv'}")

    # Summary
    anomalous = [e for e in events if e["bytes_transferred"] > 500_000_000
                 or e["country"] in ANOMALOUS_COUNTRIES
                 or int(e["timestamp"][11:13]) < 5]
    print(f"Total events: {len(events)}")
    print(f"Anomalous events: {len(anomalous)} ({len(anomalous)/len(events):.1%})")


if __name__ == "__main__":
    main()
