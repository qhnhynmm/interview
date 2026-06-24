# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=120

WORKDIR /app

# configs/backend-services.yml is read at startup (non-secret defaults).
COPY configs/backend-services.yml configs/backend-services.yml

COPY backend/requirements.txt backend/requirements.txt
# Dùng network host khi build để tránh lỗi DNS "Temporary failure in name resolution".
RUN --network=host pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/

WORKDIR /app/backend

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]