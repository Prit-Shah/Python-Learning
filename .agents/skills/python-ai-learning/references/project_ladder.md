# 🧗‍♂️ Project Ladder Specifications (P1 — P7)

The project ladder contains 7 progressive projects. Build them in order to synthesize skills learned across phases.

---

### P1 — CLI Expense Tracker
- **Phase Target**: Python Fundamentals, Files, Modules, Exceptions (Phases 1–4).
- **Core Topics**: Dataclasses, `pathlib`, JSON storage, custom exceptions, CLI arguments (`argparse` or `click`).
- **Goal**: Create a command-line expense tracker that records, categorizes, and reports expenses stored in JSON/CSV.

---

### P2 — API Data Collector
- **Phase Target**: HTTP, Async, JSON, Retries, Logging (Phases 4–6).
- **Core Topics**: `httpx.AsyncClient`, `asyncio.gather`, `logging`, error retry decorators (`tenacity`), rate limiting.
- **Goal**: Build a concurrent data fetcher that consumes external REST APIs asynchronously, handles rate limits, logs failures, and saves structured results.

---

### P3 — FastAPI Task API
- **Phase Target**: Backend Python, REST, Pydantic, PostgreSQL, Testing (Phases 7–8).
- **Core Topics**: FastAPI application structure, Pydantic v2 validation models, SQLAlchemy 2.0 ORM, PostgreSQL database, Pytest with `TestClient`.
- **Goal**: Build a production-grade Task Management REST API with full CRUD endpoints, database migrations (Alembic), and automated tests.

---

### P4 — Production Backend
- **Phase Target**: Database, Redis, Background Workers, Docker, Auth (Phase 8).
- **Core Topics**: JWT authentication middleware, Redis caching layer, Arq/Celery background task queue, Docker & Docker Compose setup, structured logging with `structlog`.
- **Goal**: Upgrade P3 into a containerized production-ready backend with user auth, caching, and background document/email processing.

---

### P5 — ML Prediction API
- **Phase Target**: Data/AI Foundations + FastAPI (Phase 9).
- **Core Topics**: NumPy, Pandas data cleaning, scikit-learn dataset splitting & model training, model serialization (`joblib`), FastAPI prediction endpoint.
- **Goal**: Train a tabular classification or regression model, serialize it, and build a high-performance FastAPI endpoint that performs real-time model inference.

---

### P6 — RAG Document Chat
- **Phase Target**: LLM / AI Application Engineering (Phase 10).
- **Core Topics**: Text document ingestion & chunking, vector embeddings generation, vector database (`pgvector` or Qdrant), vector retrieval, context-augmented LLM generation.
- **Goal**: Build a Retrieval-Augmented Generation (RAG) system that ingests local markdown/PDF files and answers user questions grounded strictly in the document content.

---

### P7 — AI Knowledge Assistant
- **Phase Target**: AI Systems Architecture & Multi-Agent Platforms (Phase 11).
- **Core Topics**: RAG pipeline, custom tool/function execution loop (ReAct pattern), Server-Sent Events (SSE) streaming, async document ingestion queue, LLM response caching, token/cost tracking, tracing/observability (LangSmith/Phoenix).
- **Goal**: Build a production-scale AI Assistant with live response streaming, tool integration (search, calculations, document lookup), background document processing, and observability.
