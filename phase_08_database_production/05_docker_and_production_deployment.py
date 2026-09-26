r"""
05_docker_and_production_deployment.py

============================================================
1. CONCEPT
============================================================

Deploying enterprise Python services into production environments (Kubernetes, AWS ECS,
Docker Swarm) requires containerization security best practices and robust process
management:

1. Multi-Stage Dockerfile Architecture for Python:
   - Stage 1 (Builder):
     * Base: `python:3.12-slim` (or 3.13-slim).
     * Installs build dependencies (C compilers, `build-essential`, header files).
     * Creates an isolated virtual environment at `/opt/venv` using high-speed package
       managers (`uv` or `pip`).
     * Compiles C extensions and pre-builds wheels into the isolated environment.
   - Stage 2 (Runtime):
     * Base: Minimal clean `python:3.12-slim`.
     * Copies ONLY the pre-built `/opt/venv` from the builder stage.
     * Leaves behind all compilation toolchains, package managers, and temporary files,
       reducing image footprint by up to 70% and drastically shrinking the CVE attack surface.
     * Creates a non-privileged system user (`appuser` with UID 1001, GID 1001) and drops root.

2. Process Management (Gunicorn Master + Uvicorn Workers):
   - Why not run standalone Uvicorn in production?
     * Standalone Uvicorn lacks process supervisor capabilities, automatic worker recovery,
       and robust master-worker IPC.
   - Gunicorn as Process Manager:
     * Command: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 main:app`.
     * Gunicorn master manages worker lifecycles, health pings, and worker restarts if a
       worker memory leaks or deadlocks.
     * Sizing rules:
       - Bare-metal / Dedicated VMs: `workers = (2 * CPU_CORES) + 1` for I/O bound backends.
       - Kubernetes Containers: Typically `workers = 1` or `2` per pod with container CPU limits,
         scaling horizontally via Kubernetes Horizontal Pod Autoscaler (HPA).

3. Graceful Termination & OS Signal Handling:
   - When Kubernetes or Docker shuts down a container:
     1. Kubelet sends `SIGTERM` to the container's PID 1 (Gunicorn).
     2. Gunicorn signals Uvicorn workers to stop accepting new connections.
     3. Workers finish in-flight HTTP requests within the grace period (e.g. 30 seconds).
     4. FastAPI's `@asynccontextmanager lifespan` shutdown block executes: drains database
        connection pools, flushes Redis task buffers, closes HTTP client sessions.
     5. Process exits cleanly with code 0. If timeout expires, `SIGKILL` is issued.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python (FastAPI / Gunicorn)        | JavaScript / TypeScript (Node.js)  |
+------------------------------+------------------------------------+------------------------------------+
| Production Process Manager   | Gunicorn master with Uvicorn worker| PM2 cluster mode / Docker + cluster|
| Multi-Core Scaling           | Multi-process (`-w <cores>`)       | Node.js `cluster` module / PM2 `-i`|
| Multi-Stage Docker Build     | Builder (/opt/venv) -> Runtime     | Builder (npm run build) -> Runner  |
| Non-Root User                | `USER appuser` (UID 1001)          | `USER node` (built-in in node image|
| Graceful Shutdown Signal     | `SIGTERM` -> Gunicorn -> Lifespan  | `process.on('SIGTERM', ...)`       |
| Multi-Container Local Dev    | `docker-compose.yml`               | `docker-compose.yml`               |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Architecture Differences:
1. Node.js applications frequently run directly under `node dist/main.js` in Kubernetes, relying
   purely on Kubernetes Pod replicas for scaling.
2. In Python, Gunicorn provides battle-tested process management with custom worker heartbeat
   protocols (`--worker-tmp-dir /dev/shm`), preventing deadlocked workers from hanging indefinitely.


============================================================
3. UNDER THE HOOD (Linux cgroups & Container Safety)
============================================================

1. The PID 1 Zombie Reaping Problem:
   - In Linux, PID 1 is responsible for reaping orphaned child processes (zombies) and forwarding
     OS signals (`SIGTERM`).
   - If a container is started with a shell command: `CMD gunicorn ...`, the shell (`/bin/sh`)
     becomes PID 1 and frequently fails to forward `SIGTERM` to Python, forcing a dirty `SIGKILL`
     after 30 seconds!
   - FIX: Always use JSON exec syntax: `CMD ["gunicorn", "-w", "4", "main:app"]`.

2. Linux cgroups CFS Quota Throttling:
   - If a Docker container is assigned `resources: limits: cpu: "1.0"`, the Linux Completely
     Fair Scheduler (CFS) grants 100ms of CPU time per 100ms quota period.
   - If you run 4 Gunicorn workers in that container, all 4 workers compete for that 100ms budget,
     exhausting the quota within 25ms and causing severe CPU throttling for the remaining 75ms!
   - FIX: Inside containerized Kubernetes pods with strict CPU limits, size worker counts strictly
     proportionate to the allocated CPU limit (1 worker per 1 CPU core limit).

3. Root Privilege Escalation Prevention:
   - If a container runs as `root`, any remote code execution vulnerability (e.g., vulnerable
     native library or command injection) grants the attacker root access to container namespaces.
   - Creating `RUN useradd -u 1001 -g 1001 appuser` and adding `USER appuser` enforces Linux DAC
     (Discretionary Access Control), preventing file tampering on host mounts.


============================================================
4. COMMON GOTCHAS
============================================================

1. Missing `.dockerignore`:
   - Leaving `.git`, `.venv`, `.env`, and `__pycache__` out of `.dockerignore` will copy local secrets,
     massive caches, and host-architecture compiled binaries into the Linux container image.
   - FIX: Always maintain a strict `.dockerignore` file excluding `.git`, `.env*`, `__pycache__`, `.venv`.

2. Hardcoding Worker Counts Across Heterogeneous Pods:
   - Configuring `-w 8` in a container running on a 0.5 CPU development cluster causes thrashing and timeouts.
   - FIX: Parameterize worker counts via environment variables: `GUNICORN_WORKERS=${WEB_CONCURRENCY:-2}`.

3. Neglecting Healthchecks in Docker Compose:
   - If the FastAPI container starts and tries to connect to PostgreSQL before PostgreSQL has finished
     initializing its disk cluster, FastAPI crashes immediately.
   - FIX: Use `depends_on: postgres: condition: service_healthy` coupled with `healthcheck: test: ["CMD-SHELL", "pg_isready"]`.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "Explain how you architect a secure, minimal Docker container for a FastAPI application."
A1: "I implement a multi-stage Docker build.
     In Stage 1 (the Builder), I start with `python:3.12-slim`, install build tools, and use `uv` to
     build wheels into an isolated virtual environment at `/opt/venv`.
     In Stage 2 (the Runtime), I start from a fresh slim base and copy ONLY `/opt/venv` and the application
     code. I create a dedicated system group and user `appuser` (UID 1001) and switch to `USER appuser`
     to guarantee non-root execution.
     This strips all compilers and package managers from the final image, reducing image size to under
     150MB and eliminating security vulnerabilities associated with root privileges and build tools."

Q2: "Why run Gunicorn as a process manager with Uvicorn workers instead of plain Uvicorn in production?"
A2: "While Uvicorn provides high-performance ASGI event loop execution, it lacks robust process
     management. Gunicorn serves as the master supervisor: it binds the listening socket, monitors
     worker heartbeats, restarts workers that crash or exceed memory thresholds, and orchestrates
     graceful zero-downtime reloads upon receiving `SIGHUP`. In production, we run `gunicorn -w 4 -k uvicorn.workers.UvicornWorker`
     to combine Gunicorn's battle-tested Unix process lifecycle management with Uvicorn's asynchronous
     HTTP parsing."

Q3: "How does graceful shutdown work when Kubernetes evicts or updates a container?"
A3: "When Kubernetes terminates a pod, it sends a `SIGTERM` signal to the container's PID 1.
     Because we use JSON exec syntax in our Docker `CMD`, Gunicorn receives `SIGTERM` directly.
     Gunicorn signals Uvicorn workers to stop accepting new client requests on the socket while allowing
     existing requests to complete within a grace period.
     Simultaneously, FastAPI's `@asynccontextmanager lifespan` executes its shutdown code: draining
     database connection pools, flushing cached telemetry buffers, and closing external HTTP clients.
     The process then terminates cleanly with exit code 0 before Kubernetes reaches its `terminationGracePeriod`
     and sends `SIGKILL`."
"""

import sys
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ==============================================================================
# 1. PRODUCTION MULTI-STAGE DOCKERFILE TEMPLATE
# ==============================================================================

PRODUCTION_DOCKERFILE = """# ==============================================================================
# STAGE 1: Dependency Builder
# ==============================================================================
FROM python:3.12-slim AS builder

WORKDIR /build

# Install minimal compilation toolchain and clean apt caches immediately
RUN apt-get update && apt-get install -y --no-install-recommends \\
    build-essential \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Install ultra-fast Python package manager 'uv'
RUN pip install --no-cache-dir uv

# Create isolated virtualenv
RUN uv venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv PATH="/opt/venv/bin:$PATH"

# Copy dependency manifests first to leverage Docker layer caching
COPY pyproject.toml .

# Install dependencies into virtualenv without building wheels in runtime
RUN uv pip install --no-cache-dir -r pyproject.toml

# ==============================================================================
# STAGE 2: Minimal Non-Root Runtime
# ==============================================================================
FROM python:3.12-slim AS runtime

WORKDIR /app

# Create unprivileged system user and group (UID 1001)
RUN groupadd -g 1001 appgroup && \\
    useradd -u 1001 -g appgroup -s /bin/bash -m appuser

# Copy virtual environment from builder stage
COPY --from=builder --chown=appuser:appgroup /opt/venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv PATH="/opt/venv/bin:$PATH"

# Copy application source code with non-root ownership
COPY --chown=appuser:appgroup . .

# Drop privileges to non-root user
USER appuser

# Expose standard FastAPI port
EXPOSE 8000

# JSON exec syntax ensures Gunicorn is PID 1 to receive SIGTERM properly
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "--access-logfile", "-", "main:app"]
"""


# ==============================================================================
# 2. PRODUCTION DOCKER-COMPOSE TEMPLATE (WITH HEALTHCHECKS)
# ==============================================================================

PRODUCTION_DOCKER_COMPOSE = """version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - APP_ENVIRONMENT=development
      - APP_PORT=8000
      - APP_DATABASE_URL=postgresql+asyncpg://postgres:secret@postgres:5432/app_db
      - APP_REDIS_URL=redis://redis:6379/0
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

  postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=secret
      - POSTGRES_DB=app_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d app_db"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
    restart: unless-stopped

volumes:
  postgres_data:
"""


# ==============================================================================
# 3. CONTAINER SECURITY & SIZING VALIDATOR
# ==============================================================================

class ContainerSecurityAuditor:
    """Audits Dockerfile configurations against production security benchmarks."""

    @staticmethod
    def audit_dockerfile(dockerfile_text: str) -> Dict[str, Any]:
        results: Dict[str, bool] = {}

        # 1. Multi-Stage Build verification
        has_builder = bool(re.search(r"FROM\s+\S+\s+AS\s+builder", dockerfile_text, re.IGNORECASE))
        has_runtime = bool(re.search(r"FROM\s+\S+\s+AS\s+runtime", dockerfile_text, re.IGNORECASE))
        results["multi_stage_build"] = has_builder and has_runtime

        # 2. Non-root user declaration
        has_useradd = bool(re.search(r"useradd\s+-u\s+\d+", dockerfile_text))
        has_user_directive = bool(re.search(r"USER\s+(?!root\b)\w+", dockerfile_text))
        results["non_root_user"] = has_useradd and has_user_directive

        # 3. Virtualenv isolation copied from builder
        has_venv_copy = bool(re.search(r"COPY\s+--from=builder.*opt/venv", dockerfile_text))
        results["venv_copied_from_builder"] = has_venv_copy

        # 4. JSON exec syntax in CMD (PID 1 signal forwarding)
        has_json_cmd = bool(re.search(r'CMD\s*\[\s*"gunicorn"', dockerfile_text))
        results["json_exec_cmd"] = has_json_cmd

        # 5. Build cache cleanup (rm -rf /var/lib/apt/lists/*)
        has_cache_cleanup = "rm -rf /var/lib/apt/lists/*" in dockerfile_text
        results["apt_cache_cleanup"] = has_cache_cleanup

        return results

    @staticmethod
    def calculate_gunicorn_workers(cpu_cores: float, is_container: bool = True) -> int:
        """
        Calculates optimal worker count based on CPU allocation and deployment target.
        - Container with cgroups CPU limit: max(1, int(cpu_cores))
        - Bare-metal / VM without cgroups: (2 * cpu_cores) + 1
        """
        if is_container:
            # Inside containers, avoid cgroups CFS throttling by sticking to allocated cores
            return max(1, int(cpu_cores))
        else:
            return int((2 * cpu_cores) + 1)


# ==============================================================================
# 4. SELF-TESTING SUITE
# ==============================================================================

def run_tests() -> None:
    print("\n[*] Starting automated test suite for 05_docker_and_production_deployment.py...")

    # ------------------------------------------------------------
    # Test 1: Dockerfile Production Security Audit
    # ------------------------------------------------------------
    print("  -> Auditing production Dockerfile security best practices...")
    audit = ContainerSecurityAuditor.audit_dockerfile(PRODUCTION_DOCKERFILE)

    assert audit["multi_stage_build"] is True, "Dockerfile must implement multi-stage build"
    assert audit["non_root_user"] is True, "Dockerfile must declare and drop to non-root USER"
    assert audit["venv_copied_from_builder"] is True, "Runtime stage must copy /opt/venv from builder"
    assert audit["json_exec_cmd"] is True, "CMD must use JSON exec syntax for proper SIGTERM PID 1 handling"
    assert audit["apt_cache_cleanup"] is True, "Apt list caches must be cleaned up to minimize image size"

    # ------------------------------------------------------------
    # Test 2: Worker Concurrency Calculation (cgroups vs Bare-metal)
    # ------------------------------------------------------------
    print("  -> Testing Gunicorn worker sizing algorithm across environments...")
    # Containerized environment: 2 CPU limit -> 2 workers (avoids CFS quota throttling)
    assert ContainerSecurityAuditor.calculate_gunicorn_workers(cpu_cores=2.0, is_container=True) == 2
    assert ContainerSecurityAuditor.calculate_gunicorn_workers(cpu_cores=0.5, is_container=True) == 1

    # Bare-metal VM: 4 CPU cores -> (2 * 4) + 1 = 9 workers
    assert ContainerSecurityAuditor.calculate_gunicorn_workers(cpu_cores=4.0, is_container=False) == 9

    # ------------------------------------------------------------
    # Test 3: Docker Compose Healthcheck Configuration
    # ------------------------------------------------------------
    print("  -> Validating docker-compose orchestration dependencies and healthchecks...")
    assert "condition: service_healthy" in PRODUCTION_DOCKER_COMPOSE
    assert "pg_isready" in PRODUCTION_DOCKER_COMPOSE
    assert "redis-cli" in PRODUCTION_DOCKER_COMPOSE
    assert "postgres_data:" in PRODUCTION_DOCKER_COMPOSE

    # Write reference deployment files to disk
    pkg_dir = Path(__file__).parent
    (pkg_dir / "Dockerfile.reference").write_text(PRODUCTION_DOCKERFILE, encoding="utf-8")
    (pkg_dir / "docker-compose.reference.yml").write_text(PRODUCTION_DOCKER_COMPOSE, encoding="utf-8")
    print("  -> Successfully synchronized Dockerfile.reference and docker-compose.reference.yml")

    print("[SUCCESS] All Docker & Production Deployment tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 8 - 05: Docker, Production Deployment & Process Management")
    print("=" * 70)
    run_tests()
    print("=" * 70)
