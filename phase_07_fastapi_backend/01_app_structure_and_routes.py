"""
Phase 7: Backend with FastAPI - Application Structure, Routes & Lifespan
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - FastAPI is a modern, high-performance web framework for building APIs with Python 3.8+
     based on standard Python type hints and Starlette/Pydantic.
   - Core Concepts:
     * App Initialization: 'app = FastAPI(title="...", version="...")'.
     * Automatic Interactive Documentation: Swagger UI at '/docs', ReDoc at '/redoc'.
     * Path Operations: '@app.get()', '@app.post()', '@app.put()', '@app.delete()'.
     * Parameter Types:
       - Path Parameters: '/items/{item_id}' (typed as int, str, UUID).
       - Query Parameters: '/items?skip=0&limit=10' (function arguments with default values).
       - Request Body: Handled via Pydantic models.
     * Application Lifespan ('@asynccontextmanager lifespan(app)'): Replaces legacy startup/shutdown
       events for cleanly initializing DB connection pools, caches, and AI model weights.
   - 'async def' vs 'def' in Route Handlers:
     * 'async def': Runs directly on the main event loop. Perfect for non-blocking I/O (async DB, httpx).
     * 'def' (plain): FastAPI automatically runs it in an external worker threadpool! Use for
       legacy synchronous SDKs so you don't freeze the event loop.
   - JS/TS Analogy:
     * Express.js: 'app.get("/items/:id", (req, res) => ...)' -> FastAPI: '@app.get("/items/{item_id}")'.
     * Unlike Express, FastAPI validates and casts path/query parameters automatically using Python types.

2. UNDER THE HOOD (CPython & Memory):
   - FastAPI is built on ASGI (Asynchronous Server Gateway Interface), the modern async replacement
     for WSGI (Flask/Django).
   - In production, an ASGI server like Uvicorn receives raw HTTP bytes, parses the HTTP/1.1 or HTTP/2
     frames, and invokes FastAPI's ASGI callable interface.

3. COMMON GOTCHA:
   - Putting blocking synchronous code (like time.sleep() or sync DB calls) inside an 'async def' handler!
     This freezes the entire Uvicorn worker process. If a call is synchronous, declare the route with
     plain 'def' so FastAPI executes it in a background threadpool.

4. 🎙️ INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   -----------------------------------------------------------------------------
   Q: "Explain the architecture of a FastAPI application, the role of ASGI, and when
       should you define route handlers with 'async def' versus plain 'def'?"
   
   HOW TO ANSWER OUT LOUD (60-90 sec script):
   1. The ASGI Architecture:
      "FastAPI is built on top of Starlette and Pydantic, adhering to the ASGI specification.
       Unlike legacy WSGI frameworks like Flask or Django that process one synchronous request per thread,
       ASGI servers like Uvicorn maintain an asynchronous event loop that can juggle thousands of
       concurrent I/O connections simultaneously on a single thread."
   2. The 'async def' vs 'def' Rule:
      "A crucial architectural question in FastAPI is whether to declare endpoints as 'async def' or plain 'def':
       - Use 'async def' when your code performs non-blocking I/O using 'await'—such as querying an
         async database (SQLAlchemy async / asyncpg), calling an external API with httpx.AsyncClient,
         or streaming LLM tokens.
       - Use plain 'def' if your endpoint uses synchronous, blocking libraries (like standard Boto3,
         sync psycopg2, or CPU-bound tasks). FastAPI automatically dispatches plain 'def' endpoints
         to a background threadpool (via AnyIO), preventing the main event loop from locking up."
   3. Lifespan Events:
      "We manage shared resources—like database pools and ML model weights—using modern async context
       managers with the 'lifespan' parameter, guaranteeing clean initialization on startup and safe
       teardown on shutdown."
================================================================================
"""

import sys
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
from contextlib import asynccontextmanager
from typing import Optional, List
from fastapi import FastAPI, HTTPException, status, Query
from fastapi.testclient import TestClient
from pydantic import BaseModel

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ==============================================================================
# 1. APPLICATION LIFESPAN & INITIALIZATION
# ==============================================================================

# In-memory storage for demonstration
FAKE_ITEMS_DB = {
    1: {"id": 1, "name": "Pythonic Coffee Mug", "price": 14.99, "is_available": True},
    2: {"id": 2, "name": "Mechanical Keyboard", "price": 99.50, "is_available": True},
    3: {"id": 3, "name": "Noise Cancelling Headphones", "price": 199.00, "is_available": False},
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Modern FastAPI lifespan context manager.
    Runs setup before receiving requests, teardown on shutdown.
    """
    print("  [Lifespan Startup] Initializing connection pools & loading models...")
    yield  # Application serves traffic while yielded
    print("  [Lifespan Shutdown] Closing connections and flushing logs...")


app = FastAPI(
    title="FastAPI Fundamentals API",
    version="1.0.0",
    description="Demonstrates routes, parameters, status codes, and lifespan events.",
    lifespan=lifespan
)


# ==============================================================================
# 2. SCHEMAS & ROUTE DEFINITIONS
# ==============================================================================

class ItemCreate(BaseModel):
    name: str
    price: float
    is_available: bool = True


@app.get("/health", status_code=status.HTTP_200_OK, tags=["System"])
async def health_check():
    """Simple health probe endpoint."""
    return {"status": "HEALTHY", "version": "1.0.0"}


@app.get("/items", tags=["Items"])
async def list_items(
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(10, ge=1, le=50, description="Max records to return"),
    available_only: bool = Query(False, description="Filter active items only")
):
    """Demonstrates Query parameters with validation constraints (ge, le)."""
    items = list(FAKE_ITEMS_DB.values())
    if available_only:
        items = [item for item in items if item["is_available"]]
    return items[skip : skip + limit]


@app.get("/items/{item_id}", tags=["Items"])
async def get_item_by_id(item_id: int):
    """Demonstrates Path parameter with automatic integer type casting and 404 handling."""
    item = FAKE_ITEMS_DB.get(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with ID {item_id} not found."
        )
    return item


@app.post("/items", status_code=status.HTTP_201_CREATED, tags=["Items"])
async def create_item(payload: ItemCreate):
    """Demonstrates POST request body parsing and HTTP 201 Created status."""
    new_id = max(FAKE_ITEMS_DB.keys(), default=0) + 1
    new_item = {
        "id": new_id,
        "name": payload.name,
        "price": payload.price,
        "is_available": payload.is_available
    }
    FAKE_ITEMS_DB[new_id] = new_item
    return new_item


# ==============================================================================
# SELF-TEST CHALLENGES (Using FastAPI TestClient)
# ==============================================================================

def run_tests():
    print("\n[*] Running automated tests for 01_app_structure_and_routes.py using TestClient...")
    with TestClient(app) as client:
        # 1. Test health check
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json() == {"status": "HEALTHY", "version": "1.0.0"}

        # 2. Test get items with pagination query params
        res = client.get("/items?skip=0&limit=2")
        assert res.status_code == 200
        assert len(res.json()) == 2

        # 3. Test get item by ID
        res = client.get("/items/1")
        assert res.status_code == 200
        assert res.json()["name"] == "Pythonic Coffee Mug"

        # 4. Test 404 on missing item
        res = client.get("/items/9999")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()

        # 5. Test POST item creation
        new_payload = {"name": "AI Mechanical Pencil", "price": 4.50, "is_available": True}
        res = client.post("/items", json=new_payload)
        assert res.status_code == 201
        data = res.json()
        assert data["id"] == 4
        assert data["name"] == "AI Mechanical Pencil"

    print("[SUCCESS] All FastAPI route tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 65)
    print("Execution: Phase 7 - FastAPI Application Structure & Routes")
    print("=" * 65)
    run_tests()
    print("=" * 65)
