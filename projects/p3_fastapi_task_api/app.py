"""
Project P3: FastAPI Application & REST Routers
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from .database import engine, Base, get_db_session
from .models import TaskStatus
from .schemas import TaskCreate, TaskUpdate, TaskResponse, TaskListResponse
from .crud import TaskRepository


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database schema
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="P3: Task Management REST API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/healthz", tags=["System"])
async def health_check():
    return {"status": "ok", "service": "task_api"}


@app.post("/api/v1/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED, tags=["Tasks"])
async def create_task(
    payload: TaskCreate,
    session: AsyncSession = Depends(get_db_session),
):
    repo = TaskRepository(session)
    return await repo.create(payload)


@app.get("/api/v1/tasks", response_model=TaskListResponse, tags=["Tasks"])
async def list_tasks(
    status_filter: TaskStatus | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
):
    repo = TaskRepository(session)
    skip = (page - 1) * page_size
    items, total = await repo.list_tasks(status=status_filter, skip=skip, limit=page_size)
    return TaskListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@app.get("/api/v1/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"])
async def get_task(
    task_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    repo = TaskRepository(session)
    task = await repo.get_by_id(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task #{task_id} not found",
        )
    return task


@app.put("/api/v1/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"])
async def update_task(
    task_id: int,
    payload: TaskUpdate,
    session: AsyncSession = Depends(get_db_session),
):
    repo = TaskRepository(session)
    task = await repo.get_by_id(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task #{task_id} not found",
        )
    return await repo.update(task, payload)


@app.delete("/api/v1/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Tasks"])
async def delete_task(
    task_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    repo = TaskRepository(session)
    task = await repo.get_by_id(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task #{task_id} not found",
        )
    await repo.delete(task)
