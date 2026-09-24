"""
Phase 8: Database & Production Backend - 12-Factor Settings & Structured Logging
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - 12-Factor App Configuration with 'pydantic-settings':
     * Replaces manual 'os.environ.get()' with strict, type-safe settings models.
     * Inherits from 'BaseSettings'. Reads environment variables automatically with case-insensitivity.
     * Automatically loads from '.env' files for local development using 'SettingsConfigDict'.
     * Validates types (ports as int, booleans as bool, database URLs as Url).
   - Production JSON Structured Logging:
     * In containerized environments (Kubernetes, AWS ECS), logs should be emitted to stdout as
       single-line JSON objects.
     * Eliminates multi-line log parsing issues in log aggregators (Datadog, Loki, CloudWatch).
   - Health Checks:
     * Liveness Probe ('/healthz/live'): Confirms the process is running.
     * Readiness Probe ('/healthz/ready'): Confirms external dependencies (Postgres, Redis) are healthy.
   - JS/TS Analogy:
     * 'envalid' / 'zod-env' in TypeScript vs 'pydantic-settings' in Python.
     * 'winston' JSON format or 'pino' vs Python JSON log formatters.

2. UNDER THE HOOD (CPython & Memory):
   - 'pydantic-settings' leverages Pydantic's Rust-backed core to parse environment strings into
     native Python types, raising informative validation errors on startup if required configuration is missing.

3. COMMON GOTCHA:
   - Performing heavy, un-cached queries in Readiness checks: A readiness check is called by Kubernetes
     every 5-10 seconds. If it executes 'SELECT count(*) FROM millions_of_rows', it will degrade your database!
     Always use 'SELECT 1' for readiness probes.

4. 🎙️ INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   -----------------------------------------------------------------------------
   Q: "How do you manage 12-factor configuration and structured logging in production
       Python services, and how do you design Kubernetes liveness vs readiness probes?"
   
   HOW TO ANSWER OUT LOUD (60-90 sec script):
   1. Type-Safe Configuration with pydantic-settings:
      "In production Python services, we follow the 12-Factor App methodology using 'pydantic-settings'.
       We define an immutable 'Settings' class that reads environment variables into strongly-typed fields
       with validation. If an essential secret or database URL is missing or malformed, the application
       fails fast on startup before taking traffic."
   2. Structured JSON Logging:
      "We configure standard Python logging with a JSON formatter that outputs single-line JSON records
       to stdout. Every log includes timestamp, log level, service name, correlation request_id, and
       exception stack traces in a parsed field. This allows log aggregators like Datadog or OpenSearch
       to index and search logs without brittle regex parsing."
   3. Liveness vs Readiness Probes:
      "For Kubernetes health checks:
       - Liveness (/healthz/live) checks if the Python process is alive. If this fails, K8s restarts the container.
       - Readiness (/healthz/ready) performs lightweight pings to downstream dependencies (like 'SELECT 1'
         to Postgres and 'PING' to Redis). If this fails, K8s stops routing incoming traffic to the pod
         without killing it, giving dependencies time to recover."
================================================================================
"""

import sys
import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "ai-production-service"
    ENVIRONMENT: str = Field(default="development", pattern="^(development|staging|production)$")
    PORT: int = Field(default=8000, ge=1024, le=65535)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:secret@localhost:5432/app_db"
    REDIS_URL: str = "redis://localhost:6379/0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }
        if hasattr(record, "request_id"):
            log_entry["request_id"] = getattr(record, "request_id")
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_entry)


def setup_json_logger() -> logging.Logger:
    logger = logging.getLogger("production_api")
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonLogFormatter())
        logger.addHandler(handler)
    return logger


def demonstrate_structured_logging():
    print("\n--- 1. Structured JSON Logging Output ---")
    logger = setup_json_logger()
    logger.info("Application starting up...")
    extra_context = {"request_id": "req-98f2b1a0"}
    logger.info("Processing user payment checkout", extra=extra_context)


def demonstrate_settings_parsing():
    print("\n--- 2. Type-Safe Environment Settings ---")
    settings = AppSettings()
    print(f"  App Name:     {settings.APP_NAME}")
    print(f"  Environment:  {settings.ENVIRONMENT}")
    print(f"  Port:         {settings.PORT}")
    print(f"  Database URL: {settings.DATABASE_URL}")
    print(f"  Debug Mode:   {settings.DEBUG}")


def run_tests():
    print("\n[*] Running automated tests for 04_pydantic_settings_and_structured_logging.py...")
    s = AppSettings()
    assert s.PORT == 8000
    assert s.DEBUG is False

    formatter = JsonLogFormatter()
    record = logging.LogRecord("test", logging.INFO, "test.py", 10, "Test message", (), None)
    output = formatter.format(record)
    parsed = json.loads(output)
    
    assert parsed["level"] == "INFO"
    assert parsed["message"] == "Test message"
    assert "timestamp" in parsed

    print("[SUCCESS] All Settings & Structured Logging tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 65)
    print("Execution: Phase 8 - 12-Factor Settings & Structured Logging")
    print("=" * 65)
    demonstrate_settings_parsing()
    demonstrate_structured_logging()
    print("-" * 65)
    run_tests()
    print("=" * 65)
