r"""
03_redis_caching_and_worker_queues.py

============================================================
1. CONCEPT
============================================================

High-throughput distributed systems rely on Redis as an in-memory data store for
sub-millisecond caching, distributed concurrency control, and asynchronous task brokering:

1. The Cache-Aside Pattern (Lazy Loading):
   - Read Workflow:
     1. Service checks Redis for key (`GET user:1001:profile`).
     2. Cache HIT: Deserializes JSON and returns response immediately (sub-millisecond latency).
     3. Cache MISS: Queries PostgreSQL primary database.
     4. Sets Redis key with an explicit Time-To-Live TTL (`SETEX user:1001:profile 300 <json>`).
     5. Returns response to client.
   - Mutation Workflow (Cache Invalidation):
     * Upon modifying the database entity (`UPDATE users ...`), immediately delete the cache
       key (`DEL user:1001:profile`). Stale data is never served, and subsequent reads lazily repopulate it.

2. The Cache Stampede (Thundering Herd) Problem & Mitigations:
   - Problem: When a heavily requested cache key (e.g. 5,000 req/sec) expires, hundreds of concurrent
     requests simultaneously experience a Cache MISS. All requests hit PostgreSQL concurrently,
     exhausting connection pools and causing database collapse.
   - Mitigation Strategies:
     * Distributed Mutex (Locking via Redis `SET lock:key token NX PX 5000`): Only the first request
       acquires the lock to query the DB and refresh the cache; all other requests wait and retry.
     * Probabilistic Early Expiration (XFetch algorithm): Recomputes the value in the background
       before the TTL expires based on request frequency.
     * Stale-While-Revalidate: Serves expired data temporarily while an async background worker fetches updates.

3. Distributed Asynchronous Worker Queues (Celery / Arq / Redis Streams):
   - Decouples heavy CPU/IO workloads (LLM generation, PDF rendering, email dispatch) from FastAPI HTTP handlers.
   - Architecture:
     * Producer: FastAPI handler enqueues a JSON task payload and returns HTTP 202 Accepted with a task ID.
     * Broker: Redis list (`LPUSH`) or Redis Stream (`XADD`) buffers the pending tasks.
     * Consumers / Workers: Independent Python worker processes pull tasks (`RPOP` / `XREADGROUP`),
       execute business logic with retries and exponential backoff, and route exhausted tasks to a
       Dead-Letter Queue (DLQ).


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python (Redis / Celery / Arq)      | JavaScript / TypeScript (Node.js)  |
+------------------------------+------------------------------------+------------------------------------+
| Redis Client                 | `redis-py` / `coredis`             | `ioredis` / `redis`                |
| Async Redis                  | `redis.asyncio`                    | Native async/await in `ioredis`    |
| Distributed Task Queue       | Celery / Arq / RQ                  | BullMQ / Bee-Queue                 |
| Worker Concurrency Model     | Multi-Process (billiard/fork)      | Multi-Thread (Worker Threads) / PM2|
| Distributed Lock             | `redis.set(..., nx=True, px=...)`  | `redlock` npm package              |
| Serialization Format         | JSON / MessagePack (avoid pickle!) | JSON / MessagePack                 |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Architecture Differences:
1. In Node.js, BullMQ runs on the single-threaded V8 event loop. Heavy CPU tasks can stall the
   event loop unless offloaded to `worker_threads`.
2. In Python, Celery uses multi-process worker pools (`prefork`) by default. Because each worker is a
   distinct operating system process with its own CPython interpreter, it completely bypasses the GIL
   and maximizes multi-core CPU utilization for CPU-bound tasks like image processing or AI token parsing.


============================================================
3. UNDER THE HOOD (Redis In-Memory Engine & Protocols)
============================================================

1. Single-Threaded Atomic Execution:
   - Redis processes all database read/write commands sequentially on a single thread using an I/O
     multiplexer (`epoll` on Linux, `kqueue` on macOS).
   - Because commands run sequentially without interleaving, primitive commands like `INCR`, `DECR`,
     and `SET NX` (Set if Not Exists) are guaranteed to be 100% atomic with zero race conditions.

2. Redis Eviction Policies (`maxmemory-policy`):
   - When Redis memory reaches `maxmemory`:
     * `noeviction`: Returns errors on write operations when memory is full (production risk).
     * `allkeys-lru` / `volatile-lru`: Evicts Least Recently Used keys across all or TTL-bearing keys.
     * `volatile-ttl`: Evicts keys with the shortest remaining TTL first.

3. Distributed Locking Mechanics:
   - To acquire a lock: `SET resource_lock <unique_uuid> NX PX <lease_time_ms>`.
   - `NX`: Ensures lock is created only if it doesn't already exist.
   - `PX`: Automatic lease expiration ensures the lock is released if the worker crashes.
   - Safe Release: Releasing the lock requires checking that the stored value matches `<unique_uuid>`
     before deleting, executed atomically using a Lua script to prevent releasing a lock that expired
     and was acquired by another process!


============================================================
4. COMMON GOTCHAS
============================================================

1. The Pickle Security Vulnerability:
   - Using Python's `pickle` module for caching allows arbitrary code execution if an attacker
     gains access to Redis and injects malicious serialized payloads (`__reduce__`).
   - FIX: Always serialize cache payloads using standard `json` or `msgpack`.

2. Caching Without TTL (The Silent Memory Leak):
   - Omitting expiration on cache keys leads to unbounded memory growth until Redis crashes with OOM.
   - FIX: Always supply a `ttl_seconds` argument with every cache write.

3. Releasing Another Worker's Lock:
   - If Worker A acquires a lock with a 5-second TTL, but work takes 7 seconds, the lock expires.
     Worker B acquires the lock. Worker A finishes and calls `DEL resource_lock`, deleting Worker B's active lock!
   - FIX: Use a unique UUID per lock acquisition and release via Lua script checking ownership.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "Explain the Cache Stampede (Thundering Herd) and how you protect high-volume systems from it."
A1: "A Cache Stampede occurs when a high-traffic cache key expires, causing hundreds of concurrent
     requests to miss the cache simultaneously. Every request falls back to querying the database,
     causing a massive traffic spike that exhausts database connection pools.
     We mitigate this using two primary techniques:
     First, Mutex Locking: upon a cache miss, the first request acquires a distributed lock in Redis
     via `SET key token NX PX 5000`. Only the lock holder queries the database and repopulates the cache;
     all other requests sleep briefly and re-read the cache.
     Second, Probabilistic Early Expiration (such as the XFetch algorithm): we periodically recompute
     the value in the background before the TTL expires based on request frequency and computation time."

Q2: "How do you implement a safe distributed lock using Redis?"
A2: "To acquire a lock safely, I execute `SET resource_key <random_uuid> NX PX <ttl_ms>`.
     The `NX` flag guarantees exclusivity, and `PX` ensures automatic lease expiration if the worker
     process crashes.
     To release the lock safely, I use a Lua script executed via `EVAL`. The Lua script inspects the
     current value in Redis and deletes the key ONLY if it matches the `<random_uuid>` that this worker
     originally wrote. This prevents a slow worker whose lease expired from accidentally deleting a lock
     that was subsequently acquired by a different worker."

Q3: "Why choose Celery or Arq over FastAPI BackgroundTasks?"
A3: "FastAPI's `BackgroundTasks` executes in-process on the local event loop after the response finishes.
     It has no persistence, no retries, and if the container restarts or crashes, all pending jobs vanish.
     Celery and Arq are distributed task queues backed by Redis or RabbitMQ. They offer message persistence,
     automatic retries with exponential backoff and jitter, dead-letter queues for unrecoverable failures,
     and separate horizontal autoscaling. Furthermore, Celery's multi-process prefork architecture isolates
     heavy CPU or blocking jobs completely from the API event loop."
"""

import sys
import json
import time
import uuid
import warnings
warnings.filterwarnings("ignore")
from typing import Any, Callable, Dict, List, Optional, Tuple

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ==============================================================================
# 1. PRODUCTION-GRADE MOCK REDIS ENGINE (WITH ATOMIC PRIMITIVES)
# ==============================================================================

class MockRedisEngine:
    """
    Simulates Redis core operations: TTL expiry, atomic SET NX,
    FIFO list queues (LPUSH / RPOP), and simulated Lua script execution.
    """

    def __init__(self) -> None:
        self._kv_store: Dict[str, Tuple[str, float]] = {}  # key -> (value, expiry_timestamp)
        self._queues: Dict[str, List[str]] = {}             # queue_name -> list of strings

    def get(self, key: str) -> Optional[str]:
        if key not in self._kv_store:
            return None
        val, expiry = self._kv_store[key]
        if expiry > 0 and time.time() > expiry:
            del self._kv_store[key]
            return None
        return val

    def set(
        self,
        key: str,
        value: str,
        ex: Optional[int] = None,
        nx: bool = False
    ) -> bool:
        """
        Atomic SET with optional TTL (ex seconds) and NX (Set if Not Exists).
        """
        current_val = self.get(key)
        if nx and current_val is not None:
            return False  # Key already exists, lock acquisition fails

        expiry = time.time() + ex if ex is not None else 0.0
        self._kv_store[key] = (value, expiry)
        return True

    def delete(self, key: str) -> bool:
        if key in self._kv_store:
            del self._kv_store[key]
            return True
        return False

    def eval_release_lock(self, key: str, expected_token: str) -> bool:
        """
        Simulates the standard Redis Lua script:
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        current = self.get(key)
        if current == expected_token:
            self.delete(key)
            return True
        return False

    def lpush(self, queue_name: str, item: str) -> int:
        if queue_name not in self._queues:
            self._queues[queue_name] = []
        self._queues[queue_name].insert(0, item)
        return len(self._queues[queue_name])

    def rpop(self, queue_name: str) -> Optional[str]:
        if queue_name not in self._queues or not self._queues[queue_name]:
            return None
        return self._queues[queue_name].pop()

    def qlen(self, queue_name: str) -> int:
        return len(self._queues.get(queue_name, []))


# ==============================================================================
# 2. CACHE-ASIDE MANAGER WITH STAMPEDE MUTEX PROTECTION
# ==============================================================================

class CacheAsideManager:
    """
    Implements Cache-Aside with Distributed Mutex to prevent Cache Stampedes.
    """

    def __init__(self, redis: MockRedisEngine, default_ttl_sec: int = 60):
        self.redis = redis
        self.default_ttl = default_ttl_sec
        self.db_reads = 0

    def get_or_compute(
        self,
        cache_key: str,
        compute_fn: Callable[[], Any],
        ttl_seconds: Optional[int] = None
    ) -> Any:
        ttl = ttl_seconds or self.default_ttl

        # 1. Inspect Cache
        cached_str = self.redis.get(cache_key)
        if cached_str is not None:
            return json.loads(cached_str)

        # 2. Cache Miss: Acquire Distributed Mutex to prevent Stampede
        lock_key = f"lock:{cache_key}"
        token = str(uuid.uuid4())
        acquired = self.redis.set(lock_key, token, ex=5, nx=True)

        if not acquired:
            # Another worker is already refreshing the cache; wait and re-read
            time.sleep(0.05)
            second_attempt = self.redis.get(cache_key)
            if second_attempt is not None:
                return json.loads(second_attempt)
            # Fallback compute if lock owner died
            return self._compute_and_cache(cache_key, compute_fn, ttl)

        try:
            return self._compute_and_cache(cache_key, compute_fn, ttl)
        finally:
            # Release lock using atomic token check
            self.redis.eval_release_lock(lock_key, token)

    def _compute_and_cache(self, key: str, compute_fn: Callable[[], Any], ttl: int) -> Any:
        self.db_reads += 1
        result = compute_fn()
        self.redis.set(key, json.dumps(result), ex=ttl)
        return result

    def invalidate(self, cache_key: str) -> None:
        self.redis.delete(cache_key)


# ==============================================================================
# 3. DISTRIBUTED ASYNCHRONOUS TASK QUEUE SIMULATOR
# ==============================================================================

class DistributedTaskQueue:
    """
    Simulates a production task queue (Celery/Arq pattern):
    - Producer enqueues tasks with unique IDs.
    - Worker consumes, executes with retries and exponential backoff.
    - Moves exhausted tasks to Dead-Letter Queue (DLQ).
    """

    def __init__(self, redis: MockRedisEngine, queue_name: str = "tasks:default", max_retries: int = 2):
        self.redis = redis
        self.queue_name = queue_name
        self.dlq_name = f"{queue_name}:dlq"
        self.max_retries = max_retries
        self.processed_tasks: List[str] = []

    def enqueue(self, task_type: str, payload: Dict[str, Any]) -> str:
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        envelope = {
            "task_id": task_id,
            "task_type": task_type,
            "payload": payload,
            "retries": 0,
            "created_at": time.time()
        }
        self.redis.lpush(self.queue_name, json.dumps(envelope))
        return task_id

    def process_next(self, handlers: Dict[str, Callable[[Dict[str, Any]], None]]) -> Optional[str]:
        raw_task = self.redis.rpop(self.queue_name)
        if not raw_task:
            return None

        task = json.loads(raw_task)
        task_id = task["task_id"]
        task_type = task["task_type"]
        handler = handlers.get(task_type)

        if not handler:
            # Unknown task type routes directly to DLQ
            self.redis.lpush(self.dlq_name, raw_task)
            return None

        try:
            handler(task["payload"])
            self.processed_tasks.append(task_id)
            return task_id
        except Exception as e:
            # Handle retry or route to DLQ
            if task["retries"] < self.max_retries:
                task["retries"] += 1
                task["last_error"] = str(e)
                self.redis.lpush(self.queue_name, json.dumps(task))
            else:
                task["fatal_error"] = str(e)
                self.redis.lpush(self.dlq_name, json.dumps(task))
            return None


# ==============================================================================
# 4. SELF-TESTING SUITE
# ==============================================================================

def run_tests() -> None:
    print("\n[*] Starting automated test suite for 03_redis_caching_and_worker_queues.py...")

    redis = MockRedisEngine()

    # ------------------------------------------------------------
    # Test 1: Atomic SET NX (Distributed Lock Primitive)
    # ------------------------------------------------------------
    print("  -> Testing atomic SET NX distributed lock acquisition...")
    token_a = "worker-process-A"
    token_b = "worker-process-B"

    # Worker A acquires lock successfully
    assert redis.set("resource:invoice_100", token_a, ex=10, nx=True) is True
    # Worker B tries to acquire same lock -> must fail
    assert redis.set("resource:invoice_100", token_b, ex=10, nx=True) is False

    # Worker B cannot release Worker A's lock
    assert redis.eval_release_lock("resource:invoice_100", token_b) is False
    assert redis.get("resource:invoice_100") == token_a

    # Worker A releases lock cleanly
    assert redis.eval_release_lock("resource:invoice_100", token_a) is True
    assert redis.get("resource:invoice_100") is None

    # ------------------------------------------------------------
    # Test 2: Cache-Aside & Stampede Mutex Protection
    # ------------------------------------------------------------
    print("  -> Testing Cache-Aside lazy load and DB query caching...")
    cache_mgr = CacheAsideManager(redis, default_ttl_sec=60)

    # Simulated DB reader
    def read_user_from_db():
        return {"id": 42, "username": "ada_lovelace", "tier": "ENTERPRISE"}

    # First call: Cache miss -> queries DB
    user1 = cache_mgr.get_or_compute("user:42", read_user_from_db)
    assert user1["username"] == "ada_lovelace"
    assert cache_mgr.db_reads == 1

    # Second call: Cache hit -> zero additional DB queries
    user2 = cache_mgr.get_or_compute("user:42", read_user_from_db)
    assert user2["username"] == "ada_lovelace"
    assert cache_mgr.db_reads == 1, "Cache hit should not trigger DB read"

    # Invalidate cache
    cache_mgr.invalidate("user:42")
    assert redis.get("user:42") is None

    # Third call after invalidation -> repopulates cache
    user3 = cache_mgr.get_or_compute("user:42", read_user_from_db)
    assert user3["username"] == "ada_lovelace"
    assert cache_mgr.db_reads == 2

    # ------------------------------------------------------------
    # Test 3: TTL Key Expiration
    # ------------------------------------------------------------
    print("  -> Testing TTL expiration mechanics...")
    redis.set("transient_token", "xyz-123", ex=0)  # expires immediately
    time.sleep(0.01)
    assert redis.get("transient_token") is None, "Expired key must yield None"

    # ------------------------------------------------------------
    # Test 4: Distributed Task Queue & Worker Execution
    # ------------------------------------------------------------
    print("  -> Testing asynchronous worker queue and task dispatch...")
    queue = DistributedTaskQueue(redis, queue_name="queue:email_dispatch", max_retries=1)

    emails_delivered: List[str] = []

    def email_handler(payload: Dict[str, Any]) -> None:
        emails_delivered.append(payload["to"])

    handlers = {"SEND_WELCOME_EMAIL": email_handler}

    # Producer enqueues task
    t_id = queue.enqueue("SEND_WELCOME_EMAIL", {"to": "architect@company.com"})
    assert queue.redis.qlen("queue:email_dispatch") == 1

    # Worker consumes task
    processed_id = queue.process_next(handlers)
    assert processed_id == t_id
    assert len(emails_delivered) == 1
    assert emails_delivered[0] == "architect@company.com"
    assert queue.redis.qlen("queue:email_dispatch") == 0

    # ------------------------------------------------------------
    # Test 5: Worker Retries & Dead-Letter Queue (DLQ)
    # ------------------------------------------------------------
    print("  -> Testing task failure retries and DLQ routing...")
    fail_attempts = 0

    def flaky_handler(payload: Dict[str, Any]) -> None:
        nonlocal fail_attempts
        fail_attempts += 1
        raise ConnectionResetError("Remote API gateway timeout")

    handlers_flaky = {"SYNC_REMOTE_CRM": flaky_handler}

    failing_id = queue.enqueue("SYNC_REMOTE_CRM", {"customer": "CUST-99"})

    # Attempt 1: Fails, retried (pushed back to queue)
    res_1 = queue.process_next(handlers_flaky)
    assert res_1 is None
    assert fail_attempts == 1
    assert queue.redis.qlen("queue:email_dispatch") == 1  # Re-enqueued

    # Attempt 2: Fails again, exceeds max_retries (1), moved to DLQ
    res_2 = queue.process_next(handlers_flaky)
    assert res_2 is None
    assert fail_attempts == 2
    assert queue.redis.qlen("queue:email_dispatch") == 0  # Drained from main queue
    assert queue.redis.qlen("queue:email_dispatch:dlq") == 1  # Moved to DLQ

    # Inspect DLQ payload
    dlq_raw = queue.redis.rpop("queue:email_dispatch:dlq")
    dlq_item = json.loads(dlq_raw)
    assert dlq_item["task_id"] == failing_id
    assert dlq_item["retries"] == 1
    assert "Remote API gateway timeout" in dlq_item["fatal_error"]

    print("[SUCCESS] All 5 Redis Caching, Mutex & Distributed Queue tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 8 - 03: Redis Caching, Mutex Locks & Distributed Worker Queues")
    print("=" * 70)
    run_tests()
    print("=" * 70)
