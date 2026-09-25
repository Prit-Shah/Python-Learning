"""
Automated Pytest Suite for Project P3: FastAPI Task API
"""
import pytest
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
from fastapi.testclient import TestClient
from ..app import app

client = TestClient(app)


def test_health_check():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "service": "task_api"}


def test_crud_lifecycle():
    # 1. Create Task
    create_payload = {
        "title": "Build Docker Image",
        "description": "Multi-stage build with non-root user",
        "priority": "high",
        "status": "todo",
    }
    res_create = client.post("/api/v1/tasks", json=create_payload)
    assert res_create.status_code == 201
    created = res_create.json()
    task_id = created["id"]
    assert created["title"] == create_payload["title"]
    assert created["priority"] == "high"
    assert created["status"] == "todo"

    # 2. Get Task by ID
    res_get = client.get(f"/api/v1/tasks/{task_id}")
    assert res_get.status_code == 200
    assert res_get.json()["id"] == task_id

    # 3. Update Task
    update_payload = {"status": "in_progress", "priority": "critical"}
    res_update = client.put(f"/api/v1/tasks/{task_id}", json=update_payload)
    assert res_update.status_code == 200
    updated = res_update.json()
    assert updated["status"] == "in_progress"
    assert updated["priority"] == "critical"

    # 4. List Tasks
    res_list = client.get("/api/v1/tasks?status=in_progress")
    assert res_list.status_code == 200
    data = res_list.json()
    assert data["total"] >= 1
    assert any(item["id"] == task_id for item in data["items"])

    # 5. Delete Task
    res_del = client.delete(f"/api/v1/tasks/{task_id}")
    assert res_del.status_code == 204

    # 6. Verify 404 after deletion
    res_404 = client.get(f"/api/v1/tasks/{task_id}")
    assert res_404.status_code == 404


def test_validation_errors():
    # Title too short (< 3 characters)
    bad_payload = {"title": "ab", "priority": "low"}
    resp = client.post("/api/v1/tasks", json=bad_payload)
    assert resp.status_code == 422  # Pydantic unprocessable entity
