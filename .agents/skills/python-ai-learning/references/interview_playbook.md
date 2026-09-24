# 🎯 Senior Python & AI Engineer Interview Playbook
### (Tailored for Experienced Full-Stack Developers transitioning from JS/TS)

This playbook contains high-frequency interview questions asked during technical screenings for Senior Python Backend & AI Engineering roles. Each question includes:
1. **The Core Question & What the Interviewer Is Really Testing**
2. **The JS/TS Comparison (Mental Bridge)**
3. **The Exact Verbal Script (How to Answer Out Loud in 60–90 seconds)**
4. **The Code Trap & Pythonic Fix**

---

## 📌 Question 1: `==` vs `is` & The CPython Memory Model
### Interviewer Intent:
Checks whether you truly understand object identity vs value equality and whether you know how CPython allocates memory on the heap.

### JS/TS Analogy:
- In JS, `===` checks value for primitives and reference equality for objects.
- In Python, `==` is value equality (calls `__eq__`), while `is` is strict pointer identity (`id(a) == id(b)`).

### 🎙️ Verbal Script (How to Answer in the Interview):
> *"In Python, `==` and `is` serve two fundamentally different purposes:*
> 1. *`==` checks **value equality**. It delegates to the object's `__eq__()` dunder method. If two distinct objects contain the same data (like two separate lists `[1, 2]` and `[1, 2]`), `==` evaluates to `True`.*
> 2. *`is` checks **identity equality**—meaning both variables point to the exact same memory address in CPython (`id(a) == id(b)`).*
> 3. *A classic trap is checking numbers with `is`. CPython interns small integers between -5 and 256 for performance, so `256 is 256` is `True`, but `1000 is 1000` can be `False` because they are separate heap allocations. Therefore, the senior rule is: **Only use `is` for singletons like `None`, `True`, and `False`. Always use `==` for data and value comparisons.**"*

---

## 📌 Question 2: The Mutable Default Argument Gotcha
### Interviewer Intent:
The single most common Python screening question. Tests if you understand when functions are evaluated and how Python handles default arguments in memory.

### JS/TS Analogy:
In JavaScript `function f(arr = [])`, the default array is evaluated **every time the function is called without arguments**. In Python, default arguments are evaluated **once at definition/import time** and stored in the function object's `__defaults__` tuple.

### 🎙️ Verbal Script (How to Answer in the Interview):
> *"In Python, default arguments are evaluated **once at function definition time**, not at invocation time. When Python compiles the `def` statement, it creates the default object (like a list or dict) and attaches it to the function object's `__defaults__` attribute.*
> *If that default object is mutable (like `def add_item(val, target=[])`), any mutation inside the function persists across subsequent calls, behaving like a hidden static variable.*
> *The production-standard solution is to use `None` as the sentinel default value and initialize the mutable structure inside the function body with `if target is None: target = []`."*

```python
# The Trap:
def bad_append(val, items=[]):
    items.append(val)
    return items

# The Senior Fix:
def good_append(val, items=None):
    if items is None:
        items = []
    items.append(val)
    return items
```

---

## 📌 Question 3: Scoping, Closures & the `nonlocal` Keyword (LEGB)
### Interviewer Intent:
Tests understanding of Python's scoping rules and whether you understand how Python differs from block-scoped JavaScript (`let`/`const`).

### JS/TS Analogy:
JavaScript has block scope (`{ let x = 1; }`). Inner functions can directly rebind outer `let` variables. Python has **no block scope** (variables leak from `if`/`for` into the function) and requires `nonlocal` to reassign an outer closure variable.

### 🎙️ Verbal Script (How to Answer in the Interview):
> *"Python resolves variable lookups using the **LEGB rule**: Local, Enclosing, Global, and Built-in.*
> *A key distinction from JavaScript is that Python has no block scope—variables defined in `for` loops or `if` blocks remain in the enclosing function scope.*
> *Furthermore, if you assign to a variable inside an inner function (`count += 1`), Python marks `count` as **local** at compile time. If it hasn't been defined locally yet, it throws an `UnboundLocalError`. To rebind an enclosing closure variable, you must explicitly declare `nonlocal count`. For module-level variables, you use `global`."*

---

## 📌 Question 4: The GIL (Global Interpreter Lock) vs Node.js Event Loop
### Interviewer Intent:
Tests your backend concurrency depth. Interviewers want to know if you understand multithreading, multiprocessing, and asyncio in Python.

### JS/TS Analogy:
Node.js is single-threaded with an event loop for I/O and libuv worker threads. Python has OS threads, but CPython enforces the GIL, meaning only one thread can execute Python bytecode at any given moment.

### 🎙️ Verbal Script (How to Answer in the Interview):
> *"The GIL is a mutex in CPython that protects access to Python objects, preventing race conditions on reference counting (`ob_refcnt`).*
> *Its practical architectural implications break down into two workloads:*
> 1. *For **I/O-bound tasks** (network calls, database queries, file I/O), the GIL is released during system calls and async operations. Using `asyncio` or `concurrent.futures.ThreadPoolExecutor` provides true concurrency and high throughput—very similar to Node's async event loop.*
> 2. *For **CPU-bound tasks** (data cleaning, ML preprocessing, image manipulation), threads will not scale across multiple cores because they fight over the single GIL lock. The solution in Python is **multiprocessing** (`ProcessPoolExecutor`), which spawns distinct OS processes with independent memory spaces and separate CPython runtimes."*

---

## 📌 Question 5: Asyncio vs JavaScript Promises & Event Loop
### Interviewer Intent:
Crucial for FastAPI and AI streaming architectures. Tests how coroutines work under the hood.

### JS/TS Analogy:
In JS, calling an `async` function immediately starts execution (a "hot" Promise). In Python, calling an `async def` function creates an idle **coroutine object** that does not start executing until it is explicitly awaited or scheduled on the loop.

### 🎙️ Verbal Script (How to Answer in the Interview):
> *"While both JavaScript and Python use event loops for cooperative multitasking, they differ in execution semantics:*
> 1. *In JavaScript, invoking an async function immediately runs synchronously until the first await, returning a hot Promise that executes in the background.*
> 2. *In Python, calling an `async def` function does **not** execute it; it creates a lazy generator-based coroutine object. It will not run until you either `await` it, pass it to `asyncio.gather()`, or wrap it into an active task via `asyncio.create_task()`.*
> 3. *In Node.js the event loop runs automatically, whereas in Python you explicitly manage it—typically with `asyncio.run(main())` or within an ASGI framework like Uvicorn."*

---

## 📌 Question 6: Python Data Model & Dunder Protocols
### Interviewer Intent:
Tests if you write Pythonic code or just write JavaScript with Python syntax.

### JS/TS Analogy:
In JS, you use `JSON.stringify()`, `[Symbol.iterator]`, or custom methods. In Python, you implement standard double-underscore (dunder) methods to hook into language primitives.

### 🎙️ Verbal Script (How to Answer in the Interview):
> *"Python uses the Data Model protocol, often called **dunder methods**, to achieve consistent duck typing:*
> - *`__str__` is for readable user display (like `toString()`), while `__repr__` is for unambiguous developer debugging.*
> - *The **Iteration Protocol** requires `__iter__` (returns an iterator) and `__next__` (returns the next item or raises `StopIteration`).*
> - *The **Context Manager Protocol** requires `__enter__` and `__exit__`, which enables the `with` statement for deterministic resource cleanup (like DB transactions or file handles), similar to `try...finally`.*
> - *The **Descriptor Protocol** (`__get__`, `__set__`) powers Python's `@property`, `@classmethod`, and ORM field mappings like SQLAlchemy and Pydantic."*

---

## 📌 Question 7: Pydantic v2 vs TypeScript Interfaces
### Interviewer Intent:
Essential for FastAPI and LLM Structured Outputs.

### JS/TS Analogy:
TypeScript interfaces only exist at compile time and are erased in JavaScript. Pydantic is like **Zod**: it runs at runtime, coerces types, validates data schemas, and serializes JSON.

### 🎙️ Verbal Script (How to Answer in the Interview):
> *"TypeScript interfaces provide compile-time static type checking, but they are erased at runtime and cannot validate incoming untrusted JSON over HTTP.*
> *Pydantic models in Python provide both static typing (for IDEs/mypy) and **runtime validation and parsing**.*
> *In Pydantic v2 (rewritten in Rust via `pydantic-core`), validation is blazing fast. When invalid data arrives, it raises detailed validation errors automatically. This is why FastAPI uses Pydantic for request validation, response serialization, and OpenAPI schema generation, and why it is the industry standard for LLM function calling and structured outputs (`response_format`)."*

---

## 📌 Question 8: RAG Architecture & Vector Search Fundamentals
### Interviewer Intent:
Core for AI Engineer roles. Checks if you understand real retrieval vs naive prompt stuffing.

### 🎙️ Verbal Script (How to Answer in the Interview):
> *"A production RAG (Retrieval-Augmented Generation) pipeline consists of two phases:*
> 1. ***Ingestion Pipeline**: Text extraction -> recursive semantic chunking (typically 500-1000 tokens with 10-20% overlap) -> embedding generation via an embedding model (e.g. `text-embedding-3-small`) -> storage in a vector database with metadata (e.g. `pgvector` or Qdrant).*
> 2. ***Query & Generation Pipeline**: User query is embedded using the same model -> vector similarity search (cosine distance or dot product with HNSW index) plus metadata filtering -> retrieve top-k chunks -> rerank if needed (Cross-Encoder) -> assemble prompt with retrieved context -> stream LLM response via SSE.*
> *To prevent hallucinations, we instruct the LLM to answer strictly from provided context, cite sources, and fall back safely when data is absent."*
