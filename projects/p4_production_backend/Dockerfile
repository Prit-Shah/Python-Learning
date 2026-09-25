# ─────────────────────────────────────────────────────────────
# Stage 1: Build & Dependencies
# ─────────────────────────────────────────────────────────────
FROM python:3.13-slim AS builder

WORKDIR /build
ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends     gcc libpq-dev     && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir uv &&     uv pip install --system --no-cache fastapi uvicorn pydantic pydantic-settings sqlalchemy aiosqlite redis structlog

# ─────────────────────────────────────────────────────────────
# Stage 2: Minimal Distroless/Non-Root Production Runtime
# ─────────────────────────────────────────────────────────────
FROM python:3.13-slim AS runtime

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1     ENV=production

# Security: Create and switch to non-root user
RUN groupadd -g 10001 appgroup &&     useradd -u 10001 -g appgroup -s /bin/bash appuser

COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --chown=appuser:appgroup . /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3     CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')"

CMD ["uvicorn", "projects.p4_production_backend.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
