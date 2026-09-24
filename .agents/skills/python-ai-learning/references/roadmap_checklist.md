# 📋 Python → AI Engineer Roadmap Complete Checklist

This checklist contains all 80+ specific learning checklist items from the master roadmap PDF, categorized by Phase and Day schedule.

---

## Phase 0 — Setup (Day 1)
- [ ] Install Python 3.x and verify `python --version` / `python3 --version`.
- [ ] Set up VS Code with Python support.
- [ ] Learn terminal basics specifically for Python projects.
- [ ] Create a Git repository: `python-learning`.
- [ ] Learn virtual environments: `python -m venv .venv`.
- [ ] Understand `pip` and `requirements.txt`/`pyproject.toml` at a basic level.
- [ ] Run a simple `hello.py` and debug it in VS Code.

---

## Phase 1 — Python Fundamentals (Days 2–6)
- [ ] Variables and dynamic typing.
- [ ] Numbers: `int`, `float`, `complex`; arithmetic operators.
- [ ] Strings, slicing, indexing, f-strings.
- [ ] Boolean values and truthiness.
- [ ] `None` and `None` checks (`is None`).
- [ ] `if` / `elif` / `else`.
- [ ] `for` / `while`, `range()`, `break`, `continue`.
- [ ] Lists and common list methods.
- [ ] Tuples and when to use them.
- [ ] Sets and set operations.
- [ ] Dictionaries and nested dictionaries.
- [ ] List/set/dict comprehensions.
- [ ] Functions, return values, default arguments.
- [ ] `*args` and `**kwargs`.
- [ ] Lambda, `map`/`filter` basics; understand but do not overuse.
- [ ] Unpacking and multiple assignment.
- [ ] `match`/`case` basics (Python 3.10+ pattern matching).
- [ ] Write 20–30 small exercises without copying solutions.

---

## Phase 2 — Pythonic Python (Days 7–10)
- [ ] Mutable vs immutable objects.
- [ ] `==` (value equality) vs `is` (identity equality).
- [ ] References and object identity (`id()`).
- [ ] Shallow copy (`copy.copy`) vs deep copy (`copy.deepcopy`).
- [ ] LEGB scope (Local, Enclosing, Global, Built-in) and closures.
- [ ] Iterables, iterators, generators, `yield`.
- [ ] Generator expressions.
- [ ] `enumerate()`, `zip()`, `sorted()`, `any()`, `all()`.
- [ ] Context managers and `with` statements.
- [ ] Decorators: understand how `@decorator` wrapper functions work.
- [ ] `dataclasses` (`@dataclass`).
- [ ] Type hints: `list[str]`, `dict[str, int]`, `Optional`, `Union`.
- [ ] Modern typing: `TypedDict`, `Protocol`, `TypeAlias` basics.
- [ ] Write clean Python instead of translating JavaScript line-by-line.

---

## Phase 3 — OOP + Real Application Code (Days 11–14)
- [ ] Classes and objects.
- [ ] `__init__`, instance methods, `@classmethod`, `@staticmethod`.
- [ ] Inheritance and composition.
- [ ] Properties (`@property`) and encapsulation conventions (`_protected`, `__private`).
- [ ] Dunder methods: `__str__`, `__repr__`, `__eq__` basics.
- [ ] Abstract base classes (`abc.ABC`, `@abstractmethod`) at a conceptual level.
- [ ] Dataclasses in real projects.
- [ ] Modules and packages.
- [ ] Imports, `__init__.py`, absolute vs relative imports.
- [ ] Circular-import problems and how to avoid them.
- [ ] Build a small CLI task manager using classes + modules.

---

## Phase 4 — Errors, Files, HTTP & Standard Library (Days 15–17)
- [ ] `try` / `except` / `else` / `finally`.
- [ ] Built-in exceptions and custom exception classes.
- [ ] `raise` and exception chaining (`raise ... from err`).
- [ ] Logging with standard `logging` module.
- [ ] Read/write text and JSON files.
- [ ] `pathlib` (`Path`) for filesystem work.
- [ ] Environment variables (`os.environ`, `python-dotenv`) and configuration.
- [ ] `datetime` and timezone-aware dates (`zoneinfo`).
- [ ] Regular expressions basics (`re` module).
- [ ] HTTP requests with `requests` or `httpx`.
- [ ] JSON serialization/deserialization (`json.dumps`, `json.loads`).
- [ ] Build a script that calls a public API, validates the response, logs failures, and saves results.

---

## Phase 5 — Professional Python Tooling (Days 18–21)
- [ ] `pyproject.toml` concept.
- [ ] Package/dependency management.
- [ ] Virtual environments and reproducible installs.
- [ ] Understand `uv` at a practical level (fast package manager).
- [ ] Formatting/linting with Ruff.
- [ ] Type checking with `mypy` or `pyright` basics.
- [ ] Testing with `pytest`.
- [ ] Fixtures (`@pytest.fixture`) and parametrized tests (`@pytest.mark.parametrize`).
- [ ] Mocking external services (`unittest.mock`, `pytest-mock`).
- [ ] Code coverage concept (`pytest-cov`).
- [ ] Git hooks/CI concept (pre-commit, GitHub Actions).
- [ ] Create a clean repository with README, tests, linting, typing, and environment setup.

---

## Phase 6 — Async + Concurrency (Days 22–25)
- [ ] Why async exists: I/O-bound vs CPU-bound work.
- [ ] `async def` and `await`.
- [ ] Event loop concept.
- [ ] `asyncio` basics (`asyncio.run()`, `asyncio.create_task()`).
- [ ] `asyncio.gather()`.
- [ ] Timeouts and cancellation (`asyncio.wait_for`, `asyncio.TimeoutError`).
- [ ] Concurrent HTTP requests with `httpx.AsyncClient`.
- [ ] Threads vs processes vs asyncio (GIL implications).
- [ ] When async makes things faster—and when it does not.
- [ ] Build a concurrent API data collector.

---

## Phase 7 — Backend Python with FastAPI (Days 26–32)
- [ ] FastAPI application structure.
- [ ] Routes and HTTP methods (`GET`, `POST`, `PUT`, `DELETE`).
- [ ] Request/response models (`BaseModel`).
- [ ] Pydantic validation (field validation, custom validators).
- [ ] Dependency injection (`Depends`).
- [ ] Authentication concepts and JWT (`python-jose`, `passlib`).
- [ ] Middleware.
- [ ] Exception handlers (`@app.exception_handler`).
- [ ] OpenAPI/Swagger (`/docs`).
- [ ] Async endpoints and database calls.
- [ ] Pagination/filtering/sorting.
- [ ] Service/repository layering.
- [ ] Background tasks (`BackgroundTasks`).
- [ ] Testing FastAPI endpoints (`TestClient`, `httpx.AsyncClient`).
- [ ] Build a production-style REST API.

---

## Phase 8 — Database + Production Backend (Days 33–39)
- [ ] PostgreSQL fundamentals.
- [ ] SQL joins, indexes, transactions, constraints.
- [ ] Use SQLAlchemy (v2.0) or SQLModel.
- [ ] Migrations with Alembic (`alembic revision --autogenerate`, `alembic upgrade head`).
- [ ] Connection pooling.
- [ ] Redis basics (key-value storage, data types, TTL).
- [ ] Caching patterns (Cache-Aside, TTL invalidation).
- [ ] Queues/background workers concept.
- [ ] Celery/RQ/Arq concept; learn one enough to build with it.
- [ ] Dockerize the API (`Dockerfile`, `docker-compose.yml`).
- [ ] Environment-based configuration (`pydantic-settings`).
- [ ] Health checks (`/healthz`) and structured logging (`structlog`).
- [ ] Deploy a small API.

---

## Phase 9 — Data/AI Python Foundations (Days 40–48)
- [ ] NumPy arrays and vectorized operations.
- [ ] Pandas `DataFrame` / `Series`.
- [ ] CSV/JSON data processing.
- [ ] Data cleaning and transformations (`fillna`, `apply`, `groupby`).
- [ ] Basic statistics: mean, median, variance, distributions.
- [ ] Matplotlib basics (plotting lines, bars, histograms).
- [ ] scikit-learn workflow: dataset → split (`train_test_split`) → train (`fit`) → evaluate (`score`, `metrics`) → predict (`predict`).
- [ ] Regression vs classification.
- [ ] Overfitting/underfitting.
- [ ] Feature engineering basics.
- [ ] Model evaluation metrics (MSE, R2, Accuracy, Precision, Recall, F1).
- [ ] Build one small prediction project and expose it through FastAPI.

---

## Phase 10 — LLM / AI Application Engineering (Days 49–60)
- [ ] LLM fundamentals: tokens, context window, temperature, top_p, structured output.
- [ ] Prompt design and system/user messages.
- [ ] Calling model APIs from Python (OpenAI / Anthropic / Gemini SDKs).
- [ ] Streaming responses (`stream=True`, SSE).
- [ ] Embeddings and vector similarity (cosine similarity, Euclidean distance).
- [ ] Vector databases: understand `pgvector` and one dedicated vector DB (Qdrant/Chroma/Weaviate).
- [ ] RAG: ingestion → chunking → embedding → retrieval → prompt → generation.
- [ ] Metadata filtering and hybrid search concepts (BM25 + vector search).
- [ ] Tool/function calling (defining tools with Pydantic schemas).
- [ ] Structured outputs and schema validation (`response_format`).
- [ ] Conversation memory patterns (window memory, summary memory).
- [ ] Evaluation: correctness, relevance, latency, cost.
- [ ] Prompt injection and basic AI security.
- [ ] Build a RAG application over your own documents.

---

## Phase 11 — AI Systems Architecture (Days 61–70)
- [ ] Understand an AI request end-to-end: frontend → API → auth → orchestration → model → tools/data → response.
- [ ] Model gateway/provider abstraction (LiteLLM / custom gateway pattern).
- [ ] Streaming architecture with SSE/WebSockets.
- [ ] Async jobs and long-running AI tasks.
- [ ] Caching LLM responses (semantic caching) and embeddings.
- [ ] Rate limits, retries, timeouts and fallbacks (tenacity).
- [ ] Token/cost tracking.
- [ ] Observability and tracing (LangSmith / Phoenix / OpenTelemetry).
- [ ] RAG service architecture.
- [ ] Agent architecture and tool execution loops (ReAct pattern).
- [ ] Queues/workers for document ingestion.
- [ ] Object storage for documents (S3 / MinIO).
- [ ] Postgres + Redis + vector search architecture.
- [ ] Docker and cloud deployment patterns.
- [ ] Security boundaries and secrets management.
- [ ] Draw the architecture before coding it.
