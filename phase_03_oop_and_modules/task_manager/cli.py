"""
CLI Entrypoint for the Task Manager package.
Executable demonstration of modules + classes working together.
"""
import sys

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from task_manager.models import TaskPriority, TaskStatus
from task_manager.service import TaskService


def run_cli_demo():
    print("=" * 65)
    print("Task Manager CLI Demo (Phase 3 Mini Application)")
    print("=" * 65)
    
    service = TaskService()
    
    # 1. Create sample tasks
    t1 = service.create_task("Learn CPython Memory Model", "Read PyObject and refcounting", TaskPriority.HIGH)
    t2 = service.create_task("Build FastAPI REST API", "Pydantic and async routing", TaskPriority.MEDIUM)
    t3 = service.create_task("Explore RAG with pgvector", "Embeddings and vector search", TaskPriority.HIGH)
    
    print(f"\nCreated {len(service)} tasks:")
    for task in service.list_tasks():
        print(f"  {task}")
    
    # 2. Complete task
    print(f"\nCompleting task #{t1.task_id}...")
    service.complete_task(t1.task_id)
    
    # 3. Filter pending tasks
    print("\nPending tasks only:")
    for task in service.list_tasks(status=TaskStatus.PENDING):
        print(f"  {task}")
        
    print("=" * 65)


def run_tests():
    print("\n[*] Running automated tests for task_manager package...")
    service = TaskService()
    t = service.create_task("Test task", "Desc", TaskPriority.LOW)
    assert t.task_id == 1
    assert t.status == TaskStatus.PENDING
    
    success = service.complete_task(1)
    assert success is True
    assert t.status == TaskStatus.COMPLETED
    assert len(service.list_tasks(status=TaskStatus.PENDING)) == 0
    assert len(service.list_tasks(status=TaskStatus.COMPLETED)) == 1
    print("[SUCCESS] All task_manager package tests passed!")


if __name__ == "__main__":
    run_cli_demo()
    run_tests()
