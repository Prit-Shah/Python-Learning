"""
Phase 11: Semantic Caching & Rate Limiting
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - Concept: Standard HTTP caches (Redis string keys) require exact character
     matches: `cache.get("What is Python?")` fails if the user types
     `"what is python?"` or `"Explain Python to me"`. Semantic Caching indexes
     cached queries by embedding vector similarity. If a new prompt has
     cosine similarity > 0.92 to a cached query, the cached response is
     served instantly (0ms LLM latency, $0 token cost).
   - Rate Limiting: LLM APIs enforce two distinct limits: Requests Per Minute (RPM)
     and Tokens Per Minute (TPM). We implement a Token Bucket algorithm to protect
     upstream quotas and provide smooth rate-limited dispatch.
   - JS/TS Equivalent: In Node.js you use `express-rate-limit` or Redis token
     buckets. For semantic caching, libraries like GPTCache exist in Python,
     backed by Redis Vector Search (RediSearch) or pgvector.

2. UNDER THE HOOD (CPython & Memory):
   - Semantic Cache: Computes query vector `q_vec`. Queries an in-memory or
     Redis vector index for nearest neighbors. If `max(cos_sim) >= threshold`,
     returns `cached_response`. If below threshold, invokes LLM, appends
     `(q_vec, query, response)` to index.
   - Token Bucket: Tracks `current_tokens` with last refill timestamp `t_last`.
     Refill rate = `capacity / time_window`. When consuming $N$ tokens:
     $\Delta t = t_{now} - t_{last}$, added tokens = $\Delta t 	imes refill\_rate$.
     If available $\ge N$, deduct and proceed; else, raise or sleep.

3. COMMON GOTCHA:
   - Cache Threshold False Positives: If threshold is too low (e.g. 0.80),
     questions with opposite meanings get cache hits!
     E.g.: "Why is Python slow?" vs "Why is Python fast?" have ~0.84 cosine
     similarity. A threshold $\ge 0.92$ is recommended in production.
   - Caching Personalized or Stateful Contexts: Never cache prompts containing
     session IDs, user names, or temporal queries like "What is today's date?".

4. 🎙️ INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   - Interview Question: "How would you implement caching and rate limiting for
     a production LLM backend?"
   - How to Answer Out Loud (60-90 sec verbal script):
     * "I implement a two-tier caching strategy: Tier 1 is an exact MD5/SHA256
       hash cache in Redis for exact prompt matches (sub-millisecond O(1) lookup)."
     * "Tier 2 is a Semantic Cache using Redis Vector Search or pgvector. The incoming
       query is embedded and matched against cached queries using cosine similarity.
       I enforce a strict similarity threshold of 0.92 or 0.95 to eliminate semantic
       false positives. If matched, we save both LLM latency and API cost."
     * "For rate limiting, I use a Redis-backed Distributed Token Bucket supporting
       both RPM (Requests Per Minute) and TPM (Tokens Per Minute) quotas."
     * "When downstream services exceed 80% TPM capacity, the rate limiter engages
       proactive queuing with exponential backoff and jitter rather than abruptly
       failing with 429 to the user."
================================================================================
"""

import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass

import time
import numpy as np
from dataclasses import dataclass, field
from typing import Any


# ── Fast Semantic Mock Embedder ──────────────────────────────────────────────

def pseudo_embed(text: str, dims: int = 32) -> np.ndarray:
    """Deterministic normalized embedding for semantic cache tests."""
    np.random.seed(hash(text.strip().lower()) % (2**31))
    vec = np.random.randn(dims).astype(np.float32)

    # Nudge semantic topical cluster weights
    lower = text.lower()
    if "python" in lower:
        vec[0:4] += np.array([2.5, 1.2, 0.8, 0.4], dtype=np.float32)
    if "rate" in lower or "limit" in lower:
        vec[4:8] += np.array([2.5, 1.2, 0.8, 0.4], dtype=np.float32)
    if "fastapi" in lower or "async" in lower:
        vec[8:12] += np.array([2.5, 1.2, 0.8, 0.4], dtype=np.float32)

    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


# ── Semantic Cache Implementation ────────────────────────────────────────────

@dataclass
class CacheEntry:
    query: str
    embedding: np.ndarray
    response: str
    created_at: float = field(default_factory=time.time)
    hits: int = 0


class SemanticCache:
    """
    Semantic Cache matching incoming prompts against stored vectors.
    """

    def __init__(self, similarity_threshold: float = 0.90):
        self.similarity_threshold = similarity_threshold
        self.entries: list[CacheEntry] = []
        self.exact_cache: dict[str, str] = {}  # Tier 1: exact string match
        self.cache_hits = 0
        self.cache_misses = 0

    def get(self, query: str) -> tuple[str | None, float]:
        """
        Check Tier 1 (exact match), then Tier 2 (semantic similarity).
        Returns (response, similarity_score).
        """
        cleaned = query.strip().lower()

        # Tier 1: Exact string hit
        if cleaned in self.exact_cache:
            self.cache_hits += 1
            return self.exact_cache[cleaned], 1.0

        if not self.entries:
            self.cache_misses += 1
            return None, 0.0

        # Tier 2: Vector search over cached embeddings
        query_vec = pseudo_embed(query)
        best_score = -1.0
        best_entry: CacheEntry | None = None

        for entry in self.entries:
            sim = cosine_sim(query_vec, entry.embedding)
            if sim > best_score:
                best_score = sim
                best_entry = entry

        if best_entry and best_score >= self.similarity_threshold:
            self.cache_hits += 1
            best_entry.hits += 1
            return best_entry.response, best_score

        self.cache_misses += 1
        return None, best_score

    def set(self, query: str, response: str):
        """Stores query, embedding, and response in cache."""
        cleaned = query.strip().lower()
        self.exact_cache[cleaned] = response
        self.entries.append(CacheEntry(
            query=query,
            embedding=pseudo_embed(query),
            response=response,
        ))


# ── Token Bucket Rate Limiter ────────────────────────────────────────────────

class TokenBucketRateLimiter:
    """
    Token Bucket rate limiter for managing RPM and TPM budgets.
    """

    def __init__(self, capacity: float, refill_rate_per_sec: float):
        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate_per_sec)
        self.tokens = float(capacity)
        self.last_refill = time.time()

    def _refill(self):
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

    def acquire(self, tokens: float = 1.0) -> bool:
        """Attempts to acquire tokens immediately without blocking."""
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def wait_and_acquire(self, tokens: float = 1.0, timeout: float = 2.0) -> bool:
        """Blocks until tokens become available or timeout expires."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.acquire(tokens):
                return True
            time.sleep(0.01)
        return False


# ── Demonstration Functions ──────────────────────────────────────────────────

def demonstrate_semantic_caching():
    """Demonstrates cache hit on semantically identical prompts."""
    print("  --- Demonstration 1: Semantic Caching ---")
    cache = SemanticCache(similarity_threshold=0.90)

    # 1. First user queries — Cache Miss
    q1 = "How do I install python packages using uv?"
    resp1 = "Run 'uv pip install <package>' or 'uv add <package>'."
    hit, score = cache.get(q1)
    print(f"    Q1: '{q1}' -> Hit: {hit is not None} (Sim: {score:.2f})")
    cache.set(q1, resp1)

    # 2. Exact match — Tier 1 Hit
    hit, score = cache.get(q1)
    print(f"    Q1 (exact): -> Hit: {hit is not None} (Sim: {score:.2f}) -> '{hit}'")

    # 3. Semantically identical prompt — Tier 2 Hit!
    q2 = "how do i install python packages using uv?"
    hit2, score2 = cache.get(q2)
    print(f"    Q2 (lowercase): -> Hit: {hit2 is not None} (Sim: {score2:.2f}) -> '{hit2}'")

    # 4. Unrelated prompt — Cache Miss
    q3 = "What is the capital of France?"
    hit3, score3 = cache.get(q3)
    print(f"    Q3 (unrelated): -> Hit: {hit3 is not None} (Sim: {score3:.2f})")


def demonstrate_rate_limiter():
    """Demonstrates token bucket depletion and rejection."""
    print("\n  --- Demonstration 2: Token Bucket Rate Limiting ---")
    # Capacity: 5 tokens, Refill: 2 tokens per second
    limiter = TokenBucketRateLimiter(capacity=5, refill_rate_per_sec=2)

    print("    Bursting 5 rapid requests:")
    for i in range(1, 7):
        success = limiter.acquire(1)
        status = "ACCEPTED" if success else "REJECTED (HTTP 429)"
        print(f"      Request #{i}: {status} (Tokens remaining: {limiter.tokens:.1f})")


# ══════════════════════════════════════════════════════════════════════
# SELF-TEST CHALLENGES
# ══════════════════════════════════════════════════════════════════════

def run_tests():
    """Automated verification for Phase 11 File 3."""
    print("\n[*] Running automated self-tests...")

    # Test 1: Exact match hits Tier 1
    cache = SemanticCache(similarity_threshold=0.85)
    cache.set("what is python", "Python is a language")
    resp, score = cache.get("what is python")
    assert resp == "Python is a language"
    assert score == 1.0

    # Test 2: Case insensitivity in Tier 1
    resp2, score2 = cache.get("WHAT IS PYTHON")
    assert resp2 == "Python is a language"

    # Test 3: Cache miss on empty cache
    empty = SemanticCache()
    r_empty, _ = empty.get("unknown")
    assert r_empty is None
    assert empty.cache_misses == 1

    # Test 4: Semantic similarity computation
    v1 = pseudo_embed("python coding")
    v2 = pseudo_embed("python coding")
    assert abs(cosine_sim(v1, v2) - 1.0) < 1e-4

    # Test 5: Cache stats tracking
    assert cache.cache_hits == 2

    # Test 6: Rate limiter full capacity burst
    tb = TokenBucketRateLimiter(capacity=3, refill_rate_per_sec=10)
    assert tb.acquire(1) is True
    assert tb.acquire(1) is True
    assert tb.acquire(1) is True
    assert tb.acquire(1) is False  # Exhausted

    # Test 7: Rate limiter refill
    time.sleep(0.15)  # 0.15s * 10 tokens/s = 1.5 tokens refilled
    assert tb.acquire(1) is True

    # Test 8: Rate limiter capacity clamp
    tb_overflow = TokenBucketRateLimiter(capacity=2, refill_rate_per_sec=100)
    time.sleep(0.05)
    tb_overflow._refill()
    assert tb_overflow.tokens <= 2.0, "Tokens must not exceed capacity"

    # Test 9: Wait and acquire succeeds within timeout
    tb_wait = TokenBucketRateLimiter(capacity=1, refill_rate_per_sec=20)
    tb_wait.acquire(1)
    acquired = tb_wait.wait_and_acquire(tokens=1, timeout=0.2)
    assert acquired is True

    # Test 10: Wait and acquire times out if deficit too large
    tb_starve = TokenBucketRateLimiter(capacity=0, refill_rate_per_sec=0.1)
    timeout_result = tb_starve.wait_and_acquire(tokens=10, timeout=0.05)
    assert timeout_result is False

    print("[SUCCESS] All 10 Semantic Caching & Rate Limiting self-tests passed!")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 11: Semantic Caching & Rate Limiting")
    print("=" * 70)
    demonstrate_semantic_caching()
    demonstrate_rate_limiter()
    print("-" * 70)
    run_tests()
    print("=" * 70)
