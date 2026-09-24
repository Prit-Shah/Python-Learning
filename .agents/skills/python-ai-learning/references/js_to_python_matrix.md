# ⚡ JavaScript/TypeScript → Python Fast-Track Matrix

For experienced Full-Stack Developers (Node.js, TypeScript, React), use this mental model translation matrix to master Python syntax and idioms at 5x speed.

---

## 1. Syntax, Types & Variables

| Concept | JavaScript / TypeScript | Python | Key Difference / Note |
| :--- | :--- | :--- | :--- |
| **Variable Declaration** | `const x = 1; let y = 2;` | `x = 1; y = 2` | Python has **no `const`**. Variables are names rebound to objects. Uppercase (`MAX_RETRIES = 5`) is convention only. |
| **Strict Equality** | `a === b` | `a is b` (Identity) vs `a == b` (Value) | **Critical gotcha**: `is` checks memory address (`id(a) == id(b)`). `==` checks value equality (`a.__eq__(b)`). |
| **Nullish / Absence** | `null`, `undefined` | `None` | `None` is a singleton of type `NoneType`. Always check with `if x is None:`. |
| **String Formatting** | `` `Hello ${name}` `` | `f"Hello {name}"` | F-strings support expressions: `f"{value:.2f}"`, `f"{x=}"`. |
| **Boolean Truthiness** | `0, "", null, undefined, NaN, false` | `0, 0.0, "", None, False, [], {}, set()` | Empty collections (`[]`, `{}`) are **falsy** in Python! In JS, `Boolean([]) === true`. In Python: `if not my_list:`. |
| **Type Coercion** | `1 + "2"` -> `"12"` | `1 + "2"` -> `TypeError` | Python is **strongly typed**. No implicit coercion between incompatible types. |
| **Type Annotations** | TypeScript: `function add(a: number): number` | Python: `def add(a: int) -> int:` | Type hints in Python are runtime annotations (PEP 484). Erased at runtime like TS, checked via `mypy`/`pyright` or validated via `pydantic`. |
| **Pattern Matching** | `switch (val) { case 'a': ... }` | `match val: case 'a': ...` | Python 3.10+ structural pattern matching can match types, sequences, and unpack attributes. |

---

## 2. Collections & Data Structures

| Data Structure | JavaScript / TypeScript | Python | Key Difference / Note |
| :--- | :--- | :--- | :--- |
| **Ordered Sequence** | `Array` (`[1, 2, 3]`) | `list` (`[1, 2, 3]`) | Mutable dynamic array. Fast append/pop at tail (`O(1)`), slow insert/delete at head (`O(n)`). |
| **Immutable Sequence** | `readonly tuple` (`as const`) | `tuple` (`(1, 2, 3)`) | Immutable, hashable (can be used as dictionary keys and set members). |
| **Key-Value Map** | `Object` (`{}`), `Map` | `dict` (`{"key": "value"}`) | Preserves insertion order (Python 3.7+). Keys must be hashable/immutable. |
| **Unique Set** | `Set` (`new Set([1, 2])`) | `set` (`{1, 2, 3}`) | Hash table of unique elements. Fast `O(1)` lookups. Mathematical set operations (`&`, `\|`, `-`, `^`). |
| **Array Slicing** | `arr.slice(1, 3)` | `arr[1:3]` | Python slice syntax `[start:stop:step]` works on lists, strings, and tuples. Negative indices count from end (`arr[-1]`). |
| **Transform / Filter** | `arr.map(x => x*2).filter(x => x > 5)` | `[x*2 for x in arr if x > 5]` | **Comprehensions** are the idiomatic Python standard. Avoid `map()`/`filter()` with `lambda`. |
| **Dictionary Transform** | `Object.fromEntries(...)` | `{k: v for k, v in items if condition}` | Dict comprehensions allow concise filtering and dictionary creation. |

---

## 3. Functions, Scopes & Closures

| Concept | JavaScript / TypeScript | Python | Key Difference / Note |
| :--- | :--- | :--- | :--- |
| **Rest / Spread** | `...args`, `...kwargs` | `*args`, `**kwargs` | `*args` packs/unpacks positional arguments (tuple); `**kwargs` packs/unpacks keyword arguments (dict). |
| **Default Arguments** | `function f(arr = [])` (new array per call) | `def f(arr=None): if arr is None: arr = []` | **THE BIG TRAP**: Python default arguments are evaluated **once at function definition time**. Mutable defaults (`def f(x=[])`) persist across calls! |
| **Arrow Functions** | `(x, y) => x + y` | `lambda x, y: x + y` | Python `lambda` can only contain a single expression, no statements. Use `def` for multi-line functions. |
| **Lexical Scoping** | Block scope (`{ let x = 1; }`) | Function / Module scope (LEGB) | Python has **no block scope**! Variables defined inside `if` or `for` leak into the enclosing function. |
| **Outer Variable Rebinding** | Lexical closure automatically mutates outer `let` | `nonlocal` keyword required | In Python, assigning to an outer variable creates a new local variable unless declared `nonlocal` or `global`. |

---

## 4. Object-Oriented Programming & Data Model

| Concept | JavaScript / TypeScript | Python | Key Difference / Note |
| :--- | :--- | :--- | :--- |
| **Constructor** | `constructor(name) { this.name = name; }` | `def __init__(self, name: str): self.name = name` | Explicit `self` receiver as first argument in instance methods. |
| **Getters / Setters** | `get prop() { ... }` | `@property` / `@prop.setter` | Encapsulate attribute access without changing public API call site (`obj.prop`). |
| **String Representation** | `toString()`, `[util.inspect.custom]` | `__repr__()` (developer debug), `__str__()` (user display) | Always implement `__repr__` for clear debugging in logs/terminals. |
| **Equality & Hashing** | Custom equals method | `__eq__`, `__hash__` | Overriding `__eq__` makes custom objects comparable with `==`. Implementing `__hash__` allows using them in sets/dict keys. |
| **Data Models / Structs** | `interface User { id: string; }` | `@dataclass` or Pydantic `BaseModel` | `@dataclass` auto-generates `__init__`, `__repr__`, `__eq__`. Pydantic adds runtime validation & JSON parsing. |
| **Protocols / Interfaces** | TypeScript `interface` / duck typing | `typing.Protocol` (PEP 544) | Formalized static duck typing. Classes do not need to inherit from the Protocol explicitly! |

---

## 5. Async, Concurrency & Event Loop

| Concept | Node.js (V8) | Python (Asyncio) | Key Difference / Note |
| :--- | :--- | :--- | :--- |
| **Event Loop Execution** | Automatic, always running in background | Explicit start via `asyncio.run(main())` | Python does not run an event loop by default. You must create and manage it. |
| **Promise vs Coroutine** | `const p = fetch()` runs immediately (hot promise) | `task = fetch()` creates a coroutine object; **does NOT run until awaited or scheduled** | Calling an `async def` function produces an idle coroutine. You must `await coro` or schedule via `asyncio.create_task(coro)`. |
| **Parallel I/O Waiting** | `Promise.all([p1, p2])` | `await asyncio.gather(c1, c2)` | Gathers concurrent coroutines and returns ordered results. |
| **Threading & CPU Bound** | Worker Threads / `worker_threads` | `multiprocessing` / `ProcessPoolExecutor` | Due to the **GIL (Global Interpreter Lock)**, Python OS threads run on a single CPU core. Use multiprocessing for CPU-bound tasks (ML/data processing). |

---

## 6. Tooling & Ecosystem

| Purpose | Node.js Ecosystem | Python Modern Ecosystem | Recommendation |
| :--- | :--- | :--- | :--- |
| **Package / Project Manager** | `npm` / `pnpm` / `bun` | `uv` / `pip` | Use **`uv`** (written in Rust, 10–100x faster than traditional pip). |
| **Project Manifest** | `package.json` | `pyproject.toml` (PEP 621) | Modern unified standard for dependencies, build tools, and linter configs. |
| **Formatter & Linter** | Prettier + ESLint + Biome | **Ruff** | Blazing fast all-in-one Python linter and formatter. |
| **Type Checker** | `tsc` | `mypy` or `pyright` | Run `mypy` or `pyright` in CI/editor for static type analysis. |
| **Test Runner** | Jest / Vitest | **Pytest** | Standard test runner with powerful fixtures and parametrization. |
| **Web Framework** | Express / Fastify / NestJS | **FastAPI** | Async-first, automatic OpenAPI/Swagger docs, Pydantic data validation. |
| **ORM / Database** | Prisma / Drizzle / TypeORM | **SQLAlchemy 2.0** / **SQLModel** | Industrial-strength SQL expression language & async ORM. |
