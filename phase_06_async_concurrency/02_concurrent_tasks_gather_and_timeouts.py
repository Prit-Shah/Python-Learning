"""
Phase 6: Async & Concurrency - Task Gathering, Timeouts & Rate Limiting
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - 'asyncio.gather(*coros_or_tasks, return_exceptions=False)':
     * Runs multiple coroutines concurrently and returns their results in order.
     * If 'return_exceptions=False' (default): A single failure immediately raises, masking others.
     * If 'return_exceptions=True': Exceptions are returned as values in the results list!
   - Timeouts with 'asyncio.wait_for(coro, timeout=seconds)':
     * Cancels the target task and raises 'asyncio.TimeoutError' if it exceeds the deadline.
     * Python 3.11+ also provides the clean context manager: 'async with asyncio.timeout(seconds):'.
   - Task Cancellation:
     * Invoking 'task.cancel()' raises 'asyncio.CancelledError' at the task's next await point.
     * Tasks can intercept CancelledError with try/finally to perform cleanup.
   - Concurrency Throttling with 'asyncio.Semaphore(max_concurrency)':
     * Prevents overwhelming downstream servers or exhausting connection pools.
     * Only 'max_concurrency' tasks can enter the 'async with sem:' block simultaneously.
   - JS/TS Analogy:
     * 'Promise.all()' -> 'asyncio.gather(..., return_exceptions=False)'.
     * 'Promise.allSettled()' -> 'asyncio.gather(..., return_exceptions=True)'.
     * 'AbortController' / 'signal.abort()' -> 'task.cancel()'.
     * 'p-limit' library -> 'asyncio.Semaphore'.

2. UNDER THE HOOD (CPython & Memory):
   - 'asyncio.gather' wraps input coroutines into Tasks (if not already Tasks) and registers
     callbacks on their completion. It maintains an internal counter of finished tasks.
   - 'CancelledError' is a subclass of 'BaseException' (Python 3.8+), so catching 'except Exception:'
     will NOT accidentally swallow cancellation signals!

3. COMMON GOTCHA:
   - Forgetting 'return_exceptions=True' in batch operations: If 1 out of 100 API calls fails,
     gather raises immediately, losing track of the 99 successful results.
   - Swallowing 'CancelledError': If you catch 'except BaseException:' without re-raising,
     the task will refuse to terminate!

4. 🎙️ INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   -----------------------------------------------------------------------------
   Q: "How do you handle batch concurrency, timeouts, and rate limiting in asyncio?"
   
   HOW TO ANSWER OUT LOUD (60-90 sec script):
   1. Batching with asyncio.gather:
      "When orchestrating multiple concurrent operations, I use 'asyncio.gather()'.
       In production services, I almost always set 'return_exceptions=True', which behaves like
       JavaScript's Promise.allSettled(). It ensures that a single transient network failure
       does not abort the entire batch; instead, errors are returned as exception instances in the
       results array for granular inspection and retry."
   2. Strict Deadlines with Timeouts:
      "To prevent external dependencies from holding open connections indefinitely, I wrap operations
       in 'asyncio.wait_for(task, timeout=seconds)'. When the timeout expires, asyncio automatically
       cancels the underlying task, triggering CancelledError."
   3. Rate Limiting with Semaphores:
      "To avoid exceeding third-party API rate limits (like OpenAI or payment gateways), I bound
       concurrency using 'asyncio.Semaphore(N)'. Every worker acquires the semaphore using
       'async with semaphore:', guaranteeing that no more than N requests run simultaneously."
================================================================================
"""

import sys
import asyncio
import time

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ==============================================================================
# DEMONSTRATIONS: Gather, Timeouts, and Semaphores
# ==============================================================================

async def fetch_user_data(user_id: int) -> dict:
    """Simulates fetching user data; fails on user_id=13."""
    await asyncio.sleep(0.05)
    if user_id == 13:
        raise ValueError("User 13 is corrupted / forbidden!")
    return {"user_id": user_id, "username": f"user_{user_id}"}


async def demonstrate_gather_with_exceptions():
    print("\n--- 1. asyncio.gather with return_exceptions=True ---")
    user_ids = [1, 2, 13, 4]
    
    # Run batch: notice user 13 raises an exception
    tasks = [fetch_user_data(uid) for uid in user_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for uid, res in zip(user_ids, results):
        if isinstance(res, Exception):
            print(f"  User {uid}: FAILED with error -> {res}")
        else:
            print(f"  User {uid}: SUCCESS -> {res['username']}")


async def demonstrate_timeouts():
    print("\n--- 2. Enforcing Strict Timeouts with asyncio.wait_for ---")
    async def slow_database_query():
        print("  Query started, requires 2.0s...")
        await asyncio.sleep(2.0)
        return "Query Results"

    try:
        # Enforce 0.2s deadline
        print("  Awaiting query with 0.2s deadline...")
        await asyncio.wait_for(slow_database_query(), timeout=0.2)
    except TimeoutError:
        print("  [TIMEOUT] Query took too long and was automatically cancelled by asyncio!")


async def demonstrate_semaphore_rate_limiting():
    print("\n--- 3. Rate Limiting with asyncio.Semaphore ---")
    # Allow at most 2 concurrent operations at a time
    sem = asyncio.Semaphore(2)
    active_workers = 0
    max_observed_concurrency = 0

    async def worker(worker_id: int):
        nonlocal active_workers, max_observed_concurrency
        async with sem:
            active_workers += 1
            max_observed_concurrency = max(max_observed_concurrency, active_workers)
            print(f"  [Worker {worker_id}] Entered critical section (Active: {active_workers})")
            await asyncio.sleep(0.05)
            active_workers -= 1
            print(f"  [Worker {worker_id}] Exited critical section")

    # Launch 6 workers concurrently
    await asyncio.gather(*(worker(i) for i in range(1, 7)))
    print(f"  Max observed concurrent workers: {max_observed_concurrency} (Bounded by Semaphore=2)")


# ==============================================================================
# SELF-TEST CHALLENGES
# ==============================================================================

async def throttled_batch_fetch(items: list[int], max_concurrent: int) -> list:
    """
    Fetches items with bounded concurrency via Semaphore.
    Returns results with exceptions captured.
    """
    sem = asyncio.Semaphore(max_concurrent)

    async def _safe_fetch(item_id: int):
        async with sem:
            await asyncio.sleep(0.02)
            if item_id < 0:
                raise ValueError(f"Negative ID: {item_id}")
            return item_id * 10

    tasks = [_safe_fetch(i) for i in items]
    return await asyncio.gather(*tasks, return_exceptions=True)


async def run_challenges():
    print("\n[*] Running automated self-tests for 02_concurrent_tasks_gather_and_timeouts.py...")
    # Test batch fetch with semaphore and error isolation
    items = [1, 2, -1, 4]
    results = await throttled_batch_fetch(items, max_concurrent=2)
    
    assert results[0] == 10
    assert results[1] == 20
    assert isinstance(results[2], ValueError)
    assert results[3] == 40
    print("[SUCCESS] All self-tests passed cleanly!")


def main():
    print("=" * 65)
    print("Execution: Phase 6 - Gather, Timeouts & Semaphores")
    print("=" * 65)
    asyncio.run(demonstrate_gather_with_exceptions())
    asyncio.run(demonstrate_timeouts())
    asyncio.run(demonstrate_semaphore_rate_limiting())
    print("-" * 65)
    asyncio.run(run_challenges())
    print("=" * 65)


if __name__ == "__main__":
    main()
