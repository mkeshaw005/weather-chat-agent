# syntax=docker/dockerfile:1.7

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

# Install system deps (if needed for some wheels) and create non-root user
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends curl ca-certificates; \
    rm -rf /var/lib/apt/lists/*; \
    useradd -m -u 10001 appuser

WORKDIR /app

# Install dependencies first for better caching
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy app source
COPY app/ ./app/

# Expose port for Azure Container Apps
EXPOSE 8080

# Switch to non-root user
RUN mkdir -p /app/data && chown -R appuser:appuser /app
USER appuser

# Start FastAPI via Uvicorn
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8080"]
