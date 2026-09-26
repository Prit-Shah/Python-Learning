r"""
04_observability_and_tracing.py

============================================================
1. CONCEPT
============================================================

Enterprise AI systems require continuous visibility into token usage, latency bottlenecks,
prompt evolution, and factual accuracy. OpenTelemetry (OTel) distributed tracing combined
with automated evaluation metrics provides full-lifecycle AI observability:

1. OpenTelemetry Distributed Tracing Architecture:
   - Traditional APM monitoring treats LLM calls as black boxes.
   - Distributed Tracing models an AI request as a Directed Acyclic Graph (DAG) of Spans:
     * Root Span (`rag_pipeline_request`): Represents the overall user interaction.
     * Child Span 1 (`embedding.create`): Measures tokenization and vector embedding latency.
     * Child Span 2 (`vector_db.query`): Measures ANN similarity search and HNSW traversal.
     * Child Span 3 (`reranker.cross_encode`): Measures candidate re-ranking.
     * Child Span 4 (`llm.generate`): Measures Time-To-First-Token, prompt tokens, completion tokens.
   - Semantic Conventions for Generative AI (OpenTelemetry SemConv):
     * Standardized attribute keys across all vendors and APMs:
       `gen_ai.system = "openai"`
       `gen_ai.request.model = "gpt-4o"`
       `gen_ai.usage.input_tokens = 450`
       `gen_ai.usage.output_tokens = 120`
       `gen_ai.response.finish_reasons = ["stop"]`

2. The RAG Triad of Evaluation Metrics:
   - Context Relevance: Does the retrieved context contain information relevant to the question?
   - Faithfulness (Groundedness): Can every factual claim in the generated answer be inferred
     STRICTLY from the provided context? (Detects hallucinations).
     $$\text{Faithfulness} = \frac{\text{Supported Claims}}{\text{Total Factual Claims}}$$
   - Answer Relevance: Does the response directly address the user's inquiry without extraneous digressions?


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python (OpenTelemetry Python)      | JavaScript / TypeScript (Node.js)  |
+------------------------------+------------------------------------+------------------------------------+
| Tracer Provider              | `trace.get_tracer(__name__)`       | `trace.getTracer('ai-service')`    |
| Span Scope Management        | `with tracer.start_as_current_span:`| `tracer.startActiveSpan(name, fn)` |
| W3C Propagation Header       | `traceparent` (32-hex trace ID)    | `traceparent` HTTP header          |
| AI Observability Tooling     | Langfuse / Arize Phoenix / TruLens | Langfuse JS / Helicone / Braintrust|
| Async Context Tracking       | Python `contextvars`               | `AsyncLocalStorage`                |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Architecture Differences:
1. In Node.js, `tracer.startActiveSpan(name, span => { ... span.end(); })` requires nested callback
   closures or explicit `.finally()` handlers to prevent dangling unclosed spans.
2. In Python, the context manager protocol (`with tracer.start_as_current_span(...) as span:`) automatically
   handles span duration measurement, status recording, and exception propagation via `__exit__`.


============================================================
3. UNDER THE HOOD (W3C TraceContext & Claim Extraction)
============================================================

1. W3C TraceContext Wire Protocol (`traceparent`):
   - Standardized 4-part string format: `version-trace_id-parent_id-trace_flags`
     Example: `00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01`
   - `trace_id`: 16-byte (32 hex char) unique ID identifying the entire transaction across services.
   - `parent_id`: 8-byte (16 hex char) ID linking a child span to its parent span.

2. Automated Faithfulness Evaluation Pipeline:
   - Step 1 (Decomposition): Parse generated text into atomic, independent propositional claims.
   - Step 2 (Verification): Evaluate each claim against retrieved context chunks using string/NLI entailment.
   - Step 3 (Score Calculation): Fraction of claims verified. If score $< 0.8$, flag for human review
     or prevent response dispatch.


============================================================
4. COMMON GOTCHAS
============================================================

1. Leaking PII into Trace Span Attributes:
   - Storing un-redacted user prompts containing credit cards, passwords, or medical records
     in trace attributes transmits sensitive data to third-party tracing platforms.
   - FIX: Implement a sanitization filter before attaching attributes to spans.

2. Failing to Mark Span Status on Exceptions:
   - If an exception is caught and handled inside the span without calling `span.set_status(StatusCode.ERROR)`
     and `span.record_exception(err)`, APM dashboards will report the span as successful!
   - FIX: Ensure context managers record exception metadata automatically.

3. Excessive Span Granularity in Token Streaming:
   - Creating an individual span for every streamed token chunk generates millions of useless
     spans, crashing tracing collectors.
   - FIX: Measure streaming within a single `llm.stream` span, recording `time_to_first_token` as an attribute.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "How do you implement distributed tracing and observability in an enterprise AI system?"
A1: "I instrument AI services using OpenTelemetry and OpenLLMetry Semantic Conventions.
     Each user interaction initiates a root transaction span carrying a W3C `traceparent` trace ID.
     Within the pipeline, we record child spans for every discrete stage: prompt rendering, embedding
     generation, vector database lookup, re-ranking, and LLM inference.
     On the LLM span, we record standardized `gen_ai.*` attributes: provider system, model version,
     temperature, prompt tokens, completion tokens, and latency.
     Traces are exported via OTLP (OpenTelemetry Protocol) to backends like Langfuse, Arize Phoenix,
     or Datadog, giving us real-time visualization of cost, latency bottlenecks, and error rates across
     all microservices."

Q2: "What is the RAG Triad, and how do you evaluate an LLM application without human labels?"
A2: "The RAG Triad consists of three automated evaluation metrics:
     First, Context Relevance: Measures how well retrieved context matches the user query, identifying
     retrieval noise and bad chunking.
     Second, Faithfulness (Groundedness): Measures the ratio of factual claims in the generated response
     that are mathematically supported by the retrieved context. This is our primary detector for hallucinations.
     Third, Answer Relevance: Measures whether the generated answer directly satisfies the user prompt.
     In production, we compute these metrics asynchronously using a lightweight 'LLM-as-a-Judge' or NLI
     model on a sampled percentage of production traces, generating automated alerts if faithfulness drops
     below our quality threshold."

Q3: "How do you trace asynchronous streaming responses without overwhelming tracing systems?"
A3: "Instead of creating a span for every token—which would generate thousands of spans per request and
     flood the collector—I encapsulate the entire streaming lifecycle in a single `llm.stream` span.
     When the async generator yields its first chunk, I record a span event or attribute: `time_to_first_token_ms`.
     As subsequent chunks stream, I accumulate token counts in memory.
     When the stream completes, I record final token usage, total stream duration, and finish reason before
     closing the span. This captures critical user-experience metrics (TTFT and overall throughput) with
     zero telemetry bloat."
"""

import sys
import time
import uuid
import re
import warnings
warnings.filterwarnings("ignore")
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ==============================================================================
# 1. OPENTELEMETRY TRACE & SPAN SIMULATION ENGINE
# ==============================================================================

class StatusCode(str, Enum):
    OK = "OK"
    ERROR = "ERROR"
    UNSET = "UNSET"


@dataclass
class Span:
    name: str
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    status: StatusCode = StatusCode.UNSET
    exception: Optional[str] = None

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def set_status(self, status: StatusCode) -> None:
        self.status = status

    def record_exception(self, exc: Exception) -> None:
        self.status = StatusCode.ERROR
        self.exception = f"{type(exc).__name__}: {str(exc)}"

    def end(self) -> None:
        self.end_time = time.time()


class Tracer:
    """Simulates an OpenTelemetry Tracer managing hierarchical span context."""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.spans: List[Span] = []
        self._active_span: Optional[Span] = None

    def start_span(self, name: str, trace_id: Optional[str] = None) -> Span:
        t_id = trace_id or (self._active_span.trace_id if self._active_span else uuid.uuid4().hex)
        parent_id = self._active_span.span_id if self._active_span else None
        span_id = uuid.uuid4().hex[:16]

        span = Span(
            name=name,
            trace_id=t_id,
            span_id=span_id,
            parent_span_id=parent_id
        )
        self.spans.append(span)
        return span

    def create_span_context(self, name: str):
        """Context manager for structured span execution."""
        return _SpanContextManager(self, name)


class _SpanContextManager:
    def __init__(self, tracer: Tracer, name: str):
        self.tracer = tracer
        self.name = name
        self.span: Optional[Span] = None
        self.previous_active: Optional[Span] = None

    def __enter__(self) -> Span:
        self.previous_active = self.tracer._active_span
        self.span = self.tracer.start_span(self.name)
        self.tracer._active_span = self.span
        return self.span

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val and self.span:
            self.span.record_exception(exc_val)
        elif self.span:
            self.span.set_status(StatusCode.OK)

        if self.span:
            self.span.end()

        # Restore previous active span
        self.tracer._active_span = self.previous_active
        return False  # Do not swallow exception


# ==============================================================================
# 2. AUTOMATED EVALUATION: FAITHFULNESS / GROUNDEDNESS EVALUATOR
# ==============================================================================

class GroundednessEvaluator:
    """
    Evaluates whether generated responses are faithful to context chunks
    (Hallucination detection).
    """

    @staticmethod
    def evaluate_faithfulness(generated_response: str, context_documents: List[str]) -> Tuple[float, List[str]]:
        """
        Decomposes response into sentences and computes the fraction of sentences
        supported by the context text.
        """
        # Split response into sentence claims
        sentences = [s.strip() for s in re.split(r"[.!?]", generated_response) if len(s.strip()) > 5]
        if not sentences:
            return 1.0, []

        joined_context = " ".join(context_documents).lower()
        unsupported_claims: List[str] = []

        supported_count = 0
        for sent in sentences:
            # Check if key words in sentence exist in context
            words = [w for w in re.findall(r"\w+", sent.lower()) if len(w) > 3]
            if not words:
                supported_count += 1
                continue

            matches = sum(1 for w in words if w in joined_context)
            support_ratio = matches / len(words)

            if support_ratio >= 0.6:  # 60% term alignment threshold
                supported_count += 1
            else:
                unsupported_claims.append(sent)

        faithfulness_score = round(supported_count / len(sentences), 2)
        return faithfulness_score, unsupported_claims


# ==============================================================================
# 3. SELF-TESTING SUITE
# ==============================================================================

def run_tests() -> None:
    print("\n[*] Starting automated test suite for 04_observability_and_tracing.py...")

    tracer = Tracer(service_name="rag_search_service")

    # ------------------------------------------------------------
    # Test 1: OpenTelemetry Hierarchical Trace & Span Tree
    # ------------------------------------------------------------
    print("  -> Testing OpenTelemetry span hierarchy and W3C trace_id propagation...")
    with tracer.create_span_context("rag_pipeline_request") as root_span:
        root_span.set_attribute("http.method", "POST")
        root_span.set_attribute("http.route", "/api/chat")

        # Child Span 1: Vector Search
        with tracer.create_span_context("vector_search") as search_span:
            search_span.set_attribute("db.system", "pgvector")
            search_span.set_attribute("db.query.top_k", 5)
            time.sleep(0.01)

        # Child Span 2: LLM Generation
        with tracer.create_span_context("llm.generate") as llm_span:
            # SemConv for GenAI
            llm_span.set_attribute("gen_ai.system", "openai")
            llm_span.set_attribute("gen_ai.request.model", "gpt-4o")
            llm_span.set_attribute("gen_ai.usage.input_tokens", 350)
            llm_span.set_attribute("gen_ai.usage.output_tokens", 85)
            time.sleep(0.01)

    assert len(tracer.spans) == 3
    root = tracer.spans[0]
    search = tracer.spans[1]
    llm = tracer.spans[2]

    # Verify W3C trace ID was propagated to all children
    assert root.trace_id == search.trace_id == llm.trace_id
    # Verify parent-child links
    assert search.parent_span_id == root.span_id
    assert llm.parent_span_id == root.span_id
    assert root.parent_span_id is None
    # Verify SemConv attributes
    assert llm.attributes["gen_ai.request.model"] == "gpt-4o"
    assert llm.status == StatusCode.OK

    # ------------------------------------------------------------
    # Test 2: Span Exception & Error Status Recording
    # ------------------------------------------------------------
    print("  -> Testing span exception capture and error status recording...")
    try:
        with tracer.create_span_context("failing_provider_call") as err_span:
            raise TimeoutError("LLM provider socket timed out after 10000ms")
    except TimeoutError:
        pass

    assert len(tracer.spans) == 4
    failed_span = tracer.spans[-1]
    assert failed_span.status == StatusCode.ERROR
    assert "TimeoutError" in failed_span.exception
    assert failed_span.end_time is not None

    # ------------------------------------------------------------
    # Test 3: Groundedness & Faithfulness Evaluation Scoring
    # ------------------------------------------------------------
    print("  -> Testing automated Faithfulness / Hallucination detection...")
    context = [
        "FastAPI is an asynchronous web framework for Python.",
        "SQLAlchemy 2.0 provides modern typed data access using Mapped and mapped_column."
    ]

    # Grounded response: 100% supported by context
    faithful_resp = (
        "FastAPI is an asynchronous web framework. "
        "SQLAlchemy provides typed data access using Mapped columns."
    )
    score_f, unsupp_f = GroundednessEvaluator.evaluate_faithfulness(faithful_resp, context)
    assert score_f == 1.0
    assert len(unsupp_f) == 0

    # Hallucinated response: mentions Django and Ruby on Rails which are not in context
    hallucinated_resp = (
        "FastAPI is an asynchronous framework. "
        "Django was created in Ruby on Rails by Japanese developers."
    )
    score_h, unsupp_h = GroundednessEvaluator.evaluate_faithfulness(hallucinated_resp, context)
    assert score_h < 1.0
    assert len(unsupp_h) > 0
    assert any("Django" in claim for claim in unsupp_h)

    print("[SUCCESS] All 3 Observability, Tracing & Evaluation tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 11 - 04: Observability, OpenTelemetry Tracing & Evaluation")
    print("=" * 70)
    run_tests()
    print("=" * 70)
