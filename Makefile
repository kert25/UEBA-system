.PHONY: setup build start pipeline test lint stop clean all

# ─── Первый запуск (один раз) ────────────────────────────────────────────────
setup:
	python3.12 -m venv .venv
	.venv/bin/pip install -e ".[dev]"
	.venv/bin/python scripts/generate_synthetic_logs.py
	.venv/bin/python scripts/train_model.py
	@echo ""
	@echo "✅ Готово. Теперь: make build && make start && make pipeline"

# ─── Сборка Docker-образов ────────────────────────────────────────────────────
build:
	docker-compose build

# ─── Запуск системы ───────────────────────────────────────────────────────────
start:
	docker-compose up -d
	@echo "Ожидаем запуск Elasticsearch..."
	@sleep 20
	@echo "Проверяем healthchecks..."
	@for p in 8001 8002 8003 8004 8005 8006; do \
		curl -sf http://localhost:$$p/health > /dev/null 2>&1 \
			&& echo "  :$$p OK" || echo "  :$$p FAIL"; \
	done

# ─── Полный пайплайн (данные уже должны быть в ES) ────────────────────────────
pipeline:
	@echo "1. Загружаем события..."
	curl -s -X POST http://localhost:8001/ingest \
		-H "Content-Type: application/json" \
		-d @data/synthetic_logs.json | python3 -m json.tool
	@echo "2. Извлекаем признаки..."
	curl -s -X POST http://localhost:8002/extract/all \
		-H "Content-Type: application/json" -d '{}' | python3 -m json.tool
	@echo "3. Строим профили..."
	curl -s -X POST http://localhost:8003/build/all \
		-H "Content-Type: application/json" -d '{}' | python3 -m json.tool
	@echo "4. Детектируем аномалии..."
	curl -s -X POST http://localhost:8004/detect/all \
		-H "Content-Type: application/json" -d '{}' | python3 -m json.tool
	@echo "5. Коррелируем инциденты..."
	curl -s -X POST http://localhost:8006/correlate \
		-H "Content-Type: application/json" -d '{}' | python3 -m json.tool
	@echo "6. Аномалии:"
	curl -s http://localhost:8005/anomalies | python3 -m json.tool | head -30
	@echo ""
	@echo "✅ Пайплайн завершён"

# ─── Всё сразу ────────────────────────────────────────────────────────────────
all: build start pipeline
	@echo "✅ Система запущена и работает"

# ─── Тесты ─────────────────────────────────────────────────────────────────────
test:
	.venv/bin/pytest --cov=services --cov=ml --cov=shared --cov-report=term-missing

lint:
	.venv/bin/ruff check .
	.venv/bin/ruff format --check .

# ─── Остановка ─────────────────────────────────────────────────────────────────
stop:
	docker-compose down

clean:
	docker-compose down -v
	rm -rf .venv data/synthetic_logs.json data/synthetic_logs.csv models/*.joblib
	@echo "✅ Проект очищен"
