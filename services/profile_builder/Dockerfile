FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

COPY shared/ ./shared/
COPY services/profile_builder/ ./services/profile_builder/

EXPOSE 8000

CMD ["uvicorn", "services.profile_builder.main:app", "--host", "0.0.0.0", "--port", "8000"]
