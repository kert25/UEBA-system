"""Tests for shared configuration."""

from shared.config import Settings


def test_default_settings() -> None:
    """Test that default settings have correct values."""
    s = Settings()
    assert s.elasticsearch_host == "localhost"
    assert s.elasticsearch_port == 9200
    assert s.contamination_rate == 0.05
    assert s.anomaly_threshold == 0.6
    assert s.num_events == 10_000


def test_elasticsearch_url() -> None:
    """Test elasticsearch_url property construction."""
    s = Settings()
    assert s.elasticsearch_url == "http://localhost:9200"

    s2 = Settings(elasticsearch_host="es-server", elasticsearch_port=9300)
    assert s2.elasticsearch_url == "http://es-server:9300"


def test_custom_anomaly_threshold() -> None:
    """Test custom threshold."""
    s = Settings(anomaly_threshold=0.8)
    assert s.anomaly_threshold == 0.8
