# 🚀 Python → AI Engineer Learning Roadmap

Welcome to **Python-Learning**! This repository is structured as a fast, practical, concept-driven learning path designed for experienced Full-Stack Developers transitioning into **Python Backend Engineering & AI Systems Architecture**.

---

## 📌 Learning Architecture & Approach

This repository follows the **70 / 20 / 10 Learning Strategy**:
- **70% Hands-on Coding**: Executable, concept-focused Python files with inline explanations, edge cases, and exercises.
- **20% Reading & Concepts**: Deep dive into Python idioms, memory models, typing, async mechanics, and AI architecture patterns.
- **10% Synthesizing & Projects**: Building 7 progressive real-world projects from CLI utilities to multi-agent RAG platforms.

> 💡 **JavaScript/TypeScript Developer Context**: Explanations compare Python constructs directly with Node.js/TS equivalents (e.g. `is` vs `===`, LEGB vs Lexical Scope, GIL vs Node Event Loop, `async/await`, Pydantic vs Zod/TypeScript types).

---

## 🗂️ Folder Structure

```text
python-learning/
├── .agents/
│   └── skills/
│       └── python-ai-learning/    # AI LLM Skill definition for roadmap guidance
│           └── SKILL.md
├── phase_00_setup/               # Env setup, venv, uv, VS Code
├── phase_01_fundamentals/        # Types, data structures, control flow, functions
├── phase_02_pythonic_python/     # Mutability, scope, generators, decorators, typing
├── phase_03_oop_and_modules/     # OOP, dunder methods, dataclasses, packages
├── phase_04_errors_files_http/   # Exceptions, logging, pathlib, httpx, JSON
├── phase_05_tooling_and_testing/ # Pytest, fixtures, mocking, ruff, mypy
├── phase_06_async_concurrency/   # asyncio, gather, tasks, multithreading vs multiprocessing
├── phase_07_fastapi_backend/     # REST APIs, Pydantic, dependency injection, auth
├── phase_08_database_production/ # PostgreSQL, SQLAlchemy, Alembic, Redis, Docker
├── phase_09_data_ai_foundations/ # NumPy, Pandas, scikit-learn workflow
├── phase_10_llm_ai_engineering/  # LLM APIs, prompt engineering, embeddings, vector DBs, RAG
├── phase_11_ai_architecture/     # System design, SSE streaming, AI gateways, agent loops
└── projects/                     # 7 Practical ladder projects (P1 - P7)
```

---

## 🧗‍♂️ Project Ladder

- [ ] **P1 — CLI Expense Tracker**: Python fundamentals, file handling, modules, exceptions.
- [ ] **P2 — API Data Collector**: HTTP, `asyncio`, JSON parsing, retry logic, logging.
- [ ] **P3 — FastAPI Task API**: RESTful architecture, Pydantic models, Pytest, PostgreSQL.
- [ ] **P4 — Production Backend**: Redis caching, background worker queue, Docker, JWT auth.
- [ ] **P5 — ML Prediction API**: Data preprocessing with NumPy/Pandas, scikit-learn model, FastAPI inference.
- [ ] **P6 — RAG Document Chat**: Ingestion pipeline, vector database (pgvector/Qdrant), embeddings, RAG prompt.
- [ ] **P7 — AI Knowledge Assistant**: Agent tool execution loops, streaming, background jobs, observability & tracing.

---

## ⚡ How to Run Code

Each topic file is **standalone and directly executable**:

```bash
# Create and activate virtual environment
python -m venv .venv

# Run any concept script directly:
python phase_01_fundamentals/01_variables_and_types.py
```

---

## 🤖 AI LLM Instructions

This repo contains an AI Skill at `.agents/skills/python-ai-learning/SKILL.md`. When interacting with any LLM in this repository, the agent will follow this skill to generate fully executable files with rich comments, JS/TS comparisons, practice questions, and phase-oriented code structure.
