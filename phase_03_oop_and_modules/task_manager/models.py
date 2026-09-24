"""
Data models for the Task Manager application.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class TaskPriority(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class TaskStatus(Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


@dataclass
class Task:
    """Task entity representing a unit of work."""
    task_id: int
    title: str
    description: str = ""
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)

    def mark_completed(self) -> None:
        self.status = TaskStatus.COMPLETED

    def __str__(self) -> str:
        return f"[{self.status.value}] #{self.task_id}: {self.title} ({self.priority.value})"
