"""
Project P3: Pydantic v2 Validation & Serialization Schemas
"""
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from .models import TaskStatus, TaskPriority


class TaskBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=200, examples=["Implement JWT auth"])
    description: str = Field(default="", max_length=2000)
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)


class TaskCreate(TaskBase):
    status: TaskStatus = Field(default=TaskStatus.TODO)


class TaskUpdate(BaseModel):
    title: str | None = Field(None, min_length=3, max_length=200)
    description: str | None = Field(None, max_length=2000)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None


class TaskResponse(TaskBase):
    id: int
    status: TaskStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int
    page: int
    page_size: int
