# backend/Dockerfile
# Builds the FastAPI backend image. Also reused by the `worker` service
# in docker-compose.yml (Celery), since both need the same dependencies.

FROM python:3.11-slim

WORKDIR /app

# System deps needed by Tree-sitter language bindings and graph libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
