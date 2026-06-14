"""Application configuration loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Centralized settings for all UEBA services."""

    # Elasticsearch
    elasticsearch_host: str = "localhost"
    elasticsearch_port: int = 9200

    # ML Model
    model_path: str = "models/isolation_forest.joblib"
    contamination_rate: float = 0.05
    anomaly_threshold: float = 0.6

    # Data generation
    num_events: int = 10_000
    anomaly_ratio: float = 0.05
    random_seed: int = 42

    # Alerting
    alert_threshold: float = 0.7
    alert_telegram_token: str = ""
    alert_telegram_chat_id: str = ""

    @property
    def elasticsearch_url(self) -> str:
        """Return full Elasticsearch URL."""
        return f"http://{self.elasticsearch_host}:{self.elasticsearch_port}"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
