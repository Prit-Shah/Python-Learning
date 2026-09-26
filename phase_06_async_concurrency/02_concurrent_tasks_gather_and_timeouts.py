"""
02_concurrent_tasks_gather_and_timeouts.py

============================================================
1. CONCEPT
============================================================

Orchestrating concurrent asynchronous operations in production Python requires
controlled batch execution, strict deadlines, cooperative cancellation, and
concurrency throttling:

1. Batch Concurrency with `asyncio.gather`:
   - Schedules multiple coroutines or Tasks concurrently and returns their
     results in an ordered list matching the input argument order.
   - `return_exceptions=False` (default): If any task raises an exception, `gather`
     raises that exception immediately, while other tasks continue running in the background.
   - `return_exceptions=True`: All tasks run to completion or failure; raised exceptions
     are captured and returned as object values in the results list (identical to
     `Promise.allSettled`).

2. Modern Structured Concurrency (`asyncio.TaskGroup` - Python 3.11+):
   - Introduced in PEP 654 as a cleaner, safer alternative to `gather`.
   - Used as an asynchronous context manager: `async with asyncio.TaskGroup() as tg:`.
   - If any task inside the group raises an unhandled error, `TaskGroup` automatically
     cancels all other sibling tasks in the group, re-raising them as an `ExceptionGroup`.
   - Guarantees that no dangling background tasks leak outside the scope!

3. Deadlines & Timeouts (`asyncio.wait_for` and `asyncio.timeout`):
   - `asyncio.wait_for(coro, timeout=seconds)`: Waits for completion; if timeout
     expires, cancels the task and raises `asyncio.TimeoutError`.
   - Python 3.11+ `async with asyncio.timeout(seconds):`: Context manager setting
     a strict cumulative deadline across multiple sequential `await` operations.

4. Task Cancellation Mechanics:
   - Calling `task.cancel()` injects an `asyncio.CancelledError` into the coroutine
     at its next `await` suspension point.
   - In Python 3.8+, `CancelledError` inherits directly from `BaseException`
     (not `Exception`). Standard `except Exception:` blocks will NOT inadvertently
     swallow cancellation requests.

5. Concurrency Throttling with `asyncio.Semaphore`:
   - Bounds the maximum number of concurrent tasks accessing a shared resource
     (e.g., third-party API rate limits, database connection limits).
   - Acquired via `async with semaphore:`. If the limit is reached, incoming
     tasks pause without blocking the event loop until a slot is freed.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python (asyncio)                   | JavaScript / TypeScript (Node.js)  |
+------------------------------+------------------------------------+------------------------------------+
| Batch Execution (Fast-Fail)  | `asyncio.gather(..., ret_exc=False)`| `Promise.all([ ... ])`            |
| Batch Execution (All Results)| `asyncio.gather(..., ret_exc=True)` | `Promise.allSettled([ ... ])`     |
| Structured Task Group        | `async with asyncio.TaskGroup():`  | No native keyword (manual cleanup) |
| Timeout Wrapper              | `asyncio.wait_for(coro, timeout)`  | `AbortSignal.timeout(ms)` / Promise.race|
| Cumulative Timeout Context   | `async with asyncio.timeout(sec):` | Custom timeout controller          |
| Task Cancellation Signal     | `task.cancel()`                    | `abortController.abort()`          |
| Concurrency Limiter          | `asyncio.Semaphore(max_parallel)`  | `p-limit` / semaphore library      |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Concurrency Differences:
1. In JavaScript, `Promise.all()` rejects as soon as the first promise rejects,
   but the other promises continue executing invisibly in the background.
   In Python 3.11+ `asyncio.TaskGroup`, an error in one child task actively triggers
   immediate cancellation of all sibling tasks in the group, preventing wasted
   cloud spend and orphaned database locks.
2. In Python, task cancellation is cooperative; a cancelled task can catch
   `asyncio.CancelledError` in a `finally` block to cleanly commit or rollback state.


============================================================
3. UNDER THE HOOD (CPython & Memory)
============================================================

1. Task Cancellation Injection:
   - When `task.cancel()` is invoked, CPython marks the internal task flag `_must_cancel = True`.
   - At the next event loop iteration when the task is scheduled to resume, instead of
     invoking `coroutine.send(val)`, the event loop calls `coroutine.throw(asyncio.CancelledError)`.
   - If the task does not catch the exception or re-raises it, the task transitions
     to the `CANCELLED` state.

2. Semaphore Internal Queue:
   - `asyncio.Semaphore` maintains an internal integer counter `_value` and a `collections.deque`
     of pending `Future` objects.
   - When `_value > 0`, acquiring the semaphore decrements `_value` in $O(1)$ time.
   - When `_value == 0`, the acquiring task creates an unresolved Future and suspends.
   - When an active task exits the context manager, it increments `_value` or resolves
     the next waiting Future in the FIFO queue.


============================================================
4. COMMON GOTCHAS
============================================================

1. Swallowing `CancelledError`:
   - Catching `except BaseException:` without re-raising `CancelledError` causes
     the task to ignore cancellation requests, hanging server shutdown sequences.
   - Always re-raise:
     ```python
     except asyncio.CancelledError:
         cleanup()
         raise
     ```

2. Relying on Default `gather(return_exceptions=False)`:
   - In a batch of 1,000 API calls, if call #5 fails, `gather` raises immediately,
     causing you to lose the return data of all 999 other successful requests!
   - For batch ETL or API aggregations, always use `return_exceptions=True`.

3. Unbounded Concurrency Memory Exhaustion:
   - Spawning 100,000 tasks concurrently with `asyncio.gather(*tasks)` without a
     semaphore opens 100,000 simultaneous sockets, exhausting OS file descriptors (`EMFILE`).
   - Always gate concurrent bursts behind an `asyncio.Semaphore`.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "How does asyncio.gather differ between return_exceptions=False and return_exceptions=True?"
Script:
"`asyncio.gather` coordinates the concurrent execution of multiple awaitables, returning
their results in an ordered list that strictly matches the input arguments. By default,
`return_exceptions=False` mirrors JavaScript's `Promise.all`: if any task encounters an
exception, `gather` aborts immediately and raises that exception to the caller. However,
the other tasks are not cancelled—they continue running unobserved. When set to
`return_exceptions=True`, `gather` mirrors `Promise.allSettled`: it guarantees all tasks run
to completion, returning successful values and exception instances side-by-side in the results
list. This allows production services to process partial successes and route failures to
dead-letter queues."

Q2: "What is structured concurrency and how does asyncio.TaskGroup improve on gather?"
Script:
"Structured concurrency, introduced in Python 3.11 via `asyncio.TaskGroup`, treats concurrent
tasks as bound within a strict lexical scope, mirroring how synchronous control flow statements
behave. With `TaskGroup`, all child tasks are guaranteed to finish before the context manager
exits. If any task raises an unhandled exception, `TaskGroup` immediately cancels all other
still-running sibling tasks in the group and bundles all resulting failures into an `ExceptionGroup`.
This completely prevents orphaned background tasks from leaking resources, exhausting connections,
or failing silently."

Q3: "How does asyncio.Semaphore prevent service outages when calling external APIs?"
Script:
"When invoking external APIs, spawning unbounded concurrent tasks can trigger HTTP 429
rate-limiting, exhaust local socket descriptors, or overwhelm downstream database connection
pools. An `asyncio.Semaphore(N)` limits the degree of parallelism by maintaining a counter
of available execution permits. By wrapping requests in `async with semaphore:`, only N tasks
can execute network I/O simultaneously. Additional tasks yield control and pause on the event
loop in a FIFO queue without blocking other application traffic, providing smooth, deterministic
traffic shaping."
"""

import asyncio
import sys

# Ensure UTF-8 standard output across environments
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ============================================================
# SIMULATED ASYNC ENDPOINTS
# ============================================================

async def fetch_price_feed(ticker: str, delay: float = 0.001) -> float:
    """Simulates successful external stock price lookup."""
    await asyncio.sleep(delay)
    mock_prices = {"AAPL": 185.50, "MSFT": 420.00, "GOOG": 175.25}
    if ticker not in mock_prices:
        raise KeyError(f"Ticker '{ticker}' not supported")
    return mock_prices[ticker]


async def slow_hanging_service() -> str:
    """Simulates an endpoint that hangs indefinitely."""
    await asyncio.sleep(10.0)
    return "completed"


async def worker_with_cancellation_cleanup(cleanup_tracker: list) -> str:
    """Demonstrates handling asyncio.CancelledError cleanly."""
    try:
        cleanup_tracker.append("worker_started")
        await asyncio.sleep(5.0)
        return "unreachable"
    except asyncio.CancelledError:
        cleanup_tracker.append("cancellation_caught_and_cleaned")
        raise  # Must re-raise to complete cancellation!


def run_tests():
    async def main_suite():
        # ============================================================
        # 1. BATCH CONCURRENCY: gather with return_exceptions=True
        # ============================================================

        tickers = ["AAPL", "UNKNOWN_TICKER", "MSFT"]
        tasks = [fetch_price_feed(t) for t in tickers]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Order matches input list
        assert len(results) == 3
        assert results[0] == 185.50
        # Failed lookup returns KeyError instance as a value!
        assert isinstance(results[1], KeyError)
        assert results[2] == 420.00


        # ============================================================
        # 2. STRUCTURED CONCURRENCY: asyncio.TaskGroup (Python 3.11+)
        # ============================================================

        collected_results = {}
        async with asyncio.TaskGroup() as tg:
            # Spawn multiple concurrent tasks inside the group
            t1 = tg.create_task(fetch_price_feed("AAPL"))
            t2 = tg.create_task(fetch_price_feed("MSFT"))

        # Both tasks guaranteed to be completed upon exiting with block
        assert t1.result() == 185.50
        assert t2.result() == 420.00


        # ============================================================
        # 3. DEADLINES & TIMEOUTS (asyncio.wait_for and asyncio.timeout)
        # ============================================================

        # asyncio.wait_for cancels task on timeout
        timed_out = False
        try:
            await asyncio.wait_for(slow_hanging_service(), timeout=0.01)
        except asyncio.TimeoutError:
            timed_out = True
        assert timed_out is True

        # Python 3.11+ asyncio.timeout context manager
        context_timed_out = False
        try:
            async with asyncio.timeout(0.01):
                await slow_hanging_service()
        except TimeoutError:
            context_timed_out = True
        assert context_timed_out is True


        # ============================================================
        # 4. TASK CANCELLATION & CLEANUP
        # ============================================================

        cleanup_log = []
        task = asyncio.create_task(worker_with_cancellation_cleanup(cleanup_log))

        # Allow task to start execution
        await asyncio.sleep(0.001)
        assert cleanup_log == ["worker_started"]

        # Cancel task
        task.cancel()

        # Awaiting cancelled task raises CancelledError
        cancelled_caught = False
        try:
            await task
        except asyncio.CancelledError:
            cancelled_caught = True

        assert cancelled_caught is True
        assert task.cancelled() is True
        # Verify cleanup code inside finally/except block ran
        assert cleanup_log == ["worker_started", "cancellation_caught_and_cleaned"]


        # ============================================================
        # 5. CONCURRENCY THROTTLING (asyncio.Semaphore)
        # ============================================================

        sem = asyncio.Semaphore(2)  # Max 2 concurrent tasks
        active_counter = 0
        peak_concurrency = 0

        async def throttled_job(job_id: int):
            nonlocal active_counter, peak_concurrency
            async with sem:
                active_counter += 1
                peak_concurrency = max(peak_concurrency, active_counter)
                await asyncio.sleep(0.005)
                active_counter -= 1
                return job_id

        # Launch 6 tasks concurrently
        job_tasks = [throttled_job(i) for i in range(6)]
        job_results = await asyncio.gather(*job_tasks)

        assert job_results == [0, 1, 2, 3, 4, 5]
        # Peak concurrency never exceeded semaphore capacity of 2!
        assert peak_concurrency <= 2

    # Execute entire async test suite under clean event loop lifecycle
    asyncio.run(main_suite())


if __name__ == "__main__":
    run_tests()
    print("02_concurrent_tasks_gather_and_timeouts.py tests passed!")
