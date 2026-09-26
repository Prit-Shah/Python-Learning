"""
03_threads_processes_and_gil.py

============================================================
1. CONCEPT
============================================================

Concurrency in Python is governed by three distinct execution models and the
Global Interpreter Lock (GIL) in CPython:

1. The Concurrency Triad:
   +--------------------+--------------------------------+--------------------------------------+
   | Model              | Best For                       | Execution Mechanism                  |
   +--------------------+--------------------------------+--------------------------------------+
   | `asyncio`          | High-concurrency network I/O   | Single OS thread, cooperative events |
   | `ThreadPoolExecutor`| Blocking synchronous I/O, C-ext| Native OS threads, shared memory     |
   | `ProcessPoolExecutor`| Heavy CPU calculations, math | Separate OS processes, bypasses GIL  |
   +--------------------+--------------------------------+--------------------------------------+

2. The Global Interpreter Lock (GIL):
   - A mutex in CPython that restricts execution of Python bytecode to a single
     native thread at any given moment.
   - Why it exists: CPython's memory management relies heavily on reference
     counting (`ob_refcnt`). Without a global mutex, every reference increment
     and decrement would require fine-grained atomic locking, crippling single-threaded
     performance by 30-50%.
   - When the GIL is released: CPython explicitly releases the GIL during blocking
     system calls (socket read/write, disk I/O, sleep) and within computational C
     extensions (NumPy, PyTorch, OpenCV).
   - PEP 703 (Free-threaded Python): Python 3.13 introduces experimental builds
     allowing the GIL to be disabled via mimalloc thread-safe memory architectures.

3. Multithreading (`concurrent.futures.ThreadPoolExecutor`):
   - Allocates native OS threads sharing the same process memory space.
   - Ideal for concurrent file reading, database queries with synchronous drivers,
     or interacting with AWS SDKs (`boto3`).
   - Anti-pattern: Running pure Python CPU loops across threads causes threads to
     fight for the GIL, making multi-threaded execution SLOWER than single-threaded!

4. Multiprocessing (`concurrent.futures.ProcessPoolExecutor`):
   - Spawns independent operating system processes, each running its own isolated
     CPython interpreter and memory heap.
   - Completely bypasses the GIL, enabling 100% utilization of all physical CPU cores.
   - Inter-Process Communication (IPC): Objects passed into processes and returned
     from processes must be serializable via `pickle`.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python                             | JavaScript / TypeScript (Node.js)  |
+------------------------------+------------------------------------+------------------------------------+
| Cooperative Async Loop       | `asyncio`                          | Native Node.js Event Loop          |
| Thread Pool                  | `ThreadPoolExecutor`               | Node.js `worker_threads` (libuv)   |
| Multi-Core Parallelism       | `ProcessPoolExecutor` / `multiprocessing`| `cluster` module / `child_process`|
| Memory Isolation             | Separate heap per process          | Separate V8 isolate per worker     |
| Data Serialization           | `pickle`                           | `structuredClone` / JSON IPC       |
| Interpreter Thread Lock      | GIL (CPython)                      | Single-threaded V8 execution       |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Concurrency Differences:
1. In Node.js, JavaScript execution is strictly single-threaded per V8 isolate;
   there is no GIL because worker threads do not share execution state.
2. In Python, multiple native OS threads CAN exist in a single process and share
   objects directly in memory, but CPython's GIL serializes the execution of pure
   Python bytecode instructions.


============================================================
3. UNDER THE HOOD (CPython & Memory)
============================================================

1. The GIL Mutex Mechanics:
   - Implemented in CPython as a condition variable (`take_gil` and `drop_gil`).
   - A thread holds the GIL while executing bytecode. Every `sys.getswitchinterval()`
     seconds (default 0.005s / 5ms), the active thread drops the GIL and checks
     if another waiting thread requested it.
   - For I/O operations, CPython wraps the syscall in `Py_BEGIN_ALLOW_THREADS`
     and `Py_END_ALLOW_THREADS` C macros, releasing the GIL during the OS wait.

2. Pickling & IPC Overhead:
   - When submitting tasks to `ProcessPoolExecutor`:
     1. The master process serializes function arguments with `pickle.dumps()`.
     2. Bytes are transferred across an OS pipe or socket to the worker process.
     3. The worker deserializes arguments with `pickle.loads()`, executes the function,
        and pickles the return value back across the pipe.
   - Rule: For tiny computations, IPC serialization latency exceeds the parallel speedup.
     Reserve `ProcessPoolExecutor` for batch, heavy CPU computations.


============================================================
4. COMMON GOTCHAS
============================================================

1. The CPU Multithreading Anti-Pattern:
   - Writing `with ThreadPoolExecutor() as p: p.map(cpu_work, data)`.
   - Result: Threads spend more time context-switching and fighting for the GIL
     than doing real work! Always use `ProcessPoolExecutor` for CPU-bound tasks.

2. The Unpicklable Argument Crash:
   - Passing lambdas, generators, or open file descriptors to `ProcessPoolExecutor` raises:
     `_pickle.PicklingError: Can't pickle <function <lambda>>`.
   - Fix: Only pass top-level module functions and standard serializable data types.

3. Missing `if __name__ == '__main__':` Guard on Windows:
   - On Windows, multiprocessing creates worker processes by re-importing the main module!
   - Without the `if __name__ == '__main__':` guard, child processes recursively spawn
     infinite child processes in an explosive process fork bomb!


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "What is the Global Interpreter Lock (GIL) and why does CPython use it?"
Script:
"The Global Interpreter Lock (GIL) is a mutual exclusion lock used by CPython to ensure
that only one native thread executes Python bytecode at any given moment. CPython's memory
management architecture relies on reference counting (`ob_refcnt`). Without a global mutex,
every single variable assignment, function argument pass, and attribute access across concurrent
threads would require atomic operations or fine-grained locks, degrading single-threaded
performance by up to 50 percent. While the GIL restricts pure Python CPU parallelism on
threads, it is released during blocking system I/O and within numerical C extensions like
NumPy, making multithreading highly effective for I/O-bound workloads."

Q2: "How do you decide between asyncio, ThreadPoolExecutor, and ProcessPoolExecutor in production?"
Script:
"The decision follows a clear architectural matrix:
First, for high-volume I/O-bound operations using modern asynchronous libraries—such as
FastAPI endpoints, streaming chat handlers, or web scraping—I use `asyncio`. It handles
tens of thousands of concurrent connections with minimal memory overhead on a single thread.
Second, for I/O-bound operations that rely on legacy synchronous SDKs—such as AWS Boto3
or synchronous database drivers—I use `ThreadPoolExecutor` or `asyncio.to_thread()`, since
the GIL is released during system I/O.
Third, for heavy CPU-bound tasks—such as image processing, tokenization, or numerical crunching—I
use `ProcessPoolExecutor`. Spawning independent OS processes bypasses the GIL entirely and
harnesses all physical CPU cores."

Q3: "Why is pickling relevant to multiprocessing, and what constraints does it impose?"
Script:
"Because `ProcessPoolExecutor` runs worker tasks in separate OS processes with independent
virtual memory spaces, objects cannot be shared directly via memory pointers. CPython uses
the `pickle` protocol to serialize functions, arguments, and return values into byte streams
transmitted across inter-process pipes. This imposes two strict constraints: first, all arguments
and return values must be picklable, excluding lambdas, open file descriptors, and active
database connections. Second, inter-process communication carries serialization overhead,
meaning tasks must be sufficiently coarse-grained to ensure that parallel speedup outweighs
the IPC transfer cost."
"""

import concurrent.futures
import math
import sys
import time

# Ensure UTF-8 standard output across environments
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# Top-level standalone functions (must be picklable for ProcessPoolExecutor)
def cpu_heavy_factorial_sum(n: int) -> int:
    """CPU-bound task: computes sum of digits in large factorials."""
    val = math.factorial(n)
    return sum(int(d) for d in str(val))


def simulated_io_operation(identifier: str, duration: float = 0.005) -> str:
    """I/O-bound task: simulates blocking I/O that releases the GIL during sleep."""
    time.sleep(duration)
    return f"processed_{identifier}"


def run_tests():
    # ============================================================
    # 1. THREAD POOL FOR I/O-BOUND CONCURRENCY
    # ============================================================

    # ThreadPoolExecutor is ideal for I/O-bound tasks where GIL is released
    io_items = ["file_a", "file_b", "file_c", "file_d"]

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as thread_pool:
        # map() runs tasks concurrently and returns results in submission order
        thread_results = list(thread_pool.map(simulated_io_operation, io_items))

    assert len(thread_results) == 4
    assert thread_results == [
        "processed_file_a",
        "processed_file_b",
        "processed_file_c",
        "processed_file_d",
    ]


    # ============================================================
    # 2. PROCESS POOL FOR CPU-BOUND PARALLELISM
    # ============================================================

    # ProcessPoolExecutor bypasses the GIL across separate OS processes
    cpu_inputs = [50, 75, 100, 125]

    with concurrent.futures.ProcessPoolExecutor(max_workers=2) as process_pool:
        process_results = list(process_pool.map(cpu_heavy_factorial_sum, cpu_inputs))

    assert len(process_results) == 4
    # Verify calculated values are non-zero integers
    for res in process_results:
        assert isinstance(res, int)
        assert res > 0

    # Verification of exact computation for n=50
    # 50! digit sum
    assert process_results[0] == cpu_heavy_factorial_sum(50)


    # ============================================================
    # 3. FUTURE OBJECT LIFECYCLE IN EXECUTORS
    # ============================================================

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        # submit() returns a Future object immediately
        future: concurrent.futures.Future = executor.submit(simulated_io_operation, "manual_job", 0.001)

        # Future resolves with result()
        result_value = future.result(timeout=2.0)
        assert result_value == "processed_manual_job"
        assert future.done() is True
        assert future.cancelled() is False


if __name__ == "__main__":
    run_tests()
    print("03_threads_processes_and_gil.py tests passed!")
