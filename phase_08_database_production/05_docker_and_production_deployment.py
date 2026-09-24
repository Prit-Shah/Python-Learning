"""
Phase 8: Database & Production Backend - Docker & Production Deployment (P4 Precursor)
================================================================================
1. PRODUCTION ARCHITECTURE:
   - Production Multi-Stage Dockerization for Python:
     * Stage 1 (Builder): Installs compiler tools, builds wheel cache, compiles dependencies.
     * Stage 2 (Runtime): Minimal distroless or python:3.13-slim base image.
       Copies pre-built wheels, creates a non-privileged system user ('appuser'),
       and runs without root privileges!
   - Multi-Container Orchestration with 'docker-compose.yml':
     * FastAPI Web Service.
     * PostgreSQL with healthchecks and persistent volumes.
     * Redis for sub-millisecond caching and task queues.
   - Process Manager:
     * Running Gunicorn as the master process manager with multiple Uvicorn worker processes:
       'gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app'.
================================================================================
"""

import sys
from pathlib import Path

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


SAMPLE_DOCKERFILE = """# Stage 1: Build dependencies
FROM python:3.13-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv
COPY pyproject.toml .
RUN uv venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv PATH="/opt/venv/bin:$PATH"
RUN uv pip install -r pyproject.toml

# Stage 2: Runtime
FROM python:3.13-slim AS runtime
WORKDIR /app
RUN groupadd -g 1001 appgroup && useradd -u 1001 -g appgroup -s /bin/bash appuser
COPY --from=builder /opt/venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv PATH="/opt/venv/bin:$PATH"
COPY --chown=appuser:appgroup . .
USER appuser
EXPOSE 8000
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "main:app"]
"""

SAMPLE_DOCKER_COMPOSE = """version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:secret@postgres:5432/app_db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=secret
      - POSTGRES_DB=app_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  postgres_data:
"""


def demonstrate_deployment_files():
    print("\n--- 1. Multi-Stage Production Dockerfile ---")
    print(SAMPLE_DOCKERFILE[:300] + "\n  ... [trimmed for display] ...\n")

    print("\n--- 2. Multi-Container docker-compose.yml ---")
    print(SAMPLE_DOCKER_COMPOSE[:300] + "\n  ... [trimmed for display] ...\n")


def run_tests():
    print("\n[*] Running automated tests for 05_docker_and_production_deployment.py...")
    assert "FROM python:3.13-slim AS builder" in SAMPLE_DOCKERFILE
    assert "useradd -u 1001" in SAMPLE_DOCKERFILE
    assert "USER appuser" in SAMPLE_DOCKERFILE
    assert "service_healthy" in SAMPLE_DOCKER_COMPOSE
    assert "postgres_data:" in SAMPLE_DOCKER_COMPOSE

    (Path(__file__).parent / "Dockerfile.reference").write_text(SAMPLE_DOCKERFILE, encoding="utf-8")
    (Path(__file__).parent / "docker-compose.reference.yml").write_text(SAMPLE_DOCKER_COMPOSE, encoding="utf-8")
    print("  Created reference Dockerfile and docker-compose templates.")

    print("[SUCCESS] All Docker & Deployment tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 65)
    print("Execution: Phase 8 - Docker & Production Deployment (P4 Precursor)")
    print("=" * 65)
    demonstrate_deployment_files()
    print("-" * 65)
    run_tests()
    print("=" * 65)
