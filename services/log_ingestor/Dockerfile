FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

COPY shared/ ./shared/
COPY services/log_ingestor/ ./services/log_ingestor/

EXPOSE 8000

CMD ["uvicorn", "services.log_ingestor.main:app", "--host", "0.0.0.0", "--port", "8000"]
