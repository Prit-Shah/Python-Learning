"""
Phase 6: Async & Concurrency - Threads, Processes & The GIL Explained
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - Python Concurrency Triad:
     * 1. Asyncio: Single-thread cooperative multitasking for high-volume I/O (network/API).
     * 2. Multithreading ('concurrent.futures.ThreadPoolExecutor'): OS threads. Good for I/O and
          third-party C-extensions (NumPy, OpenCV) that explicitly release the GIL.
     * 3. Multiprocessing ('concurrent.futures.ProcessPoolExecutor'): Spawns separate OS processes,
          each with its own independent CPython interpreter and memory space. Bypasses the GIL
          for true multi-core CPU-bound parallelism!
   - What is the GIL (Global Interpreter Lock)?
     * A mutual exclusion lock in CPython ensuring only one native thread executes Python bytecode
       at any given moment.
     * Threading will NOT speed up pure Python CPU calculations (in fact, GIL lock contention
       makes multi-threaded CPU work SLOWER than single-threaded!).
   - Offloading in Asyncio:
     * 'asyncio.to_thread(func, *args)': Offloads blocking synchronous functions to a background
       thread pool without blocking the async event loop (Python 3.9+).
   - JS/TS Analogy:
     * Asyncio -> Node.js event loop.
     * Multithreading / ThreadPool -> Node libuv worker threads.
     * Multiprocessing / ProcessPool -> Node 'cluster' module / child_process.fork().

2. UNDER THE HOOD (CPython & Memory):
   - The GIL exists because CPython's memory manager uses reference counting ('ob_refcnt'). Without
     a global lock, every reference increment/decrement would require fine-grained atomic locking,
     introducing severe overhead for single-threaded code.
   - When Python makes an OS I/O call (e.g. read socket or file), CPython explicitly releases the GIL.

3. COMMON GOTCHA:
   - Attempting CPU parallelization with threads:
     with ThreadPoolExecutor() as executor:
         executor.map(cpu_heavy_task, numbers) # BUG: Fights over the GIL! Use ProcessPoolExecutor.
   - Pickling errors in Multiprocessing: Arguments passed to ProcessPoolExecutor must be serializable
     (picklable) to pass across process boundaries (no lambdas or open file handles).

4. 🎙️ INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   -----------------------------------------------------------------------------
   Q: "Explain the GIL, and detail when you choose between asyncio, threading, and
       multiprocessing for production Python workloads."
   
   HOW TO ANSWER OUT LOUD (60-90 sec script):
   1. The GIL Definition:
      "The Global Interpreter Lock (GIL) is a mutex in CPython that restricts execution of Python
       bytecode to a single OS thread at a time, protecting CPython's reference counting memory model
       against race conditions."
   2. The Decision Matrix:
      "Because of the GIL, I select concurrency tools based on the nature of the workload:
       1. I/O-Bound with High Concurrency (FastAPI, Web scraping, Chatbots): Use 'asyncio'.
          It provides high throughput with minimal memory overhead, handling tens of thousands
          of concurrent socket connections on a single OS thread.
       2. I/O-Bound with Legacy Synchronous SDKs (Boto3, legacy DB drivers): Use 'ThreadPoolExecutor'
          or 'asyncio.to_thread()'. The GIL is released during system calls, allowing true concurrent I/O.
       3. CPU-Bound (ML inference, tokenization, image transformations): Use 'ProcessPoolExecutor'.
          By spawning distinct OS processes with independent memory spaces and separate CPython
          interpreters, we bypass the GIL and utilize all CPU cores."
================================================================================
"""

import sys
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ==============================================================================
# CPU-BOUND VS I/O-BOUND WORKLOAD SIMULATIONS
# ==============================================================================

def cpu_heavy_calculation(n: int) -> int:
    """Pure CPU computation: counting sum of squares."""
    count = 0
    for i in range(n):
        count += i * i
    return count


def blocking_io_task(name: str, duration: float = 0.1) -> str:
    """Simulates a legacy blocking synchronous I/O call."""
    time.sleep(duration)
    return f"Completed {name}"


def demonstrate_gil_with_threadpool():
    print("\n--- 1. ThreadPool for I/O vs CPU Tasks ---")
    
    # 1. ThreadPool with blocking I/O: Releases GIL, achieves concurrent speedup!
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(blocking_io_task, ["taskA", "taskB", "taskC"]))
    duration_io = time.perf_counter() - t0
    print(f"  ThreadPool on 3 I/O tasks: {duration_io:.2f}s (Concurrent speedup: ~0.1s instead of 0.3s!)")
    print(f"  Results: {results}")

    # 2. CPU task: Notice threads fight over the single GIL
    size = 2_000_000
    t0 = time.perf_counter()
    cpu_heavy_calculation(size)
    cpu_heavy_calculation(size)
    serial_cpu_time = time.perf_counter() - t0
    print(f"\n  Serial CPU calculation (2 runs): {serial_cpu_time:.3f}s")

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(cpu_heavy_calculation, [size, size]))
    thread_cpu_time = time.perf_counter() - t0
    print(f"  ThreadPool CPU calculation (2 threads): {thread_cpu_time:.3f}s (NO speedup due to GIL!)")


async def demonstrate_asyncio_to_thread():
    print("\n--- 2. Offloading Blocking Functions via asyncio.to_thread ---")
    t0 = time.perf_counter()
    
    # Run blocking I/O in worker thread without halting the async loop
    task1 = asyncio.to_thread(blocking_io_task, "Legacy-Client-1", 0.1)
    task2 = asyncio.to_thread(blocking_io_task, "Legacy-Client-2", 0.1)
    
    res1, res2 = await asyncio.gather(task1, task2)
    duration = time.perf_counter() - t0
    print(f"  Offloaded two blocking calls concurrently: took {duration:.2f}s (Expected ~0.1s)")
    print(f"  Returned: '{res1}' and '{res2}'")


# ==============================================================================
# SELF-TEST CHALLENGES
# ==============================================================================

async def async_safe_blocking_call(val: int) -> int:
    """Wraps synchronous computation in asyncio.to_thread."""
    def _sync_work(x: int) -> int:
        time.sleep(0.02)
        return x * 10

    return await asyncio.to_thread(_sync_work, val)


async def run_challenges():
    print("\n[*] Running automated self-tests for 03_threads_processes_and_gil.py...")
    # Test concurrent offloaded tasks
    t0 = time.perf_counter()
    tasks = [async_safe_blocking_call(i) for i in [1, 2, 3]]
    results = await asyncio.gather(*tasks)
    elapsed = time.perf_counter() - t0

    assert results == [10, 20, 30]
    assert elapsed < 0.08, f"Expected concurrency under 0.08s, took {elapsed:.2f}s"
    print("[SUCCESS] All self-tests passed cleanly!")


def main():
    print("=" * 65)
    print("Execution: Phase 6 - Threads, Processes & The GIL")
    print("=" * 65)
    demonstrate_gil_with_threadpool()
    asyncio.run(demonstrate_asyncio_to_thread())
    print("-" * 65)
    asyncio.run(run_challenges())
    print("=" * 65)


if __name__ == "__main__":
    main()
