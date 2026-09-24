"""
Phase 6: Async & Concurrency - Asyncio Fundamentals & The Event Loop
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - Python 'asyncio' is a built-in library for writing concurrent code using the async/await syntax.
   - Coroutine vs Task:
     * Calling 'async def f():' does NOT start execution! It returns a dormant 'coroutine' object.
     * To run it, you must either:
       1) 'await f()' (runs sequentially in the current context).
       2) 'asyncio.create_task(f())' (schedules it on the event loop as a concurrent Task).
       3) 'asyncio.run(f())' (creates a fresh event loop, executes to completion, and cleans up).
   - Event Loop Model:
     * Single-threaded cooperative multitasking.
     * Tasks yield control at 'await' points (I/O, timers, socket reads).
     * If a task executes blocking synchronous CPU code, the ENTIRE event loop freezes!
   - JS/TS Analogy:
     * In JavaScript, calling an async function immediately runs synchronously until the first await,
       returning a "hot" Promise that is already scheduled.
     * In Python, calling an async function creates a "lazy" coroutine object that stays completely
       dormant until scheduled or awaited.
     * In Node.js, the event loop runs automatically. In Python, you start it with 'asyncio.run()'.

2. UNDER THE HOOD (CPython & Memory):
   - Coroutines in Python are state machines implemented on top of generator machinery (PEP 492).
   - When a coroutine awaits, CPython pauses the frame, stores its local variables on the heap,
     and hands execution back to the event loop selector (epoll on Linux, IOCP on Windows).
   - When the I/O event is ready, the event loop resumes the frame via 'coroutine.send()'.

3. COMMON GOTCHA:
   - THE UN-AWAITED COROUTINE:
     async def get_data(): return 42
     get_data() # BUG: RuntimeWarning: coroutine 'get_data' was never awaited!
   - BLOCKING THE EVENT LOOP:
     Calling 'time.sleep(5)' or synchronous database calls inside async def blocks ALL concurrent
     tasks from progressing! Always use 'await asyncio.sleep(5)' or 'await asyncio.to_thread(...)'.

4. 🎙️ INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   -----------------------------------------------------------------------------
   Q: "How does asyncio in Python differ from JavaScript Promises and the Node.js event
       loop, and what happens when an async def function is called?"
   
   HOW TO ANSWER OUT LOUD (60-90 sec script):
   1. Hot Promises vs Lazy Coroutines:
      "The most critical semantic difference between Node.js and Python asyncio is eager vs lazy execution:
       - In JavaScript, invoking an async function immediately executes up to the first await and returns
         a 'hot' Promise that is already queued in the microtask queue.
       - In Python, invoking an 'async def' function does NOT execute anything; it creates a lazy
         coroutine object. It will not run until it is explicitly awaited or converted into a scheduled
         Task via 'asyncio.create_task()'."
   2. Event Loop Lifecycle:
      "In Node.js, the runtime event loop is global and starts automatically with the V8 engine.
       In Python, the event loop must be explicitly managed, typically by calling 'asyncio.run(main())'
       as the application entry point or managed by an ASGI server like Uvicorn in FastAPI."
   3. The Anti-Pattern:
      "Never call blocking synchronous I/O or 'time.sleep()' inside an async function. Since asyncio
       is cooperative and runs on a single OS thread, blocking code halts all other concurrent tasks.
       For blocking operations, always offload them to worker threads via 'asyncio.to_thread()'."
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
# DEMONSTRATIONS: Coroutines, Tasks, and Scheduling
# ==============================================================================

async def simulate_io_operation(task_id: int, delay: float) -> str:
    """Simulates a non-blocking asynchronous I/O operation (e.g. DB or API query)."""
    print(f"  [Task {task_id}] Started (will take {delay:.1f}s)...")
    await asyncio.sleep(delay)  # Yields control back to event loop!
    print(f"  [Task {task_id}] Finished!")
    return f"Result-{task_id}"


async def demonstrate_sequential_vs_concurrent():
    print("\n--- 1. Sequential Await vs Concurrent Tasks ---")
    
    # Sequential execution: 0.2s + 0.2s = ~0.4s
    t0 = time.perf_counter()
    print("  Running sequentially with 'await':")
    res1 = await simulate_io_operation(1, 0.2)
    res2 = await simulate_io_operation(2, 0.2)
    duration_seq = time.perf_counter() - t0
    print(f"  Sequential Duration: {duration_seq:.2f}s (Expected ~0.4s)")

    # Concurrent execution using asyncio.create_task(): both overlap in ~0.2s
    t0 = time.perf_counter()
    print("\n  Running concurrently with 'asyncio.create_task()':")
    task1 = asyncio.create_task(simulate_io_operation(3, 0.2))
    task2 = asyncio.create_task(simulate_io_operation(4, 0.2))
    
    # Both tasks are now running concurrently on the event loop
    res3 = await task1
    res4 = await task2
    duration_conc = time.perf_counter() - t0
    print(f"  Concurrent Duration: {duration_conc:.2f}s (Expected ~0.2s -> 2x speedup!)")


async def demonstrate_lazy_coroutine_object():
    print("\n--- 2. Inspecting Lazy Coroutine Objects ---")
    # Calling async function returns coroutine object without executing it!
    coro = simulate_io_operation(99, 0.1)
    print(f"  Type of un-awaited call: {type(coro).__name__}")
    print(f"  Is coroutine? {asyncio.iscoroutine(coro)}")
    
    # Now await it to actually execute
    result = await coro
    print(f"  Awaited execution result: '{result}'")


# ==============================================================================
# SELF-TEST CHALLENGES
# ==============================================================================

async def async_multiplier(x: int, delay: float = 0.05) -> int:
    """Multiplies input by 2 after a simulated async delay."""
    await asyncio.sleep(delay)
    return x * 2


async def run_challenges():
    print("\n[*] Running automated self-tests for 01_asyncio_fundamentals_and_event_loop.py...")
    # Challenge: Schedule 3 tasks concurrently and verify total duration is ~0.05s, not 0.15s
    t0 = time.perf_counter()
    t1 = asyncio.create_task(async_multiplier(10))
    t2 = asyncio.create_task(async_multiplier(20))
    t3 = asyncio.create_task(async_multiplier(30))

    results = [await t1, await t2, await t3]
    elapsed = time.perf_counter() - t0

    assert results == [20, 40, 60], f"Expected [20, 40, 60], got {results}"
    assert elapsed < 0.12, f"Expected concurrency under 0.12s, took {elapsed:.2f}s"
    print("[SUCCESS] All self-tests passed cleanly!")


def main():
    print("=" * 65)
    print("Execution: Phase 6 - Asyncio Fundamentals & Event Loop")
    print("=" * 65)
    asyncio.run(demonstrate_sequential_vs_concurrent())
    asyncio.run(demonstrate_lazy_coroutine_object())
    print("-" * 65)
    asyncio.run(run_challenges())
    print("=" * 65)


if __name__ == "__main__":
    main()
