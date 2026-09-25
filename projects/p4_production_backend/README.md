# 🧗 Project P4: Containerized Production Backend
> **Roadmap Target**: Synthesizes Production Tooling, Docker, Redis Caching, RBAC Auth, and Background Queues (Phase 8).

---

## 🏛️ Architecture & Component Design

```text
p4_production_backend/
├── config.py           # 12-Factor Settings with pydantic-settings
├── auth.py             # Stateless HMAC-SHA256 JWT & RBAC dependencies
├── cache.py            # Cache-Aside pattern implementation
├── tasks.py            # Background worker & audit log processing
├── app.py              # Middleware, Request Tracing, and API Endpoints
├── Dockerfile          # Multi-stage build with non-root security user
├── docker-compose.yml  # Multi-container production stack (API, Postgres, Redis)
└── tests/              # Pytest verification suite
```

---

## ⚡ Technical Highlights

1. **Security-Hardened Multi-Stage Dockerfile**:
   - Stage 1 compiles C extensions using `uv` for 10x faster package resolution.
   - Stage 2 copies only compiled wheels to a slim distroless/debian base.
   - Runs as non-root user `appuser (uid: 10001)`.
   - Incorporates native Docker `HEALTHCHECK`.

2. **Cache-Aside Pattern (`cache.py`)**:
   - Queries check the cache key first. On cache miss, loads from primary source and writes back with TTL.
   - Mutations (Admin actions) proactively invalidate relevant cache keys to prevent stale reads.

3. **Stateless JWT with RBAC (`auth.py`)**:
   - Decoupled token issuance and signature verification.
   - Clean FastAPI dependency injection with `require_role('admin')`.

---

## 🚀 Running the Stack

```bash
# Local development:
uvicorn projects.p4_production_backend.app:app --reload --port 8000

# Production Docker Compose:
docker-compose up -d --build
```
