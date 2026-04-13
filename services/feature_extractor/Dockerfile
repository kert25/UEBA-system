FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

COPY shared/ ./shared/
COPY services/feature_extractor/ ./services/feature_extractor/

EXPOSE 8000

CMD ["uvicorn", "services.feature_extractor.main:app", "--host", "0.0.0.0", "--port", "8000"]
