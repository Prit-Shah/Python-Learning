"""
Project P7: Multi-Provider LLM Gateway with Resilient Fallback Chain
"""
import asyncio
import time
from dataclasses import dataclass
from typing import AsyncIterator


@dataclass
class CompletionResult:
    content: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    latency_ms: float


class ModelGateway:
    """Manages multi-provider routing, failover, and token accounting."""

    def __init__(self):
        self.total_cost_usd = 0.0
        self.total_tokens = 0
        self.calls_by_provider = {"openai": 0, "anthropic": 0}

    async def complete(self, prompt: str, force_fail_primary: bool = False) -> CompletionResult:
        t0 = time.perf_counter()

        # Attempt primary provider (OpenAI)
        if not force_fail_primary:
            await asyncio.sleep(0.01)
            self.calls_by_provider["openai"] += 1
            cost = 0.0015
            tokens = 45
            self.total_cost_usd += cost
            self.total_tokens += tokens
            latency = (time.perf_counter() - t0) * 1000.0
            return CompletionResult(
                content=f"[OpenAI GPT-4o]: Responding to '{prompt}'",
                provider="openai",
                model="gpt-4o",
                prompt_tokens=25,
                completion_tokens=20,
                total_tokens=tokens,
                cost_usd=cost,
                latency_ms=round(latency, 2),
            )

        # Fallback to secondary provider (Anthropic)
        await asyncio.sleep(0.015)
        self.calls_by_provider["anthropic"] += 1
        cost = 0.0012
        tokens = 48
        self.total_cost_usd += cost
        self.total_tokens += tokens
        latency = (time.perf_counter() - t0) * 1000.0
        return CompletionResult(
            content=f"[Anthropic Claude 3.5 Sonnet]: Recovered response to '{prompt}'",
            provider="anthropic",
            model="claude-3-5-sonnet",
            prompt_tokens=28,
            completion_tokens=20,
            total_tokens=tokens,
            cost_usd=cost,
            latency_ms=round(latency, 2),
        )

    async def stream_tokens(self, text: str) -> AsyncIterator[str]:
        words = text.split()
        for w in words:
            await asyncio.sleep(0.01)
            yield w + " "


gateway = ModelGateway()
