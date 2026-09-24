r"""
Phase 4: Errors, Files, HTTP & Stdlib - Logging, Environment Config & Dates
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - Logging in Python:
     * Never use bare 'print()' in production backend services!
     * Python includes a robust standard 'logging' module with 5 core levels:
       DEBUG (10) -> INFO (20) -> WARNING (30) -> ERROR (40) -> CRITICAL (50).
     * Formatters define output layout (timestamp, log level, logger name, message).
     * Handlers determine destination (StreamHandler for console, FileHandler for file logs).
     * Always create module loggers: 'logger = logging.getLogger(__name__)'.
   - Environment Variables & Config:
     * Access via 'os.environ.get("KEY", default_val)'.
     * Avoid 'os.environ["KEY"]' unless you want an immediate 'KeyError' when missing.
   - Date & Time:
     * Always use TIMEZONE-AWARE datetimes: 'datetime.now(timezone.utc)'.
     * Naive datetimes (without timezone info) create subtle bugs during daylight savings
       or cross-server data exchanges.
   - Regular Expressions:
     * Standard 're' module: 're.search()', 're.match()', 're.findall()', 're.sub()'.
     * Compile reusable patterns for performance: 'pattern = re.compile(r"^\w+@\w+\.\w+$")'.
   - JS/TS Analogy:
     * 'console.log' / 'pino' / 'winston' -> Python 'logging'.
     * 'process.env.PORT' -> 'os.environ.get("PORT")'.
     * 'new Date().toISOString()' -> 'datetime.now(timezone.utc).isoformat()'.

2. UNDER THE HOOD (CPython & Memory):
   - Python's logging module uses thread-safe locks on handlers, ensuring log records from concurrent
     threads do not interleave or corrupt output streams.
   - 're' compiles regular expressions into an internal bytecode format executed by CPython's C-engine.

3. COMMON GOTCHA:
   - Naive vs Aware Datetimes:
     t1 = datetime.now() # Naive (local machine time without tzinfo)
     t2 = datetime.now(timezone.utc) # Aware
     # BUG: t1 < t2 raises TypeError: can't compare offset-naive and offset-aware datetimes!
     # FIX: Always standardize on UTC: datetime.now(timezone.utc).

4. 🎙️ INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   -----------------------------------------------------------------------------
   Q: "How do you configure logging in a Python backend service, and why should you
       always use timezone-aware datetimes?"
   
   HOW TO ANSWER OUT LOUD (60-90 sec script):
   1. Production Logging Hierarchy:
      "In production Python services, we instantiate loggers using 'logging.getLogger(__name__)'
       to maintain a hierarchical namespace matching our package layout. We configure handlers
       (such as StreamHandler for stdout in Docker/Kubernetes) and attach formatters outputting
       structured formats—often JSON in production via structlog or python-json-logger.
       This enables log aggregators like Datadog or ELK to parse timestamps, levels, and request IDs."
   2. Timezone-Aware Dates:
      "A classic senior pitfall is using datetime.now() without tzinfo, which creates a naive datetime.
       When naive datetimes are stored in PostgreSQL or compared against UTC timestamps, they trigger
       TypeErrors or timezone mismatch bugs across servers. The golden rule is to always use
       'datetime.now(timezone.utc)' and store ISO-8601 UTC strings."
================================================================================
"""

import sys
import os
import re
import logging
from datetime import datetime, timezone, timedelta

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def setup_demo_logger() -> logging.Logger:
    """Configures a clean stream logger with custom format."""
    logger = logging.getLogger("demo_service")
    logger.setLevel(logging.DEBUG)
    
    # Avoid duplicate handlers on re-run
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] (%(name)s): %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def demonstrate_logging():
    print("\n--- 1. Structured Logging Demonstration ---")
    logger = setup_demo_logger()
    logger.debug("Database connection pool initialized (5 connections).")
    logger.info("API Server started listening on port 8000.")
    logger.warning("Cache miss for user profile session_id=xyz.")
    logger.error("Failed to connect to secondary replica, falling back to primary.")


def demonstrate_dates_and_timezones():
    print("\n--- 2. Timezone-Aware Datetime Demonstration ---")
    # 1. UTC current time
    now_utc = datetime.now(timezone.utc)
    print(f"  Current UTC time: {now_utc.isoformat()}")
    
    # 2. Date arithmetic with timedelta
    token_expiry = now_utc + timedelta(hours=2, minutes=30)
    print(f"  Token expires at: {token_expiry.isoformat()}")
    print(f"  Time remaining:   {token_expiry - now_utc}")


def demonstrate_regex_parsing():
    print("\n--- 3. Regular Expressions (Named Groups) ---")
    log_line = "2026-09-24 [ERROR] user_id=402: Payment gateway timeout"
    
    # Regex with named capture groups: (?P<name>pattern)
    pattern = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})\s+\[(?P<level>\w+)\]\s+user_id=(?P<uid>\d+):\s+(?P<msg>.+)$")
    match = pattern.search(log_line)
    
    if match:
        data = match.groupdict()
        print(f"  Parsed date:    {data['date']}")
        print(f"  Parsed level:   {data['level']}")
        print(f"  Parsed user_id: {data['uid']}")
        print(f"  Parsed message: {data['msg']}")


# ==============================================================================
# SELF-TEST CHALLENGES
# ==============================================================================

def is_valid_email(email_str: str) -> bool:
    """Validates basic email format using regular expressions."""
    if not isinstance(email_str, str):
        return False
    pattern = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    return bool(pattern.match(email_str.strip()))


def get_server_config() -> dict:
    """Reads environment variables with sensible defaults."""
    return {
        "host": os.environ.get("APP_HOST", "0.0.0.0"),
        "port": int(os.environ.get("APP_PORT", 8080)),
        "debug": os.environ.get("APP_DEBUG", "false").lower() == "true",
    }


def run_tests():
    print("\n[*] Running automated self-tests for 03_logging_and_configuration.py...")
    # Email regex tests
    assert is_valid_email("developer@company.com") is True
    assert is_valid_email("first.last+ai@sub.domain.co") is True
    assert is_valid_email("invalid-email@") is False
    assert is_valid_email("@missing-user.com") is False
    assert is_valid_email("") is False
    
    # Environment config tests
    cfg = get_server_config()
    assert cfg["host"] == "0.0.0.0"
    assert cfg["port"] == 8080
    assert cfg["debug"] is False
    
    # Timezone check
    utc_dt = datetime.now(timezone.utc)
    assert utc_dt.tzinfo is not None, "Must be timezone-aware"
    
    print("[SUCCESS] All self-tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 65)
    print("Execution: Phase 4 - Logging, Configuration & Dates")
    print("=" * 65)
    demonstrate_logging()
    demonstrate_dates_and_timezones()
    demonstrate_regex_parsing()
    print("-" * 65)
    run_tests()
    print("=" * 65)
