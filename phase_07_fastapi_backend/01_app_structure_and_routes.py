"""
01_app_structure_and_routes.py

============================================================
1. CONCEPT
============================================================

FastAPI is a modern, high-performance web framework for building APIs with Python,
grounded in the ASGI specification, standard Python type annotations, Pydantic,
and Starlette:

1. ASGI (Asynchronous Server Gateway Interface):
   - The modern asynchronous successor to WSGI (used by legacy Flask and Django).
   - Enables handling long-lived connections, WebSockets, Server-Sent Events (SSE),
     and thousands of concurrent HTTP requests on a single event loop process.
   - ASGI servers like Uvicorn handle raw TCP/TLS socket connections and invoke
     the FastAPI application callable interface.

2. Route Operations & Modular Routers (`APIRouter`):
   - HTTP Verbs: `@app.get()`, `@app.post()`, `@app.put()`, `@app.delete()`.
   - Modular decomposition: `APIRouter(prefix="/api/v1/users", tags=["users"])`
     allows decomposing microservices into dedicated domain modules.
   - Included via `app.include_router(user_router)`.

3. Automatic Parameter Parsing & Validation:
   - Path Parameters: `/users/{user_id}` (e.g. `user_id: int`). FastAPI casts
     and validates inputs, returning HTTP 422 Unprocessable Entity if type constraints fail.
   - Query Parameters: Function arguments with default values (`skip: int = 0, limit: int = 20`).
   - Request Bodies: Pydantic schemas mapped automatically from incoming JSON.

4. The Handler Concurrency Rule (`async def` vs `def`):
   - `async def`: Executed directly on the main event loop thread. Must use `await`
     for non-blocking I/O. (NEVER call blocking synchronous code like `time.sleep` here!).
   - Plain `def`: FastAPI automatically offloads plain synchronous endpoints to an
     external worker threadpool (via AnyIO), ensuring the event loop is never blocked
     by legacy synchronous SDKs (e.g. AWS Boto3, synchronous DB drivers).

5. Modern Lifespan Management (`lifespan` parameter):
   - Standardized via `@asynccontextmanager` passing `app: FastAPI`.
   - Code before `yield`: Startup initialization (DB pools, caches, ML models).
   - Code after `yield`: Teardown cleanup (closing connections, flushing queues).
   - Supersedes legacy `@app.on_event("startup")` / `"shutdown"`.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python (FastAPI)                   | JavaScript / TypeScript (Express)  |
+------------------------------+------------------------------------+------------------------------------+
| Framework Foundation         | ASGI (Starlette)                   | Node.js `http` module              |
| Route Declaration            | `@app.get("/items/{id}")`          | `app.get("/items/:id", ...)`       |
| Parameter Type Validation    | Automatic via type hints + Pydantic| Manual parsing / Zod middleware    |
| Validation Error Response    | Automatic HTTP 422 JSON            | Manual 400 Bad Request error       |
| Modular Sub-Routing          | `APIRouter()`                      | `express.Router()`                 |
| OpenAPI Documentation        | Built-in (`/docs` & `/redoc`)      | Requires swagger-ui-express plugin |
| App Lifespan Management      | `@asynccontextmanager lifespan(app)`| Server `listen` and `close` hooks  |
| Sync Function Offloading     | Automatic threadpool dispatch      | Manual worker_threads dispatch     |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Web Framework Differences:
1. In Express or Fastify, route parameters (`req.params.id`) are raw strings. You
   must manually parse `parseInt(req.params.id, 10)` and validate. In FastAPI,
   writing `id: int` automatically parses, type-checks, and validates the input.
2. FastAPI auto-generates interactive Swagger documentation at `/docs` directly
   from Python type annotations without any external YAML or decorator clutter.


============================================================
3. UNDER THE HOOD (CPython & Memory)
============================================================

1. The ASGI Callable Interface:
   - An ASGI application is an async callable matching:
     `async def app(scope, receive, send):`
   - `scope`: Dictionary containing connection metadata (HTTP method, headers, path).
   - `receive`: Async callable yielding incoming HTTP request body chunks.
   - `send`: Async callable transmitting HTTP headers and response body chunks.

2. AnyIO Worker Threadpool Dispatch:
   - When a route is defined with plain `def endpoint():`, FastAPI inspects it
     using `inspect.iscoroutinefunction()`.
   - Because it is synchronous, FastAPI routes execution through `anyio.to_thread.run_sync()`,
     allocating an OS thread from a dynamic thread pool while keeping the ASGI loop active.


============================================================
4. COMMON GOTCHAS
============================================================

1. Blocking the Event Loop in `async def`:
   - Writing `time.sleep(5)` or synchronous DB queries inside `async def` halts
     all concurrent traffic across the entire Uvicorn worker!
   - Solution: Use `await asyncio.sleep(5)` or declare the handler with plain `def`.

2. Forgetting Path Parameter Braces:
   - Defining `@app.get("/items/item_id")` instead of `@app.get("/items/{item_id}")`.
   - FastAPI treats `item_id` as a query parameter instead of extracting from URL path.

3. Mutating Global State Across Requests:
   - FastAPI handlers run concurrently. Mutating shared in-memory dictionaries
     without async locks introduces race conditions.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "Explain how FastAPI leverages ASGI and how it differs from traditional WSGI frameworks like Flask."
Script:
"FastAPI is built on top of Starlette and adheres to the Asynchronous Server Gateway
Interface (ASGI) specification. Traditional WSGI frameworks like Flask and Django operate
on a synchronous model where each worker thread processes one request at a time, requiring
massive thread pools that incur heavy OS context-switching overhead under load. ASGI servers
like Uvicorn maintain an asynchronous event loop that multiplexes thousands of concurrent I/O
connections on a single OS thread. When an endpoint awaits database responses or microservice
calls, the worker immediately handles other requests, providing orders of magnitude higher
throughput for I/O-bound web services."

Q2: "In FastAPI, when should you define a route handler with 'async def' versus plain 'def'?"
Script:
"The decision hinges entirely on whether the endpoint's dependencies are asynchronous:
You should use `async def` when your handler executes non-blocking asynchronous operations
using `await`—such as querying an async database with SQLAlchemy/asyncpg, issuing HTTP calls
with `httpx.AsyncClient`, or streaming tokens from an LLM.
Conversely, you should declare the route with plain `def` if the endpoint uses synchronous,
blocking libraries—like AWS Boto3, legacy database drivers, or CPU-heavy processing. When
FastAPI detects a plain `def` handler, it automatically offloads its execution to an external
AnyIO worker thread pool, preventing the main event loop from locking up."

Q3: "How does FastAPI's lifespan context manager work, and why is it preferred over on_event?"
Script:
"FastAPI's `lifespan` parameter uses standard Python `@asynccontextmanager` syntax to govern
the entire application lifecycle. Code before the `yield` statement executes during application
startup, making it the ideal location to initialize database connection pools, warm up ML model
weights, or configure Redis clients. Execution pauses while the application serves traffic.
When the server initiates a graceful shutdown, execution resumes after `yield`, allowing
resources to be closed and flushed cleanly. This context-manager pattern is vastly superior
to legacy `@app.on_event` decorators because it supports clean error handling, state sharing via
`app.state`, and deterministic teardown."
"""

import asyncio
from contextlib import asynccontextmanager
import sys
from fastapi import APIRouter, FastAPI, HTTPException, status
from pydantic import BaseModel
import httpx

# Ensure UTF-8 standard output across environments
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ============================================================
# PYDANTIC SCHEMAS FOR ROUTE VALIDATION
# ============================================================

class ItemCreate(BaseModel):
    name: str
    price: float
    is_offer: bool = False


class ItemResponse(ItemCreate):
    item_id: int


# ============================================================
# LIFESPAN CONTEXT MANAGER
# ============================================================

@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """Manages application startup and graceful shutdown."""
    # Startup phase: Initialize in-memory storage and state
    app.state.database = {
        1: {"item_id": 1, "name": "Standard Widget", "price": 19.99, "is_offer": False},
        2: {"item_id": 2, "name": "Premium Gadget", "price": 99.50, "is_offer": True},
    }
    app.state.is_healthy = True
    yield
    # Teardown phase: Clean up state
    app.state.database.clear()
    app.state.is_healthy = False


# ============================================================
# MODULAR API ROUTER
# ============================================================

items_router = APIRouter(prefix="/api/v1/items", tags=["items"])


@items_router.get("/{item_id}", response_model=ItemResponse)
async def get_item_by_id(item_id: int):
    """Async endpoint: fetches item by integer path parameter."""
    # Simulated non-blocking async lookup
    await asyncio.sleep(0.001)
    db = app.state.database
    if item_id not in db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {item_id} not found",
        )
    return db[item_id]


@items_router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(payload: ItemCreate):
    """Async endpoint: creates new item from validated Pydantic body."""
    db = app.state.database
    new_id = max(db.keys(), default=0) + 1
    new_record = {"item_id": new_id, **payload.model_dump()}
    db[new_id] = new_record
    return new_record


# Synchronous endpoint: FastAPI automatically dispatches to AnyIO threadpool
@items_router.get("/metrics/sync-calc")
def synchronous_heavy_calculation(base_val: int = 10):
    """Plain def endpoint: runs in background threadpool to avoid event loop blocking."""
    # Simulates legacy synchronous calculation
    total = sum(i * base_val for i in range(100))
    return {"calculation": total, "mode": "threadpool_dispatched"}


# ============================================================
# APPLICATION INSTANTIATION & ROUTER MOUNTING
# ============================================================

app = FastAPI(
    title="Apex Enterprise API",
    version="1.0.0",
    description="High-throughput asynchronous microservice",
    lifespan=app_lifespan,
)

app.include_router(items_router)


@app.get("/health", tags=["system"])
async def health_check():
    """System health check endpoint."""
    return {"status": "healthy" if app.state.is_healthy else "unhealthy"}


def run_tests():
    # In-memory ASGI testing via httpx.ASGITransport without opening network sockets
    async def main_suite():
        # Using AsyncClient with lifespan context manager
        async with app_lifespan(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:

                # ------------------------------------------------------------
                # Health Check Endpoint
                # ------------------------------------------------------------
                health_resp = await client.get("/health")
                assert health_resp.status_code == 200
                assert health_resp.json() == {"status": "healthy"}

                # ------------------------------------------------------------
                # Successful GET Item by ID
                # ------------------------------------------------------------
                item_resp = await client.get("/api/v1/items/1")
                assert item_resp.status_code == 200
                data = item_resp.json()
                assert data["item_id"] == 1
                assert data["name"] == "Standard Widget"
                assert data["price"] == 19.99

                # ------------------------------------------------------------
                # 404 Not Found Handling
                # ------------------------------------------------------------
                missing_resp = await client.get("/api/v1/items/999")
                assert missing_resp.status_code == 404
                assert "Item 999 not found" in missing_resp.json()["detail"]

                # ------------------------------------------------------------
                # Automatic Type Validation: 422 Unprocessable Entity
                # Passing string 'invalid-id' where int is required
                # ------------------------------------------------------------
                invalid_resp = await client.get("/api/v1/items/not-a-number")
                assert invalid_resp.status_code == 422

                # ------------------------------------------------------------
                # Successful POST with Pydantic JSON Body
                # ------------------------------------------------------------
                new_item_payload = {"name": "AI Coprocessor", "price": 499.00, "is_offer": True}
                create_resp = await client.post("/api/v1/items", json=new_item_payload)
                assert create_resp.status_code == 201
                created_data = create_resp.json()
                assert created_data["item_id"] == 3
                assert created_data["name"] == "AI Coprocessor"

                # ------------------------------------------------------------
                # Synchronous Endpoint Dispatched via Threadpool
                # ------------------------------------------------------------
                sync_resp = await client.get("/api/v1/items/metrics/sync-calc?base_val=2")
                assert sync_resp.status_code == 200
                assert sync_resp.json()["mode"] == "threadpool_dispatched"

    asyncio.run(main_suite())


if __name__ == "__main__":
    run_tests()
    print("01_app_structure_and_routes.py tests passed!")
