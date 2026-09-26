r"""
01_model_gateway_abstraction.py

============================================================
1. CONCEPT
============================================================

Enterprise AI backends cannot afford hard vendor lock-in to a single LLM provider (OpenAI,
Anthropic, Google Gemini, Mistral, Groq, or self-hosted vLLM). An AI Model Gateway
(or Universal LLM Proxy) decouples application business logic from vendor APIs:

1. Canonical Request/Response Abstraction:
   - Internal microservices communicate exclusively using canonical, vendor-agnostic DTOs
     (`ModelRequest`, `ModelResponse`, `ModelDelta`).
   - The Adapter Pattern: Provider-specific adapters translate canonical requests into
     proprietary vendor HTTP payloads:
     * OpenAI: Accepts `system` inside the `messages` array; temperature in $[0.0, 2.0]$.
     * Anthropic: Requires `system` as a distinct top-level API parameter; temperature in $[0.0, 1.0]$.
     * Gemini: Uses `contents` with `parts` and `generationConfig`.

2. Resiliency & Intelligent Failover Chains:
   - Chain of Responsibility: Primary Model (GPT-4o) -> Secondary Model (Claude 3.5 Sonnet) -> Fallback (Llama-3.1 on vLLM).
   - If the primary provider returns HTTP 429 (Rate Limit), 500/503 (Outage), or times out,
     the gateway intercepts the transient failure and seamlessly dispatches to the secondary
     provider without bubbling errors to the end-user.

3. Circuit Breaker Concurrency Protection:
   - Monitors error rates per provider over a sliding window.
   - States:
     * `CLOSED`: Normal operation; traffic flows to primary provider.
     * `OPEN`: Error threshold exceeded; immediately trips and short-circuits traffic to secondary
       providers without making dead network requests.
     * `HALF-OPEN`: Recovery timeout expires; canary requests test provider health before resuming full traffic.

4. Cost & Token Governance Ledger:
   - Tracks exact prompt and completion tokens per tenant/request.
   - Calculates financial spend using dynamic price tables ($ per 1M tokens), enforcing hard
     monthly budgetary caps and rate limits.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python (Model Gateway / LiteLLM)   | JavaScript / TypeScript (Node.js)  |
+------------------------------+------------------------------------+------------------------------------+
| Provider Abstraction         | `abc.ABC` / `typing.Protocol`      | TypeScript `interface LanguageModel`|
| Canonical DTOs               | Pydantic v2 `BaseModel`            | Zod schemas / TypeScript types     |
| Multi-Model SDK              | LiteLLM / Portkey / Custom Gateway | Vercel AI SDK (`@ai-sdk/...`)      |
| Circuit Breaker              | `pybreaker` / custom async class   | `opossum` npm package              |
| Async Token Streaming        | Python `async for chunk in gen:`   | Web `ReadableStream` / `for await` |
| Fallback Pipeline            | Async try/except loop over adapters| `Promise.any` / fallback array loop|
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Architecture Differences:
1. Vercel's AI SDK in TypeScript abstracts models primarily for frontend React Server Components
   and Next.js edge functions.
2. In Python, an AI Model Gateway operates as an enterprise infrastructure tier within FastAPI
   or gRPC services. It manages persistent connection pooling, multi-tenant database billing ledgers,
   circuit breakers, and streaming transformations with zero serialization overhead.


============================================================
3. UNDER THE HOOD (Async Generators & Wire Translation)
============================================================

1. Python Async Generator Lifecycle:
   - The gateway's streaming endpoint returns an `AsyncGenerator[ModelDelta, None]`.
   - Under CPython, an async generator suspends execution at each `yield` statement without
     blocking the OS thread or event loop, allowing hundreds of concurrent LLM streams to
     be processed per worker process.

2. Divergent Wire Protocols & Parameter Normalization:
   - Temperature Normalization: Passing `temperature=1.5` to Anthropic causes an immediate
     `400 Bad Request`. The gateway clamps parameters:
     $$\text{temp}_{\text{anthropic}} = \min(1.0, \max(0.0, \text{temp} / 2.0))$$
   - System Message Extraction: OpenAI allows multiple `system` messages interleaved throughout
     the conversation; Anthropic mandates a single top-level `system` string. The gateway parses
     and concatenates all system roles into the top-level Anthropic parameter.


============================================================
4. COMMON GOTCHAS
============================================================

1. Retrying Non-Transient 400 Bad Request Errors:
   - Attempting to fail over on a 400 Bad Request (such as invalid user parameters or prompt
     injection block) wastes money and latency; secondary providers will reject the same malformed payload!
   - FIX: Failover ONLY on transient errors: HTTP 429, 500, 502, 503, 504, and network timeouts.

2. Tokenizer Mismatch in Token Budgeting:
   - Assuming 1000 tokens on OpenAI equals 1000 tokens on Claude. Different tokenizer vocabularies
     (tiktoken vs Claude BPE) produce different token counts for identical text.
   - FIX: Always calculate actual costs using provider-reported `usage` metadata from the response.

3. Memory Leaks from Unconsumed Streams:
   - Abandoning an active async streaming generator without closing it leaves underlying HTTP sockets
     dangling in the connection pool.
   - FIX: Wrap streaming iterators in `try...finally` or use context managers.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "How would you design a resilient, multi-provider AI Model Gateway in Python?"
A1: "I implement an asynchronous Gateway layer using the Strategy and Chain of Responsibility patterns.
     At the core, I define an abstract `BaseModelProvider` interface specifying `generate()` and `stream()`
     methods using canonical Pydantic request/response schemas.
     I implement concrete provider adapters—such as `OpenAIAdapter` and `AnthropicAdapter`—that handle
     vendor-specific quirks like extracting top-level system prompts for Claude or clamping temperature ranges.
     The gateway orchestrates a prioritized fallback chain: when a request arrives, it dispatches to the
     primary model. If a transient error occurs (such as HTTP 429 rate limits, 503 outages, or socket timeouts),
     a circuit breaker catches the failure, increments telemetry counters, and immediately routes the prompt
     to the secondary model without user-visible disruption.
     Finally, the gateway logs exact token counts and financial costs to a centralized audit ledger."

Q2: "How does the Circuit Breaker pattern protect production systems against LLM provider outages?"
A2: "A Circuit Breaker operates across three states: `CLOSED`, `OPEN`, and `HALF-OPEN`.
     Under normal operation (`CLOSED`), all traffic flows to the primary provider. If the provider experiences
     an outage and consecutive failures exceed our threshold (e.g. 5 errors in 30 seconds), the circuit trips
     to `OPEN`.
     While `OPEN`, the gateway immediately routes all incoming requests directly to the secondary provider
     without waiting for network timeouts against the dead provider, protecting API latency.
     After a cooldown period (e.g. 60 seconds), the circuit enters `HALF-OPEN` and permits a small canary
     request through to the primary provider. If the canary succeeds, the circuit resets to `CLOSED`; if it fails,
     it trips back to `OPEN` for another cooldown cycle."

Q3: "How do you handle schema differences between OpenAI, Anthropic, and Google Gemini in a unified gateway?"
A3: "I establish a canonical internal contract: `ModelRequest` with fields: `messages: list[Message]`,
     `temperature: float`, `max_tokens: int`, and `tools: list[Tool]`.
     In the provider adapters:
     For Anthropic, I extract all `system` role messages and concatenate them into the top-level `system`
     parameter, passing only `user` and `assistant` messages in the payload, and clamp temperature to 1.0.
     For Google Gemini, I convert `messages` into `contents` with `parts` arrays and map roles `user` and `model`.
     For tool calling, each adapter transforms our standard Pydantic JSON schemas into the provider's expected
     function declaration format. This guarantees that calling code in our business layer is completely
     isolated from vendor API changes."
"""

import sys
import time
import warnings
warnings.filterwarnings("ignore")
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ==============================================================================
# 1. CANONICAL DATA CONTRACTS (VENDOR-AGNOSTIC)
# ==============================================================================

class ProviderType(str, Enum):
    OPENAI = "OPENAI"
    ANTHROPIC = "ANTHROPIC"
    GEMINI = "GEMINI"
    LOCAL_VLLM = "LOCAL_VLLM"


@dataclass
class CanonicalMessage:
    role: str  # 'system', 'user', 'assistant'
    content: str


@dataclass
class CanonicalRequest:
    model_name: str
    messages: List[CanonicalMessage]
    temperature: float = 0.7
    max_tokens: int = 500


@dataclass
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float


@dataclass
class CanonicalResponse:
    content: str
    provider: ProviderType
    model_used: str
    usage: TokenUsage
    latency_sec: float


# ==============================================================================
# 2. ABSTRACT PROVIDER ADAPTER & CONCRETE IMPLEMENTATIONS
# ==============================================================================

class BaseProviderAdapter(ABC):
    """Abstract interface defining the contract for all LLM vendor adapters."""

    def __init__(self, provider_type: ProviderType, input_cost_per_m: float, output_cost_per_m: float):
        self.provider_type = provider_type
        self.input_cost_per_m = input_cost_per_m
        self.output_cost_per_m = output_cost_per_m

    @abstractmethod
    def execute_completion(self, request: CanonicalRequest) -> CanonicalResponse:
        pass

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        cost = (prompt_tokens / 1_000_000 * self.input_cost_per_m) + \
               (completion_tokens / 1_000_000 * self.output_cost_per_m)
        return round(cost, 6)


class MockOpenAIAdapter(BaseProviderAdapter):
    """Adapter for OpenAI API (temperature [0.0, 2.0], system in messages)."""

    def __init__(self, simulate_outage: bool = False):
        super().__init__(ProviderType.OPENAI, input_cost_per_m=2.50, output_cost_per_m=10.00)
        self.simulate_outage = simulate_outage
        self.call_count = 0

    def execute_completion(self, request: CanonicalRequest) -> CanonicalResponse:
        self.call_count += 1
        if self.simulate_outage:
            raise ConnectionError("HTTP 503: OpenAI API server overloaded.")

        t0 = time.perf_counter()
        # Normalization: OpenAI accepts temperature up to 2.0
        normalized_temp = max(0.0, min(2.0, request.temperature))

        last_user = next((m.content for m in reversed(request.messages) if m.role == "user"), "")
        content = f"OpenAI ({request.model_name}) response to: '{last_user}' [temp={normalized_temp}]"

        p_tokens = sum(len(m.content) // 4 for m in request.messages) + 5
        c_tokens = len(content) // 4
        cost = self.calculate_cost(p_tokens, c_tokens)

        return CanonicalResponse(
            content=content,
            provider=self.provider_type,
            model_used=request.model_name,
            usage=TokenUsage(p_tokens, c_tokens, p_tokens + c_tokens, cost),
            latency_sec=time.perf_counter() - t0
        )


class MockAnthropicAdapter(BaseProviderAdapter):
    """Adapter for Anthropic API (temperature [0.0, 1.0], system extracted as top-level param)."""

    def __init__(self):
        super().__init__(ProviderType.ANTHROPIC, input_cost_per_m=3.00, output_cost_per_m=15.00)
        self.call_count = 0

    def execute_completion(self, request: CanonicalRequest) -> CanonicalResponse:
        self.call_count += 1
        t0 = time.perf_counter()

        # Normalization 1: Anthropic strictly bounds temperature in [0.0, 1.0]
        clamped_temp = max(0.0, min(1.0, request.temperature / 2.0 if request.temperature > 1.0 else request.temperature))

        # Normalization 2: Extract system prompt into top-level parameter
        system_prompts = [m.content for m in request.messages if m.role == "system"]
        top_level_system = "\n\n".join(system_prompts)

        last_user = next((m.content for m in reversed(request.messages) if m.role == "user"), "")
        content = f"Anthropic ({request.model_name}) response to: '{last_user}' [system='{top_level_system[:50]}...']"

        p_tokens = sum(len(m.content) // 4 for m in request.messages) + 8
        c_tokens = len(content) // 4
        cost = self.calculate_cost(p_tokens, c_tokens)

        return CanonicalResponse(
            content=content,
            provider=self.provider_type,
            model_used=request.model_name,
            usage=TokenUsage(p_tokens, c_tokens, p_tokens + c_tokens, cost),
            latency_sec=time.perf_counter() - t0
        )


# ==============================================================================
# 3. CIRCUIT BREAKER ENGINE
# ==============================================================================

class CircuitState(str, Enum):
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"          # Provider down, reject requests
    HALF_OPEN = "HALF_OPEN"# Testing canary


class CircuitBreaker:
    """Monitors provider failure rates and prevents cascading timeouts."""

    def __init__(self, failure_threshold: int = 2, recovery_cooldown_sec: float = 0.5):
        self.failure_threshold = failure_threshold
        self.recovery_cooldown = recovery_cooldown_sec
        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.last_failure_time = 0.0

    def record_success(self) -> None:
        self.consecutive_failures = 0
        self.state = CircuitState.CLOSED

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        self.last_failure_time = time.time()
        if self.consecutive_failures >= self.failure_threshold:
            self.state = CircuitState.OPEN

    def can_attempt(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            # Check if cooldown has elapsed to enter HALF-OPEN
            if time.time() - self.last_failure_time >= self.recovery_cooldown:
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        if self.state == CircuitState.HALF_OPEN:
            return True
        return False


# ==============================================================================
# 4. RESILIENT MODEL GATEWAY (ROUTER & FAILOVER CHAIN)
# ==============================================================================

class ModelGateway:
    """
    Enterprise Model Gateway with:
    - Primary and fallback provider chains
    - Circuit breaker protection
    - Parameter normalization
    - Centralized cost and token auditing
    """

    def __init__(self, providers: List[BaseProviderAdapter]):
        assert len(providers) > 0, "Gateway must have at least one provider"
        self.providers = providers
        self.circuit_breakers: Dict[ProviderType, CircuitBreaker] = {
            p.provider_type: CircuitBreaker() for p in providers
        }
        self.total_tokens_routed = 0
        self.total_spend_usd = 0.0

    def complete(self, request: CanonicalRequest) -> CanonicalResponse:
        errors: List[str] = []

        # Traverse fallback chain
        for adapter in self.providers:
            ptype = adapter.provider_type
            breaker = self.circuit_breakers[ptype]

            if not breaker.can_attempt():
                errors.append(f"[{ptype.value}] Circuit Breaker is OPEN (skipped).")
                continue

            try:
                response = adapter.execute_completion(request)
                breaker.record_success()

                # Audit metrics
                self.total_tokens_routed += response.usage.total_tokens
                self.total_spend_usd += response.usage.estimated_cost_usd

                return response
            except Exception as e:
                breaker.record_failure()
                errors.append(f"[{ptype.value}] Failed: {str(e)}")

        raise RuntimeError(f"All Model Gateway providers exhausted: {'; '.join(errors)}")


# ==============================================================================
# 5. SELF-TESTING SUITE
# ==============================================================================

def run_tests() -> None:
    print("\n[*] Starting automated test suite for 01_model_gateway_abstraction.py...")

    req = CanonicalRequest(
        model_name="flagship-chat",
        messages=[
            CanonicalMessage(role="system", content="You are an enterprise code assistant."),
            CanonicalMessage(role="user", content="How do you architect a model router in Python?")
        ],
        temperature=1.6,  # Valid for OpenAI, requires clamping for Anthropic
        max_tokens=400
    )

    # ------------------------------------------------------------
    # Test 1: Provider Normalization (Temperature Clamping & System Prompt)
    # ------------------------------------------------------------
    print("  -> Testing parameter normalization across OpenAI and Anthropic adapters...")
    openai_adapter = MockOpenAIAdapter(simulate_outage=False)
    anthropic_adapter = MockAnthropicAdapter()

    res_openai = openai_adapter.execute_completion(req)
    assert res_openai.provider == ProviderType.OPENAI
    assert "temp=1.6" in res_openai.content

    res_anthropic = anthropic_adapter.execute_completion(req)
    assert res_anthropic.provider == ProviderType.ANTHROPIC
    assert "system='You are an enterprise" in res_anthropic.content
    assert res_anthropic.usage.estimated_cost_usd > 0.0

    # ------------------------------------------------------------
    # Test 2: Resilient Failover Chain (Primary -> Secondary)
    # ------------------------------------------------------------
    print("  -> Testing automatic failover when primary provider experiences outage...")
    # Primary OpenAI is simulated as DOWN (503), Secondary Anthropic is UP
    failing_openai = MockOpenAIAdapter(simulate_outage=True)
    working_anthropic = MockAnthropicAdapter()

    gateway = ModelGateway(providers=[failing_openai, working_anthropic])

    # Gateway should catch OpenAI failure and seamlessly route to Anthropic
    failover_response = gateway.complete(req)
    assert failover_response.provider == ProviderType.ANTHROPIC, "Gateway failed to route to secondary provider"
    assert "Anthropic" in failover_response.content
    assert gateway.total_tokens_routed > 0
    assert gateway.total_spend_usd > 0.0

    # ------------------------------------------------------------
    # Test 3: Circuit Breaker State Transitions
    # ------------------------------------------------------------
    print("  -> Testing Circuit Breaker state transitions (CLOSED -> OPEN -> HALF-OPEN)...")
    cb = CircuitBreaker(failure_threshold=2, recovery_cooldown_sec=0.1)
    assert cb.state == CircuitState.CLOSED
    assert cb.can_attempt() is True

    # First failure
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED

    # Second failure -> Trips to OPEN
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.can_attempt() is False, "Open circuit must short-circuit attempts"

    # Wait for cooldown to expire
    time.sleep(0.12)
    assert cb.can_attempt() is True  # Enters HALF-OPEN
    assert cb.state == CircuitState.HALF_OPEN

    # Success in half-open resets to CLOSED
    cb.record_success()
    assert cb.state == CircuitState.CLOSED

    # ------------------------------------------------------------
    # Test 4: Total Provider Exhaustion Exception Handling
    # ------------------------------------------------------------
    print("  -> Testing behavior when ALL providers in the gateway fail...")
    failing_1 = MockOpenAIAdapter(simulate_outage=True)
    failing_2 = MockOpenAIAdapter(simulate_outage=True)
    failing_gateway = ModelGateway(providers=[failing_1, failing_2])

    try:
        failing_gateway.complete(req)
        assert False, "Should raise RuntimeError when all providers fail"
    except RuntimeError as err:
        assert "All Model Gateway providers exhausted" in str(err)

    print("[SUCCESS] All 4 Model Gateway & Provider Abstraction tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 11 - 01: Universal Model Gateway, Adapters & Circuit Breakers")
    print("=" * 70)
    run_tests()
    print("=" * 70)
