"""
01_sqlalchemy_v2_async_orm.py

============================================================
1. CONCEPT
============================================================

SQLAlchemy 2.0 represents the industry standard Object-Relational Mapping (ORM) and
SQL abstraction engine for Python enterprise services. Version 2.0 fundamentally
modernized Python database architecture by introducing strict typing and native async:

1. Declarative Base with Modern Typing (`Mapped[T]` & `mapped_column()`):
   - Replaces legacy untyped `Column(String)` syntax with Python 3.10+ PEP 484 annotations:
     ```python
     class User(DeclarativeBase):
         __tablename__ = "users"
         id: Mapped[int] = mapped_column(primary_key=True)
         email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
         is_active: Mapped[bool] = mapped_column(default=True)
     ```
   - Static type checkers (Mypy/Pyright) and IDEs gain immediate compile-time type safety.

2. Modern 2.0 Query Construction (`select()`):
   - Deprecates legacy 1.x `session.query(User)` in favor of explicit SQL expressions:
     ```python
     stmt = select(User).where(User.is_active.is_(True)).order_by(User.id.desc())
     result = await session.scalars(stmt)
     users = result.all()
     ```

3. The Unit of Work Pattern & Identity Map:
   - The `AsyncSession` acts as a transactional boundary and an in-memory Identity Map.
   - It tracks object states:
     * Transient: Newly created object, not attached to session.
     * Pending: Added to session via `session.add()`, not yet written to DB.
     * Persistent: Saved in DB and tracked in identity map.
     * Detached: Previously persistent, now disconnected from session.
   - Computes state diffs and flushes all modifications atomically within a single SQL transaction
     upon `await session.commit()`.

4. Eager Loading Strategies (Eliminating N+1 Queries):
   - Async SQLAlchemy strictly disallows implicit synchronous lazy loading (which would block
     the event loop).
   - `selectinload`: Emits 2 optimized SQL queries using an `IN (...)` clause. Mandatory for
     collections and 1-to-many relationships.
   - `joinedload`: Emits a single SQL query using `LEFT OUTER JOIN`. Ideal for scalar, 1-to-1,
     and many-to-one parent relationships.

5. Async Engine & Connection Pool (`QueuePool`):
   - Created with `create_async_engine("sqlite+aiosqlite:///:memory:")` or `postgresql+asyncpg://...`.
   - Maintains a pool of reusable TCP socket connections, preventing handshake overhead.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python (SQLAlchemy 2.0)            | JavaScript / TypeScript (Prisma/Drizzle)|
+------------------------------+------------------------------------+------------------------------------+
| Schema Definition            | `class User(Base): Mapped[str]`    | Prisma schema file / Drizzle table |
| Type Safety                  | Native PEP 484 / Mypy inference    | TypeScript compiler AST inference  |
| Query Builder                | `select(User).where(...)`          | `db.select().from(users).where(..)`|
| Change Tracking              | Unit of Work (automatic diffing)   | Explicit `prisma.user.update(...)` |
| Identity Map                 | Built-in (`session.get` returns is)| None (new JS object instantiated)  |
| Eager Loading                | `options(selectinload(User.orders))`| `include: { orders: true }`        |
| Async Driver                 | `aiosqlite` / `asyncpg`            | `pg` / `@prisma/client`            |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Architecture Differences:
1. Prisma and Drizzle generate TypeScript interfaces from schema definitions or SQL migrations via
   a codegen step (`prisma generate`). SQLAlchemy 2.0 operates directly on native Python classes
   using runtime descriptor protocols and Python type hints, with zero codegen required.
2. In Prisma, updating an entity requires an explicit call to `prisma.user.update({ where, data })`.
   In SQLAlchemy, you simply mutate Python object attributes (`user.email = "new@mail.com"`).
   When `session.commit()` is called, the Unit of Work automatically generates minimal SQL UPDATE
   statements for only the dirty columns.


============================================================
3. UNDER THE HOOD (CPython & Async Engine Mechanics)
============================================================

1. The Greenlet Bridge:
   - Python's standard DBAPI (PEP 249) was architected synchronously decades ago.
   - SQLAlchemy's async extension (`create_async_engine`) uses `greenlet` (a lightweight micro-thread
     extension for CPython).
   - When an async query executes, SQLAlchemy enters a greenlet context, runs the synchronous core
     compiler, and safely yields control back to the `asyncio` event loop whenever socket I/O is awaited.

2. Why `expire_on_commit=False` is Mandatory in Async:
   - In legacy sync SQLAlchemy, `session.commit()` expires all attributes on tracked objects, meaning
     the next attribute read triggers a background `SELECT` lazy load.
   - In async Python, background I/O cannot happen implicitly during attribute access (`obj.name`)
     because attribute access is synchronous and cannot be `await`ed!
   - Setting `expire_on_commit=False` in `async_sessionmaker` keeps object attributes populated in
     memory after commit, preventing `sqlalchemy.exc.MissingGreenlet` crashes.

3. The Identity Map:
   - The session maintains a Python dictionary mapping `(ModelClass, primary_key_value) -> object_instance`.
   - If you query the same database row multiple times within one session, SQLAlchemy returns the EXACT
     same in-memory Python object: `user1 is user2` is `True`. This eliminates data duplication and
     inconsistency within a single request.


============================================================
4. COMMON GOTCHAS
============================================================

1. `sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called`:
   - Occurs when accessing a relationship attribute (e.g. `user.orders`) that was not eagerly loaded.
   - FIX: Always explicitly attach `.options(selectinload(User.orders))` or `.options(joinedload(User.profile))`
     to your `select()` statement.

2. Dangling Uncommitted Transactions & Connection Starvation:
   - Leaving an async session open without calling `commit()` or `rollback()` holds database connection
     locks in the pool. Under high traffic, the connection pool (`QueuePool`) exhausts all connections,
     causing request timeouts across the entire service.
   - FIX: Always use `async with async_session_factory() as session:` context managers.

3. Using Sync SQLite Driver (`sqlite:///`) in Async Code:
   - Passing `sqlite:///` instead of `sqlite+aiosqlite:///` attempts to run synchronous I/O on the
     asyncio thread, blocking all concurrent HTTP requests.
   - FIX: Always verify database driver prefixes (`sqlite+aiosqlite`, `postgresql+asyncpg`).


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "Explain how the Unit of Work pattern operates in SQLAlchemy 2.0."
A1: "The Unit of Work pattern, implemented by SQLAlchemy's `AsyncSession`, acts as a transaction
     manager and change tracker. As you modify model attributes, add entities, or mark records for
     deletion during a request, the session records these mutations in an in-memory Identity Map.
     Instead of firing immediate individual SQL statements, the session waits until `session.flush()`
     or `session.commit()` is called. At that point, it topologically sorts dependencies, batches
     operations, generates optimized SQL statements, and executes them atomically within a single
     database transaction. This minimizes network round-trips and guarantees data consistency."

Q2: "What is the N+1 query problem, and how do you resolve it in SQLAlchemy 2.0 async?"
A2: "The N+1 problem occurs when fetching N parent records and then querying each parent's child
     records in individual queries, resulting in 1 initial query plus N secondary queries. In async
     SQLAlchemy, lazy loading is disabled and throws `MissingGreenlet` to prevent accidental event loop
     blocking. We eliminate N+1 queries by using explicit eager loading options: `selectinload()` for
     one-to-many collections (which issues 2 queries: one for parents, and one with `WHERE parent_id IN (...)`),
     or `joinedload()` for one-to-one and many-to-one relationships (which joins the child table in
     a single SQL statement)."

Q3: "Why is `expire_on_commit=False` standard in FastAPI async session factories?"
A3: "By default, SQLAlchemy expires object attributes upon commit so the next read fetches fresh data
     from the database. However, in an async architecture, accessing an expired attribute outside the
     active session context triggers implicit lazy loading. Because Python attribute access is synchronous,
     it cannot await the event loop, causing a `MissingGreenlet` exception. Setting `expire_on_commit=False`
     retains the cached attribute values in memory after commit, allowing FastAPI routes to serialize
     models into Pydantic responses safely without triggering secondary queries."
"""

import sys
import asyncio
import warnings
warnings.filterwarnings("ignore")
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import String, Float, ForeignKey, Integer, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, selectinload, joinedload
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ==============================================================================
# 1. DECLARATIVE BASE & DOMAIN MODELS
# ==============================================================================

class Base(DeclarativeBase):
    pass


class Profile(Base):
    """1-to-1 Relationship with User."""
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    bio: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    reputation_score: Mapped[int] = mapped_column(Integer, default=100)

    user: Mapped["User"] = relationship(back_populates="profile")

    def __repr__(self) -> str:
        return f"<Profile(id={self.id}, user_id={self.user_id}, score={self.reputation_score})>"


class Order(Base):
    """1-to-Many Relationship with User."""
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship(back_populates="orders")

    def __repr__(self) -> str:
        return f"<Order(id={self.id}, amount=${self.total_amount:.2f}, status='{self.status}')>"


class User(Base):
    """Core User entity demonstrating 1-to-1 and 1-to-many associations."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    # 1-to-1 relationship
    profile: Mapped[Optional[Profile]] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )

    # 1-to-many relationship
    orders: Mapped[List[Order]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="Order.id"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', active={self.is_active})>"


# ==============================================================================
# 2. ASYNC ENGINE & SESSION FACTORY SETUP
# ==============================================================================

# In-memory async SQLite engine
DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True
)

# Async sessionmaker with expire_on_commit=False to prevent MissingGreenlet
async_session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession
)


async def init_db() -> None:
    """Creates database tables asynchronously."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ==============================================================================
# 3. SELF-TESTING SUITE
# ==============================================================================

async def run_tests() -> None:
    print("\n[*] Starting automated test suite for 01_sqlalchemy_v2_async_orm.py...")
    await init_db()

    # ------------------------------------------------------------
    # Test 1: Unit of Work, Identity Map & Transactions
    # ------------------------------------------------------------
    print("  -> Testing Unit of Work and Identity Map caching...")
    async with async_session_factory() as session:
        # Create users
        alice = User(username="alice_arch", email="alice@ai-systems.io")
        bob = User(username="bob_cloud", email="bob@systems.io")
        session.add_all([alice, bob])
        await session.commit()

        # Verify identity map: Fetching the same row returns the exact same object
        fetched_1 = await session.get(User, alice.id)
        fetched_2 = await session.get(User, alice.id)
        assert fetched_1 is fetched_2, "Identity Map violation: Expected identical Python object instance"
        assert fetched_1.username == "alice_arch"

        # Update entity attribute (Unit of Work change tracking)
        alice.username = "alice_lead_architect"
        await session.commit()

    # Verify changes persisted across separate session
    async with async_session_factory() as session:
        refreshed = await session.get(User, alice.id)
        assert refreshed is not None
        assert refreshed.username == "alice_lead_architect"

    # ------------------------------------------------------------
    # Test 2: Relationships (1-to-1 and 1-to-Many Creation)
    # ------------------------------------------------------------
    print("  -> Testing 1-to-1 and 1-to-many relationship creation...")
    async with async_session_factory() as session:
        user = (await session.scalars(select(User).where(User.username == "alice_lead_architect"))).one()
        
        # Attach 1-to-1 profile
        user.profile = Profile(bio="Specializing in scalable distributed systems", reputation_score=250)

        # Attach 1-to-many orders
        order1 = Order(total_amount=150.00, status="PAID", user=user)
        order2 = Order(total_amount=320.50, status="SHIPPED", user=user)
        order3 = Order(total_amount=45.00, status="PENDING", user=user)
        session.add_all([order1, order2, order3])

        await session.commit()

    # ------------------------------------------------------------
    # Test 3: Eager Loading with selectinload & joinedload (N+1 Elimination)
    # ------------------------------------------------------------
    print("  -> Testing eager loading (selectinload & joinedload)...")
    async with async_session_factory() as session:
        stmt = (
            select(User)
            .where(User.username == "alice_lead_architect")
            .options(
                joinedload(User.profile),       # joinedload for 1-to-1
                selectinload(User.orders)       # selectinload for 1-to-many collection
            )
        )
        res = await session.execute(stmt)
        user_eager = res.scalar_one()

        # Access attributes without MissingGreenlet error
        assert user_eager.profile is not None
        assert user_eager.profile.reputation_score == 250
        assert len(user_eager.orders) == 3
        assert [o.status for o in user_eager.orders] == ["PAID", "SHIPPED", "PENDING"]

    # ------------------------------------------------------------
    # Test 4: Aggregation & Filtering Queries
    # ------------------------------------------------------------
    print("  -> Testing SQL aggregations and filtering...")
    async with async_session_factory() as session:
        # Sum total amount of all orders
        agg_stmt = select(func.count(Order.id), func.sum(Order.total_amount))
        count, total = (await session.execute(agg_stmt)).one()
        assert count == 3
        assert round(total, 2) == 515.50

        # Filter by status
        paid_stmt = select(Order).where(Order.status == "PAID")
        paid_orders = (await session.scalars(paid_stmt)).all()
        assert len(paid_orders) == 1
        assert paid_orders[0].total_amount == 150.00

    # ------------------------------------------------------------
    # Test 5: Cascade Deletion & Atomic Rollback
    # ------------------------------------------------------------
    print("  -> Testing cascade delete and transaction rollback...")
    async with async_session_factory() as session:
        # Delete user should cascade delete profile and orders
        u_delete = (await session.scalars(select(User).where(User.username == "alice_lead_architect"))).one()
        user_id = u_delete.id
        await session.delete(u_delete)
        await session.commit()

        # Verify child records are pruned
        orders_remaining = (await session.scalars(select(Order).where(Order.user_id == user_id))).all()
        assert len(orders_remaining) == 0, "Cascade delete failed for orders"

        profile_remaining = (await session.scalars(select(Profile).where(Profile.user_id == user_id))).first()
        assert profile_remaining is None, "Cascade delete failed for profile"

    # Test Transaction Rollback
    async with async_session_factory() as session:
        charlie = User(username="charlie_test", email="charlie@test.com")
        session.add(charlie)
        await session.flush()  # Generates ID without committing transaction
        assert charlie.id is not None

        # Rollback discards pending writes
        await session.rollback()

        # Ensure charlie was not persisted
        check_charlie = (await session.scalars(select(User).where(User.username == "charlie_test"))).first()
        assert check_charlie is None, "Transaction rollback failed to discard pending record"

    print("[SUCCESS] All 5 SQLAlchemy 2.0 Async ORM tests passed cleanly!")


async def main() -> None:
    print("=" * 70)
    print("Phase 8 - 01: SQLAlchemy 2.0 Async ORM & Production Data Access")
    print("=" * 70)
    await run_tests()
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
