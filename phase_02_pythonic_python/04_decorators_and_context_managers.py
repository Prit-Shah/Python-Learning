"""
04_decorators_and_context_managers.py

============================================================
1. CONCEPT
============================================================

Python provides two elegant, expressive meta-programming mechanisms for
encapsulating cross-cutting concerns and managing resource lifecycles:

1. Decorators:
   - A decorator is a higher-order callable that accepts a function (or class),
     extends or modifies its behavior, and returns a callable.
   - The `@decorator` syntax is syntactic sugar:
     `@dec` above `def func(): ...` translates directly to `func = dec(func)`.
   - Decorator variants:
     - Simple decorators (no arguments): takes `func`, returns `wrapper`.
     - Parameterized decorators (decorator factories): takes configuration
       arguments, returns a decorator, which in turn returns a `wrapper`.
     - Class-based decorators: classes implementing `__call__` to maintain
       stateful invocation counts or cached results.
   - Metadata preservation: Decorators must use `@functools.wraps(func)` to
     preserve the underlying function's `__name__`, `__doc__`, `__module__`,
     and `__annotations__`, while exposing `__wrapped__` for introspection.
   - Stacking order: Multiple decorators evaluate bottom-up (inside-out):
     `@dec1` over `@dec2` over `def f():` evaluates as `f = dec1(dec2(f))`.

2. Context Managers and the `with` Statement:
   - The context manager protocol guarantees deterministic resource allocation
     and release, preventing leaks of file handles, sockets, database transactions,
     and locks.
   - The Protocol:
     - `__enter__(self)`: Prepares the resource; its return value is bound to
       the variable specified in the `as <var>` clause.
     - `__exit__(self, exc_type, exc_val, exc_tb)`: Executes cleanup. If an
       exception occurred in the block, its type, value, and traceback are passed.
       Returning `True` suppresses the exception; returning `False` or `None`
       propagates it.
   - Generator-based Context Managers:
     - `@contextlib.contextmanager` transforms a generator containing a single
       `yield` inside a `try...finally` block into a full context manager.
   - Advanced contextlib utilities: `contextlib.suppress`, `contextlib.ExitStack`.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python                             | JavaScript / TypeScript            |
+------------------------------+------------------------------------+------------------------------------+
| Decorator Syntax             | `@my_decorator`                    | `@myDecorator` (Stage 3 Decorators)|
| Function Wrapping            | Higher-order function / closure    | Higher-order function / closure    |
| Metadata Preservation        | `@functools.wraps(func)`           | `Object.defineProperty(..., 'name')|
| Stack Order                  | Bottom-up: `@a` then `@b` -> a(b(f))| Bottom-up / inside-out             |
| Resource Management          | `with acquire() as res:`           | `using res = acquire()` (TS 5.2+)  |
| Lifecycle Methods            | `__enter__` and `__exit__`         | `[Symbol.dispose]()`               |
| Exception Suppression        | Return `True` from `__exit__`      | `try / catch` swallow pattern      |
| Clean Teardown Guarantee     | Guaranteed via `__exit__`          | `finally` block or `using`         |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Differences:
1. Python decorators are universally used across functions, methods, and classes
   for logging, caching (`@lru_cache`), authentication, rate limiting, and route
   registration (FastAPI / Flask).
2. Before TypeScript 5.2's `using` keyword (`Symbol.dispose`), JavaScript had no
   standard syntactic construct equivalent to Python's `with` statement, relying
   exclusively on verbose `try...finally` blocks.


============================================================
3. UNDER THE HOOD (CPython & Memory)
============================================================

1. Bytecode Compilation of Decorators:
   - A decorated function compiles to:
     - `MAKE_FUNCTION`: creates the inner function object.
     - `LOAD_NAME dec`: pushes decorator callable.
     - `PRECALL` / `CALL`: executes `dec(func)`.
     - `STORE_NAME func`: binds resulting wrapper to original name.

2. Bytecode Mechanics of `with`:
   - In Python 3.11+, `with mgr as target:` generates:
     - `LOAD_NAME mgr`, `CALL`
     - `BEFORE_WITH`: calls `__enter__` and pushes `__exit__` onto the stack frame.
     - `STORE_FAST target`
     - Encloses the block in an implicit exception-handling table.
     - Normal exit: invokes `WITH_EXCEPT_START` and `CALL` on `__exit__(None, None, None)`.
     - Exception exit: pushes exception info, calls `__exit__(exc_type, exc_val, tb)`.
       If `__exit__` returns a truthy value, `POP_EXCEPT` discards the exception.

3. The `__wrapped__` Chain:
   - When `@functools.wraps` is used, it sets the `__wrapped__` attribute on the wrapper.
   - This creates an inspectable pointer chain to the original un-decorated function,
     allowing unit tests to bypass decorators (e.g. testing `func.__wrapped__` directly).


============================================================
4. COMMON GOTCHAS
============================================================

1. Forgetting `@functools.wraps`:
   - Omitting `@functools.wraps(func)` replaces the function's name with `"wrapper"`
     and obliterates its docstring.
   - Breaks API documentation tools (Swagger / OpenAPI / Sphinx) and debuggers.

2. Decorator Factory Parentheses:
   - Simple decorator: `@my_dec` (no parens).
   - Parameterized decorator: `@my_dec()` (MUST include parens to call the factory).

3. Accidental Exception Suppression:
   - Returning any truthy value (like `1` or a string) from `__exit__` suppresses
     exceptions!
   - Ensure `__exit__` returns `True` strictly when explicit suppression is intended,
     and returns `False` or `None` otherwise.

4. Unhandled Exception in `@contextmanager` Generator:
   - In `@contextmanager`, an exception raised inside the `with` block is re-raised
     at the `yield` statement inside the generator!
   - If the generator does not wrap `yield` in a `try...finally`, cleanup code
     below `yield` WILL NEVER EXECUTE on error.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "Explain how decorators work in Python and why functools.wraps is essential."
Script:
"A decorator is a callable that takes a function as an argument, wraps it with
supplementary behavior, and returns a new callable. The `@decorator` syntax is syntactic
sugar that re-binds the function identifier to the result of `decorator(function)`.
Because a custom wrapper replaces the original function object, attributes like `__name__`,
`__doc__`, and `__annotations__` would normally be overwritten by the wrapper's attributes.
Applying `@functools.wraps(func)` to the inner wrapper preserves the original metadata
and establishes a `__wrapped__` reference, ensuring seamless debugging, introspection,
and testability."

Q2: "What is the context manager protocol, and how does exception suppression work in __exit__?"
Script:
"The context manager protocol requires implementing two dunder methods: `__enter__` and
`__exit__`. When entering a `with` statement, `__enter__` executes setup logic and its return
value is bound to the target variable. Upon exiting the block, `__exit__` is called
guaranteeing cleanup. If an unhandled exception occurs inside the block, CPython passes
`(exc_type, exc_val, exc_tb)` to `__exit__`. If `__exit__` returns a truthy value such as
`True`, Python completely suppresses the exception, allowing execution to resume normally
after the `with` statement. If it returns `False` or `None`, the exception is re-raised."

Q3: "How does contextlib.contextmanager convert a generator into a context manager?"
Script:
"`contextlib.contextmanager` is a decorator that converts a generator function with a single
`yield` into a full context manager. The code preceding `yield` acts as `__enter__`, with the
yielded value returned to the `as` clause. Execution pauses until the `with` block finishes.
Any exception raised inside the block is re-injected into the generator at the `yield` point
via `.throw()`. Placing cleanup logic in a `finally` block guarantees that teardown occurs
whether the block finishes normally or raises an exception."
"""

import functools
import sys
import time
from contextlib import contextmanager, suppress

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# Class-based decorator for stateful call counting
class CallCounter:
    """Decorator that tracks the number of times a function is called."""
    def __init__(self, func):
        functools.wraps(func)(self)
        self.func = func
        self.call_count = 0

    def __call__(self, *args, **kwargs):
        self.call_count += 1
        return self.func(*args, **kwargs)


# Custom Class Context Manager
class DatabaseTransaction:
    """Demonstrates complete __enter__ and __exit__ protocol with rollback."""
    def __init__(self, db_name):
        self.db_name = db_name
        self.committed = False
        self.rolled_back = False

    def __enter__(self):
        return self

    def commit(self):
        self.committed = True

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Exception occurred -> rollback
            self.rolled_back = True
            # Return False to propagate exception, or True to suppress
            return False
        # Clean completion
        self.commit()
        return True


# Exception Suppressing Context Manager
class ErrorSilencer:
    """Suppresses specific exception types."""
    def __init__(self, *exceptions_to_catch):
        self.exceptions_to_catch = exceptions_to_catch
        self.suppressed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type and issubclass(exc_type, self.exceptions_to_catch):
            self.suppressed = True
            return True  # Suppress!
        return False  # Propagate other exceptions


def run_tests():
    # ============================================================
    # 1. BASIC DECORATOR & METADATA PRESERVATION (@functools.wraps)
    # ============================================================

    def audit_log(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            wrapper.calls += 1
            return func(*args, **kwargs)
        wrapper.calls = 0
        return wrapper

    @audit_log
    def calculate_tax(amount: float, rate: float = 0.08) -> float:
        """Calculate tax on an amount."""
        return amount * rate

    # Invocation
    tax = calculate_tax(100.0)
    assert tax == 8.0
    assert calculate_tax.calls == 1

    # Metadata preservation check
    assert calculate_tax.__name__ == "calculate_tax"
    assert calculate_tax.__doc__ == "Calculate tax on an amount."
    assert calculate_tax.__annotations__ == {"amount": float, "rate": float, "return": float}

    # Bypassing decorator via __wrapped__
    unwrapped_result = calculate_tax.__wrapped__(200.0, 0.10)
    assert unwrapped_result == 20.0
    assert calculate_tax.calls == 1  # Not incremented because decorator was bypassed!


    # ============================================================
    # 2. PARAMETERIZED DECORATORS (DECORATOR FACTORIES)
    # ============================================================
    # Three-level function nesting:
    # 1. Factory receives configuration parameters
    # 2. Decorator receives target function
    # 3. Wrapper receives runtime arguments

    def retry(max_attempts=3, expected_exception=Exception):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                attempts = 0
                while attempts < max_attempts:
                    try:
                        return func(*args, **kwargs)
                    except expected_exception:
                        attempts += 1
                        if attempts >= max_attempts:
                            raise
            return wrapper
        return decorator

    # Test flaky function succeeding on attempt 3
    failure_counter = 0

    @retry(max_attempts=3, expected_exception=ValueError)
    def flaky_network_call():
        nonlocal failure_counter
        failure_counter += 1
        if failure_counter < 3:
            raise ValueError("Transient error")
        return "SUCCESS"

    assert flaky_network_call() == "SUCCESS"
    assert failure_counter == 3


    # ============================================================
    # 3. CLASS-BASED DECORATORS
    # ============================================================
    # Using a class with __call__ as a stateful decorator.

    @CallCounter
    def process_order(order_id):
        return f"Order {order_id} processed"

    assert process_order("ORD-001") == "Order ORD-001 processed"
    assert process_order("ORD-002") == "Order ORD-002 processed"
    assert process_order.call_count == 2
    assert process_order.__name__ == "process_order"


    # ============================================================
    # 4. DECORATOR STACKING / CHAINING ORDER
    # ============================================================
    # Bottom-up decoration, top-down wrapper execution.

    trace = []

    def dec_outer(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            trace.append("outer_start")
            res = func(*args, **kwargs)
            trace.append("outer_end")
            return res
        return wrapper

    def dec_inner(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            trace.append("inner_start")
            res = func(*args, **kwargs)
            trace.append("inner_end")
            return res
        return wrapper

    @dec_outer
    @dec_inner
    def core_action():
        trace.append("core")
        return "OK"

    result = core_action()
    assert result == "OK"
    assert trace == [
        "outer_start",
        "inner_start",
        "core",
        "inner_end",
        "outer_end",
    ]


    # ============================================================
    # 5. CLASS-BASED CONTEXT MANAGERS (__enter__ & __exit__)
    # ============================================================

    # ------------------------------------------------------------
    # Normal execution -> Commit
    # ------------------------------------------------------------
    with DatabaseTransaction("production_db") as tx:
        tx_ref = tx

    assert tx_ref.committed is True
    assert tx_ref.rolled_back is False

    # ------------------------------------------------------------
    # Exception handling -> Rollback and propagation
    # ------------------------------------------------------------
    failed_tx = None
    caught_error = False
    try:
        with DatabaseTransaction("production_db") as tx:
            failed_tx = tx
            raise RuntimeError("Database connection reset")
    except RuntimeError:
        caught_error = True

    assert caught_error is True
    assert failed_tx.rolled_back is True
    assert failed_tx.committed is False


    # ============================================================
    # 6. EXCEPTION SUPPRESSION IN __exit__
    # ============================================================
    # Returning True from __exit__ suppresses the exception.

    with ErrorSilencer(ZeroDivisionError) as silencer:
        _ = 1 / 0

    assert silencer.suppressed is True

    # Unhandled exception propagates normally
    unhandled_raised = False
    try:
        with ErrorSilencer(KeyError):
            _ = 1 / 0
    except ZeroDivisionError:
        unhandled_raised = True
    assert unhandled_raised is True


    # ============================================================
    # 7. GENERATOR-BASED CONTEXT MANAGERS (@contextlib.contextmanager)
    # ============================================================
    # try ... yield ... finally structure

    cleanup_log = []

    @contextmanager
    def managed_resource(name):
        cleanup_log.append(f"acquired_{name}")
        try:
            yield {"name": name, "active": True}
        finally:
            cleanup_log.append(f"released_{name}")

    with managed_resource("gpu_cluster") as res:
        assert res == {"name": "gpu_cluster", "active": True}
        assert cleanup_log == ["acquired_gpu_cluster"]

    assert cleanup_log == ["acquired_gpu_cluster", "released_gpu_cluster"]

    # Even on error, 'finally' block is guaranteed to execute
    cleanup_log.clear()
    error_seen = False
    try:
        with managed_resource("temp_scratchpad"):
            raise ValueError("Computation failed")
    except ValueError:
        error_seen = True

    assert error_seen is True
    assert cleanup_log == ["acquired_temp_scratchpad", "released_temp_scratchpad"]


    # ============================================================
    # 8. STANDARD LIBRARY contextlib HELPERS: suppress()
    # ============================================================
    # Eliminates boilerplate try...except pass blocks

    d = {"status": "active"}
    with suppress(KeyError):
        del d["nonexistent_key"]  # Does not raise KeyError!

    assert d == {"status": "active"}


if __name__ == "__main__":
    run_tests()
    print("04_decorators_and_context_managers.py tests passed!")
