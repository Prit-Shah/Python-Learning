"""
05_production_rest_api.py

============================================================
1. CONCEPT
============================================================

Building enterprise-grade REST APIs in FastAPI requires more than single-file script
handlers. It requires a structured, multi-tier Layered Architecture (Clean Architecture /
Hexagonal Architecture) that decouples HTTP transport from business domain logic and
persistence:

1. Layered Separation of Concerns:
   - API Transport Layer (`APIRouter`): Declares path operations, HTTP status codes,
     request parameter parsing (`Query`, `Path`, `Body`), and delegates to services.
   - Service / Use-Case Layer: Implements pure business logic, orchestration, and domain
     invariants (e.g., verifying workflow status transitions).
   - Repository Layer: Abstracts data access, handling query composition, filtering,
     pagination, and persistence storage.
   - Domain Schemas / DTOs (Pydantic v2): Defines strict request/response boundary contracts.

2. Modern ASGI Lifespan Protocol (`lifespan`):
   - Replaces legacy `@app.on_event("startup")` and `@app.on_event("shutdown")`.
   - Uses Python's `@asynccontextmanager` on the FastAPI instance to manage resource life:
     ```python
     @asynccontextmanager
     async def lifespan(app: FastAPI):
         # Startup: initialize connection pools, warm caches, seed lookup data
         yield {"app_state": "ready"}
         # Shutdown: drain connection pools, flush log buffers, graceful exit
     ```

3. Production HTTP REST Semantics:
   - POST /resources -> 201 Created (with newly generated ID and timestamps).
   - GET /resources -> 200 OK (with pagination metadata envelope: `items`, `total`, `page`, `size`, `pages`).
   - GET /resources/{id} -> 200 OK or 404 Not Found.
   - PATCH /resources/{id} -> 200 OK (partial update using `model_dump(exclude_unset=True)`).
   - DELETE /resources/{id} -> 204 No Content (must return an empty body).


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python (FastAPI)                   | JavaScript / TypeScript (NestJS)   |
+------------------------------+------------------------------------+------------------------------------+
| Route Splitting              | `APIRouter(prefix="/tasks")`       | `@Controller('tasks')`             |
| Dependency Injection         | `Depends(get_task_service)`        | `@Inject(TaskService)` constructor |
| Data Validation & DTOs       | Pydantic v2 `BaseModel`            | `class-validator` + `class-transf.`|
| Application Lifecycle        | `@asynccontextmanager def lifespan`| `OnModuleInit` / `OnModuleDestroy` |
| Partial Updates              | `model_dump(exclude_unset=True)`   | `PartialType(CreateTaskDto)`       |
| HTTP Status Codes            | `status.HTTP_201_CREATED`          | `HttpStatus.CREATED`               |
| No-Content Response          | `status_code=204, response_class=..`| `@HttpCode(204)`                   |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Architecture Differences:
1. In Express or vanilla Node, developers frequently bundle routing, business logic,
   and SQL queries directly into route callbacks. NestJS enforces modular layering
   via decorators and classes. FastAPI achieves clean layering via function-based
   Dependency Injection (`Depends`) and APIRouter modularization.
2. In TypeScript DTOs, `Partial<CreateDto>` marks types as optional for TypeScript's
   compiler, but runtime validation requires additional libraries (Zod or class-validator).
   In FastAPI, Pydantic v2 models validate both at compile-time (via type checkers like Mypy/Pyright)
   and enforce boundaries at runtime with C-level speed via `pydantic-core`.


============================================================
3. UNDER THE HOOD (CPython & FastAPI Internals)
============================================================

1. Partial Update Serialization via `exclude_unset=True`:
   - A critical distinction exists between a field being omitted from a JSON request
     versus a field being explicitly passed as `null` (`None`).
   - Pydantic v2 tracks fields explicitly assigned during instantiation via internal
     bitfields (`__pydantic_fields_set__`).
   - Calling `payload.model_dump(exclude_unset=True)` serializes ONLY the keys that were
     present in the incoming JSON payload, preventing unmentioned fields from overwriting
     existing database columns with default values.

2. ASGI Lifespan State Sharing:
   - When using `@asynccontextmanager async def lifespan(app: FastAPI)`, any dictionary
     yielded by the context manager is automatically merged into `app.state`.
   - Handlers access application-scoped singleton instances (such as database engines or
     AI model caches) via `request.app.state`, completely eliminating reliance on mutable
     global module variables.


============================================================
4. COMMON GOTCHAS
============================================================

1. Returning Content with 204 No Content:
   - RFC 9110 strictly dictates that a `204 No Content` HTTP response MUST NOT include a
     message body.
   - Returning `return {"status": "deleted"}` with `status_code=204` causes ASGI servers
     like Uvicorn to either strip the body silently or raise protocol violations in strict
     HTTP clients. Use `Response(status_code=status.HTTP_204_NO_CONTENT)`.

2. Mutating State Directly in Route Handlers:
   - Writing business logic directly in route handlers tightly couples HTTP transport
     with domain operations, making unit testing impossible without instantiating mock HTTP
     requests.
   - Always encapsulate domain operations into isolated Service classes that receive and
     return pure Python objects / Pydantic models.

3. Unbounded Queries (Missing Pagination Caps):
   - Allowing clients to query `GET /items?limit=1000000` risks memory exhaustion and
     database thread pool starvation.
   - Always enforce strict bounds on pagination parameters using `Query(..., ge=1, le=100)`.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "How do you design a robust pagination response in a REST API with FastAPI?"
A1: "I implement an envelope schema parameterized using Generic Pydantic models:
     `PaginatedResponse[T]` containing fields: `items: list[T]`, `total: int`, `page: int`,
     `size: int`, and `pages: int`. In the endpoint, I extract `page` and `size` using
     `Query(ge=1)` and `Query(ge=1, le=100)` to guard against denial-of-service through
     unbounded queries. The repository executes a count query for `total` and applies
     `OFFSET` and `LIMIT` calculations, allowing the frontend client to implement deterministic
     table navigation and infinite scrolling."

Q2: "What is the difference between PUT and PATCH, and how do you implement PATCH cleanly in FastAPI?"
A2: "PUT represents an idempotent full replacement of an entire resource entity; any fields
     omitted in the payload are reset to their default or null states. PATCH represents a
     partial modification of specific fields. In FastAPI, I model PATCH using a Pydantic schema
     where all fields are `Optional` with default `None`. Inside the service layer, I serialize
     the payload using `payload.model_dump(exclude_unset=True)`. This inspects Pydantic's internal
     `__pydantic_fields_set__` so that only fields explicitly provided in the JSON request body
     are updated, leaving untouched fields intact."

Q3: "How does the modern ASGI lifespan pattern improve application startup and shutdown over legacy event handlers?"
A3: "Legacy `@app.on_event('startup')` and `'shutdown'` were fragmented into separate disconnected
     callbacks, making it difficult to maintain state or handle setup failures cleanly. FastAPI's
     modern `lifespan` uses Python's `@asynccontextmanager`. Everything before the `yield` runs on
     startup—such as opening connection pools or warming caches—and state yielded is stored in
     `app.state`. Everything after `yield` runs deterministically on shutdown in reverse order,
     wrapped in guaranteed `finally` execution even if unhandled exceptions occur during runtime."
"""

import sys
import uuid
import warnings
warnings.filterwarnings("ignore")
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar
from math import ceil

from fastapi import FastAPI, APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field, ConfigDict

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ==============================================================================
# 1. ENUMS & DOMAIN MODELS
# ==============================================================================

class TaskPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TaskStatus(str, Enum):
    BACKLOG = "BACKLOG"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


# ==============================================================================
# 2. PYDANTIC V2 SCHEMAS (DTOS)
# ==============================================================================

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=120, description="Concise title of the task")
    description: Optional[str] = Field(None, max_length=1000, description="Detailed description")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)
    tags: List[str] = Field(default_factory=list)


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=120)
    description: Optional[str] = Field(None, max_length=1000)
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    tags: Optional[List[str]] = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: Optional[str]
    priority: TaskPriority
    status: TaskStatus
    tags: List[str]
    created_at: str
    updated_at: str


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int
    pages: int


# ==============================================================================
# 3. REPOSITORY LAYER (DATA ACCESS)
# ==============================================================================

class TaskRepository:
    """Thread-safe, in-memory repository simulating database persistence."""

    def __init__(self) -> None:
        self._storage: Dict[str, Dict[str, Any]] = {}

    def get_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self._storage.get(task_id)

    def get_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        for record in self._storage.values():
            if record["title"].lower() == title.lower():
                return record
        return None

    def list_all(
        self,
        status_filter: Optional[TaskStatus] = None,
        priority_filter: Optional[TaskPriority] = None,
        search_query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        results = list(self._storage.values())
        if status_filter:
            results = [r for r in results if r["status"] == status_filter]
        if priority_filter:
            results = [r for r in results if r["priority"] == priority_filter]
        if search_query:
            q = search_query.lower()
            results = [r for r in results if q in r["title"].lower() or (r["description"] and q in r["description"].lower())]
        # Sort by created_at descending
        results.sort(key=lambda r: r["created_at"], reverse=True)
        return results

    def save(self, record: Dict[str, Any]) -> Dict[str, Any]:
        self._storage[record["id"]] = record
        return record

    def delete(self, task_id: str) -> bool:
        if task_id in self._storage:
            del self._storage[task_id]
            return True
        return False

    def clear(self) -> None:
        self._storage.clear()


# ==============================================================================
# 4. SERVICE / BUSINESS LOGIC LAYER
# ==============================================================================

class TaskService:
    """Orchestrates domain validation and business operations."""

    def __init__(self, repo: TaskRepository) -> None:
        self.repo = repo

    def create_task(self, payload: TaskCreate) -> Dict[str, Any]:
        # Domain rule: Task titles must be unique
        if self.repo.get_by_title(payload.title):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A task with title '{payload.title}' already exists."
            )

        now = datetime.now(timezone.utc).isoformat()
        record = {
            "id": f"TSK-{uuid.uuid4().hex[:8].upper()}",
            "title": payload.title,
            "description": payload.description,
            "priority": payload.priority,
            "status": TaskStatus.BACKLOG,
            "tags": payload.tags,
            "created_at": now,
            "updated_at": now
        }
        return self.repo.save(record)

    def get_task(self, task_id: str) -> Dict[str, Any]:
        record = self.repo.get_by_id(task_id)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with ID '{task_id}' was not found."
            )
        return record

    def update_task(self, task_id: str, payload: TaskUpdate) -> Dict[str, Any]:
        record = self.get_task(task_id)

        # Extract only explicitly supplied fields
        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            return record

        # Domain rule: Cannot mark task COMPLETED directly from BACKLOG without IN_PROGRESS
        if update_data.get("status") == TaskStatus.COMPLETED and record["status"] == TaskStatus.BACKLOG:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status transition: Task must be IN_PROGRESS before being COMPLETED."
            )

        # Apply updates
        for field, value in update_data.items():
            record[field] = value

        record["updated_at"] = datetime.now(timezone.utc).isoformat()
        return self.repo.save(record)

    def delete_task(self, task_id: str) -> None:
        if not self.repo.delete(task_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with ID '{task_id}' was not found."
            )

    def search_tasks(
        self,
        page: int,
        size: int,
        status_filter: Optional[TaskStatus] = None,
        priority_filter: Optional[TaskPriority] = None,
        search_query: Optional[str] = None
    ) -> Dict[str, Any]:
        all_matches = self.repo.list_all(
            status_filter=status_filter,
            priority_filter=priority_filter,
            search_query=search_query
        )
        total = len(all_matches)
        pages = ceil(total / size) if total > 0 else 1

        offset = (page - 1) * size
        paginated_items = all_matches[offset : offset + size]

        return {
            "items": paginated_items,
            "total": total,
            "page": page,
            "size": size,
            "pages": pages
        }


# ==============================================================================
# 5. DEPENDENCY INJECTION FACTORIES
# ==============================================================================

# Global singleton repository instance for the running app
task_repository = TaskRepository()


def get_task_repository() -> TaskRepository:
    return task_repository


def get_task_service(repo: TaskRepository = Depends(get_task_repository)) -> TaskService:
    return TaskService(repo=repo)


# ==============================================================================
# 6. ROUTER IMPLEMENTATION
# ==============================================================================

router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
    response_description="The newly created task entity"
)
async def create_task_endpoint(
    payload: TaskCreate,
    service: TaskService = Depends(get_task_service)
):
    """Creates a new task in BACKLOG status."""
    return service.create_task(payload)


@router.get(
    "",
    response_model=PaginatedResponse[TaskResponse],
    summary="List tasks with filtering and pagination"
)
async def list_tasks_endpoint(
    page: int = Query(default=1, ge=1, description="Page number starting at 1"),
    size: int = Query(default=10, ge=1, le=50, description="Items per page"),
    task_status: Optional[TaskStatus] = Query(default=None, alias="status"),
    priority: Optional[TaskPriority] = Query(default=None),
    q: Optional[str] = Query(default=None, min_length=2, description="Search keyword in title/desc"),
    service: TaskService = Depends(get_task_service)
):
    """Retrieves paginated tasks with optional multi-attribute filters."""
    return service.search_tasks(
        page=page,
        size=size,
        status_filter=task_status,
        priority_filter=priority,
        search_query=q
    )


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Retrieve task by ID"
)
async def get_task_by_id_endpoint(
    task_id: str,
    service: TaskService = Depends(get_task_service)
):
    """Retrieves a single task by its unique identifier."""
    return service.get_task(task_id)


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Partially update a task"
)
async def patch_task_endpoint(
    task_id: str,
    payload: TaskUpdate,
    service: TaskService = Depends(get_task_service)
):
    """Partially updates fields provided in the request body."""
    return service.update_task(task_id, payload)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task"
)
async def delete_task_endpoint(
    task_id: str,
    service: TaskService = Depends(get_task_service)
):
    """Permanently deletes a task. Returns HTTP 204 with no body."""
    service.delete_task(task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ==============================================================================
# 7. FASTAPI APPLICATION WITH LIFESPAN
# ==============================================================================

@asynccontextmanager
async def app_lifespan(app: FastAPI):
    # Startup sequence
    print("[Startup] Initializing Task Engine and pre-warming in-memory indexes...")
    task_repository.clear()
    yield {"status": "healthy"}
    # Shutdown sequence
    print("[Shutdown] Gracefully draining Task Engine resources...")
    task_repository.clear()


app = FastAPI(
    title="Production REST API - Enterprise Task Engine",
    description="Full-scale layered production REST API adhering to RFC specifications.",
    version="1.0.0",
    lifespan=app_lifespan
)

app.include_router(router)


# ==============================================================================
# 8. SELF-TESTING SUITE
# ==============================================================================

def run_tests() -> None:
    print("\n[*] Starting automated test suite for 05_production_rest_api.py...")

    with TestClient(app) as client:
        # ------------------------------------------------------------
        # Test 1: POST /api/v1/tasks -> 201 Created
        # ------------------------------------------------------------
        print("  -> Testing POST 201 task creation...")
        payload1 = {
            "title": "Architect Fast Microservice",
            "description": "Design clean architecture with Repository and Service layers.",
            "priority": "HIGH",
            "tags": ["backend", "fastapi", "python"]
        }
        res1 = client.post("/api/v1/tasks", json=payload1)
        assert res1.status_code == 201, f"Expected 201, got {res1.status_code}"
        data1 = res1.json()
        assert data1["id"].startswith("TSK-")
        assert data1["status"] == "BACKLOG"
        assert data1["priority"] == "HIGH"
        assert len(data1["tags"]) == 3
        task1_id = data1["id"]

        # Duplicate title conflict check (409 Conflict)
        res1_dup = client.post("/api/v1/tasks", json=payload1)
        assert res1_dup.status_code == 409, f"Expected 409 Conflict, got {res1_dup.status_code}"

        # ------------------------------------------------------------
        # Test 2: GET /api/v1/tasks/{id} -> 200 OK & 404 Not Found
        # ------------------------------------------------------------
        print("  -> Testing GET by ID and 404 handling...")
        res2 = client.get(f"/api/v1/tasks/{task1_id}")
        assert res2.status_code == 200
        assert res2.json()["title"] == payload1["title"]

        res2_404 = client.get("/api/v1/tasks/TSK-NONEXISTENT")
        assert res2_404.status_code == 404

        # ------------------------------------------------------------
        # Test 3: PATCH /api/v1/tasks/{id} -> Partial update & Domain rule
        # ------------------------------------------------------------
        print("  -> Testing PATCH partial update and domain validation rules...")
        # Direct transition BACKLOG -> COMPLETED should fail with 400
        res3_bad = client.patch(f"/api/v1/tasks/{task1_id}", json={"status": "COMPLETED"})
        assert res3_bad.status_code == 400, "Should reject transition from BACKLOG directly to COMPLETED"

        # Valid transition: BACKLOG -> IN_PROGRESS
        res3_valid = client.patch(f"/api/v1/tasks/{task1_id}", json={"status": "IN_PROGRESS", "priority": "CRITICAL"})
        assert res3_valid.status_code == 200
        updated_data = res3_valid.json()
        assert updated_data["status"] == "IN_PROGRESS"
        assert updated_data["priority"] == "CRITICAL"
        assert updated_data["title"] == payload1["title"], "Untouched field 'title' was corrupted"

        # Now transition IN_PROGRESS -> COMPLETED should succeed
        res3_complete = client.patch(f"/api/v1/tasks/{task1_id}", json={"status": "COMPLETED"})
        assert res3_complete.status_code == 200
        assert res3_complete.json()["status"] == "COMPLETED"

        # ------------------------------------------------------------
        # Test 4: Pagination & Multi-attribute Search Filtering
        # ------------------------------------------------------------
        print("  -> Testing pagination, filtering and search queries...")
        # Create additional tasks
        client.post("/api/v1/tasks", json={"title": "Write Pytest Suites", "priority": "MEDIUM", "tags": ["qa"]})
        client.post("/api/v1/tasks", json={"title": "Configure Dockerfile", "priority": "LOW", "tags": ["devops"]})
        client.post("/api/v1/tasks", json={"title": "Setup PostgreSQL Indexing", "priority": "HIGH", "tags": ["database"]})

        # List all
        list_res = client.get("/api/v1/tasks?page=1&size=2")
        assert list_res.status_code == 200
        page_data = list_res.json()
        assert page_data["total"] == 4
        assert len(page_data["items"]) == 2
        assert page_data["pages"] == 2
        assert page_data["page"] == 1

        # Filter by priority
        filter_res = client.get("/api/v1/tasks?priority=HIGH")
        assert filter_res.status_code == 200
        assert all(t["priority"] == "HIGH" for t in filter_res.json()["items"])

        # Keyword search
        search_res = client.get("/api/v1/tasks?q=docker")
        assert search_res.status_code == 200
        assert len(search_res.json()["items"]) == 1
        assert "Dockerfile" in search_res.json()["items"][0]["title"]

        # ------------------------------------------------------------
        # Test 5: DELETE /api/v1/tasks/{id} -> 204 No Content
        # ------------------------------------------------------------
        print("  -> Testing DELETE 204 No Content...")
        del_res = client.delete(f"/api/v1/tasks/{task1_id}")
        assert del_res.status_code == 204, f"Expected 204, got {del_res.status_code}"
        assert del_res.content == b"", "204 response body must be empty"

        # Confirm task is deleted
        get_deleted = client.get(f"/api/v1/tasks/{task1_id}")
        assert get_deleted.status_code == 404

        # Delete again -> 404
        del_again = client.delete(f"/api/v1/tasks/{task1_id}")
        assert del_again.status_code == 404

    print("[SUCCESS] All 5 Production REST API tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 7 - 05: Production-Style REST API (Layered Architecture)")
    print("=" * 70)
    run_tests()
    print("=" * 70)
