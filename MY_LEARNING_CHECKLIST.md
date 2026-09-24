# 🎓 My Personal Python -> AI Engineer Learning Progress
### (Track your study, practice drills, and interview mastery here)

> **Instructions**: Check off items (`[x]`) as you study each concept, run the self-test code, and can deliver the 60-second verbal answer without looking at notes!

---

## 📅 Target Pace: 60–90 min/day, 6 days/week
- [ ] **Core Python Mastery**: ~2–3 weeks (Phases 0–5)
- [ ] **Backend & Production Engineering**: ~3–4 weeks (Phases 6–8)
- [ ] **Data, ML & AI Systems Engineering**: ~4–6 weeks (Phases 9–11)

---

## Phase 0 — Setup & Environment (Day 1)
- [ ] Verified Python 3.13 installation (`python --version`)
- [ ] VS Code configured with Python extension & terminal
- [ ] Created and activated virtual environment (`.venv`)
- [ ] Understand `pip` vs `uv` and `pyproject.toml`
- [ ] Successfully ran & debugged a script in VS Code
- [ ] **Phase 0 Exit Gate**: Can set up a clean venv from scratch in under 2 minutes.

---

## Phase 1 — Python Fundamentals (Days 2–6)
- [ ] Dynamic typing & CPython object model (`PyObject`, names as pointers)
- [ ] Numbers (`int` arbitrary precision, `float`, `complex`, arithmetic)
- [ ] Strings: Slicing (`[start:stop:step]`), negative indexing, f-string expressions
- [ ] Boolean values & truthiness (Gotcha: empty `[]`, `{}` are falsy!)
- [ ] `None` and identity checks (`is None` vs `== None`)
- [ ] Control flow: `if` / `elif` / `else` (no block scope gotcha)
- [ ] Loops: `for` / `while`, `range()`, `break`, `continue`
- [ ] Lists: slicing, methods (`append`, `extend`, `pop`, `insert`)
- [ ] Tuples: immutability, tuple packing/unpacking, when to use
- [ ] Sets: set operations (`&`, `|`, `-`, `^`), `O(1)` membership lookups
- [ ] Dictionaries: hash maps, key restrictions (hashable), `.get()`, dict iteration
- [ ] Comprehensions: list, set, dict comprehensions vs `.map()/.filter()`
- [ ] Functions: return values, default arguments
- [ ] Mutable default argument trap (`def f(x=[])`)
- [ ] `*args` (positional tuple) and `**kwargs` (keyword dict)
- [ ] Lambdas (single-expression limitations vs JS arrow functions)
- [ ] Unpacking: starred assignment (`a, *rest, b = lst`), tuple swap (`a, b = b, a`)
- [ ] Structural pattern matching: `match` / `case` (Python 3.10+)
- [ ] Solved 20–30 small exercises without copying solutions
- [ ] **Phase 1 Interview Question**: Can explain `==` vs `is` and memory allocation in 60s verbally.
- [ ] **Phase 1 Exit Gate**: Wrote a data transformation function using comprehensions and unpacking from memory.

---

## Phase 2 — Pythonic Python (Days 7–10)
- [ ] Mutable vs immutable objects (memory addresses via `id()`)
- [ ] `==` (value equality via `__eq__`) vs `is` (identity equality)
- [ ] Small integer caching & string interning trap (-5 to 256)
- [ ] Shallow copy (`copy.copy`) vs deep copy (`copy.deepcopy`)
- [ ] LEGB scoping rule (Local, Enclosing, Global, Built-in)
- [ ] Closures and the `nonlocal` keyword
- [ ] Late-binding closure loop trap (`lambda: i`) and default-argument fix
- [ ] Iteration protocol: `__iter__` and `__next__`
- [ ] Generators with `yield` & lazy memory evaluation
- [ ] Generator expressions vs list comprehensions (single-pass exhaustion gotcha)
- [ ] Built-in helpers: `enumerate()`, `zip()`, `sorted(key=)`, `any()`, `all()`
- [ ] Context managers and the `with` statement (`__enter__` / `__exit__`)
- [ ] Decorator mechanics: `@decorator`, wrapper functions, `@functools.wraps`
- [ ] Dataclasses: `@dataclass`, `frozen=True`, `field()`
- [ ] Modern typing: `int | None`, `list[str]`, `TypedDict`, `Protocol` (static duck typing)
- [ ] **Phase 2 Interview Question**: Can explain the mutable default argument and how decorators work verbally.
- [ ] **Phase 2 Exit Gate**: Built a custom generator and a `@timing` decorator from memory.

---

## Phase 3 — OOP & Real Application Code (Days 11–14)
- [ ] Classes, instances, and the explicit `self` parameter
- [ ] `__init__`, instance methods, `@classmethod`, `@staticmethod`
- [ ] Inheritance vs Composition
- [ ] Encapsulation conventions (`_protected`, `__private` name mangling)
- [ ] Dunder methods: `__str__`, `__repr__`, `__eq__`, `__len__`, `__getitem__`
- [ ] Abstract Base Classes (`abc.ABC`, `@abstractmethod`)
- [ ] Dataclasses in real-world domain models
- [ ] Modules, packages, and `__init__.py`
- [ ] Absolute vs relative imports, avoiding circular imports
- [ ] **Phase 3 Project**: Built P1 (CLI Expense Tracker using classes + modules).

---

## Phase 4 — Errors, Files, HTTP & Standard Library (Days 15–17)
- [ ] `try` / `except` / `else` / `finally` execution flow
- [ ] Built-in exceptions and custom domain exception hierarchies
- [ ] `raise` and exception chaining (`raise CustomError from original_err`)
- [ ] Structured logging using the `logging` module
- [ ] Text & JSON file I/O with context managers
- [ ] Modern filesystem operations using `pathlib.Path`
- [ ] Environment variables (`os.environ`, `python-dotenv`)
- [ ] Dates and timezones (`datetime`, `zoneinfo`)
- [ ] Regular expressions (`re` module)
- [ ] HTTP requests with `httpx` (sync & async)
- [ ] **Phase 4 Project**: Public API scraper with validation, logging, and error retries.

---

## Phase 5 — Professional Tooling & Testing (Days 18–21)
- [ ] Modern packaging with `pyproject.toml`
- [ ] Package management with `uv`
- [ ] Linting & formatting with `ruff`
- [ ] Static type checking with `mypy` / `pyright`
- [ ] Testing with `pytest`
- [ ] Fixtures (`@pytest.fixture`) and parametrization (`@pytest.mark.parametrize`)
- [ ] Mocking external services (`unittest.mock`, `pytest-mock`)
- [ ] Test coverage measurement (`pytest-cov`)
- [ ] Git hooks & pre-commit configuration
- [ ] **Phase 5 Exit Gate**: Clean repo setup with passing tests, strict typing, and zero lint warnings.

---

## Phase 6 — Async & Concurrency (Days 22–25)
- [ ] I/O-bound vs CPU-bound computing
- [ ] Coroutines: `async def` and `await`
- [ ] Python Event Loop mechanics vs Node.js Event Loop
- [ ] `asyncio.run()`, `asyncio.create_task()`, `asyncio.gather()`
- [ ] Timeouts and task cancellation (`asyncio.wait_for`)
- [ ] Concurrent HTTP requests with `httpx.AsyncClient`
- [ ] Concurrency models: Asyncio vs Threads vs Multiprocessing (GIL deep dive)
- [ ] When async helps vs when it hurts
- [ ] **Phase 6 Project**: Built P2 (Concurrent API Data Collector).

---

## Phase 7 — Backend Python with FastAPI (Days 26–32)
- [ ] FastAPI application architecture & lifespan events
- [ ] Routing & HTTP verbs (`GET`, `POST`, `PUT`, `DELETE`)
- [ ] Request / Response models with Pydantic v2
- [ ] Advanced Pydantic validation (custom validators, field constraints)
- [ ] Dependency Injection system (`Depends`)
- [ ] JWT Authentication & password hashing (`passlib`, `python-jose`)
- [ ] Custom Middleware (request timing, CORS)
- [ ] Global exception handlers
- [ ] Interactive OpenAPI / Swagger documentation (`/docs`)
- [ ] Testing FastAPI endpoints with `httpx.AsyncClient` and `TestClient`
- [ ] **Phase 7 Project**: Built P3 (Production-style RESTful Task API).

---

## Phase 8 — Database & Production Backend (Days 33–39)
- [ ] PostgreSQL fundamentals (joins, indexing strategies, constraints, transactions)
- [ ] SQLAlchemy 2.0 async ORM / SQLModel
- [ ] Database migrations with Alembic (`autogenerate` & `upgrade head`)
- [ ] Connection pooling & session lifecycle management
- [ ] Redis caching patterns (Cache-Aside, TTL expiration)
- [ ] Asynchronous task queues (Celery / Arq / RQ)
- [ ] Docker containerization (`Dockerfile`, `docker-compose.yml`)
- [ ] Production environment settings (`pydantic-settings`)
- [ ] Health check endpoints (`/healthz`) & structured JSON logging (`structlog`)
- [ ] **Phase 8 Project**: Built P4 (Containerized production backend with Redis & background queue).

---

## Phase 9 — Data/AI Foundations (Days 40–48)
- [ ] NumPy ndarrays, broadcasting, and vectorized operations
- [ ] Pandas `Series` and `DataFrame` manipulation
- [ ] CSV/JSON data ingestion and data cleaning (`dropna`, `fillna`, `apply`)
- [ ] Descriptive statistics (mean, median, variance, correlations)
- [ ] Data visualization basics with Matplotlib
- [ ] Scikit-learn workflow: dataset -> `train_test_split` -> `fit` -> `evaluate` -> `predict`
- [ ] Classification vs Regression models
- [ ] Overfitting vs underfitting & regularization
- [ ] Model evaluation metrics (MSE, R2, Accuracy, Precision, Recall, F1)
- [ ] **Phase 9 Project**: Built P5 (ML prediction service with FastAPI inference endpoint).

---

## Phase 10 — LLM / AI Application Engineering (Days 49–60)
- [ ] LLM fundamentals: tokens, context windows, temperature, top_p
- [ ] Prompt engineering: system, user, and assistant messages
- [ ] Model API integration (OpenAI, Anthropic, Gemini SDKs)
- [ ] Streaming responses via Server-Sent Events (SSE)
- [ ] Vector embeddings generation & cosine similarity calculations
- [ ] Vector databases: `pgvector` extension & dedicated DBs (Qdrant / Chroma)
- [ ] End-to-end RAG architecture: Ingestion -> Chunking -> Embedding -> Retrieval -> Generation
- [ ] Hybrid search (BM25 keyword search + semantic vector search)
- [ ] Tool & function calling with Pydantic JSON schemas
- [ ] Structured outputs & schema enforcement (`response_format`)
- [ ] Conversation memory patterns (sliding window, summary memory)
- [ ] Evaluation metrics: correctness, retrieval precision, latency, token costs
- [ ] Prompt injection defense & AI security hygiene
- [ ] **Phase 10 Project**: Built P6 (RAG document search engine over local documents).

---

## Phase 11 — AI Systems Architecture (Days 61–70)
- [ ] End-to-end production AI request flow
- [ ] Model gateway / provider abstraction layer (fallback routing)
- [ ] Real-time streaming architecture (SSE / WebSockets)
- [ ] Asynchronous document ingestion queues (RabbitMQ / Redis Streams / Celery)
- [ ] Semantic caching for LLM responses and embeddings
- [ ] Rate-limiting, retry decorators with exponential backoff (`tenacity`)
- [ ] Token usage & operational cost tracking
- [ ] Distributed tracing & observability (OpenTelemetry, LangSmith, Phoenix)
- [ ] Autonomous Agent loops (ReAct pattern: Reason -> Act -> Observe)
- [ ] Security boundaries, guardrails, and secrets management
- [ ] **Phase 11 Project**: Built P7 (Production AI Knowledge Assistant with tools, streaming, and observability).

---

## 🏆 Project Ladder Completion
- [ ] **P1 — CLI Expense Tracker**
- [ ] **P2 — API Data Collector**
- [ ] **P3 — FastAPI Task API**
- [ ] **P4 — Production Backend**
- [ ] **P5 — ML Prediction API**
- [ ] **P6 — RAG Document Chat**
- [ ] **P7 — AI Knowledge Assistant**
