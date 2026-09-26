"""
01_asyncio_fundamentals_and_event_loop.py

============================================================
1. CONCEPT
============================================================

Asynchronous programming in Python is powered by `asyncio`, cooperative multitasking,
the event loop, and coroutines (PEP 492):

1. Coroutine vs Task vs Future:
   - Coroutine Function: Defined with `async def`. Calling it does NOT execute code;
     it returns a dormant `coroutine` object.
   - Coroutine Object: A lazy state machine. Execution only begins when explicitly
     `await`ed or scheduled on an event loop.
   - Task (`asyncio.Task`): A wrapper around a coroutine scheduled on the event
     loop for concurrent execution. Created via `asyncio.create_task()`.
   - Future (`asyncio.Future`): A low-level object representing an eventual result
     of an asynchronous operation (analogous to a Promise).

2. The Event Loop Architecture:
   - Single-threaded cooperative multitasking.
   - The loop monitors I/O readiness (using OS primitives like `epoll` on Linux,
     `kqueue` on macOS, or `IOCP` / `ProactorEventLoop` on Windows).
   - Tasks voluntarily yield control back to the event loop whenever an `await`
     expression is reached (e.g. `await asyncio.sleep()`, socket read, HTTP request).

3. The Blocking Event Loop Trap:
   - Because `asyncio` runs cooperatively on a single OS thread, calling blocking
     synchronous functions (such as `time.sleep()`, synchronous DB drivers, or
     heavy CPU operations) completely freezes the entire event loop!
   - Resolution: Offload synchronous blocking operations to thread pools using
     `await asyncio.to_thread(sync_fn, *args)` (Python 3.9+).

4. Application Entry Point (`asyncio.run`):
   - Introduced in Python 3.7.
   - Instantiates a fresh event loop, executes the passed root coroutine until
     completion, cancels any remaining pending tasks, and shuts down the loop
     and asynchronous generators cleanly.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python (asyncio)                   | JavaScript / TypeScript (Node.js)  |
+------------------------------+------------------------------------+------------------------------------+
| Function Declaration         | `async def f():`                   | `async function f() { ... }`       |
| Invocation Semantics         | LAZY: Returns un-started coroutine | EAGER: Starts immediately ("Hot")  |
| Starting Concurrent Execution| `task = asyncio.create_task(f())`  | Invoking function starts Promise   |
| Yielding Execution           | `await asyncio.sleep(0.01)`        | `await new Promise(...)`           |
| Non-blocking Delay           | `await asyncio.sleep(seconds)`     | `await setTimeout(ms)`             |
| Event Loop Initialization    | Explicit: `asyncio.run(main())`    | Implicit: Global Node.js event loop|
| Offload Blocking CPU/Sync    | `await asyncio.to_thread(cpu_work)`| `worker_threads` / Thread pool     |
| Low-level Result Holder      | `asyncio.Future`                   | `Promise`                          |
+------------------------------+------------------------------------+------------------------------------+

Crucial JS vs Python Semantic Difference: Eager vs Lazy!
- In JavaScript:
  `const p = fetchUser();` -> The network request starts IMMEDIATELY upon invocation!
- In Python:
  `coro = fetch_user()` -> Zero network activity occurs! The coroutine sits dormant in RAM.
  Execution only begins when you write `await coro` or `asyncio.create_task(coro)`.


============================================================
3. UNDER THE HOOD (CPython & Memory)
============================================================

1. PyCoroObject Structure:
   - Coroutines in CPython are implemented as specialized `PyCoroObject` structs,
     built upon the generator infrastructure.
   - When a coroutine hits `await`, CPython pauses the stack frame, saves local
     variables in `f_localsplus` on the heap, and yields control back to the loop.
   - When the underlying socket or timer becomes ready, the event loop selector
     resumes the coroutine by calling `coroutine.send(result)`.

2. OS Polling Engines:
   - Windows: Defaults to `ProactorEventLoop` backed by I/O Completion Ports (IOCP),
     enabling kernel-level overlapped asynchronous I/O.
   - Linux: Defaults to `SelectorEventLoop` backed by `epoll`.
   - macOS: Backed by `kqueue`.

3. Microsecond Overhead of `to_thread`:
   - `asyncio.to_thread` delegates work to CPython's internal `ThreadPoolExecutor`.
   - The thread pool handles OS thread scheduling, releasing the GIL during
     C-level operations, and resolving a `Future` on the event loop when finished.


============================================================
4. COMMON GOTCHAS
============================================================

1. The "Never Awaited" Coroutine:
   - Calling `async_func()` without `await` or `create_task()`:
   - Result: `RuntimeWarning: coroutine 'async_func' was never awaited`.
   - The function body NEVER runs!

2. Blocking the Event Loop with `time.sleep`:
   - Writing `time.sleep(2)` inside an `async def` function halts all concurrent
     traffic across the entire server!
   - Always use `await asyncio.sleep(2)`.

3. Unhandled Exceptions in Detached Tasks:
   - Creating tasks with `asyncio.create_task(f())` without retaining a reference
     or awaiting them can cause the task to be garbage collected mid-execution!
   - PEP 654 and modern best practices recommend `asyncio.TaskGroup` to guarantee
     task completion and error propagation.

4. Invoking `asyncio.run()` Inside a Running Event Loop:
   - Calling `asyncio.run()` inside an active event loop (e.g. inside FastAPI or
     Jupyter Notebook) raises:
     `RuntimeError: asyncio.run() cannot be called from a running event loop`.
   - Fix: Await the coroutine directly: `await coro()`.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "Explain the fundamental difference between how Python asyncio executes coroutines versus how JavaScript executes async functions."
Script:
"The fundamental difference is eager versus lazy execution. In JavaScript, invoking an
async function immediately starts executing synchronously until the first `await` keyword
is encountered, returning an eager, 'hot' Promise that is already scheduled on the microtask
queue. In Python, invoking an `async def` function does not execute a single line of code;
it constructs a lazy `coroutine` object that remains completely dormant on the heap.
Execution only begins when the coroutine is explicitly awaited or passed to `asyncio.create_task()`,
which wraps it in a `Task` and registers it with the event loop."

Q2: "What happens if a developer calls time.sleep() or a synchronous database driver inside an async function?"
Script:
"Because Python asyncio operates on a single OS thread using cooperative multitasking,
tasks only yield control back to the event loop at explicit `await` expressions. If a
function calls a blocking synchronous operation like `time.sleep()` or a synchronous ORM
query, that operation monopolizes the thread's CPU cycles. The event loop cannot poll
network sockets, process timers, or advance other tasks. The entire application freezes
for the duration of the call. In production, any synchronous, CPU-intensive, or blocking
I/O must be offloaded to worker threads using `await asyncio.to_thread(func, *args)`."

Q3: "How does the Python event loop manage I/O readiness under the hood?"
Script:
"Under the hood, the Python event loop delegates I/O multiplexing to operating system kernel
mechanisms—specifically `epoll` on Linux, `kqueue` on macOS, and I/O Completion Ports (IOCP)
on Windows via the Proactor loop. When an async socket operation cannot complete immediately,
the coroutine suspends and registers its file descriptor with the OS selector. The event loop
then enters an OS wait state. When the kernel signals that the descriptor is ready for reading
or writing, the loop wakes up and resumes the paused coroutine via its internal `.send()`
method, allowing thousands of concurrent network connections to be serviced with a tiny memory
footprint."
"""

import asyncio
import sys
import time

# Ensure UTF-8 standard output across environments
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ============================================================
# COROUTINE DEFINITIONS & WORKERS
# ============================================================

async def compute_square_async(x: int) -> int:
    """Asynchronous non-blocking computation."""
    await asyncio.sleep(0.001)  # Yield control to event loop
    return x * x


def blocking_cpu_bound_operation(n: int) -> int:
    """Simulates a blocking synchronous CPU computation that should be offloaded."""
    # Pure CPU work
    total = 0
    for i in range(n):
        total += i
    return total


async def worker_with_lifecycle(worker_id: str, log: list) -> str:
    """Demonstrates cooperative scheduling order."""
    log.append(f"{worker_id}_started")
    await asyncio.sleep(0.002)  # Yields control
    log.append(f"{worker_id}_resumed")
    return f"{worker_id}_done"


def run_tests():
    # ============================================================
    # 1. LAZY COROUTINE OBJECT VERIFICATION
    # ============================================================

    # Calling an async def function does NOT execute it; returns coroutine object
    dormant_coro = compute_square_async(5)
    assert asyncio.iscoroutine(dormant_coro) is True

    # Clean up un-awaited test coroutine to prevent RuntimeWarning
    dormant_coro.close()


    # ============================================================
    # 2. RUNNING ASYNC WORKFLOWS WITH asyncio.run()
    # ============================================================

    async def main_suite():
        # ------------------------------------------------------------
        # Basic Sequential Await
        # ------------------------------------------------------------
        res = await compute_square_async(7)
        assert res == 49

        # ------------------------------------------------------------
        # Concurrent Task Execution via asyncio.create_task()
        # ------------------------------------------------------------
        execution_trace = []
        task_a = asyncio.create_task(worker_with_lifecycle("TaskA", execution_trace))
        task_b = asyncio.create_task(worker_with_lifecycle("TaskB", execution_trace))

        # Both tasks start and yield cooperatively
        res_a = await task_a
        res_b = await task_b

        assert res_a == "TaskA_done"
        assert res_b == "TaskB_done"

        # Verification of cooperative interleaved execution:
        # Both started before either resumed!
        assert execution_trace == [
            "TaskA_started",
            "TaskB_started",
            "TaskA_resumed",
            "TaskB_resumed",
        ]

        # ------------------------------------------------------------
        # Offloading Blocking Sync Code via asyncio.to_thread()
        # ------------------------------------------------------------
        cpu_result = await asyncio.to_thread(blocking_cpu_bound_operation, 1000)
        assert cpu_result == sum(range(1000))

        # ------------------------------------------------------------
        # Future Object State Management
        # ------------------------------------------------------------
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()

        assert future.done() is False

        # Set result on future
        future.set_result("future_resolved_payload")
        assert future.done() is True
        assert await future == "future_resolved_payload"

    # Execute entire async test suite under clean event loop lifecycle
    asyncio.run(main_suite())


if __name__ == "__main__":
    run_tests()
    print("01_asyncio_fundamentals_and_event_loop.py tests passed!")
