# ⚡ Rapid Learning Protocol: The Daily Acceleration Loop

This document outlines the high-velocity daily learning method designed to compress a standard 6-month Python learning curve into ~6–8 weeks for an experienced developer.

---

## 1. The 70 / 20 / 10 Daily Formula (60–90 Minutes/Day)

| Allocation | Activity | Duration | Action |
| :--- | :--- | :--- | :--- |
| **20% (Fast Intake)** | Concept & Mental Model | 15–20 mins | Read the concept summary, inspect the JS/TS difference matrix, identify the CPython memory trap. |
| **70% (Active Coding)** | Executable Implementation | 45–60 mins | Run the concept script, inspect output, write code to pass the automated `assert` challenges, spot bugs in intentionally broken code. |
| **10% (Synthesis)** | Architecture / Project Application | 10–15 mins | Tie the learned concept into the current Project Ladder tier (e.g. using dataclasses in the CLI Expense Tracker). |

---

## 2. The 3-Step Active Mastery Drill

For every topic in the roadmap:

### Step 1: Memory & Identity Verification
Always run diagnostic checks:
- Is this object mutable or immutable?
- What are its memory addresses (`id()`) before and after mutation?
- How does `==` differ from `is` for this type?

### Step 2: The Bug Hunt
Find and fix the classic gotcha:
- Does this function use a mutable default?
- Does this loop closure bind lazily?
- Does this exception swallow root causes without chaining (`raise from`)?

### Step 3: Automated Test Verification
Every lesson script comes equipped with an automated self-test block:
```python
def run_tests():
    assert my_func(...) == expected, "Test failed!"
    print("[SUCCESS] All self-tests passed!")
```
Write and modify code until all assertions pass.

---

## 3. Phase Acceleration Exit Gates

To avoid getting stuck in tutorial loops, use these strict exit gates. As soon as you satisfy the gate, immediately sprint to the next phase!

| Phase | Exit Gate Challenge |
| :--- | :--- |
| **Phase 1: Fundamentals** | Write a data processing function using dict/list comprehensions and tuple unpacking without looking up syntax. |
| **Phase 2: Pythonic Python** | Build a custom generator with `yield` and a custom decorator with `@functools.wraps` that logs execution time. |
| **Phase 3: OOP & Modules** | Create a class hierarchy using `@dataclass`, implement `__str__` and `__eq__`, and organize into a 2-file package with clean absolute imports. |
| **Phase 4: Errors & Stdlib** | Build a script that uses `pathlib` to read JSON, queries a public API with `httpx`, chains custom exceptions, and logs using `logging`. |
| **Phase 5: Modern Tooling** | Initialize a project with `uv`, configure `pyproject.toml`, write 3 pytest fixtures, and run `ruff check` + `mypy` with zero warnings. |
| **Phase 6: Async Concurrency** | Fetch 10 URLs concurrently using `asyncio.gather()` and `httpx.AsyncClient` with proper timeouts and error recovery. |
| **Phase 7: FastAPI Backend** | Build a 3-endpoint REST API with Pydantic request/response models, dependency injection, and Pytest coverage. |
| **Phase 8: Database & Production** | Connect FastAPI to PostgreSQL with SQLAlchemy 2.0 async sessions, run Alembic migrations, cache responses in Redis, and run in Docker. |
| **Phase 9: Data/AI Foundations** | Ingest a CSV into Pandas, clean nulls, engineer 2 features, train a scikit-learn classifier, and serialize model with `joblib`. |
| **Phase 10: LLM Engineering** | Build a RAG script: chunk local text, generate OpenAI/Gemini embeddings, store in vector DB, retrieve by cosine similarity, and stream LLM answer. |
| **Phase 11: AI Architecture** | Draw and implement a production AI request loop: API gateway -> prompt orchestration -> tool calling loop -> SSE streaming response -> cost/token tracking. |
