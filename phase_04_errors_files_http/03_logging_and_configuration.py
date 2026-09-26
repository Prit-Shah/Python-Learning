r"""
03_logging_and_configuration.py

============================================================
1. CONCEPT
============================================================

Production Python services require deterministic configuration management,
hierarchical structured logging, timezone-aware temporal tracking, and compiled
pattern matching:

1. Hierarchical Logging Architecture (`logging` module):
   - Named Loggers: Created via `logging.getLogger(__name__)`. The dot-separated
     name (e.g. `"app.services.auth"`) establishes an automatic parent-child hierarchy.
   - Severity Thresholds:
     - `DEBUG` (10): Detailed diagnostic information.
     - `INFO` (20): High-level operational events.
     - `WARNING` (30): Non-fatal anomalies or deprecation notices.
     - `ERROR` (40): Operation failures that require attention.
     - `CRITICAL` (50): System-halting conditions.
   - Handlers & Formatters:
     - Handlers direct output streams (`StreamHandler` for stdout, `FileHandler` for disk).
     - Formatters define the textual layout or structured JSON shape.
   - Log Propagation: Records cascade up the logger hierarchy to root handlers
     unless `logger.propagate = False`.
   - Exception Logging: `logger.exception("msg")` automatically logs the full
     stack trace via `exc_info=True`.

2. Environment Configuration:
   - `os.environ`: Live process environment mapping.
   - Safe Lookups: `os.getenv("KEY", default_val)` prevents `KeyError`.
   - Strict Lookups: `os.environ["KEY"]` ensures missing mandatory credentials fail fast.

3. Dates, Times, and Timezones (`datetime`):
   - Naive Datetimes: Datetimes without timezone info (`datetime.now()`). Naive
     datetimes assume local machine time and cause subtle bugs across Daylight Savings
     and distributed clusters.
   - Aware Datetimes: Datetimes explicitly stamped with a timezone (`datetime.now(timezone.utc)`).
   - Python strictly forbids comparing naive and aware datetimes (`TypeError`).
   - ISO-8601 Standardization: `dt.isoformat()` and `datetime.fromisoformat()`.
   - Duration Arithmetic: `timedelta(days=7, hours=2)`.

4. Regular Expressions (`re` module):
   - Pre-compilation: `pattern = re.compile(r"...")` compiles regex into CPython
     internal regex bytecode for maximum throughput.
   - Matching functions:
     - `re.search()`: Scans through string for first match.
     - `re.match()`: Checks for match ONLY at string beginning.
     - `re.fullmatch()`: Ensures entire string matches pattern.
     - `re.sub()`: Regex search and replace.
     - Named capture groups: `(?P<group_name>pattern)`.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python                             | JavaScript / TypeScript (Node.js)  |
+------------------------------+------------------------------------+------------------------------------+
| Production Logging           | `logging.getLogger(__name__)`      | `pino` / `winston` loggers         |
| Log Exception with Traceback | `logger.exception("Failed")`       | `logger.error(err)`                |
| Environment Variables        | `os.getenv("PORT", "8080")`        | `process.env.PORT || "8080"`       |
| UTC Current Timestamp        | `datetime.now(timezone.utc)`       | `new Date().toISOString()`         |
| ISO Timestamp Parsing        | `datetime.fromisoformat(iso_str)`  | `new Date(iso_str)`                |
| Date Arithmetic              | `dt + timedelta(days=1)`           | `new Date(dt.getTime() + 86400000)`|
| Regular Expressions          | `re.compile(r"...")`               | `new RegExp("...")` / `/.../`      |
| Named Regex Groups           | `(?P<user_id>\\d+)`                 | `(?<user_id>\\d+)`                 |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Gotchas:
1. In JS, `new Date()` is always internally UTC millisecond epoch based.
   In Python, `datetime.now()` without arguments is OFFSET-NAIVE and assumes
   local server time.
2. In Python, comparing a naive datetime with an aware datetime throws a `TypeError`.
   Always default to `datetime.now(timezone.utc)`.


============================================================
3. UNDER THE HOOD (CPython & Memory)
============================================================

1. Thread Safety in `logging`:
   - Every `logging.Handler` allocates an internal `threading.RLock()` re-entrant lock.
   - Emitting a log record acquires the handler lock, serializes the message,
     and flushes to the stream, guaranteeing that multithreaded services do not
     produce interleaved corrupted log outputs.

2. CPython Regex Engine (`_sre`):
   - The `re` module delegates pattern compilation to the `_sre` C extension module.
   - Regex patterns are compiled into a specialized bytecode instruction stream
     (`sre_compile.py`) that runs in native C, avoiding Python interpreter overhead
     during repetitive matching.

3. Datetime Internal Storage:
   - `datetime` objects in CPython are stored in compact C structs
     (`PyDateTime_DateTime`).
   - Naive datetimes store year, month, day, hour, minute, second, microsecond.
   - Aware datetimes include a pointer to a `tzinfo` instance (`timezone.utc`).


============================================================
4. COMMON GOTCHAS
============================================================

1. The Naive vs Aware Comparison Crash:
   - `t1 = datetime.now()`
   - `t2 = datetime.now(timezone.utc)`
   - `assert t1 < t2` -> `TypeError: can't compare offset-naive and offset-aware datetimes`.
   - Fix: Use `datetime.now(timezone.utc)` everywhere.

2. Using Bare `print()` in Backend Services:
   - Output lacks timestamps, severity levels, logger names, and exception tracebacks.
   - Cannot be filtered dynamically by log level or redirected to log aggregation tools.

3. Regex String Escaping Without Raw Strings:
   - Writing `re.compile("\\d+")` vs `re.compile(r"\\d+")`.
   - In standard Python strings, backslashes are interpreted as string escape codes.
   - Always prefix regex strings with `r"..."`.

4. Logger Handler Duplication:
   - Calling `logger.addHandler(handler)` multiple times (e.g. inside a request handler)
     causes every subsequent log to be printed 2x, 3x, 4x!
   - Ensure handlers are attached once during application bootstrap.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "How do you set up structured logging in a production Python service, and why is logger propagation important?"
Script:
"In production Python services, we instantiate loggers using `logging.getLogger(__name__)`,
creating a dot-delimited hierarchy that mirrors the codebase package structure. We attach
a `StreamHandler` configured with a structured JSON formatter to output to `stdout`, which
container engines like Docker and Kubernetes ingest into centralized platforms like Datadog
or Elasticsearch. Logger propagation allows child loggers in submodules to pass their records
up to the root logger without needing dedicated handlers attached to each individual logger.
We can adjust log levels globally at the root or target specific noisy third-party libraries
by setting their individual logger levels."

Q2: "What is the difference between offset-naive and offset-aware datetimes in Python, and how should datetimes be managed?"
Script:
"An offset-naive datetime contains no timezone information, representing an ambiguous local
clock reading, whereas an offset-aware datetime contains a reference to a `tzinfo` object
that explicitly defines its UTC offset. Comparing a naive datetime with an aware datetime
raises an immediate `TypeError`. In distributed backend systems, relying on naive datetimes
causes insidious bugs across servers operating in different regions or during Daylight Saving
transitions. The senior best practice is to strictly use `datetime.now(timezone.utc)` across
all internal business logic, database storage, and API communications, converting to local
timezones solely at the presentation layer."

Q3: "How does the re module compile regular expressions, and why should you use re.compile?"
Script:
"The standard library `re` module parses regular expressions into Abstract Syntax Trees and
compiles them into a compact, optimized bytecode format executed by CPython\'s C-level
`_sre` pattern matching engine. While convenience functions like `re.search()` cache compiled
patterns internally, calling `pattern = re.compile(r'...')` at module initialization guarantees
that compilation happens exactly once at startup. It also provides clean object-oriented
access to methods like `.search()`, `.finditer()`, and `.sub()`, improving performance in
hot execution paths like request validation and text extraction pipelines."
"""

import io
import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta, timezone

# Ensure UTF-8 standard output across environments
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ============================================================
# STRUCTURED JSON LOG FORMATTER
# ============================================================

class JsonLogFormatter(logging.Formatter):
    """Custom Formatter outputting structured JSON log events."""
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


def run_tests():
    # ============================================================
    # 1. HIERARCHICAL LOGGING & LEVEL FILTERING
    # ============================================================

    # Capture log output in an in-memory buffer
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setFormatter(JsonLogFormatter())

    test_logger = logging.getLogger("app.services.payment")
    test_logger.setLevel(logging.INFO)
    test_logger.addHandler(handler)
    test_logger.propagate = False  # Isolate from root logger during test

    # DEBUG message should be filtered out (threshold is INFO)
    test_logger.debug("Processing card validation step")
    assert log_stream.getvalue() == ""

    # INFO message is captured
    test_logger.info("Payment authorized successfully")
    logged_output = log_stream.getvalue()
    assert "Payment authorized successfully" in logged_output

    parsed_log = json.loads(logged_output)
    assert parsed_log["level"] == "INFO"
    assert parsed_log["logger"] == "app.services.payment"
    assert "timestamp" in parsed_log


    # ============================================================
    # 2. EXCEPTION LOGGING (logger.exception)
    # ============================================================

    log_stream.truncate(0)
    log_stream.seek(0)

    try:
        _ = 10 / 0
    except ZeroDivisionError:
        test_logger.exception("Transaction calculation failed")

    error_log = json.loads(log_stream.getvalue())
    assert error_log["level"] == "ERROR"
    assert "Transaction calculation failed" in error_log["message"]
    assert "ZeroDivisionError" in error_log["exception"]


    # ============================================================
    # 3. ENVIRONMENT CONFIGURATION & PARSING
    # ============================================================

    # Setting temporary environment variables
    os.environ["APP_ENV"] = "production"
    os.environ["MAX_WORKERS"] = "8"
    os.environ["ENABLE_CACHE"] = "true"

    # Reading with type conversion and default fallbacks
    app_env = os.getenv("APP_ENV", "development")
    max_workers = int(os.getenv("MAX_WORKERS", "4"))
    enable_cache = os.getenv("ENABLE_CACHE", "false").lower() == "true"
    db_timeout = float(os.getenv("DB_TIMEOUT", "30.5"))

    assert app_env == "production"
    assert max_workers == 8
    assert enable_cache is True
    assert db_timeout == 30.5

    # Missing mandatory variable detection
    assert os.getenv("NON_EXISTENT_VAR") is None


    # ============================================================
    # 4. TIMEZONE-AWARE DATETIMES & ARITHMETIC
    # ============================================================

    # Aware UTC datetime
    utc_now = datetime.now(timezone.utc)
    assert utc_now.tzinfo is not None
    assert utc_now.tzinfo == timezone.utc

    # ISO-8601 formatting and round-trip parsing
    iso_string = utc_now.isoformat()
    parsed_dt = datetime.fromisoformat(iso_string)
    assert parsed_dt == utc_now

    # Timedelta arithmetic
    tomorrow = utc_now + timedelta(days=1)
    difference = tomorrow - utc_now
    assert difference.total_seconds() == 86400

    # Naive vs Aware comparison error verification
    naive_dt = datetime.now()  # No timezone
    caught_type_error = False
    try:
        _ = naive_dt < utc_now
    except TypeError:
        caught_type_error = True
    assert caught_type_error is True


    # ============================================================
    # 5. REGULAR EXPRESSIONS (COMPILED PATTERNS & GROUPS)
    # ============================================================

    # Compiled regex with named groups
    email_regex = re.compile(r"^(?P<user>[a-zA-Z0-9_.+-]+)@(?P<domain>[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)$")

    match = email_regex.match("developer@python.org")
    assert match is not None
    assert match.group("user") == "developer"
    assert match.group("domain") == "python.org"

    # re.sub: Pattern search and replacement
    sensitive_log = "User token: bearer_secret_12345 in session"
    sanitized = re.sub(r"bearer_secret_\w+", "[REDACTED]", sensitive_log)
    assert sanitized == "User token: [REDACTED] in session"


if __name__ == "__main__":
    run_tests()
    print("03_logging_and_configuration.py tests passed!")
