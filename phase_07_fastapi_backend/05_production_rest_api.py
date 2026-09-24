"""
Phase 7: Backend with FastAPI - Production-Style REST API (Project P3 Precursor)
================================================================================
1. PRODUCTION ARCHITECTURE:
   - Complete, multi-layered RESTful service demonstrating:
     * Pydantic v2 Models: TaskCreate, TaskUpdate, TaskResponse.
     * Service / Repository layer pattern separating business logic from HTTP transport.
     * Full CRUD operations:
       - POST   /api/v1/tasks       (Create task, returns 201 Created)
       - GET    /api/v1/tasks       (List tasks with pagination & status filtering)
       - GET    /api/v1/tasks/{id}  (Get task by ID, returns 404 if missing)
       - PUT    /api/v1/tasks/{id}  (Update task, returns updated entity)
       - DELETE /api/v1/tasks/{id}  (Delete task, returns 204 No Content)
     * Comprehensive TestClient integration test suite validating all HTTP status codes.
================================================================================
"""

import sys
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
from enum import Enum
from typing import List, Optional
from datetime import datetime
from fastapi import FastAPI, APIRouter, HTTPException, status, Query
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ==============================================================================
# 1. DOMAIN SCHEMAS
# ==============================================================================

class TaskPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    priority: TaskPriority = TaskPriority.MEDIUM


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None


class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    priority: TaskPriority
    status: TaskStatus
    created_at: str


# ==============================================================================
# 2. IN-MEMORY SERVICE / REPOSITORY LAYER
# ==============================================================================

class TaskRepository:
    def __init__(self):
        self._tasks: dict[int, dict] = {}
        self._next_id: int = 1

    def create(self, payload: TaskCreate) -> dict:
        task_id = self._next_id
        self._next_id += 1
        record = {
            "id": task_id,
            "title": payload.title,
            "description": payload.description,
            "priority": payload.priority,
            "status": TaskStatus.PENDING,
            "created_at": datetime.now().isoformat()
        }
        self._tasks[task_id] = record
        return record

    def get(self, task_id: int) -> Optional[dict]:
        return self._tasks.get(task_id)

    def list_all(self, status_filter: Optional[TaskStatus] = None) -> List[dict]:
        items = list(self._tasks.values())
        if status_filter:
            items = [t for t in items if t["status"] == status_filter]
        return items

    def update(self, task_id: int, payload: TaskUpdate) -> Optional[dict]:
        record = self.get(task_id)
        if not record:
            return None
        
        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            record[key] = value
        return record

    def delete(self, task_id: int) -> bool:
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False


repo = TaskRepository()

# ==============================================================================
# 3. ROUTER DEFINITION
# ==============================================================================

router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_new_task(payload: TaskCreate):
    return repo.create(payload)


@router.get("", response_model=List[TaskResponse])
async def get_tasks(
    status_filter: Optional[TaskStatus] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50)
):
    tasks = repo.list_all(status_filter=status_filter)
    return tasks[skip : skip + limit]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_by_id(task_id: int):
    task = repo.get(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task {task_id} not found.")
    return task


@router.put("/{task_id}", response_model=TaskResponse)
async def update_existing_task(task_id: int, payload: TaskUpdate):
    updated = repo.update(task_id, payload)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task {task_id} not found.")
    return updated


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int):
    success = repo.delete(task_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task {task_id} not found.")
    return None


app = FastAPI(title="Production Task REST API")
app.include_router(router)


# ==============================================================================
# SELF-TEST CHALLENGES
# ==============================================================================

def run_tests():
    print("\n[*] Running automated tests for 05_production_rest_api.py...")
    with TestClient(app) as client:
        # 1. Create a task
        create_res = client.post("/api/v1/tasks", json={"title": "Master FastAPI", "priority": "HIGH"})
        assert create_res.status_code == 201
        task_id = create_res.json()["id"]
        assert create_res.json()["status"] == "PENDING"

        # 2. Get task by ID
        get_res = client.get(f"/api/v1/tasks/{task_id}")
        assert get_res.status_code == 200
        assert get_res.json()["title"] == "Master FastAPI"

        # 3. Update task status to COMPLETED
        update_res = client.put(f"/api/v1/tasks/{task_id}", json={"status": "COMPLETED"})
        assert update_res.status_code == 200
        assert update_res.json()["status"] == "COMPLETED"

        # 4. Filter by status
        list_res = client.get("/api/v1/tasks?status=COMPLETED")
        assert list_res.status_code == 200
        assert len(list_res.json()) >= 1

        # 5. Delete task
        del_res = client.delete(f"/api/v1/tasks/{task_id}")
        assert del_res.status_code == 204

        # 6. Verify 404 after deletion
        get_again = client.get(f"/api/v1/tasks/{task_id}")
        assert get_again.status_code == 404

    print("[SUCCESS] All Production REST API CRUD tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 65)
    print("Execution: Phase 7 - Production REST API (P3 Precursor)")
    print("=" * 65)
    run_tests()
    print("=" * 65)
