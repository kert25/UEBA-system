# UEBA System — Прототип системы обнаружения аномалий в поведении пользователей

> Курсовой проект по дисциплине «Методы и технологии программирования», вариант 9

## Описание

Прототип **UEBA** (User and Entity Behavior Analytics) — системы для автоматического выявления подозрительной активности пользователей (инсайдерские угрозы). Система анализирует логи событий, строит профили нормального поведения и обнаруживает отклонения с помощью алгоритма **Isolation Forest**.

### Три измерения детекции

| Измерение | Признаки | Пример аномалии |
|---|---|---|
| **Время** | hour_of_day, day_of_week, deviation_from_mean | Вход в 03:00 ночи |
| **Геолокация** | country, city, distance_from_previous | Москва → Сидней за 1 час |
| **Объём данных** | bytes_transferred, daily_total_bytes | Скачивание 2 ГБ за сеанс |

## Архитектура

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ Log Ingestor│────▶│Feature Extractor │────▶│Profile Builder   │
│  (:8001)    │     │  (:8002)         │     │  (:8003)         │
└─────────────┘     └──────────────────┘     └──────────────────┘
                                                        │
┌─────────────┐     ┌──────────────────┐               ▼
│  Alerting   │◀────│Anomaly Detector  │◀─────────── [Features]
│  (:8005)    │     │  (:8004)         │
└─────────────┘     └──────────────────┘
       │
       ▼
  ┌─────────────┐     ┌─────────────┐
  │Elasticsearch│◀───▶│   Kibana    │
  │   (:9200)   │     │   (:5601)   │
  └─────────────┘     └─────────────┘
```

## Технологический стек

- **Python 3.12+**, **FastAPI**, **Uvicorn**
- **pandas**, **NumPy**, **scikit-learn** (Isolation Forest)
- **Elasticsearch** + **Kibana** (ELK)
- **Docker** + **Docker Compose**
- **pytest** (покрытие ≥70%), **Bandit**, **safety**

## Быстрый старт

### 1. Клонирование и установка

```bash
cd ueba-system
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Генерация синтетических данных

```bash
python scripts/generate_synthetic_logs.py
# Создаёт data/synthetic_logs.json и data/synthetic_logs.csv
```

### 3. Обучение ML-модели

```bash
python scripts/train_model.py
# Сохраняет models/isolation_forest.joblib
```

### 4. Запуск системы

```bash
docker compose up -d
# Elasticsearch: http://localhost:9200
# Kibana:        http://localhost:5601
# API сервисов:  http://localhost:8001-8005
```

### 5. Ингестия данных

```bash
curl -X POST http://localhost:8001/ingest \
  -H "Content-Type: application/json" \
  -d @data/synthetic_logs.json
```

### 6. Запрос аномалий

```bash
curl http://localhost:8005/anomalies | jq
```

## Структура проекта

```
ueba-system/
├── docker-compose.yml
├── pyproject.toml
├── services/
│   ├── log_ingestor/          # Приём и парсинг логов
│   ├── feature_extractor/     # Извлечение признаков
│   ├── profile_builder/       # Построение профилей
│   ├── anomaly_detector/      # Детекция (Isolation Forest)
│   └── alerting/              # Оповещения и API
├── ml/model.py                # Обучение и сериализация модели
├── shared/                    # Общие утилиты (config, es_client, models)
├── scripts/                   # Генерация данных, обучение
├── tests/                     # Модульные и интеграционные тесты
└── models/                    # Сериализованные модели
```

## API эндпоинты

| Сервис | Порт | Эндпоинты |
|---|---|---|
| Log Ingestor | 8001 | `POST /ingest`, `POST /ingest/csv` |
| Feature Extractor | 8002 | `POST /extract`, `POST /extract/all` |
| Profile Builder | 8003 | `POST /build`, `GET /profile/{user_id}` |
| Anomaly Detector | 8004 | `POST /detect`, `POST /detect/all` |
| Alerting | 8005 | `GET /anomalies`, `GET /anomalies/{user_id}`, `GET /stats` |

Swagger UI доступен по адресу `http://localhost:PORT/docs` для каждого сервиса.

## Тестирование

```bash
pytest --cov=services --cov=ml --cov=shared --cov-report=term-missing
```

## Безопасность

```bash
bandit -r .
safety check
```

## Семантические коммиты

- `feat:` — новая функциональность
- `fix:` — исправление ошибки
- `docs:` — документация
- `test:` — тесты
- `refactor:` — рефакторинг
- `chore:` — вспомогательные задачи

## Лицензия

MIT
