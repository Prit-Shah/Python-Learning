"""
04_middleware_exceptions_and_background.py

============================================================
1. CONCEPT
============================================================

FastAPI builds upon Starlette's ASGI toolkit to provide three critical production
infrastructure mechanisms for intercepting, formatting, and deferring execution:

1. Custom HTTP & ASGI Middleware:
   - Intercepts requests before reaching routing layers and intercepts responses
     before reaching the client socket.
   - Use cases: Request ID / Correlation ID injection, request latency timing
     (`X-Process-Time`), security headers, CORS negotiation, and distributed tracing.
   - Created with `@app.middleware("http")` or by implementing raw ASGI middleware
     classes (`async def __call__(self, scope, receive, send)`).

2. Centralized Global Exception Handling:
   - Production microservices must never leak unformatted raw Python tracebacks or
     500 Internal Server Errors with internal stack frames to clients.
   - Domain-Driven Exception Architecture:
     * Define custom base domain exceptions (`DomainException`, `EntityNotFoundError`,
       `RateLimitExceededError`).
     * Register global handlers via `@app.exception_handler(CustomException)`.
     * Override FastAPI's default 422 validation handler (`RequestValidationError`) to
       transform internal Pydantic error schemas into clean, standardized API error envelopes.
   - All API errors (400, 404, 422, 429, 500) follow a unified JSON envelope:
     `{"error": {"code": "...", "message": "...", "details": ..., "request_id": "..."}}`.

3. Post-Response Background Tasks (`BackgroundTasks`):
   - Offloads non-blocking side effects to run AFTER the HTTP response headers and
     body bytes have already been transmitted to the client socket.
   - Injected via dependency parameter: `background_tasks: BackgroundTasks`.
   - Use cases: audit logging, sending confirmation emails, cache warming, fire-and-forget
     metrics dispatch.
   - Distinction: Runs in the same process/memory space. Not a replacement for distributed
     queues (Celery/RabbitMQ) for heavy CPU jobs or mission-critical durability.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python (FastAPI / Starlette)       | JavaScript / TypeScript (Express)  |
+------------------------------+------------------------------------+------------------------------------+
| Request Interception         | `@app.middleware("http")`          | `app.use((req, res, next) => ...)` |
| Downstream Execution         | `response = await call_next(req)`  | `next()` (callback-based)          |
| Error Interception           | `@app.exception_handler(CustomErr)`| `app.use((err, req, res, next))`   |
| Validation Error Override    | Handler for `RequestValidationError`| Middleware checking `validationResult`|
| Post-Response Work           | `background_tasks.add_task(fn)`    | `res.on('finish', fn)` / unawaited |
| Correlation ID Context       | `contextvars.ContextVar`           | `AsyncLocalStorage` (`cls-hooked`) |
| Distributed Work Queue       | Celery / Redis Streams / Arq       | BullMQ / RabbitMQ                  |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Architecture Differences:
1. In Express, error handling middleware relies on parameter arity (4 arguments:
   `err, req, res, next`). If an error is thrown in an async handler without being
   passed to `next(err)`, Express (v4) drops it or crashes the process.
2. In FastAPI, exceptions raised in any async or sync endpoint are caught by Starlette's
   exception middleware and dispatched to registered handlers by type inheritance.
3. Express developers often fire un-awaited Promises (`sendEmail().catch(...)`) for
   background work, which can cause unhandled promise rejections or memory leaks during
   server shutdown. FastAPI's `BackgroundTasks` integrates with the ASGI request lifecycle.


============================================================
3. UNDER THE HOOD (CPython & ASGI Protocols)
============================================================

1. The ASGI 3.0 Protocol Interface:
   - FastAPI is an ASGI (Asynchronous Server Gateway Interface) application:
     `async def app(scope: dict, receive: Callable, send: Callable) -> None`.
   - `scope`: Connection state (`type='http'`, `'websocket'`, `'lifespan'`, HTTP headers, path).
   - `receive()`: Awaitable event stream from the server (e.g. `http.request` chunk).
   - `send()`: Awaitable callable to send events back to the client (`http.response.start`,
     `http.response.body`).

2. `BaseHTTPMiddleware` Call Stack:
   - When a request arrives, `call_next(request)` spawns a sub-task running the downstream
     route handler.
   - The response stream is wrapped in a channel. Once the endpoint returns, `call_next` yields
     the `Response` object to your middleware so you can mutate headers or inspect status before
     transmitting bytes.

3. `BackgroundTasks` Execution Mechanics:
   - `BackgroundTasks` holds an internal list: `self.tasks: list[BackgroundTask]`.
   - In Starlette's `Response.__call__`, after the final `http.response.body` event is sent
     over the ASGI socket, the response runner checks `if self.background: await self.background()`.
   - Each task is executed concurrently or sequentially in the event loop before the ASGI
     scope closes.


============================================================
4. COMMON GOTCHAS
============================================================

1. Reading Request Body Inside Middleware:
   - The ASGI `receive` stream is a single-pass asynchronous iterator.
   - If you call `await request.body()` inside HTTP middleware, the stream is consumed.
     Subsequent Pydantic route parsing will hang or receive an empty byte string!
   - FIX: If you must read the body, re-inject the bytes back into the request scope or
     use a custom ASGI class that caches the body buffer.

2. Unhandled Exceptions in BackgroundTasks:
   - `BackgroundTasks` run AFTER the HTTP response status and headers are already committed.
   - If a background task raises an exception, the HTTP status code CANNOT be changed to 500
     because the client has already received 200 OK!
   - FIX: Always wrap background task implementations in robust `try...except` blocks with
     alert logging or dead-letter storage.

3. BackgroundTasks Durability Illusion:
   - FastAPI's `BackgroundTasks` live purely in process RAM.
   - If your server pod restarts, scales down, or crashes during deployment, all queued
     in-flight background tasks are permanently lost.
   - FIX: Use BackgroundTasks strictly for low-stakes, transient side effects (cache warming,
     non-critical audit logs). Use Celery or Redis Streams for financial transactions, billing,
     or emails.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "How do you implement uniform error responses across your entire FastAPI service?"
A1: "I establish a Domain Exception hierarchy inheriting from an abstract `AppException`.
     Then I register custom exception handlers on the FastAPI app for `AppException` and
     `RequestValidationError`. The validation handler intercepts Pydantic's 422 format and
     maps it into our unified API error envelope containing `code`, `message`, `details`,
     and the request's correlation ID. This guarantees that whether a failure is a schema
     violation, an entity lookup failure, or a database timeout, the client always receives
     a deterministic, contract-compliant JSON payload."

Q2: "What is the danger of reading the request body in FastAPI middleware, and how does ASGI handle streams?"
A2: "In ASGI, the request body is an async streaming iterator accessed via the `receive`
     callable. Because it is a single-pass stream, if middleware consumes `await request.body()`,
     the stream buffer is exhausted. When the downstream route attempts to parse Pydantic
     models, it sees empty bytes and fails or hangs. To inspect request bodies in middleware,
     you must intercept `receive`, buffer the raw bytes into memory, and replace the receive
     callable in the scope with an async generator that yields the cached bytes."

Q3: "When do you use FastAPI BackgroundTasks versus a distributed queue like Celery or RQ?"
A3: "I use `BackgroundTasks` for fast, low-stakes side-effects that execute within hundreds
     of milliseconds and can tolerate failure—such as updating an in-memory cache or dispatching
     a metrics ping. For mission-critical operations like payment processing, guaranteed email
     delivery, or heavy CPU workloads like video transcoding or PDF generation, I always use
     a distributed task queue like Celery, Arq, or Redis Streams. Distributed queues provide
     message persistence, automatic retries with exponential backoff, worker dead-letter queues,
     and process isolation so heavy tasks don't block the API event loop."
"""

import sys
import time
import uuid
import warnings
warnings.filterwarnings("ignore")
from typing import Any, Callable, Dict, List, Optional
from contextvars import ContextVar

from fastapi import FastAPI, Request, Response, BackgroundTasks, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ==============================================================================
# 1. ASYNC CONTEXT VAR & CORRELATION ID
# ==============================================================================
# ContextVar maintains request-scoped state across async tasks without mutating global variables
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")


# ==============================================================================
# 2. DOMAIN EXCEPTIONS HIERARCHY
# ==============================================================================

class AppException(Exception):
    """Base class for all domain-specific business exceptions."""
    def __init__(self, message: str, code: str, status_code: int = status.HTTP_400_BAD_REQUEST, details: Any = None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class EntityNotFoundError(AppException):
    def __init__(self, entity_name: str, entity_id: Any):
        super().__init__(
            message=f"{entity_name} with id '{entity_id}' was not found.",
            code="ENTITY_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"entity": entity_name, "id": entity_id}
        )


class InsufficientPermissionsError(AppException):
    def __init__(self, required_scope: str):
        super().__init__(
            message=f"Access denied: missing required scope '{required_scope}'.",
            code="INSUFFICIENT_PERMISSIONS",
            status_code=status.HTTP_403_FORBIDDEN,
            details={"required_scope": required_scope}
        )


# ==============================================================================
# 3. FASTAPI APP & MIDDLEWARE SETUP
# ==============================================================================

app = FastAPI(
    title="Middleware, Exceptions & Background Tasks Engine",
    description="Production-grade middleware, centralized error handling, and background task pipelines.",
    version="1.0.0"
)

# Simulated in-memory persistent audit log and notification store
AUDIT_LOGS: List[Dict[str, Any]] = []
NOTIFICATIONS_SENT: List[Dict[str, Any]] = []


@app.middleware("http")
async def correlation_and_timing_middleware(request: Request, call_next: Callable[[Request], Any]) -> Response:
    """
    Production HTTP middleware that:
    1. Extracts or generates a UUID correlation ID (X-Request-ID).
    2. Stores it in a thread-safe / task-safe ContextVar.
    3. Measures precise request-response execution latency.
    4. Attaches telemetry headers to the outgoing HTTP response.
    """
    # 1. Extract or generate Request ID
    req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    token = correlation_id_ctx.set(req_id)

    # 2. Track timing
    start_time = time.perf_counter()
    
    try:
        response: Response = await call_next(request)
    finally:
        # Calculate process time
        duration = time.perf_counter() - start_time
        # Reset context variable to prevent cross-request leakage
        correlation_id_ctx.reset(token)

    # 3. Attach standard observability headers
    response.headers["X-Request-ID"] = req_id
    response.headers["X-Process-Time-Sec"] = f"{duration:.6f}"
    return response


# ==============================================================================
# 4. CENTRALIZED EXCEPTION HANDLERS
# ==============================================================================

@app.exception_handler(AppException)
async def domain_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Catches all application domain exceptions and formats them into
    a clean, standardized RFC-style error structure.
    """
    req_id = request.headers.get("X-Request-ID", correlation_id_ctx.get())
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "request_id": req_id,
                "path": request.url.path
            }
        },
        headers={"X-Request-ID": req_id}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Overrides FastAPI's default 422 error response to provide clean,
    developer-friendly error lists matching our unified API error envelope.
    """
    req_id = request.headers.get("X-Request-ID", correlation_id_ctx.get())
    formatted_errors = []
    for err in exc.errors():
        field_loc = " -> ".join(str(loc) for loc in err.get("loc", []))
        formatted_errors.append({
            "field": field_loc,
            "issue": err.get("msg"),
            "type": err.get("type")
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "error": {
                "code": "VALIDATION_FAILED",
                "message": "Input validation error in request body or parameters.",
                "details": formatted_errors,
                "request_id": req_id,
                "path": request.url.path
            }
        },
        headers={"X-Request-ID": req_id}
    )


# ==============================================================================
# 5. SCHEMAS & BACKGROUND TASKS IMPLEMENTATION
# ==============================================================================

class OrderItem(BaseModel):
    sku: str = Field(..., min_length=3, max_length=20)
    quantity: int = Field(..., gt=0, le=100)
    unit_price: float = Field(..., gt=0.0)


class PlaceOrderRequest(BaseModel):
    customer_email: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    items: List[OrderItem] = Field(..., min_length=1)


def async_audit_worker(action: str, entity_id: str, actor: str, req_id: str) -> None:
    """Simulates recording an immutable audit log entry."""
    entry = {
        "timestamp": time.time(),
        "action": action,
        "entity_id": entity_id,
        "actor": actor,
        "request_id": req_id
    }
    AUDIT_LOGS.append(entry)


def async_notification_worker(recipient: str, subject: str, body: str) -> None:
    """Simulates sending an external notification/email."""
    message = {
        "recipient": recipient,
        "subject": subject,
        "body": body,
        "dispatched_at": time.time()
    }
    NOTIFICATIONS_SENT.append(message)


# In-memory inventory database
INVENTORY_DB: Dict[str, int] = {
    "SKU-PYTHON-PRO": 50,
    "SKU-FASTAPI-BOOK": 15
}


# ==============================================================================
# 6. ROUTE HANDLERS
# ==============================================================================

@app.post("/api/v1/orders", status_code=status.HTTP_202_ACCEPTED)
async def place_order(
    payload: PlaceOrderRequest,
    background_tasks: BackgroundTasks,
    request: Request
):
    """
    Places an order:
    1. Verifies stock (raises EntityNotFoundError if SKU missing).
    2. Offloads audit logging and email notifications to BackgroundTasks.
    3. Responds immediately with 202 Accepted.
    """
    req_id = request.headers.get("X-Request-ID", correlation_id_ctx.get())

    # Business logic check
    for item in payload.items:
        if item.sku not in INVENTORY_DB:
            raise EntityNotFoundError(entity_name="InventorySKU", entity_id=item.sku)

    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"

    # Queue post-response background work
    background_tasks.add_task(
        async_audit_worker,
        action="ORDER_CREATED",
        entity_id=order_id,
        actor=payload.customer_email,
        req_id=req_id
    )
    background_tasks.add_task(
        async_notification_worker,
        recipient=payload.customer_email,
        subject=f"Confirmation for Order {order_id}",
        body=f"Your order containing {len(payload.items)} item(s) has been accepted."
    )

    return {
        "order_id": order_id,
        "status": "PROCESSING",
        "message": "Order accepted and background jobs scheduled."
    }


@app.get("/api/v1/secure-vault")
async def secure_vault(scope: Optional[str] = None):
    """Demonstrates raising a permission domain error."""
    if scope != "vault:read":
        raise InsufficientPermissionsError(required_scope="vault:read")
    return {"secret_data": "classified_cpython_bytecode"}


# ==============================================================================
# 7. SELF-TESTING SUITE
# ==============================================================================

def run_tests() -> None:
    print("\n[*] Starting automated test suite for 04_middleware_exceptions_and_background.py...")

    client = TestClient(app)

    # ------------------------------------------------------------
    # Test 1: Middleware attaches X-Request-ID & X-Process-Time
    # ------------------------------------------------------------
    print("  -> Testing middleware correlation ID and latency injection...")
    custom_req_id = "test-req-uuid-12345"
    res1 = client.get("/api/v1/secure-vault?scope=vault:read", headers={"X-Request-ID": custom_req_id})
    assert res1.status_code == 200, f"Expected 200, got {res1.status_code}"
    assert res1.headers.get("X-Request-ID") == custom_req_id, "Middleware failed to echo X-Request-ID"
    assert "X-Process-Time-Sec" in res1.headers, "Middleware failed to inject X-Process-Time-Sec"
    assert float(res1.headers["X-Process-Time-Sec"]) >= 0.0

    # Test auto-generated UUID if X-Request-ID header is omitted
    res1_auto = client.get("/api/v1/secure-vault?scope=vault:read")
    assert res1_auto.status_code == 200
    assert len(res1_auto.headers.get("X-Request-ID", "")) > 10, "Failed to auto-generate request ID"

    # ------------------------------------------------------------
    # Test 2: Custom Domain Exception (403 Forbidden)
    # ------------------------------------------------------------
    print("  -> Testing custom domain exception handler (InsufficientPermissionsError)...")
    res2 = client.get("/api/v1/secure-vault")
    assert res2.status_code == 403, f"Expected 403, got {res2.status_code}"
    data2 = res2.json()
    assert "error" in data2, "Unified error envelope missing"
    assert data2["error"]["code"] == "INSUFFICIENT_PERMISSIONS"
    assert "vault:read" in data2["error"]["details"]["required_scope"]
    assert "X-Request-ID" in res2.headers

    # ------------------------------------------------------------
    # Test 3: Custom Domain Exception (404 Not Found)
    # ------------------------------------------------------------
    print("  -> Testing custom domain exception handler (EntityNotFoundError)...")
    bad_order_payload = {
        "customer_email": "engineer@python.org",
        "items": [
            {"sku": "SKU-NON-EXISTENT", "quantity": 2, "unit_price": 49.99}
        ]
    }
    res3 = client.post("/api/v1/orders", json=bad_order_payload)
    assert res3.status_code == 404, f"Expected 404, got {res3.status_code}"
    data3 = res3.json()
    assert data3["error"]["code"] == "ENTITY_NOT_FOUND"
    assert data3["error"]["details"]["id"] == "SKU-NON-EXISTENT"

    # ------------------------------------------------------------
    # Test 4: Custom Pydantic 422 Validation Error Handler
    # ------------------------------------------------------------
    print("  -> Testing overridden 422 RequestValidationError handler...")
    invalid_payload = {
        "customer_email": "not-an-email",  # Invalid regex
        "items": []                        # min_length=1 violated
    }
    res4 = client.post("/api/v1/orders", json=invalid_payload)
    assert res4.status_code == 422, f"Expected 422, got {res4.status_code}"
    data4 = res4.json()
    assert data4["error"]["code"] == "VALIDATION_FAILED"
    assert isinstance(data4["error"]["details"], list)
    assert len(data4["error"]["details"]) >= 2
    # Check that error fields are properly mapped
    fields = [d["field"] for d in data4["error"]["details"]]
    assert any("customer_email" in f for f in fields)
    assert any("items" in f for f in fields)

    # ------------------------------------------------------------
    # Test 5: BackgroundTasks Execution Lifecycle
    # ------------------------------------------------------------
    print("  -> Testing BackgroundTasks asynchronous execution...")
    AUDIT_LOGS.clear()
    NOTIFICATIONS_SENT.clear()

    valid_payload = {
        "customer_email": "developer@fastapi.tiangolo.com",
        "items": [
            {"sku": "SKU-PYTHON-PRO", "quantity": 1, "unit_price": 99.00}
        ]
    }
    res5 = client.post("/api/v1/orders", json=valid_payload, headers={"X-Request-ID": "audit-track-001"})
    assert res5.status_code == 202, f"Expected 202 Accepted, got {res5.status_code}"
    order_data = res5.json()
    assert order_data["status"] == "PROCESSING"

    # In TestClient, BackgroundTasks are synchronously executed before client.post returns!
    assert len(AUDIT_LOGS) == 1, "Audit log background task did not execute"
    assert AUDIT_LOGS[0]["action"] == "ORDER_CREATED"
    assert AUDIT_LOGS[0]["actor"] == "developer@fastapi.tiangolo.com"
    assert AUDIT_LOGS[0]["request_id"] == "audit-track-001"

    assert len(NOTIFICATIONS_SENT) == 1, "Notification background task did not execute"
    assert NOTIFICATIONS_SENT[0]["recipient"] == "developer@fastapi.tiangolo.com"
    assert "Confirmation" in NOTIFICATIONS_SENT[0]["subject"]

    print("[SUCCESS] All 5 Middleware, Exception & BackgroundTask tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 7 - 04: Middleware, Centralized Exceptions & Background Tasks")
    print("=" * 70)
    run_tests()
    print("=" * 70)
