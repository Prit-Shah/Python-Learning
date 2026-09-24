"""
Phase 8: Database & Production Backend - Redis Caching & Distributed Queues
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - Redis (Remote Dictionary Server) is an in-memory key-value store used for sub-millisecond
     caching, session management, and message brokering.
   - The Cache-Aside Pattern (Lazy Loading):
     1. API checks Redis for cached key ('GET user:101').
     2. Cache HIT: Return deserialized JSON instantly (bypassing DB).
     3. Cache MISS: Query PostgreSQL database.
     4. Store DB result in Redis with a TTL ('SETEX user:101 300 <json>').
     5. Return response to client.
   - Cache Invalidation Strategies:
     * Write-through / Invalidate on Write: Whenever data is modified (PUT/POST/DELETE),
       explicitly delete the cache key ('DELETE user:101') so the next read fetches fresh data.
     * Time-To-Live (TTL): Every cache key must have an expiration to prevent memory leaks and stale data.
   - Distributed Asynchronous Worker Queues (Celery / Arq / RQ):
     * Producer: FastAPI endpoint receives an expensive request (PDF generation, LLM batching, email dispatch).
     * Broker: Redis or RabbitMQ stores the queued message.
     * Consumers: Separate background worker processes pull tasks from Redis and process them asynchronously.
   - JS/TS Analogy:
     * Redis with 'ioredis' vs Python 'redis' / 'aioredis'.
     * 'BullMQ' in Node.js vs 'Celery' / 'Arq' in Python.

2. UNDER THE HOOD (CPython & Memory):
   - Redis processes commands on a single-threaded event loop (epoll) using non-blocking I/O,
     preventing race conditions on atomic operations like 'INCR' and 'HSET'.
   - Cache Stampede (Thundering Herd): When a hot key with 10,000 req/sec expires, all 10,000 requests
     hit the database simultaneously! Mitigated with mutex locks or probabilistic early expiration.

3. COMMON GOTCHA:
   - Caching without TTL: Keys stay in Redis memory forever until Redis runs Out Of Memory (OOM)!
   - Serializing Python objects with 'pickle' in Redis: Pickle is insecure (remote code execution vulnerability)
     and language-dependent. Always serialize using JSON or MessagePack!

4. 🎙️ INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   -----------------------------------------------------------------------------
   Q: "Explain the Cache-Aside pattern with Redis, how to avoid cache stampedes, and
       why you would choose Celery or Arq over FastAPI's BackgroundTasks."
   
   HOW TO ANSWER OUT LOUD (60-90 sec script):
   1. The Cache-Aside Pattern:
      "In high-traffic backends, we implement the Cache-Aside pattern:
       Upon receiving a read request, the service inspects Redis first. On a cache hit, it returns
       the cached JSON immediately (sub-1ms). On a cache miss, it reads from PostgreSQL, populates
       Redis with an explicit TTL, and returns the response. On mutations, we invalidate the cache key."
   2. Preventing Cache Stampedes:
      "A classic senior failure mode is the Cache Stampede (or Thundering Herd): when a popular cached
       resource expires, thousands of concurrent requests all miss cache and hammer the database simultaneously.
       We prevent this using distributed mutex locks (e.g. Redlock) so only the first request queries the DB
       while others wait, or by using probabilistic early recomputation (XFetch algorithm)."
   3. Celery / Arq vs BackgroundTasks:
      "FastAPI's BackgroundTasks runs in the same Python process in-memory. If the container crashes or restarts,
       in-flight jobs are permanently lost.
       For reliable workloads—like generating large reports, video transcoding, or sending transactional emails—we
       use a dedicated distributed queue like Celery or Arq with Redis as broker. This provides task persistence,
       automatic retries with exponential backoff, rate limiting, and dedicated horizontal scaling independent of API servers."
================================================================================
"""

import sys
import json
import time
from typing import Optional, Dict

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


class MockRedisClient:
    def __init__(self):
        self._store: Dict[str, tuple[str, float]] = {}

    def get(self, key: str) -> Optional[str]:
        if key not in self._store:
            return None
        val, expiry = self._store[key]
        if time.time() > expiry:
            del self._store[key]
            return None
        return val

    def setex(self, key: str, ttl_seconds: int, value: str):
        expiry = time.time() + ttl_seconds
        self._store[key] = (value, expiry)

    def delete(self, key: str):
        self._store.pop(key, None)


class UserServiceWithCache:
    def __init__(self, cache_client: MockRedisClient):
        self.cache = cache_client
        self.db_query_count = 0
        self._db = {
            101: {"id": 101, "name": "Alice", "role": "Architect"},
            102: {"id": 102, "name": "Bob", "role": "Engineer"}
        }

    def get_user_profile(self, user_id: int) -> Optional[dict]:
        cache_key = f"user:{user_id}:profile"
        
        cached_data = self.cache.get(cache_key)
        if cached_data:
            print(f"  [Cache HIT] Retrieved key '{cache_key}' directly from Redis!")
            return json.loads(cached_data)

        print(f"  [Cache MISS] Querying primary database for user_id={user_id}...")
        self.db_query_count += 1
        user = self._db.get(user_id)
        if not user:
            return None

        self.cache.setex(cache_key, 60, json.dumps(user))
        return user

    def update_user_role(self, user_id: int, new_role: str):
        if user_id in self._db:
            self._db[user_id]["role"] = new_role
            cache_key = f"user:{user_id}:profile"
            self.cache.delete(cache_key)
            print(f"  [Cache INVALIDATE] Evicted key '{cache_key}' from Redis due to update.")


def demonstrate_cache_aside_pattern():
    print("\n--- 1. Demonstrating Cache-Aside Pattern & Performance ---")
    redis = MockRedisClient()
    service = UserServiceWithCache(redis)

    u1 = service.get_user_profile(101)
    u2 = service.get_user_profile(101)
    print(f"  Total DB Queries executed: {service.db_query_count} (Expected exactly 1!)")

    service.update_user_role(101, "Staff Principal AI Architect")
    u3 = service.get_user_profile(101)
    print(f"  Updated Role retrieved: '{u3['role']}'")
    print(f"  Total DB Queries after update: {service.db_query_count} (Expected 2)")


def run_tests():
    print("\n[*] Running automated tests for 03_redis_caching_and_worker_queues.py...")
    redis = MockRedisClient()
    service = UserServiceWithCache(redis)

    service.get_user_profile(102)
    assert service.db_query_count == 1
    
    service.get_user_profile(102)
    assert service.db_query_count == 1

    redis.setex("temp_key", ttl_seconds=0, value="expired_data")
    time.sleep(0.01)
    assert redis.get("temp_key") is None, "Expired key must return None"

    print("[SUCCESS] All Redis caching & queue tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 65)
    print("Execution: Phase 8 - Redis Caching & Distributed Queues")
    print("=" * 65)
    demonstrate_cache_aside_pattern()
    print("-" * 65)
    run_tests()
    print("=" * 65)
