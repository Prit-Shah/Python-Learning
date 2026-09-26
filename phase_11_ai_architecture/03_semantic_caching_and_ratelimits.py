r"""
03_semantic_caching_and_ratelimits.py

============================================================
1. CONCEPT
============================================================

High-scale AI applications face two massive operational challenges: exorbitant API inference
costs / latency, and strict provider rate limits. Two architectural patterns resolve these:
Semantic Caching and Dual-Constraint Token Bucket Rate Limiting:

1. Semantic Caching (Vector Similarity Caching):
   - Traditional Caching Failure: Exact-match caches (`MD5(prompt)`) fail because users ask
     the same question with minor lexical variations:
     * "How do I reset my password?"
     * "What are the steps to change my password?"
     * "Forgot my login password, how to fix?"
   - Semantic Cache Workflow:
     1. Compute dense embedding vector of the incoming query: $v_q \in \mathbb{R}^D$.
     2. Query the vector database for nearest cached query embedding:
        $$\text{score} = \cos(v_q, v_{\text{cached}})$$
     3. If $\text{score} \ge \tau$ (Similarity Threshold, typically $\tau \in [0.92, 0.96]$):
        * Cache HIT: Return cached response immediately (latency $< 15\text{ms}$, cost = \$0.00).
     4. If $\text{score} < \tau$:
        * Cache MISS: Route to LLM API, store `(v_q, prompt, response)` with TTL, and return.

2. Dual-Constraint Token Bucket Rate Limiting (RPM + TPM):
   - Traditional web APIs rate limit purely on Requests-Per-Minute (RPM).
   - In AI backends, RPM is insufficient: a single request might consume 10 tokens or 100,000 tokens.
     A single user can exhaust the organization's entire Tokens-Per-Minute (TPM) quota!
   - Token Bucket Mechanics:
     * Bucket has a maximum capacity $C$ and continuously refills at rate $r$ tokens/second.
     * Current Tokens: $T(t) = \min(C, T_{\text{last}} + \Delta t \cdot r)$.
     * When a request arrives with estimated token cost $K$:
       - If $T(t) \ge K$: Deduct $K$ tokens and allow the request.
       - If $T(t) < K$: Reject immediately with HTTP 429 and `Retry-After: <seconds>`.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python (Redis / GPTCache)          | JavaScript / TypeScript (Node.js)  |
+------------------------------+------------------------------------+------------------------------------+
| Semantic Cache               | Vector DB cosine similarity lookup | Upstash RAG / custom vector search |
| Rate Limiter Algorithm       | Token Bucket (RPM + TPM)           | `@upstash/ratelimit` / custom Redis|
| Atomic Concurrency           | Redis Lua scripts / atomic classes | Redis Lua scripts                  |
| Tenant Namespacing           | `cache:{tenant_id}:{embedding}`    | `cache:${tenantId}:${id}`          |
| Token Estimation             | `tiktoken` heuristic               | `gpt-tokenizer`                    |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Architecture Differences:
1. In Express or Next.js, standard rate-limiting middleware (`express-rate-limit`) tracks only IP/User
   request counts.
2. In Python AI microservices, the rate limiter inspects the incoming request body, computes
   estimated prompt + max completion tokens, and evaluates atomic multi-resource rate limits (RPM + TPM)
   before forwarding calls to the LLM gateway.


============================================================
3. UNDER THE HOOD (Threshold Tuning & Mathematical Guarantees)
============================================================

1. The Similarity Threshold Tradeoff Curve ($\tau$):
   - If $\tau \ge 0.98$: Cache hit rate drops toward zero, behaving like brittle exact string matching.
   - If $\tau \le 0.85$: False positive hits occur. Incompatible intents with similar keywords
     (e.g., "How do I CREATE an account?" vs "How do I DELETE an account?") will match and return
     catastrophically wrong instructions!
   - The Sweet Spot: Empirically calibrated between $0.92 \le \tau \le 0.95$ for general customer
     support and informational domains.

2. Atomic Redis Token Bucket via Lua:
   - Calculating elapsed time and refilling tokens in Python application memory creates severe
     race conditions across multiple concurrent server pods.
   - In production, the refill calculation and token deduction are bundled inside a Redis Lua script
     executed atomically on Redis's single-threaded event loop.


============================================================
4. COMMON GOTCHAS
============================================================

1. Cross-Tenant Data Leaks in Shared Cache:
   - Caching responses globally across all users without tenant isolation. If User A asks
     "Show my account balance" and receives a response containing their balance, User B asking
     the same question will receive User A's private data!
   - FIX: Always partition semantic cache indexes by tenant and role: `tenant_id == X`.

2. Caching Without TTL (Stale Hallucinations):
   - Storing cached answers indefinitely. When business rules or documentation change, the cache
     continues serving obsolete answers.
   - FIX: Always attach an explicit TTL (e.g. 24 hours to 7 days).

3. Static Non-Refilling Rate Limits:
   - Resetting quotas abruptly at the top of the hour creates a traffic spike where all clients
     hammer the API at minute :00.
   - FIX: Use continuous Token Bucket refill dynamics to smooth traffic uniformly over time.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "Explain how Semantic Caching works and how you prevent false positive cache hits."
A1: "Semantic Caching replaces brittle exact string hashing with vector similarity.
     When a prompt arrives, we embed it using an embedding model and query our vector index using
     cosine similarity. If the closest match exceeds our similarity threshold $\tau$ (typically 0.92 to 0.95),
     we return the cached answer with sub-15ms latency, saving 100% of LLM generation cost.
     To prevent false positives, we employ three guardrails:
     First, we calibrate $\tau$ strictly above 0.92 to ensure high semantic fidelity.
     Second, we enforce exact metadata filtering on tenant ID and user permission scope so private
     data is never leaked across tenants.
     Third, for sensitive domains like code execution or financial calculations, we bypass the semantic
     cache entirely or require $\tau \ge 0.98$."

Q2: "Why is traditional request-based rate limiting insufficient for LLM APIs, and how does the Token Bucket solve this?"
A2: "Traditional rate limiters count only Requests-Per-Minute (RPM). In generative AI, requests are
     highly asymmetrical: a short ping might consume 50 tokens, whereas a RAG query or long document
     analysis can consume 100,000 tokens. A single user staying well below their 60 RPM limit could
     burn 6,000,000 tokens in a minute, exhausting provider TPM quotas and taking down the entire service.
     We solve this by implementing a dual-constraint Token Bucket algorithm in Redis. The bucket tracks
     both RPM and TPM with independent capacities and continuous refill rates. When a request arrives,
     we estimate its token footprint (input tokens + requested max output) and deduct that amount atomically.
     If the bucket lacks sufficient tokens, the request is rejected with HTTP 429 before hitting the LLM."

Q3: "How do you implement atomic Token Bucket rate limiting in a distributed architecture?"
A3: "In a multi-pod cluster, keeping token counters in Python process memory causes race conditions.
     I implement the Token Bucket using an atomic Lua script executed inside Redis.
     The Lua script takes the tenant key, capacity, refill rate, requested token cost, and current timestamp.
     It computes the time delta since the last refill, adds newly accumulated tokens up to the maximum capacity,
     checks if available tokens satisfy the request cost, decrements the balance, and records the timestamp.
     Because Redis executes Lua scripts atomically on its single thread, this guarantees zero race conditions
     and sub-millisecond evaluation across hundreds of concurrent API pods."
"""

import sys
import time
import math
import warnings
warnings.filterwarnings("ignore")
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ==============================================================================
# 1. SEMANTIC VECTOR CACHE ENGINE
# ==============================================================================

@dataclass
class CacheEntry:
    query_text: str
    embedding: np.ndarray
    response_text: str
    tenant_id: str
    created_at: float
    ttl_seconds: float


class SemanticCache:
    """
    In-memory semantic cache using cosine similarity:
    - Enforces similarity threshold tau to prevent false positive matches.
    - Strictly namespaces by tenant_id to prevent cross-tenant data leaks.
    - Honors Time-To-Live (TTL) expiration.
    """

    def __init__(self, similarity_threshold: float = 0.92, default_ttl_seconds: float = 3600):
        self.threshold = similarity_threshold
        self.default_ttl = default_ttl_seconds
        self.entries: List[CacheEntry] = []
        self.hit_count = 0
        self.miss_count = 0

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def get(self, query_vector: np.ndarray, tenant_id: str) -> Optional[Tuple[str, float]]:
        now = time.time()
        best_match: Optional[CacheEntry] = None
        best_score = -1.0

        # Scan cached entries for matching tenant
        for entry in self.entries:
            # Check tenant isolation
            if entry.tenant_id != tenant_id:
                continue

            # Check TTL expiry
            if now - entry.created_at > entry.ttl_seconds:
                continue

            score = self._cosine_similarity(query_vector, entry.embedding)
            if score > best_score:
                best_score = score
                best_match = entry

        # Check if best score satisfies semantic threshold
        if best_match and best_score >= self.threshold:
            self.hit_count += 1
            return best_match.response_text, best_score

        self.miss_count += 1
        return None

    def set(
        self,
        query_text: str,
        query_vector: np.ndarray,
        response_text: str,
        tenant_id: str,
        ttl_seconds: Optional[float] = None
    ) -> None:
        entry = CacheEntry(
            query_text=query_text,
            embedding=query_vector,
            response_text=response_text,
            tenant_id=tenant_id,
            created_at=time.time(),
            ttl_seconds=ttl_seconds or self.default_ttl
        )
        self.entries.append(entry)


# ==============================================================================
# 2. DUAL-CONSTRAINT TOKEN BUCKET RATE LIMITER (RPM + TPM)
# ==============================================================================

class TokenBucketLimiter:
    """
    Implements continuous refill Token Bucket algorithm tracking:
    1. Requests-Per-Minute (RPM)
    2. Tokens-Per-Minute (TPM)
    """

    def __init__(
        self,
        max_requests: float = 60.0,
        requests_refill_per_sec: float = 1.0,
        max_tokens: float = 10_000.0,
        tokens_refill_per_sec: float = 166.67  # 10,000 tokens / 60s
    ):
        self.max_requests = max_requests
        self.req_refill_rate = requests_refill_per_sec
        self.current_requests = max_requests

        self.max_tokens = max_tokens
        self.token_refill_rate = tokens_refill_per_sec
        self.current_tokens = max_tokens

        self.last_update = time.time()

    def _refill(self) -> None:
        now = time.time()
        elapsed = now - self.last_update
        self.last_update = now

        # Refill request tokens
        self.current_requests = min(self.max_requests, self.current_requests + (elapsed * self.req_refill_rate))
        # Refill token budget
        self.current_tokens = min(self.max_tokens, self.current_tokens + (elapsed * self.token_refill_rate))

    def try_acquire(self, estimated_tokens: int = 100) -> Tuple[bool, str]:
        self._refill()

        # 1. Check RPM constraint
        if self.current_requests < 1.0:
            return False, "Rate limit exceeded: RPM quota exhausted."

        # 2. Check TPM constraint
        if self.current_tokens < estimated_tokens:
            return False, f"Rate limit exceeded: TPM quota exhausted (requires {estimated_tokens} tokens)."

        # Deduct from both buckets
        self.current_requests -= 1.0
        self.current_tokens -= estimated_tokens
        return True, "Request permitted."


# ==============================================================================
# 3. SELF-TESTING SUITE
# ==============================================================================

def run_tests() -> None:
    print("\n[*] Starting automated test suite for 03_semantic_caching_and_ratelimits.py...")

    # ------------------------------------------------------------
    # Test 1: Semantic Caching Hit on Paraphrased Queries
    # ------------------------------------------------------------
    print("  -> Testing semantic cache hit on semantically equivalent paraphrasing...")
    cache = SemanticCache(similarity_threshold=0.90)

    # Base query: "How do I reset my password?"
    vec_base = np.array([0.98, 0.12, 0.05], dtype=np.float32)
    cache.set(
        query_text="How do I reset my password?",
        query_vector=vec_base,
        response_text="Go to Settings -> Security -> Reset Password.",
        tenant_id="tenant_alpha"
    )

    # Paraphrased query: "Steps to change my account password" (high cosine similarity: ~0.99)
    vec_paraphrase = np.array([0.97, 0.14, 0.04], dtype=np.float32)
    cached_res, score = cache.get(vec_paraphrase, tenant_id="tenant_alpha")

    assert cached_res is not None, "Semantic cache failed to hit on paraphrase"
    assert cached_res == "Go to Settings -> Security -> Reset Password."
    assert score >= 0.90
    assert cache.hit_count == 1

    # ------------------------------------------------------------
    # Test 2: Semantic Cache Miss on Distinct Queries
    # ------------------------------------------------------------
    print("  -> Testing semantic cache miss when query is semantically divergent...")
    # Divergent query: "How do I cancel my billing subscription?"
    vec_unrelated = np.array([0.05, 0.95, 0.20], dtype=np.float32)
    miss_res = cache.get(vec_unrelated, tenant_id="tenant_alpha")

    assert miss_res is None, "Semantic cache erroneously matched unrelated query"
    assert cache.miss_count == 1

    # ------------------------------------------------------------
    # Test 3: Multi-Tenant Cache Isolation (No Cross-Tenant Leaks)
    # ------------------------------------------------------------
    print("  -> Testing tenant isolation (preventing cross-tenant data leaks)...")
    # Same vector queried by different tenant -> MUST RESULT IN CACHE MISS
    tenant_beta_res = cache.get(vec_paraphrase, tenant_id="tenant_beta")
    assert tenant_beta_res is None, "Security violation: Cross-tenant cache contamination detected"

    # ------------------------------------------------------------
    # Test 4: Dual-Constraint Token Bucket Rate Limiting (RPM + TPM)
    # ------------------------------------------------------------
    print("  -> Testing Dual-Constraint Token Bucket rate limiter (RPM + TPM)...")
    limiter = TokenBucketLimiter(
        max_requests=3.0,
        requests_refill_per_sec=0.5,
        max_tokens=500.0,
        tokens_refill_per_sec=50.0
    )

    # 1. Normal requests within quota
    ok1, _ = limiter.try_acquire(estimated_tokens=100)
    assert ok1 is True
    ok2, _ = limiter.try_acquire(estimated_tokens=150)
    assert ok2 is True

    # 2. Large request that exceeds remaining TPM (requires 300, only 250 left)
    ok3, msg3 = limiter.try_acquire(estimated_tokens=300)
    assert ok3 is False
    assert "TPM quota exhausted" in msg3

    # 3. Exhausting RPM
    ok4, _ = limiter.try_acquire(estimated_tokens=50)
    assert ok4 is True  # 3rd request succeeds, exhausts RPM to ~0
    ok5, msg5 = limiter.try_acquire(estimated_tokens=10)
    assert ok5 is False
    assert "RPM quota exhausted" in msg5

    # 4. Refill over time
    time.sleep(0.1)
    limiter._refill()
    assert limiter.current_tokens > 0

    print("[SUCCESS] All 4 Semantic Caching & Rate Limiting tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 11 - 03: Semantic Caching & Dual-Constraint Rate Limiting")
    print("=" * 70)
    run_tests()
    print("=" * 70)
