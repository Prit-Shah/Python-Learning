r"""
04_pydantic_settings_and_structured_logging.py

============================================================
1. CONCEPT
============================================================

Enterprise backends running in cloud-native containerized environments (Kubernetes,
AWS ECS, GCP Cloud Run) must strictly adhere to the Twelve-Factor App methodology for
configuration and observability:

1. Twelve-Factor Configuration (Factor III: Store Config in the Environment):
   - Replace manual `os.environ.get()` calls with strict, type-safe settings models
     via `pydantic-settings`:
     * Inherit from `BaseSettings` and configure `SettingsConfigDict(env_prefix="APP_", extra="ignore")`.
     * Validates and coerces environment variables at startup: string ports to `int`,
       URLs to `AnyHttpUrl` / `PostgresDsn`, booleans to `bool`.
     * Prevents service boot if required variables or secrets are missing (Fail-Fast principle).
     * Masks sensitive credentials via `SecretStr` to prevent accidental leaks in logs or exceptions.

2. Production Structured JSON Logging (Factor XI: Logs as Event Streams):
   - In containerized environments, logs must be streamed to `stdout` as single-line JSON objects.
   - Eliminates brittle multi-line regex parsing in log aggregation pipelines (Datadog, Loki,
     CloudWatch, Elasticsearch).
   - Contextual Tracing via `contextvars.ContextVar`:
     * Injects distributed `request_id`, `tenant_id`, and `user_id` into every log emitted
       during an async request cycle without polluting function arguments.
   - Exception Serialization:
     * Automatically extracts `record.exc_info` and structures stack traces into dedicated
       JSON attributes (`exception_class`, `exception_message`, `traceback`).

3. Kubernetes Health Check Probing Architecture:
   - Liveness Probe (`/healthz/liveness`):
     * Answers: "Is the Python process and event loop healthy?"
     * If failed: Kubernetes kills the container and initiates a pod restart.
   - Readiness Probe (`/healthz/readiness`):
     * Answers: "Are all downstream dependencies (PostgreSQL, Redis) ready to receive traffic?"
     * If failed: Kubernetes temporarily removes the pod from the Service routing endpoints,
       preventing 500 errors to clients while downstream resources recover.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python (pydantic-settings)         | JavaScript / TypeScript (Node.js)  |
+------------------------------+------------------------------------+------------------------------------+
| Env Config Validation        | `pydantic-settings` `BaseSettings` | `zod` (`z.object()`) / `envalid`   |
| Secret Masking               | `SecretStr` (masks in repr/str)    | Custom getter / `dotenv-safe`      |
| Structured JSON Logger       | `logging.Formatter` emitting JSON  | `pino` / `winston`                 |
| Async Context Propagation    | `contextvars.ContextVar`           | `AsyncLocalStorage` (`node:async_hooks`)|
| Cloud Health Checks          | Liveness / Readiness functions     | `@godaddy/terminus`                |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Architecture Differences:
1. In Node.js, `pino` uses extreme serialization optimizations and worker threads to format JSON.
   In Python, standard `logging` is thread-safe and synchronous. In async applications, using a
   streamlined JSON formatter writing to `sys.stdout` ensures minimal latency overhead.
2. In TypeScript with Zod, environment parsing requires invoking `.parse(process.env)` manually.
   In Python with `pydantic-settings`, instantiating `Settings()` automatically coordinates
   CLI overrides, environment variables, and local `.env` files with priority order.


============================================================
3. UNDER THE HOOD (CPython & Memory Safety)
============================================================

1. Settings Source Priority Hierarchy:
   - `pydantic-settings` resolves configuration values using strict precedence:
     1. Explicit keyword arguments passed to `Settings(...)`.
     2. Environment variables matching field names or `env_prefix`.
     3. Key-value pairs read from `.env` files.
     4. Default values declared on the model fields.

2. `SecretStr` Memory and Display Protection:
   - `SecretStr` encapsulates sensitive strings (API keys, passwords, database credentials).
   - Its `__repr__` and `__str__` methods return `SecretStr('**********')`.
   - If an engineer accidentally executes `logger.info(f"Database settings: {settings}")`,
     the password is NEVER written to the logs.
   - To access the raw secret for authentication: `settings.DB_PASSWORD.get_secret_value()`.

3. ContextVar Thread-Safe Async Propagation:
   - When an async request spawns sub-coroutines or child tasks via `asyncio.create_task()`,
     Python copies the active `contextvars.ContextVar` map to the child task.
   - The JSON log formatter reads `correlation_id_ctx.get()` at log emission time, guaranteeing
     that every log record emitted across concurrent requests is tagged with the correct request ID.


============================================================
4. COMMON GOTCHAS
============================================================

1. Heavy Database Queries in Readiness Probes:
   - A Kubernetes readiness probe runs every 5 to 10 seconds per container.
   - If your probe executes `SELECT COUNT(*) FROM orders`, 50 running pods will execute 300 to 600
     heavy aggregate queries per minute, self-DDoS'ing the primary database!
   - FIX: Use the lightest possible probe: `SELECT 1` for PostgreSQL, and `PING` for Redis.

2. Mutating Settings at Runtime:
   - Modifying `settings.PORT = 9000` at runtime creates race conditions and state divergence.
   - FIX: Treat configuration as strictly read-only and immutable. Cache via `@lru_cache()`.

3. Multi-line Stack Traces in CloudWatch / Datadog:
   - Default logging formats print tracebacks across multiple newline-separated lines.
   - Log forwarders often interpret each line as an independent log entry, shattering the error
     trace across hundreds of unrelated events.
   - FIX: Always format stack traces into a single JSON field with escaped newlines.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "How do you implement 12-factor configuration in Python, and how do you protect production secrets?"
A1: "I use `pydantic-settings` to define an immutable `Settings` class that loads environment variables
     into strongly-typed fields with fail-fast validation at application startup.
     For sensitive data like database passwords or private API tokens, I declare them as `SecretStr`.
     `SecretStr` overrides string formatting and representation to output asterisks, preventing passwords
     from leaking if someone logs the settings object or prints it in an exception traceback. We only unwrap
     the raw value using `.get_secret_value()` at the exact moment of establishing the database connection."

Q2: "What is the difference between Kubernetes Liveness and Readiness probes, and how should they be implemented?"
A2: "Liveness and Readiness probes serve two distinct operational purposes:
     Liveness checks whether the Python application process is alive and its event loop is responsive.
     If the liveness probe fails, Kubernetes assumes the process is deadlocked and restarts the container.
     Readiness checks whether the application is capable of serving client traffic by verifying downstream
     dependencies like PostgreSQL and Redis using lightweight pings (`SELECT 1` or `PING`). If readiness fails,
     Kubernetes does NOT restart the container; instead, it removes the pod from the load balancer pool
     so incoming requests are routed to healthy pods while this pod attempts to reconnect."

Q3: "How do you achieve distributed correlation logging in an async Python architecture?"
A3: "I store the incoming HTTP request ID in a Python `contextvars.ContextVar` at the ASGI middleware layer.
     Because `ContextVar` is automatically propagated across asyncio task boundaries, it provides request-scoped
     isolation without thread-local race conditions.
     I configure a custom JSON `logging.Formatter` that reads from the `ContextVar` and injects `request_id`,
     along with timestamp, log level, and parsed exception tracebacks, into a single-line JSON object emitted
     to `stdout`. This integrates seamlessly with log aggregators like Datadog or OpenSearch for instant
     end-to-end distributed tracing."
"""

import sys
import os
import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone
from enum import Enum
from functools import lru_cache
from typing import Any, Dict, Optional, Tuple

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ==============================================================================
# 1. ASYNC CONTEXT VARIABLE FOR DISTRIBUTED TRACING
# ==============================================================================

correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="SYSTEM")
user_id_ctx: ContextVar[Optional[str]] = ContextVar("user_id", default=None)


# ==============================================================================
# 2. TYPE-SAFE PRODUCTION SETTINGS (12-FACTOR APP)
# ==============================================================================

class EnvironmentType(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class DatabaseConfig(BaseSettings):
    """Sub-configuration for database connection parameters."""
    HOST: str = "localhost"
    PORT: int = Field(default=5432, ge=1024, le=65535)
    NAME: str = "app_db"
    USER: str = "app_user"
    PASSWORD: SecretStr = Field(default=SecretStr("super_secret_pg_pass"))

    @property
    def dsn(self) -> str:
        # Securely unwraps secret strictly when generating the connection DSN
        raw_pass = self.PASSWORD.get_secret_value()
        return f"postgresql+asyncpg://{self.USER}:{raw_pass}@{self.HOST}:{self.PORT}/{self.NAME}"


class AppSettings(BaseSettings):
    """
    Primary 12-factor configuration model.
    Reads environment variables with prefix 'APP_' and supports local .env fallback.
    """
    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "ai-core-service"
    ENVIRONMENT: EnvironmentType = EnvironmentType.DEVELOPMENT
    PORT: int = Field(default=8000, ge=1024, le=65535)
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    API_KEY: SecretStr = Field(default=SecretStr("production_ai_gateway_key_9981"))
    DB: DatabaseConfig = Field(default_factory=DatabaseConfig)


@lru_cache()
def get_settings() -> AppSettings:
    """Returns singleton settings instance cached via LRU cache."""
    return AppSettings()


# ==============================================================================
# 3. STRUCTURED JSON LOG FORMATTER WITH CONTEXTVAR INJECTION
# ==============================================================================

class StructuredJsonFormatter(logging.Formatter):
    """
    Formats log records into single-line JSON objects, incorporating
    async request correlation IDs and structured exception representations.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
            "request_id": correlation_id_ctx.get(),
        }

        # Include user_id if present in context
        uid = user_id_ctx.get()
        if uid:
            log_payload["user_id"] = uid

        # Structured exception handling
        if record.exc_info:
            exc_type, exc_val, _ = record.exc_info
            log_payload["exception"] = {
                "type": exc_type.__name__ if exc_type else "Exception",
                "message": str(exc_val),
                "stacktrace": self.formatException(record.exc_info).splitlines()
            }

        return json.dumps(log_payload)


def configure_structured_logger(name: str = "api_service") -> logging.Logger:
    """Configures and returns a production-ready JSON logger."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers on re-configuration
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredJsonFormatter())
        logger.addHandler(handler)

    return logger


# ==============================================================================
# 4. KUBERNETES HEALTH & READINESS PROBE EVALUATOR
# ==============================================================================

class HealthProbeEvaluator:
    """
    Evaluates system operational health for Kubernetes orchestration.
    """

    def __init__(self, db_connected: bool = True, redis_connected: bool = True):
        self.db_connected = db_connected
        self.redis_connected = redis_connected

    def check_liveness(self) -> Dict[str, Any]:
        """
        Liveness: Confirms the process is running.
        Always returns 200 OK unless deadlocked.
        """
        return {
            "status": "UP",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def check_readiness(self) -> Tuple[int, Dict[str, Any]]:
        """
        Readiness: Performs lightweight health pings to external dependencies.
        Returns HTTP 200 if all ready, or HTTP 503 if any dependency is degraded.
        """
        checks: Dict[str, str] = {
            "database": "HEALTHY" if self.db_connected else "UNAVAILABLE",
            "redis": "HEALTHY" if self.redis_connected else "UNAVAILABLE"
        }

        all_ready = all(status == "HEALTHY" for status in checks.values())
        status_code = 200 if all_ready else 503

        response = {
            "status": "READY" if all_ready else "NOT_READY",
            "dependencies": checks,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        return status_code, response


# ==============================================================================
# 5. SELF-TESTING SUITE
# ==============================================================================

def run_tests() -> None:
    print("\n[*] Starting automated test suite for 04_pydantic_settings_and_structured_logging.py...")

    # ------------------------------------------------------------
    # Test 1: Pydantic Settings & SecretStr Masking
    # ------------------------------------------------------------
    print("  -> Testing Pydantic settings loading and SecretStr security masking...")
    settings = get_settings()

    assert settings.APP_NAME == "ai-core-service"
    assert settings.ENVIRONMENT == EnvironmentType.DEVELOPMENT
    assert settings.PORT == 8000
    assert settings.DEBUG is False

    # Verify SecretStr masks raw values in repr and str
    str_repr = str(settings.API_KEY)
    assert "production_ai_gateway_key_9981" not in str_repr, "Secret leaked in str()!"
    assert "**********" in str_repr

    # Verify raw secret extraction strictly via .get_secret_value()
    assert settings.API_KEY.get_secret_value() == "production_ai_gateway_key_9981"
    assert "super_secret_pg_pass" in settings.DB.dsn

    # ------------------------------------------------------------
    # Test 2: Structured JSON Log Formatter with ContextVar
    # ------------------------------------------------------------
    print("  -> Testing JSON log formatter with ContextVar correlation ID...")
    formatter = StructuredJsonFormatter()

    # Set correlation ID in context
    token = correlation_id_ctx.set("req-test-uuid-999")
    u_token = user_id_ctx.set("user_789")

    try:
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="service.py",
            lineno=42,
            msg="User completed checkout successfully",
            args=(),
            exc_info=None
        )
        json_output = formatter.format(record)
        parsed = json.loads(json_output)

        assert parsed["level"] == "INFO"
        assert parsed["message"] == "User completed checkout successfully"
        assert parsed["request_id"] == "req-test-uuid-999"
        assert parsed["user_id"] == "user_789"
        assert "timestamp" in parsed
    finally:
        correlation_id_ctx.reset(token)
        user_id_ctx.reset(u_token)

    # ------------------------------------------------------------
    # Test 3: Structured Exception Stacktrace Serialization
    # ------------------------------------------------------------
    print("  -> Testing structured exception serialization...")
    try:
        raise ValueError("Invalid payment currency: BTC")
    except ValueError:
        exc_info = sys.exc_info()
        err_record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="billing.py",
            lineno=105,
            msg="Payment processing failed",
            args=(),
            exc_info=exc_info
        )
        err_json = formatter.format(err_record)
        err_parsed = json.loads(err_json)

        assert err_parsed["level"] == "ERROR"
        assert "exception" in err_parsed
        assert err_parsed["exception"]["type"] == "ValueError"
        assert "Invalid payment currency" in err_parsed["exception"]["message"]
        assert isinstance(err_parsed["exception"]["stacktrace"], list)
        assert len(err_parsed["exception"]["stacktrace"]) > 0

    # ------------------------------------------------------------
    # Test 4: Kubernetes Liveness and Readiness Probes
    # ------------------------------------------------------------
    print("  -> Testing Kubernetes Liveness and Readiness probe responses...")
    healthy_evaluator = HealthProbeEvaluator(db_connected=True, redis_connected=True)
    live_res = healthy_evaluator.check_liveness()
    assert live_res["status"] == "UP"

    code, ready_res = healthy_evaluator.check_readiness()
    assert code == 200
    assert ready_res["status"] == "READY"
    assert ready_res["dependencies"]["database"] == "HEALTHY"
    assert ready_res["dependencies"]["redis"] == "HEALTHY"

    # Degraded dependency scenario
    degraded_evaluator = HealthProbeEvaluator(db_connected=False, redis_connected=True)
    deg_code, deg_res = degraded_evaluator.check_readiness()
    assert deg_code == 503, f"Expected 503 on DB failure, got {deg_code}"
    assert deg_res["status"] == "NOT_READY"
    assert deg_res["dependencies"]["database"] == "UNAVAILABLE"
    assert deg_res["dependencies"]["redis"] == "HEALTHY"

    print("[SUCCESS] All Settings, Structured Logging & Health Probe tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 8 - 04: 12-Factor Settings, Structured Logging & Probes")
    print("=" * 70)
    run_tests()
    print("=" * 70)
