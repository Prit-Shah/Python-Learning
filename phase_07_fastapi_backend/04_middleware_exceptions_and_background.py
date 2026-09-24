"""
Phase 7: Backend with FastAPI - Middleware, Exceptions & Background Tasks
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - Custom Middleware:
     * Intercepts incoming requests before routes, and modifies outgoing responses.
     * Created with '@app.middleware("http")':
       async def add_process_time(request, call_next):
           t0 = time.perf_counter()
           response = await call_next(request)
           response.headers["X-Process-Time"] = f"{time.perf_counter() - t0:.4f}"
           return response
   - Global Exception Handlers:
     * Catch domain exceptions globally and format them into clean JSON responses with proper HTTP status.
     * Decorated with '@app.exception_handler(CustomExceptionClass)'.
   - Background Tasks ('BackgroundTasks'):
     * Executes non-blocking tasks AFTER the HTTP response has already been sent to the client!
     * Perfect for sending emails, audit logging, webhook dispatching.
   - JS/TS Analogy:
     * Middleware maps directly to Express 'app.use()'.
     * Global Exception Handlers map to Express error middleware '(err, req, res, next)'.
     * BackgroundTasks map to Node.js 'setImmediate()' or firing un-awaited promises, but with
       guaranteed lifecycle management inside FastAPI.

2. UNDER THE HOOD (CPython & Memory):
   - BackgroundTasks are stored in a queue on the Request object.
   - Once Starlette finishes streaming the HTTP response bytes to the client socket, the ASGI runner
     executes all functions queued in BackgroundTasks asynchronously before terminating the scope.

3. COMMON GOTCHA:
   - Overusing BackgroundTasks for heavy CPU processing or distributed workflows:
     FastAPI BackgroundTasks execute in the same process/memory space. If the server crashes or restarts,
     pending background tasks are lost! For mission-critical or long-running work (>30s), use a
     dedicated distributed task queue like Celery or Redis Streams.

4. 🎙️ INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   -----------------------------------------------------------------------------
   Q: "How does middleware work in FastAPI, what is the proper way to handle global
       exceptions, and when should you use BackgroundTasks versus an external queue like Celery?"
   
   HOW TO ANSWER OUT LOUD (60-90 sec script):
   1. Middleware Flow:
      "In FastAPI, HTTP middleware wraps the entire request-response cycle using '@app.middleware('http')'.
       It's ideal for cross-cutting concerns like measuring request latency ('X-Process-Time'),
       attaching correlation request IDs, or configuring CORS."
   2. Global Exception Mapping:
      "Instead of cluttering routes with repetitive try/except blocks, we raise custom domain exceptions
       and register global handlers using '@app.exception_handler(DomainException)'. This ensures uniform
       error JSON payloads across the entire API and keeps route controllers clean and readable."
   3. BackgroundTasks vs Celery:
      "FastAPI's built-in 'BackgroundTasks' is great for lightweight, in-process jobs that can safely run
       immediately after the response is delivered—such as sending a confirmation email or logging an audit trail.
       However, because it runs in-process without persistence, if the worker crashes, the task is lost.
       For heavy CPU-bound work, guaranteed delivery, scheduled cron jobs, or retries across crashes,
       an external distributed worker queue like Celery, Arq, or Redis Streams is strictly required."
================================================================================
"""

import sys
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
import time
from typing import List
from fastapi import FastAPI, Request, BackgroundTasks, status
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


app = FastAPI(title="Middleware, Exceptions & Background Tasks")

# In-memory background log simulation
AUDIT_LOG_STORAGE: List[str] = []


# ==============================================================================
# 1. CUSTOM DOMAIN EXCEPTION & GLOBAL EXCEPTION HANDLER
# ==============================================================================

class ResourceExhaustedError(Exception):
    def __init__(self, resource_name: str):
        self.resource_name = resource_name


@app.exception_handler(ResourceExhaustedError)
async def resource_exhausted_handler(request: Request, exc: ResourceExhaustedError):
    """Global handler intercepting ResourceExhaustedError."""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error_code": "RESOURCE_EXHAUSTED",
            "message": f"Resource limit exceeded for: {exc.resource_name}",
            "path": request.url.path
        }
    )


# ==============================================================================
# 2. CUSTOM HTTP TIMING MIDDLEWARE
# ==============================================================================

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    t0 = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - t0
    response.headers["X-Process-Time"] = f"{elapsed:.4f}s"
    return response


# ==============================================================================
# 3. BACKGROUND TASK SIMULATION
# ==============================================================================

def write_audit_log(action: str, user_id: int):
    """Background task executed after response delivery."""
    entry = f"ACTION: {action} by user #{user_id}"
    AUDIT_LOG_STORAGE.append(entry)


@app.post("/orders", status_code=status.HTTP_202_ACCEPTED)
async def create_order(user_id: int, background_tasks: BackgroundTasks):
    """Demonstrates queuing a background task."""
    # Queue task for post-response execution
    background_tasks.add_task(write_audit_log, action="ORDER_PLACED", user_id=user_id)
    return {"message": "Order accepted for processing."}


@app.get("/trigger-exhaustion")
async def trigger_exhaustion():
    """Demonstrates raising custom domain exception caught by global handler."""
    raise ResourceExhaustedError("OpenAI_API_Tokens")


# ==============================================================================
# SELF-TEST CHALLENGES (Using FastAPI TestClient)
# ==============================================================================

def run_tests():
    print("\n[*] Running automated tests for 04_middleware_exceptions_and_background.py...")
    with TestClient(app) as client:
        # 1. Test middleware attaches 'X-Process-Time' header
        res = client.post("/orders?user_id=42")
        assert res.status_code == 202
        assert "X-Process-Time" in res.headers
        
        # 2. Verify BackgroundTask ran after response
        assert len(AUDIT_LOG_STORAGE) == 1
        assert AUDIT_LOG_STORAGE[0] == "ACTION: ORDER_PLACED by user #42"

        # 3. Test global exception handler catches ResourceExhaustedError
        res = client.get("/trigger-exhaustion")
        assert res.status_code == 429
        data = res.json()
        assert data["error_code"] == "RESOURCE_EXHAUSTED"
        assert "OpenAI_API_Tokens" in data["message"]

    print("[SUCCESS] All Middleware, Exception & BackgroundTask tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 65)
    print("Execution: Phase 7 - Middleware, Exceptions & BackgroundTasks")
    print("=" * 65)
    run_tests()
    print("=" * 65)
