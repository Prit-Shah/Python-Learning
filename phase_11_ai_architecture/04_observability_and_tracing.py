"""
Phase 11: Observability, Tracing & Cost Accounting
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - Concept: Debugging distributed AI pipelines cannot be done with `print()`
     statements. A single user question may trigger embedding generation,
     vector retrieval, prompt template construction, multiple model inferences,
     and 3 tool calls. Distributed Tracing tracks this entire DAG as a single
     `Trace`, containing nested, timed `Spans`.
   - JS/TS Equivalent: In Node.js, you use OpenTelemetry with `AsyncLocalStorage`
     to pass `trace_id` down the async call stack. In Python, we use standard
     library `contextvars` to pass trace and span context seamlessly across
     `async`/`await` boundaries without polluting function signatures.
   - Production Platforms: LangSmith, Arize Phoenix, OpenInference, Datadog LLM
     Observability.

2. UNDER THE HOOD (CPython & Memory):
   - `contextvars.ContextVar`: Thread-safe and coroutine-safe storage. When
     asyncio schedules a task via `create_task()`, CPython clones the current
     Context, ensuring child spans inherit the parent's `trace_id`.
   - Key Production Metrics:
     * TTFT (Time-to-First-Token): Latency between prompt submission and first token.
     * TPS (Tokens-Per-Second): Generation velocity.
     * End-to-End Latency: Total elapsed wall-clock time.
     * Cost Breakdown: Prompt tokens + Completion tokens in USD.

3. COMMON GOTCHA:
   - Logging Raw PII in Traces: Prompts frequently contain API keys, emails,
     passwords, and HIPAA/GDPR sensitive data. Production tracing must
     implement an interceptor/redactor regex pipeline before exporting spans!
   - Tracing Overhead in Hot Loops: Serializing massive spans on every token
     creates huge CPU overhead. Only trace at the span boundary (start/finish),
     not per individual token chunk.

4. 🎙️ INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   - Interview Question: "How do you monitor and debug LLM applications in production?"
   - How to Answer Out Loud (60-90 sec verbal script):
     * "I instrument the system using OpenTelemetry and dedicated LLM tracing tools
       like Arize Phoenix or LangSmith."
     * "Every incoming request generates a root `TraceID` stored in Python's
       `contextvars`. Each subsystem—Vector Retriever, Re-ranker, LLM Provider,
       and Tool Dispatcher—opens a child `Span` with start/end timestamps,
       input attributes, and output metadata."
     * "I monitor four core metrics: Time-to-First-Token (TTFT) for user-perceived
       responsiveness, Tokens-Per-Second (TPS) for engine throughput, E2E latency p95,
       and token cost broken down per customer tenant."
     * "Before traces are flushed to the collector, a sanitization middleware masks
       credit cards, emails, and authorization headers to guarantee compliance."
================================================================================
"""

import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass

import asyncio
import contextvars
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


# ── Async Context Propagation ────────────────────────────────────────────────

current_trace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("current_trace_id", default=None)
current_span_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("current_span_id", default=None)


# ── Span & Trace Data Structures ─────────────────────────────────────────────

@dataclass
class Span:
    span_id: str
    trace_id: str
    parent_span_id: str | None
    name: str
    start_time: float
    end_time: float | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    @property
    def duration_ms(self) -> float:
        if self.end_time is None:
            return 0.0
        return round((self.end_time - self.start_time) * 1000.0, 2)


# ── PII Sanitizer / Redactor ─────────────────────────────────────────────────

class PIIRedactor:
    """Masks emails, API keys, and sensitive data before trace export."""
    EMAIL_REGEX = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")
    BEARER_REGEX = re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]+", re.IGNORECASE)

    @classmethod
    def sanitize(cls, text: str) -> str:
        text = cls.EMAIL_REGEX.sub("[REDACTED_EMAIL]", text)
        text = cls.BEARER_REGEX.sub("Bearer [REDACTED_TOKEN]", text)
        return text


# ── In-Memory Tracing Collector ──────────────────────────────────────────────

class Tracer:
    """Lightweight OpenTelemetry-style distributed tracer."""

    def __init__(self):
        self.spans: list[Span] = []

    def start_trace(self, root_name: str) -> "SpanContext":
        trace_id = f"trace-{uuid.uuid4().hex[:8]}"
        current_trace_id.set(trace_id)
        current_span_id.set(None)
        return self.start_span(root_name)

    def start_span(self, name: str) -> "SpanContext":
        trace_id = current_trace_id.get() or f"trace-{uuid.uuid4().hex[:8]}"
        parent_id = current_span_id.get()
        span_id = f"span-{uuid.uuid4().hex[:6]}"

        span = Span(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_id,
            name=name,
            start_time=time.perf_counter(),
        )
        self.spans.append(span)
        return SpanContext(self, span)


class SpanContext:
    """Async Context Manager for automatic span lifecycle management."""

    def __init__(self, tracer: Tracer, span: Span):
        self.tracer = tracer
        self.span = span
        self.prev_span_token = None

    def __enter__(self):
        self.prev_span_token = current_span_id.set(self.span.span_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.span.end_time = time.perf_counter()
        if exc_val:
            self.span.error = str(exc_val)
        if self.prev_span_token:
            current_span_id.reset(self.prev_span_token)

    def set_attribute(self, key: str, value: Any):
        if isinstance(value, str):
            value = PIIRedactor.sanitize(value)
        self.span.attributes[key] = value


# ── Demonstration Functions ──────────────────────────────────────────────────

async def demonstrate_full_request_tracing():
    """Simulates a RAG pipeline execution traced end-to-end."""
    print("  --- Demonstration: End-to-End Distributed Tracing ---")
    tracer = Tracer()

    with tracer.start_trace("POST /api/v1/chat") as root_span:
        root_span.set_attribute("http.method", "POST")
        root_span.set_attribute("user.email", "alice@example.com")  # Will be sanitized

        # Sub-span 1: Vector Retrieval
        with tracer.start_span("retriever.search") as ret_span:
            await asyncio.sleep(0.015)
            ret_span.set_attribute("vector_db", "pgvector")
            ret_span.set_attribute("top_k", 3)
            ret_span.set_attribute("chunks_retrieved", 3)

        # Sub-span 2: Model Inference Call
        with tracer.start_span("llm.completion") as llm_span:
            await asyncio.sleep(0.030)
            llm_span.set_attribute("llm.provider", "openai")
            llm_span.set_attribute("llm.model", "gpt-4o")
            llm_span.set_attribute("llm.prompt_tokens", 450)
            llm_span.set_attribute("llm.completion_tokens", 85)
            llm_span.set_attribute("llm.cost_usd", 0.0035)

    print("    Trace Completed. Spans Captured:")
    for s in tracer.spans:
        parent_str = f" (parent: {s.parent_span_id})" if s.parent_span_id else " (ROOT)"
        print(f"      [{s.name:<20}] {s.duration_ms:>6.2f}ms {parent_str}")
        for k, v in s.attributes.items():
            print(f"         * {k}: {v}")

    return tracer


# ══════════════════════════════════════════════════════════════════════
# SELF-TEST CHALLENGES
# ══════════════════════════════════════════════════════════════════════

def run_tests():
    """Automated verification for Phase 11 File 4."""
    print("\n[*] Running automated self-tests...")

    # Test 1: PII Redactor masks emails
    raw_email = "Contact developer at john.doe@company.org for access"
    clean_email = PIIRedactor.sanitize(raw_email)
    assert "[REDACTED_EMAIL]" in clean_email
    assert "john.doe@" not in clean_email

    # Test 2: PII Redactor masks Bearer tokens
    raw_auth = "Authorization: Bearer sk-ant-api03-secretkey"
    clean_auth = PIIRedactor.sanitize(raw_auth)
    assert "Bearer [REDACTED_TOKEN]" in clean_auth

    # Test 3: Root span creation
    tracer = Tracer()
    with tracer.start_trace("root_operation") as root:
        root.set_attribute("env", "prod")
    assert len(tracer.spans) == 1
    root_s = tracer.spans[0]
    assert root_s.parent_span_id is None
    assert root_s.duration_ms >= 0

    # Test 4: Nested child span inherits trace_id and sets parent_span_id
    with tracer.start_trace("parent_op") as p:
        with tracer.start_span("child_op") as c:
            c.set_attribute("step", 2)

    parent_span = tracer.spans[1]
    child_span = tracer.spans[2]
    assert child_span.trace_id == parent_span.trace_id, "Child must share trace_id"
    assert child_span.parent_span_id == parent_span.span_id, "Child must reference parent_span_id"

    # Test 5: Sanitizer automatically invoked on set_attribute
    with tracer.start_trace("test_sanitization") as s:
        s.set_attribute("email", "test@test.com")
    assert tracer.spans[-1].attributes["email"] == "[REDACTED_EMAIL]"

    # Test 6: Span duration measurement
    assert parent_span.duration_ms > 0

    # Test 7: Span captures exceptions as error field
    try:
        with tracer.start_trace("faulty_op"):
            raise ValueError("Database connection lost")
    except ValueError:
        pass
    assert tracer.spans[-1].error == "Database connection lost"

    # Test 8: Context resets cleanly after exit
    assert current_span_id.get() is None

    # Test 9: Concurrent traces maintain separate trace IDs
    async def run_async_trace(name: str):
        with tracer.start_trace(name) as s:
            await asyncio.sleep(0.01)
            return s.span.trace_id

    async def test_concurrent():
        t1, t2 = await asyncio.gather(run_async_trace("t1"), run_async_trace("t2"))
        assert t1 != t2, "Concurrent traces must have distinct trace IDs"

    asyncio.run(test_concurrent())

    # Test 10: Span count correctness
    assert len(tracer.spans) >= 6

    print("[SUCCESS] All 10 Observability & Tracing self-tests passed!")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 11: Observability, Tracing & Cost Accounting")
    print("=" * 70)
    asyncio.run(demonstrate_full_request_tracing())
    print("-" * 70)
    run_tests()
    print("=" * 70)
