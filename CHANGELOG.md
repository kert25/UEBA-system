# Changelog

## v1.0.0 (2026-05-28)

### Added
- **One-Class SVM model** (`ml/model.py`): New `OCSVMModel` class with the same interface as `AnomalyModel` (train, predict, save, load, feature contributions)
- **Model comparison script** (`scripts/compare_models.py`): Side-by-side comparison of Isolation Forest vs One-Class SVM on synthetic data
- **Auto-profile updates** (`services/profile_builder/main.py`): `AsyncIOScheduler` automatically rebuilds user profiles every N minutes (configurable via `PROFILE_REBUILD_INTERVAL`, default 60)
- **CI/CD pipeline** (`.github/workflows/ci.yml`): GitHub Actions with linting (ruff), SAST (bandit), dependency check (safety), test coverage, and model training verification
- **Load testing** (`locustfile.py`, `scripts/run_load_test.sh`): Locust-based performance testing for ≥1000 req/s
- **Tests**: 34 new tests (OCSVM, ES client, ES fallback edge cases, detector edge cases, deviation features, alert sending, scheduler health)
- **Coverage**: Raised from 66% to **71%** (threshold updated to 70%)

### Changed
- `pyproject.toml`: Added `apscheduler>=3.10`, `locust>=2.31.0` dependencies; coverage `fail_under` → 70
- `services/profile_builder/main.py`: Added scheduler status to `/health` endpoint
- `shared/models.py`: Updated `IncidentRecord` to use `model_config`
- `tests/test_feature_extractor.py`: Added geo, distance, and deviation feature tests
- `tests/test_detector.py`: Added profile-based z-score, zero-std, geography edge case tests

### Fixed
- `ml/model.py`: `get_feature_contributions` uses `scaler.mean_` (not `data_min_`), handles zero-total edge case with uniform fallback
- `tests/test_profile_builder.py`: Inline `pytest.raises` import → `pytest.raises` direct usage

## v0.1.0 (2026-05-18)

### Added
- Initial MVP with 5 microservices (log-ingestor, feature-extractor, profile-builder, anomaly-detector, alerting)
- Isolation Forest anomaly detection
- Elasticsearch + Kibana integration
- Synthetic data generation (10000 events, 5% anomalies)
- Docker Compose orchestration
- Pydantic v2 models
- FastAPI endpoints with Swagger UI
- Pre-commit hooks (ruff, bandit, safety)
- Emergency ES fallback, Haversine geo-distance, impossible travel detection
- Z-score profile-based detection
- Correlator microservice (sliding windows, cross-user correlation)
- ML interpretability (feature contributions via permutation)
- Real email (SMTP) and Telegram alerts
