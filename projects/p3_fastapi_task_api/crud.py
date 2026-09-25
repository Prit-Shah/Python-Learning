"""
Project P3: CRUD Operations & Repository Logic
"""
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from .models import TaskModel, TaskStatus
from .schemas import TaskCreate, TaskUpdate


class TaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, schema: TaskCreate) -> TaskModel:
        task = TaskModel(
            title=schema.title,
            description=schema.description,
            status=schema.status,
            priority=schema.priority,
        )
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def get_by_id(self, task_id: int) -> TaskModel | None:
        stmt = select(TaskModel).where(TaskModel.id == task_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_tasks(
        self,
        status: TaskStatus | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[TaskModel], int]:
        query = select(TaskModel)
        count_query = select(func.count(TaskModel.id))

        if status:
            query = query.where(TaskModel.status == status)
            count_query = count_query.where(TaskModel.status == status)

        query = query.order_by(TaskModel.created_at.desc()).offset(skip).limit(limit)

        total_res = await self.session.execute(count_query)
        total = total_res.scalar_one()

        items_res = await self.session.execute(query)
        items = list(items_res.scalars().all())

        return items, total

    async def update(self, task: TaskModel, schema: TaskUpdate) -> TaskModel:
        update_data = schema.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(task, key, value)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def delete(self, task: TaskModel) -> None:
        await self.session.delete(task)
        await self.session.commit()
