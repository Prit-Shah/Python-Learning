# 🧗 Project P3: Production FastAPI Task Management API
> **Roadmap Target**: Synthesizes Modern Async REST, Pydantic v2, and SQLAlchemy 2.0 (Phases 7–8).

---

## 🏛️ Architecture & Component Design

```text
p3_fastapi_task_api/
├── database.py     # Async engine, sessionmaker, request-scoped get_db_session
├── models.py       # SQLAlchemy 2.0 ORM Mapped Declarative models
├── schemas.py      # Pydantic v2 Request/Response validation models
├── crud.py         # Repository pattern isolating SQL queries from HTTP routers
├── app.py          # FastAPI application, lifespan manager, and endpoint routes
└── tests/          # Pytest API integration suite using TestClient
```

---

## ⚡ Technical Highlights

1. **SQLAlchemy 2.0 Async ORM with Unit of Work**:
   Leverages `async_sessionmaker` and `aiosqlite`/`asyncpg` for non-blocking database queries without thread pool starvation.

2. **Pydantic v2 Core Validation**:
   Pre-validates incoming JSON payloads at C/Rust speed via Pydantic v2, eliminating manual type guards and returning structured 422 errors automatically.

3. **Clean Repository Layer**:
   Route handlers do not contain raw SQL statements. `TaskRepository` encapsulates query construction, pagination, and sorting.

---

## 🚀 Running the API

```bash
# Start Uvicorn live server
uvicorn projects.p3_fastapi_task_api.app:app --reload --port 8000

# Open interactive Swagger UI:
# http://127.0.0.1:8000/docs
```

---

## 🎙️ Senior Interview Script: Async Database Architecture

- **Interview Question**: *"Why use SQLAlchemy 2.0 Async ORM instead of synchronous ORMs in a FastAPI backend?"*
- **60-Second Verbal Answer Script**:
  * *"In a high-concurrency Node.js or FastAPI backend, endpoints spend 90% of their lifecycle waiting on I/O (database queries, Redis, external APIs)."*
  * *"If you use a synchronous ORM like Django ORM or old SQLAlchemy inside `async def` endpoints, the database driver blocks the single event loop thread, dropping throughput from 5,000 req/sec to under 50."*
  * *"SQLAlchemy 2.0 with async drivers like `asyncpg` or `aiosqlite` yields control back to the event loop during SQL network execution, allowing a single Python worker to interleave thousands of concurrent connections concurrently."*
