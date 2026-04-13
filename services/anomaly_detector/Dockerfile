FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

COPY shared/ ./shared/
COPY ml/ ./ml/
COPY services/anomaly_detector/ ./services/anomaly_detector/
COPY models/ ./models/

EXPOSE 8000

CMD ["uvicorn", "services.anomaly_detector.main:app", "--host", "0.0.0.0", "--port", "8000"]
