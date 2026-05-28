# UEBA System — Система обнаружения аномалий в поведении пользователей

> Курсовой проект по дисциплине «Методы и технологии программирования», вариант 9

## Описание

**UEBA** (User and Entity Behavior Analytics) — система для автоматического выявления подозрительной активности пользователей (инсайдерские угрозы). Система анализирует логи событий, строит профили нормального поведения и обнаруживает отклонения с помощью алгоритма **Isolation Forest** и **z-score детекции**.

### Пять измерений детекции

| Измерение | Признаки | Пример аномалии |
|---|---|---|
| **Время** | hour_of_day, z-score от avg_hour | Вход в 03:00 для дневного сотрудника |
| **Геолокация** | country, city, haversine distance | Москва → Сидней за 1 час |
| **Impossible Travel** | distance_km, hours_since_last | 7500 км за 30 минут |
| **Объём данных** | bytes_transferred, z-score от avg_bytes | Скачивание 2 ГБ при норме 10 МБ |
| **Поведение** | event_type, z-score от профиля | Удаление файлов при норме чтения |

### Ключевые возможности

- **Профиль-зависимая детекция** — z-score относительно индивидуального профиля пользователя
- **Haversine distance** — расчёт расстояния между последовательными входами
- **Impossible travel detection** — детекция невозможного перемещения (>900 км/ч)
- **Корреляция событий** — группировка аномалий в инциденты (скользящие окна 5/15/60 мин)
- **Cross-user correlation** — обнаружение координированных атак по IP
- **ML интерпретируемость** — вклад каждого признака в аномальный скор
- **Оповещения** — Email (SMTP) и Telegram Bot API с rate limiting и deduplication
- **Graceful degradation** — сервисы работают при недоступности Elasticsearch

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
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│Elasticsearch│◀───▶│   Kibana         │     │ Correlator  │
│   (:9200)   │     │   (:5601)        │     │  (:8006)    │
└─────────────┘     └──────────────────┘     └─────────────┘
```

## Технологический стек

- **Python 3.12+**, **FastAPI**, **Uvicorn**
- **pandas**, **NumPy**, **scikit-learn** (Isolation Forest + One-Class SVM)
- **Elasticsearch 8.x** + **Kibana 8.x** (ELK)
- **Docker** + **Docker Compose**
- **aiosmtplib** (email), **httpx** (Telegram API)
- **pytest** (покрытие ≥70%), **Bandit**, **safety**, **ruff**
- **GitHub Actions** (CI/CD), **Locust** (нагрузочное тестирование)
- **APScheduler** (автообновление профилей)

## Быстрый старт

### 1. Клонирование и установка

```bash
cd ueba-system
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Конфигурация

```bash
cp .env.example .env
# При необходимости настройте SMTP и Telegram в .env
```

### 3. Генерация синтетических данных

```bash
python scripts/generate_synthetic_logs.py
# Создаёт data/synthetic_logs.json и data/synthetic_logs.csv
```

### 4. Обучение ML-модели

```bash
python scripts/train_model.py
# Сохраняет models/isolation_forest.joblib
```

### 5. Запуск системы

```bash
docker compose up -d
# Elasticsearch: http://localhost:9200
# Kibana:        http://localhost:5601
# API сервисов:  http://localhost:8001-8006
```

### 6. Ингестия данных

```bash
curl -X POST http://localhost:8001/ingest \
  -H "Content-Type: application/json" \
  -d @data/synthetic_logs.json
```

### 7. Полный пайплайн

```bash
# Извлечение признаков
curl -X POST http://localhost:8002/extract/all -H "Content-Type: application/json" -d '{}'

# Построение профилей
curl -X POST http://localhost:8003/build/all -H "Content-Type: application/json" -d '{}'

# Детекция аномалий
curl -X POST http://localhost:8004/detect/all -H "Content-Type: application/json" -d '{}'

# Корреляция инцидентов
curl -X POST http://localhost:8006/correlate -H "Content-Type: application/json" -d '{}'

# Просмотр аномалий
curl http://localhost:8005/anomalies | python3 -m json.tool
```

## Структура проекта

```
ueba-system/
├── docker-compose.yml
├── pyproject.toml
├── services/
│   ├── log_ingestor/          # Приём и парсинг логов
│   ├── feature_extractor/     # Извлечение признаков (+ geo)
│   ├── profile_builder/       # Построение профилей
│   ├── anomaly_detector/      # Детекция (Isolation Forest + z-score)
│   ├── alerting/              # Оповещения (Email, Telegram)
│   └── correlator/            # Корреляция событий в инциденты
├── ml/model.py                # Обучение и сериализация модели
├── shared/                    # Общие утилиты
│   ├── config.py              # Настройки из .env
│   ├── es_client.py           # Клиент Elasticsearch
│   ├── es_health.py           # Health check ES
│   ├── geo_data.py            # Haversine + координаты
│   └── models.py              # Pydantic v2 модели
├── scripts/                   # Генерация данных, обучение
├── tests/                     # Модульные и интеграционные тесты
└── models/                    # Сериализованные модели
```

## API эндпоинты

| Сервис | Порт | Эндпоинты |
|---|---|---|
| Log Ingestor | 8001 | `POST /ingest`, `POST /ingest/csv` |
| Feature Extractor | 8002 | `POST /extract`, `POST /extract/all` |
| Profile Builder | 8003 | `POST /build`, `POST /build/all`, `GET /profile/{user_id}` |
| Anomaly Detector | 8004 | `POST /detect`, `POST /detect/all` |
| Alerting | 8005 | `GET /anomalies`, `GET /anomalies/{user_id}`, `GET /stats`, `POST /process` |
| Correlator | 8006 | `POST /correlate`, `GET /incidents` |

Swagger UI доступен по адресу `http://localhost:PORT/docs` для каждого сервиса.

## Модели данных

### EventIngest
Входящее событие: `event_id`, `user_id`, `timestamp`, `ip_address`, `country`, `city`, `bytes_transferred`, `action_type`, `resource`, `latitude`, `longitude`

### FeatureRecord
Извлечённые признаки: `hour_of_day`, `day_of_week`, `minutes_from_midnight`, `country_code`, `bytes_transferred`, `latitude`, `longitude`, `distance_from_previous_km`, `hours_since_last_event`

### UserProfile
Статистический профиль: `user_id`, `avg_hour`, `std_hour`, `avg_bytes`, `std_bytes`, `top_countries`

### AnomalyRecord
Запись аномалии: `anomaly_id`, `event_id`, `user_id`, `anomaly_score`, `dimensions`, `feature_contributions`, `top_features`, `source_ip`

### IncidentRecord
Сгруппированный инцидент: `incident_id`, `user_ids`, `anomaly_count`, `severity` (single/repeated/critical), `window_minutes`, `anomaly_ids`, `top_dimensions`

## Тестирование

```bash
pytest --cov=services --cov=ml --cov=shared --cov-report=term-missing
```

Текущее покрытие: **≥71%** (требование ≥70%).

### Сравнение моделей

```bash
python scripts/compare_models.py
```

Результаты (на 10 000 синтетических событий):

| Метрика | Isolation Forest | One-Class SVM |
|---|---|---|
| Precision | 0.8922 | 1.0000 |
| Recall | 0.9334 | 0.8089 |
| F1 | 0.9123 | 0.8943 |
| Training time | 0.11s | 0.04s |
| Inference time | 0.04s | 0.05s |

### Нагрузочное тестирование

```bash
# Запуск системы
docker compose up -d

# Загрузка данных в ES
python scripts/generate_synthetic_logs.py
# ... ингестия данных ...

# Запуск Locust
bash scripts/run_load_test.sh
```

## Безопасность

```bash
bandit -r . --exclude .venv,tests
safety check
```

## Troubleshooting

### Elasticsearch не поднимается
```bash
docker compose down
docker volume rm ueba-system_es-data
docker compose up -d
```

### Сервисы не видят Elasticsearch
Проверьте, что ES использует версию 8.x. Клиент Python совместим с ES 8.15.

### Модель не обучена
```bash
python scripts/train_model.py
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
