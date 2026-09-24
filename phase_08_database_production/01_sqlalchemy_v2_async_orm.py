"""
Phase 8: Database & Production Backend - SQLAlchemy 2.0 Async ORM & Data Access
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - SQLAlchemy 2.0 is the enterprise-grade SQL toolkit and Object Relational Mapper for Python.
   - Core 2.0 Architectural Patterns:
     * Declarative Base: Models inherit from 'DeclarativeBase' using 'Mapped[T]' and 'mapped_column()'.
     * Async Engine & Session: Created via 'create_async_engine()' and 'async_sessionmaker(..., class_=AsyncSession)'.
     * Unit of Work Pattern: 'AsyncSession' tracks dirty, pending, and deleted objects, flushing
       changes in an atomic transaction upon 'await session.commit()'.
     * Modern 2.0 Query Syntax: 'select(User).where(User.is_active == True).order_by(User.created_at.desc())'.
     * Relationships & Eager Loading:
       - 'relationship("Order", back_populates="user")'.
       - Eager loading using 'options(selectinload(User.orders))' to ELIMINATE the N+1 query problem!
     * FastAPI Dependency Injection:
       async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
           async with async_session_factory() as session:
               yield session
   - JS/TS Analogy:
     * Prisma / TypeORM / Drizzle ORM in Node.js vs SQLAlchemy 2.0 in Python.
     * Like Prisma schemas, SQLAlchemy 2.0 provides static type checking with Mypy via 'Mapped[int]'.

2. UNDER THE HOOD (CPython & Memory):
   - SQLAlchemy 2.0 async uses 'greenlet' under the hood to bridge asynchronous Python loops with
     PEP 249 database driver bindings.
   - Connection Pooling: 'QueuePool' maintains a pool of open persistent TCP database connections,
     reusing sockets across concurrent requests to avoid TCP/TLS handshake overhead.

3. COMMON GOTCHA:
   - THE ASYNC N+1 QUERY TRAP: In synchronous SQLAlchemy, accessing 'user.orders' would silently issue
     a secondary SQL query. In async SQLAlchemy, lazy loading raises 'sqlalchemy.exc.MissingGreenlet'
     because IO cannot happen implicitly! Always use 'selectinload()' or 'joinedload()' explicitly.

4. 🎙️ INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   -----------------------------------------------------------------------------
   Q: "How does SQLAlchemy 2.0 async ORM work, how does the Unit of Work pattern function,
       and how do you prevent the N+1 query problem in production?"
   
   HOW TO ANSWER OUT LOUD (60-90 sec script):
   1. SQLAlchemy 2.0 Typing & Async Engine:
      "SQLAlchemy 2.0 modernized Python data access by unifying query syntax with explicit 'select()'
       constructs and strict type hints via 'Mapped[T]' and 'mapped_column()'.
       In async applications (FastAPI/asyncpg), we instantiate an async engine with connection pooling
       and yield 'AsyncSession' objects per request via dependency injection."
   2. The Unit of Work Pattern:
      "The 'AsyncSession' acts as an in-memory Unit of Work and Identity Map:
       - It tracks every object instantiated or modified during the request.
       - Instead of issuing individual SQL UPDATE statements on every attribute change, it computes
         the diff and flushes all changes atomically inside a single database transaction upon commit."
   3. Preventing the N+1 Problem:
      "In async SQLAlchemy, lazy loading is disabled because implicit I/O inside attribute getters
       violates async principles and triggers a MissingGreenlet error.
       We solve this by explicitly declaring eager loading strategies in our queries—specifically using
       'selectinload()' for one-to-many relationships (which performs two optimized queries using SQL IN clauses)
       or 'joinedload()' for many-to-one relationships (which performs a SQL JOIN)."
================================================================================
"""

import sys
import asyncio
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Float, ForeignKey, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, selectinload
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)

    orders: Mapped[List["Order"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")

    user: Mapped["User"] = relationship(back_populates="orders")

    def __repr__(self) -> str:
        return f"<Order(id={self.id}, amount=${self.total_amount:.2f}, status='{self.status}')>"


DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def demonstrate_async_orm_crud():
    print("\n--- 1. Asynchronous CRUD & Atomic Transactions ---")
    await init_models()

    async with async_session_factory() as session:
        user_alice = User(username="alice_architect", email="alice@ai-systems.io")
        user_bob = User(username="bob_backend", email="bob@cloud.io")
        
        session.add_all([user_alice, user_bob])
        await session.commit()
        print(f"  Created Users: {user_alice}, {user_bob}")

        order1 = Order(user_id=user_alice.id, total_amount=149.99, status="PAID")
        order2 = Order(user_id=user_alice.id, total_amount=49.50, status="SHIPPED")
        order3 = Order(user_id=user_bob.id, total_amount=299.00, status="PENDING")
        
        session.add_all([order1, order2, order3])
        await session.commit()
        print(f"  Created 3 Orders successfully.")


async def demonstrate_eager_loading_and_n_plus_one():
    print("\n--- 2. Eager Loading with selectinload (Preventing N+1) ---")
    async with async_session_factory() as session:
        stmt = (
            select(User)
            .where(User.username == "alice_architect")
            .options(selectinload(User.orders))
        )
        result = await session.execute(stmt)
        user = result.scalar_one()

        print(f"  Fetched User: {user.username}")
        print(f"  Associated Orders (Eagerly Loaded):")
        for ord in user.orders:
            print(f"    * Order #{ord.id}: ${ord.total_amount:.2f} [{ord.status}]")


async def run_challenges():
    print("\n[*] Running automated tests for 01_sqlalchemy_v2_async_orm.py...")
    async with async_session_factory() as session:
        stmt = select(Order).where(Order.status == "PAID")
        paid_orders = (await session.scalars(stmt)).all()
        assert len(paid_orders) == 1
        assert paid_orders[0].total_amount == 149.99

        user_bob = (await session.scalars(select(User).where(User.username == "bob_backend"))).one()
        await session.delete(user_bob)
        await session.commit()

        bob_orders = (await session.scalars(select(Order).where(Order.user_id == user_bob.id))).all()
        assert len(bob_orders) == 0, "Orders must be cascade deleted with user!"

    print("[SUCCESS] All SQLAlchemy 2.0 Async ORM tests passed cleanly!")


async def main():
    print("=" * 65)
    print("Execution: Phase 8 - SQLAlchemy 2.0 Async ORM & Data Access")
    print("=" * 65)
    await demonstrate_async_orm_crud()
    await demonstrate_eager_loading_and_n_plus_one()
    print("-" * 65)
    await run_challenges()
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())
