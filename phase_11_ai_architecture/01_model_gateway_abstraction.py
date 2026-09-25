"""
Phase 11: Model Gateway & Provider Abstraction
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - Concept: An AI Model Gateway (or LLM Router) decouples your application
     logic from individual LLM vendors (OpenAI, Anthropic, Google, Mistral,
     or self-hosted vLLM). It provides a unified API, intelligent load balancing,
     automated failover, cost-aware model routing, and token spend tracking.
   - JS/TS Equivalent: Similar to the Multi-Provider Payment Gateway pattern
     in Node.js (e.g. abstracting Stripe vs Adyen vs PayPal behind a uniform
     PaymentService interface), or ORMs abstracting Postgres vs MySQL.
     In Python AI engineering, libraries like LiteLLM or Portkey implement this,
     but every production system needs a tailored internal gateway layer.
   - Key benefits: Zero-downtime model switches, multi-region fallback during
     outages, routing simple queries to cheap models and complex queries to
     flagship models, unified cost ledger.

2. UNDER THE HOOD (CPython & Memory):
   - Gateway acts as an asynchronous facade using Python's Protocol / Abstract
     Base Classes (`abc.ABC`).
   - Normalization: Ingests a canonical request structure (e.g. messages list,
     temperature, max_tokens) and translates it to provider-specific payloads:
     OpenAI `max_tokens` vs Anthropic `max_tokens_to_sample` vs Google `max_output_tokens`.
   - Dynamic Dispatch & Async Chain: Evaluates provider health, executes the
     call via an async client, and if a 429 (Rate Limit) or 503 (Overloaded)
     occurs, catches the exception and immediately invokes the next provider
     in the fallback chain without blocking the event loop.

3. COMMON GOTCHA:
   - Parameter & Tokenizer Mismatches: Token counts differ wildly between
     tokenizers (tiktoken for OpenAI vs Claude BPE vs SentencePiece). Never
     assume 1 token on OpenAI equals 1 token on Claude.
   - Clamped Temperature Ranges: Anthropic supports temperature in [0.0, 1.0],
     whereas OpenAI supports [0.0, 2.0]. Sending 1.5 to Anthropic throws an
     immediate 400 Bad Request unless your gateway normalizes/clamps inputs.

4. 🎙️ INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   - Interview Question: "How would you design an enterprise Model Gateway in
     Python to handle vendor outages and optimize LLM spend?"
   - How to Answer Out Loud (60-90 sec verbal script):
     * "I implement a Model Gateway using the Strategy and Chain of Responsibility
       patterns. At the core is an abstract `ModelProvider` protocol with unified
       `complete()` and `stream()` methods."
     * "The gateway sits between our business microservices and external LLMs.
       When a request arrives, the router checks the task classification:
       high-volume extraction jobs route to cheap models like GPT-4o-mini or
       Claude 3.5 Haiku; complex reasoning routes to flagship models."
     * "For resiliency, I configure a fallback chain: if the primary provider
       returns a 429, 500, or times out after 8 seconds, the gateway catches the
       transient error, increments a circuit breaker counter, and seamlessly
       invokes the secondary provider with the translated prompt."
     * "Finally, the gateway logs token usage and estimated cost to a centralized
       Redis/TimescaleDB ledger to enforce per-tenant quotas and budget alerts."
================================================================================
"""

import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator


# ── Canonical Gateway Domain Models ──────────────────────────────────────────

class ProviderName(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"


@dataclass(frozen=True)
class GatewayMessage:
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class GatewayResponse:
    content: str
    provider: ProviderName
    model_name: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    latency_ms: float


class ProviderException(Exception):
    """Base exception for provider errors."""
    def __init__(self, provider: ProviderName, message: str, status_code: int = 500):
        super().__init__(f"[{provider.value}] {status_code}: {message}")
        self.provider = provider
        self.status_code = status_code


class RateLimitExceededException(ProviderException):
    """Raised when provider returns HTTP 429."""
    def __init__(self, provider: ProviderName):
        super().__init__(provider, "Rate limit exceeded (HTTP 429)", status_code=429)


# ── Provider Abstract Base Class ─────────────────────────────────────────────

class ModelProvider(ABC):
    """Abstract Strategy representing an LLM Provider Adapter."""

    def __init__(self, name: ProviderName, cost_per_1k_input: float, cost_per_1k_output: float):
        self.name = name
        self.cost_per_1k_input = cost_per_1k_input
        self.cost_per_1k_output = cost_per_1k_output

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Unified cost calculation based on token pricing."""
        input_cost = (prompt_tokens / 1000.0) * self.cost_per_1k_input
        output_cost = (completion_tokens / 1000.0) * self.cost_per_1k_output
        return round(input_cost + output_cost, 6)

    @abstractmethod
    async def complete(
        self,
        messages: list[GatewayMessage],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> GatewayResponse:
        """Execute non-streaming completion."""
        pass


# ── Concrete Mock Providers ──────────────────────────────────────────────────

class MockOpenAIProvider(ModelProvider):
    def __init__(self, should_fail: bool = False):
        super().__init__(ProviderName.OPENAI, cost_per_1k_input=0.005, cost_per_1k_output=0.015)
        self.should_fail = should_fail
        self.call_count = 0

    async def complete(
        self,
        messages: list[GatewayMessage],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> GatewayResponse:
        self.call_count += 1
        t0 = time.perf_counter()
        await asyncio.sleep(0.01)  # Simulate network hop

        if self.should_fail:
            raise RateLimitExceededException(self.name)

        # Normalize temperature: OpenAI supports [0.0, 2.0]
        clamped_temp = max(0.0, min(temperature, 2.0))
        prompt_text = " ".join(m.content for m in messages)
        p_tokens = len(prompt_text.split()) * 2
        c_tokens = 35

        latency = (time.perf_counter() - t0) * 1000.0
        return GatewayResponse(
            content=f"[OpenAI gpt-4o response at temp {clamped_temp:.1f}]: Answer to '{messages[-1].content}'",
            provider=self.name,
            model_name="gpt-4o",
            prompt_tokens=p_tokens,
            completion_tokens=c_tokens,
            total_tokens=p_tokens + c_tokens,
            cost_usd=self.calculate_cost(p_tokens, c_tokens),
            latency_ms=round(latency, 2),
        )


class MockAnthropicProvider(ModelProvider):
    def __init__(self, should_fail: bool = False):
        super().__init__(ProviderName.ANTHROPIC, cost_per_1k_input=0.003, cost_per_1k_output=0.015)
        self.should_fail = should_fail
        self.call_count = 0

    async def complete(
        self,
        messages: list[GatewayMessage],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> GatewayResponse:
        self.call_count += 1
        t0 = time.perf_counter()
        await asyncio.sleep(0.01)

        if self.should_fail:
            raise ProviderException(self.name, "Service Unavailable (HTTP 503)", 503)

        # Gotcha fix: Anthropic temperature is strictly in [0.0, 1.0]
        clamped_temp = max(0.0, min(temperature, 1.0))
        prompt_text = " ".join(m.content for m in messages)
        p_tokens = int(len(prompt_text.split()) * 1.8)
        c_tokens = 40

        latency = (time.perf_counter() - t0) * 1000.0
        return GatewayResponse(
            content=f"[Anthropic Claude 3.5 Sonnet at temp {clamped_temp:.1f}]: Answer to '{messages[-1].content}'",
            provider=self.name,
            model_name="claude-3-5-sonnet",
            prompt_tokens=p_tokens,
            completion_tokens=c_tokens,
            total_tokens=p_tokens + c_tokens,
            cost_usd=self.calculate_cost(p_tokens, c_tokens),
            latency_ms=round(latency, 2),
        )


class MockGeminiProvider(ModelProvider):
    def __init__(self):
        super().__init__(ProviderName.GEMINI, cost_per_1k_input=0.00125, cost_per_1k_output=0.005)
        self.call_count = 0

    async def complete(
        self,
        messages: list[GatewayMessage],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> GatewayResponse:
        self.call_count += 1
        t0 = time.perf_counter()
        await asyncio.sleep(0.01)

        p_tokens = len(" ".join(m.content for m in messages).split()) * 2
        c_tokens = 45
        latency = (time.perf_counter() - t0) * 1000.0

        return GatewayResponse(
            content=f"[Google Gemini 1.5 Pro]: Answer to '{messages[-1].content}'",
            provider=self.name,
            model_name="gemini-1.5-pro",
            prompt_tokens=p_tokens,
            completion_tokens=c_tokens,
            total_tokens=p_tokens + c_tokens,
            cost_usd=self.calculate_cost(p_tokens, c_tokens),
            latency_ms=round(latency, 2),
        )


# ── The Model Gateway Orchestrator ───────────────────────────────────────────

class ModelGateway:
    """
    Enterprise LLM Router with:
    1. Primary-to-Secondary Fallback Chain
    2. Cost and Token Metrics Aggregation
    3. Circuit breaker awareness
    """

    def __init__(self, fallback_chain: list[ModelProvider]):
        if not fallback_chain:
            raise ValueError("Fallback chain must have at least one provider.")
        self.fallback_chain = fallback_chain
        self.total_spend_usd = 0.0
        self.total_tokens_consumed = 0
        self.failed_provider_attempts: dict[str, int] = {}

    async def execute_with_fallback(
        self,
        messages: list[GatewayMessage],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> GatewayResponse:
        """Executes completion with automated fallback along the chain."""
        errors: list[str] = []

        for provider in self.fallback_chain:
            try:
                resp = await provider.complete(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                # On success: accumulate metrics
                self.total_spend_usd += resp.cost_usd
                self.total_tokens_consumed += resp.total_tokens
                return resp
            except ProviderException as ex:
                provider_key = provider.name.value
                self.failed_provider_attempts[provider_key] = (
                    self.failed_provider_attempts.get(provider_key, 0) + 1
                )
                errors.append(str(ex))
                print(f"  [GATEWAY WARNING] Provider {provider_key} failed ({ex}). Falling back...")
                continue

        raise RuntimeError(f"All providers in fallback chain failed! Details: {errors}")


# ── Demonstration Functions ──────────────────────────────────────────────────

async def demonstrate_gateway_happy_path():
    """Demonstrates successful call using primary provider."""
    print("  --- Demonstration 1: Gateway Normal Flow ---")
    p1 = MockOpenAIProvider(should_fail=False)
    p2 = MockAnthropicProvider(should_fail=False)
    gateway = ModelGateway(fallback_chain=[p1, p2])

    msgs = [
        GatewayMessage(role="system", content="You are a senior enterprise architect."),
        GatewayMessage(role="user", content="Design a resilient LLM gateway."),
    ]
    resp = await gateway.execute_with_fallback(msgs, temperature=0.7)
    print(f"    Resolved by Provider: {resp.provider.value} (Model: {resp.model_name})")
    print(f"    Content: {resp.content}")
    print(f"    Tokens: {resp.total_tokens} | Cost: ${resp.cost_usd:.6f} | Latency: {resp.latency_ms}ms")
    return resp


async def demonstrate_gateway_automatic_failover():
    """Demonstrates failover when primary throws 429."""
    print("\n  --- Demonstration 2: Gateway Automatic Failover ---")
    p1 = MockOpenAIProvider(should_fail=True)      # Simulating 429
    p2 = MockAnthropicProvider(should_fail=False)  # Resilient fallback
    p3 = MockGeminiProvider()
    gateway = ModelGateway(fallback_chain=[p1, p2, p3])

    msgs = [GatewayMessage(role="user", content="Summarize quarterly system uptime.")]
    resp = await gateway.execute_with_fallback(msgs)

    print(f"    Fallback Success: Handled by {resp.provider.value} ({resp.model_name})")
    print(f"    OpenAI call count: {p1.call_count} (Failed)")
    print(f"    Anthropic call count: {p2.call_count} (Recovered)")
    print(f"    Total Gateway Spend: ${gateway.total_spend_usd:.6f}")
    return resp


# ══════════════════════════════════════════════════════════════════════
# SELF-TEST CHALLENGES
# ══════════════════════════════════════════════════════════════════════

def run_tests():
    """Automated verification for Phase 11 File 1."""
    print("\n[*] Running automated self-tests...")

    async def _test_runner():
        # Test 1: Provider cost calculation
        p_ai = MockOpenAIProvider()
        cost = p_ai.calculate_cost(prompt_tokens=1000, completion_tokens=1000)
        assert abs(cost - 0.020) < 1e-5, f"Cost expected 0.020, got {cost}"

        # Test 2: Primary provider success
        p_ant = MockAnthropicProvider()
        gateway = ModelGateway([p_ai, p_ant])
        msgs = [GatewayMessage("user", "Hello")]
        resp = await gateway.execute_with_fallback(msgs)
        assert resp.provider == ProviderName.OPENAI
        assert p_ai.call_count == 1
        assert p_ant.call_count == 0

        # Test 3: Failover trigger on 429
        p_ai_fail = MockOpenAIProvider(should_fail=True)
        p_ant_ok = MockAnthropicProvider(should_fail=False)
        gw_fallback = ModelGateway([p_ai_fail, p_ant_ok])
        resp2 = await gw_fallback.execute_with_fallback(msgs)
        assert resp2.provider == ProviderName.ANTHROPIC
        assert p_ai_fail.call_count == 1
        assert p_ant_ok.call_count == 1
        assert gw_fallback.failed_provider_attempts["openai"] == 1

        # Test 4: All providers fail raises RuntimeError
        p_ant_fail = MockAnthropicProvider(should_fail=True)
        gw_all_fail = ModelGateway([p_ai_fail, p_ant_fail])
        caught = False
        try:
            await gw_all_fail.execute_with_fallback(msgs)
        except RuntimeError:
            caught = True
        assert caught, "Should raise RuntimeError when all fail"

        # Test 5: Metrics accumulation
        assert gw_fallback.total_tokens_consumed > 0
        assert gw_fallback.total_spend_usd > 0.0

        # Test 6: Temperature clamping
        resp_clamp = await p_ant_ok.complete(msgs, temperature=1.8)
        assert "temp 1.0" in resp_clamp.content, "Anthropic temperature should clamp to 1.0"

        # Test 7: Empty fallback chain validation
        init_failed = False
        try:
            ModelGateway([])
        except ValueError:
            init_failed = True
        assert init_failed, "Should reject empty fallback chain"

        # Test 8: Gemini provider resolution
        gemini = MockGeminiProvider()
        gw_gemini = ModelGateway([gemini])
        resp_gemini = await gw_gemini.execute_with_fallback(msgs)
        assert resp_gemini.provider == ProviderName.GEMINI
        assert "Gemini" in resp_gemini.content

        # Test 9: Gateway message immutability
        gm = GatewayMessage(role="user", content="Immutable test")
        attr_failed = False
        try:
            gm.content = "Changed"  # type: ignore
        except (AttributeError, TypeError):
            attr_failed = True
        assert attr_failed, "GatewayMessage should be frozen/immutable"

        # Test 10: Latency tracking
        assert resp2.latency_ms > 0, "Latency should be measured"

    asyncio.run(_test_runner())
    print("[SUCCESS] All 10 Model Gateway self-tests passed!")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 11: Model Gateway & Provider Abstraction")
    print("=" * 70)
    asyncio.run(demonstrate_gateway_happy_path())
    asyncio.run(demonstrate_gateway_automatic_failover())
    print("-" * 70)
    run_tests()
    print("=" * 70)
