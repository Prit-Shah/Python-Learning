"""
Business logic service for managing tasks.
"""
from typing import List, Optional
from .models import Task, TaskPriority, TaskStatus


class TaskService:
    """Encapsulates task repository and business rules."""

    def __init__(self):
        self._tasks: dict[int, Task] = {}
        self._next_id: int = 1

    def create_task(self, title: str, description: str = "", priority: TaskPriority = TaskPriority.MEDIUM) -> Task:
        if not title.strip():
            raise ValueError("Task title cannot be empty.")
        
        task = Task(
            task_id=self._next_id,
            title=title.strip(),
            description=description.strip(),
            priority=priority,
            status=TaskStatus.PENDING
        )
        self._tasks[task.task_id] = task
        self._next_id += 1
        return task

    def get_task(self, task_id: int) -> Optional[Task]:
        return self._tasks.get(task_id)

    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[Task]:
        if status is None:
            return list(self._tasks.values())
        return [t for t in self._tasks.values() if t.status == status]

    def complete_task(self, task_id: int) -> bool:
        task = self.get_task(task_id)
        if not task:
            return False
        task.mark_completed()
        return True

    def __len__(self) -> int:
        return len(self._tasks)
