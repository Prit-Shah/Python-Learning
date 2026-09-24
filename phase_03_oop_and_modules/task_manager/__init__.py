"""
Task Manager Package
--------------------
Demonstrates a production-style modular package with clean exports.
"""
from .models import Task, TaskPriority, TaskStatus
from .service import TaskService

__all__ = ["Task", "TaskPriority", "TaskStatus", "TaskService"]
