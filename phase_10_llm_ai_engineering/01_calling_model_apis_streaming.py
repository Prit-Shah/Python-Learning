r"""
01_calling_model_apis_streaming.py

============================================================
1. CONCEPT
============================================================

Large Language Model (LLM) APIs (OpenAI, Anthropic, Google Gemini, Groq, Mistral)
form the inference foundation of modern AI engineering. Integrating these models into
production Python backends requires understanding inference parameters, tokenization,
Server-Sent Events (SSE) streaming, and resilient retry architectures:

1. Unified LLM Request Structure:
   - Messages Envelope: Ordered sequence of dictionaries containing `role` and `content`:
     * `system`: Guides persona, instructions, tone, and guardrails.
     * `user`: The end-user prompt or operational instruction.
     * `assistant`: Prior model responses (used for multi-turn context).
     * `tool`: Output from executed functions or API calls.
   - Inference Hyperparameters:
     * `temperature`: Softmax logit divisor ($T \in [0.0, 2.0]$). $T = 0.0$ generates
       deterministic greedy outputs; $T \ge 0.7$ increases diversity.
     * `top_p` (Nucleus Sampling): Limits candidate tokens to the smallest cumulative
       probability mass exceeding $P$ ($P \in [0.0, 1.0]$).
     * `max_tokens`: Enforces hard truncation on generated output tokens.
     * `stop`: Sequence or list of sequences that immediately halt model generation.

2. Streaming Token Generation via Server-Sent Events (SSE):
   - Rather than waiting 5-15 seconds for a model to generate hundreds of tokens,
     streaming delivers tokens incrementally as they are sampled from the transformer.
   - Uses HTTP chunked transfer encoding (`Content-Type: text/event-stream`).
   - Drastically reduces Time-To-First-Token (TTFT) from seconds to milliseconds.

3. Context Windows & Token Economics:
   - Models operate on subword tokens derived via Byte-Pair Encoding (BPE).
     1 token $\approx$ 4 English characters or 0.75 words.
   - Total Context Window = $\text{Input Tokens} + \text{Output Tokens}$. Exceeding the window
     causes immediate API rejection (e.g. `context_length_exceeded`).

4. Resilient Multi-Tier Retry Patterns:
   - LLM APIs are subject to transient network failures, provider outages (HTTP 500/503),
     and strict TPM (tokens-per-minute) / RPM (requests-per-minute) rate limits (HTTP 429).
   - Production systems require exponential backoff with full jitter:
     $t_{\text{wait}} = \text{random}(0, \min(M, B \cdot 2^{\text{attempt}}))$.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python (OpenAI SDK / httpx)        | JavaScript / TypeScript (Node.js)  |
+------------------------------+------------------------------------+------------------------------------+
| Async Client                 | `client = AsyncOpenAI()`           | `const client = new OpenAI()`      |
| Async Streaming              | `async for chunk in response:`     | `for await (const chunk of stream)`|
| Event Stream Transport       | Generator yielding typed objects   | `ReadableStream` / EventSource     |
| Tokenizer                    | `tiktoken` (official Rust/C binding)| `gpt-tokenizer` / `@dqbd/tiktoken`|
| Backoff & Retries            | `tenacity` decorator / SDK retries | `p-retry` / SDK built-in retries   |
| Streaming API Response       | Starlette `StreamingResponse`      | Express `res.write()` / Next.js SSE|
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Architecture Differences:
1. In Node.js, `new OpenAI()` is inherently asynchronous and returns Promises. In Python,
   the `openai` package provides two distinct clients: synchronous `OpenAI()` (blocks OS thread)
   and asynchronous `AsyncOpenAI()` (runs on the `asyncio` event loop). In FastAPI, always use
   `AsyncOpenAI` to avoid freezing the event loop.
2. In TypeScript, streaming involves piping web streams (`ReadableStream`). In Python, the SDK
   exposes an async generator yielding strongly-typed Pydantic model deltas (`chunk.choices[0].delta.content`),
   which integrates cleanly with FastAPI's `StreamingResponse`.


============================================================
3. UNDER THE HOOD (Tokenization & Sampling Mathematics)
============================================================

1. Byte-Pair Encoding (BPE) Tokenization:
   - LLMs do not see characters, words, or strings; they process sequences of integer token IDs.
   - BPE starts with individual bytes and iteratively merges the most frequent pairs into single
     tokens (e.g., `'Ġlearning'` is a single token).
   - In Python, `tiktoken` executes compiled Rust algorithms capable of tokenizing 1 million tokens/sec.

2. Softmax Temperature & Nucleus Sampling Mathematics:
   - Given un-normalized model logits $z_i$ over vocabulary $V$:
     $$P(w_i) = \frac{\exp(z_i / T)}{\sum_{j \in V} \exp(z_j / T)}$$
   - As $T \to 0$, probabilities for the highest logit approach 1.0 (greedy decoding).
   - In Top-P sampling, tokens are sorted descending by probability. The model keeps only the
     top tokens whose cumulative sum satisfies $\sum_{i=1}^k P(w_i) \ge P$, dynamically truncating
     the tail of improbable tokens.

3. Memory Mechanics of Streaming vs Buffering:
   - Non-Streaming: The entire response is buffered in memory by the server, serialized to JSON,
     and transmitted in a single HTTP payload. Memory consumption scales with response length.
   - Streaming: The server emits SSE chunks (`data: {"choices":[{"delta":{"content":"..."}}]}\n\n`).
     The client process retains $O(1)$ memory per chunk, streaming tokens directly to downstream
     sockets or UI interfaces.


============================================================
4. COMMON GOTCHAS
============================================================

1. Modifying Both Temperature AND Top-P Simultaneously:
   - Setting both high leads to chaotic distributions; setting both low creates unnatural repetition.
   - Standard Best Practice: Alter `temperature` OR `top_p`, keeping the other at default (1.0).

2. Hardcoding Context Without Truncation:
   - Storing all user and assistant turns in an unbounded list guarantees that long conversations
     will eventually exceed the model's context window (e.g. 128k tokens).
   - FIX: Implement a sliding context window or summarization strategy that prunes older turns
     while preserving the system prompt.

3. Blocking the Event Loop with Synchronous SDK Calls:
   - Calling synchronous `client.chat.completions.create(...)` inside an async FastAPI handler
     blocks the entire worker process, preventing concurrent request handling.
   - FIX: Use `await async_client.chat.completions.create(...)`.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "Explain how you implement token streaming from an LLM API to a frontend client in FastAPI."
A1: "I instantiate an `AsyncOpenAI` client and invoke `await client.chat.completions.create(..., stream=True)`.
     This returns an asynchronous generator yielding `ChatCompletionChunk` objects.
     I wrap this in an async generator function that formats each token chunk into the standard SSE
     wire protocol: `f'data: {json.dumps({\"token\": content})}\\n\\n'`.
     In FastAPI, I return a `StreamingResponse` with media type `text/event-stream`. This sets HTTP
     headers `Transfer-Encoding: chunked` and `Cache-Control: no-cache`, allowing the frontend client
     to consume tokens via `EventSource` or `fetch()` with reader streams, drastically reducing Time-To-First-Token."

Q2: "What is the difference between Temperature and Top-P (nucleus sampling)?"
A2: "Temperature modifies the sharpness of the probability distribution across vocabulary logits before
     sampling. High temperatures flatten the distribution, making less likely tokens more probable and
     increasing creativity; low temperatures sharpen the distribution toward the top token, approaching
     deterministic output at temperature 0.
     Top-P (nucleus sampling) does not alter the logits directly; instead, it dynamically cuts off the
     tail of the distribution by keeping only the smallest set of top tokens whose cumulative probability
     equals P (e.g., 0.9). This prevents the model from ever selecting bizarre, low-probability tokens
     regardless of temperature."

Q3: "How do you handle rate limits and API failures when communicating with LLM providers?"
A3: "I implement exponential backoff with full jitter and retries for transient errors like HTTP 429
     (rate limits) and 500/503 (server overloads). I calculate sleep intervals using `random.uniform(0, min(max_backoff, base * 2**attempt))`.
     For rate limits specifically, I parse the `Retry-After` header if provided by the vendor.
     In high-availability enterprise systems, I also implement model fallback routing: if primary requests
     to OpenAI GPT-4o fail after two retries, the service automatically fails over to an alternative provider
     like Anthropic Claude 3.5 Sonnet or a self-hosted open-weights model on vLLM."
"""

import sys
import time
import random
import json
import warnings
warnings.filterwarnings("ignore")
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, Generator, List, Optional

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ==============================================================================
# 1. DOMAIN MODELS & SCHEMAS
# ==============================================================================

@dataclass
class UsageMetadata:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class ChatDelta:
    content: Optional[str] = None
    role: Optional[str] = None


@dataclass
class StreamChoice:
    delta: ChatDelta
    index: int = 0
    finish_reason: Optional[str] = None


@dataclass
class ChatCompletionChunk:
    id: str
    choices: List[StreamChoice]
    created: int
    model: str


@dataclass
class ChatMessage:
    role: str
    content: str


# ==============================================================================
# 2. TOKEN ESTIMATOR & CONTEXT SLICER
# ==============================================================================

class TokenEstimator:
    """Estimates subword token counts using BPE heuristic rules (~4 chars/token)."""

    @staticmethod
    def estimate_tokens(text: str) -> int:
        if not text:
            return 0
        # Heuristic: 1 token ~= 4 characters for English text + punctuation
        return max(1, len(text) // 4)

    @staticmethod
    def calculate_messages_tokens(messages: List[Dict[str, str]]) -> int:
        total = 0
        for msg in messages:
            # Add message framing overhead (~3 tokens for role/formatting)
            total += 3 + TokenEstimator.estimate_tokens(msg.get("content", ""))
        return total + 3  # Add reply primer overhead


class ConversationManager:
    """Manages multi-turn conversation history within hard token budgets."""

    def __init__(self, system_prompt: str, max_context_tokens: int = 4000):
        self.system_prompt = system_prompt
        self.max_context_tokens = max_context_tokens
        self.history: List[Dict[str, str]] = []

    def add_user_message(self, content: str) -> None:
        self.history.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str) -> None:
        self.history.append({"role": "assistant", "content": content})

    def get_pruned_messages(self) -> List[Dict[str, str]]:
        """
        Returns message list guaranteed to fit within max_context_tokens.
        Preserves the system prompt, pruning oldest user/assistant turns if needed.
        """
        system_msg = {"role": "system", "content": self.system_prompt}
        sys_tokens = TokenEstimator.calculate_messages_tokens([system_msg])

        available_budget = self.max_context_tokens - sys_tokens
        if available_budget <= 0:
            return [system_msg]

        pruned_turns: List[Dict[str, str]] = []
        current_tokens = 0

        # Traverse history from newest to oldest
        for msg in reversed(self.history):
            msg_tokens = TokenEstimator.calculate_messages_tokens([msg])
            if current_tokens + msg_tokens <= available_budget:
                pruned_turns.insert(0, msg)
                current_tokens += msg_tokens
            else:
                break  # Context limit reached, drop older turns

        return [system_msg] + pruned_turns


# ==============================================================================
# 3. PRODUCTION MOCK LLM CLIENT (WITH RETRIES & STREAMING)
# ==============================================================================

class MockLLMProvider:
    """
    Simulates production LLM APIs (OpenAI / Anthropic):
    - Validates parameters (temperature, top_p)
    - Generates chunked SSE streams
    - Implements exponential backoff with jitter on simulated 429 errors
    """

    def __init__(self, simulate_flakiness: bool = False):
        self.simulate_flakiness = simulate_flakiness
        self.call_count = 0

    def chat_complete(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        top_p: float = 1.0,
        max_tokens: int = 500,
        stream: bool = False
    ) -> Any:
        if not (0.0 <= temperature <= 2.0):
            raise ValueError(f"Invalid temperature {temperature}. Must be in [0.0, 2.0].")
        if not (0.0 <= top_p <= 1.0):
            raise ValueError(f"Invalid top_p {top_p}. Must be in [0.0, 1.0].")

        self.call_count += 1

        # Simulate transient rate limit failure on first attempt if flakiness enabled
        if self.simulate_flakiness and self.call_count == 1:
            raise ConnectionError("HTTP 429: Rate limit exceeded (TPM quota reached).")

        # Mock generated response based on last message
        last_user_content = messages[-1]["content"] if messages else ""
        synthetic_response = f"AI Analysis of: '{last_user_content}' [Model: {model}]"

        prompt_tokens = TokenEstimator.calculate_messages_tokens(messages)
        comp_tokens = TokenEstimator.estimate_tokens(synthetic_response)

        if not stream:
            return {
                "id": f"chatcmpl-{int(time.time())}",
                "model": model,
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": synthetic_response},
                    "finish_reason": "stop"
                }],
                "usage": UsageMetadata(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=comp_tokens,
                    total_tokens=prompt_tokens + comp_tokens
                )
            }
        else:
            return self._generate_stream_chunks(model, synthetic_response)

    def _generate_stream_chunks(self, model: str, response_text: str) -> Generator[ChatCompletionChunk, None, None]:
        req_id = f"chatcmpl-stream-{int(time.time())}"
        words = response_text.split(" ")

        # 1. Initial role chunk
        yield ChatCompletionChunk(
            id=req_id,
            choices=[StreamChoice(delta=ChatDelta(role="assistant"))],
            created=int(time.time()),
            model=model
        )

        # 2. Token content chunks
        for idx, word in enumerate(words):
            token_text = word + (" " if idx < len(words) - 1 else "")
            yield ChatCompletionChunk(
                id=req_id,
                choices=[StreamChoice(delta=ChatDelta(content=token_text))],
                created=int(time.time()),
                model=model
            )

        # 3. Final stop chunk
        yield ChatCompletionChunk(
            id=req_id,
            choices=[StreamChoice(delta=ChatDelta(), finish_reason="stop")],
            created=int(time.time()),
            model=model
        )


def execute_with_exponential_backoff(
    provider_fn: Any,
    max_retries: int = 3,
    base_delay: float = 0.05
) -> Any:
    """Executes provider call with exponential backoff and jitter."""
    attempt = 0
    while True:
        try:
            return provider_fn()
        except ConnectionError as err:
            attempt += 1
            if attempt > max_retries:
                raise err
            # Exponential backoff with jitter
            backoff = base_delay * (2 ** attempt)
            jitter = random.uniform(0.01, 0.05)
            time.sleep(backoff + jitter)


# ==============================================================================
# 4. SELF-TESTING SUITE
# ==============================================================================

def run_tests() -> None:
    print("\n[*] Starting automated test suite for 01_calling_model_apis_streaming.py...")

    # ------------------------------------------------------------
    # Test 1: Token Counting & BPE Estimation
    # ------------------------------------------------------------
    print("  -> Testing subword token counting heuristics...")
    sample_text = "Machine learning architectures utilize transformer attention mechanisms."
    tokens = TokenEstimator.estimate_tokens(sample_text)
    assert tokens > 0
    assert tokens == len(sample_text) // 4

    messages = [
        {"role": "system", "content": "You are a senior AI engineer."},
        {"role": "user", "content": "Explain self-attention."}
    ]
    total_tokens = TokenEstimator.calculate_messages_tokens(messages)
    assert total_tokens > tokens, "Total message tokens must include role and framing overhead"

    # ------------------------------------------------------------
    # Test 2: Non-Streaming Completion & Usage Tracking
    # ------------------------------------------------------------
    print("  -> Testing non-streaming API completion and usage metadata...")
    provider = MockLLMProvider()
    resp = provider.chat_complete(
        model="gpt-4o",
        messages=messages,
        temperature=0.2,
        top_p=0.9,
        stream=False
    )
    assert resp["model"] == "gpt-4o"
    assert resp["choices"][0]["message"]["role"] == "assistant"
    assert "Explain self-attention" in resp["choices"][0]["message"]["content"]
    assert resp["choices"][0]["finish_reason"] == "stop"

    usage: UsageMetadata = resp["usage"]
    assert usage.prompt_tokens > 0
    assert usage.completion_tokens > 0
    assert usage.total_tokens == (usage.prompt_tokens + usage.completion_tokens)

    # ------------------------------------------------------------
    # Test 3: SSE Token Streaming & Delta Assembly
    # ------------------------------------------------------------
    print("  -> Testing SSE streaming generation and token delta reassembly...")
    stream_gen = provider.chat_complete(
        model="gpt-4o",
        messages=messages,
        stream=True
    )
    chunks = list(stream_gen)
    assert len(chunks) >= 3, "Stream must yield at least role, content, and stop chunks"

    # Verify first chunk sets role
    assert chunks[0].choices[0].delta.role == "assistant"

    # Assemble tokens
    collected_tokens = []
    for c in chunks:
        delta_text = c.choices[0].delta.content
        if delta_text:
            collected_tokens.append(delta_text)

    assembled_output = "".join(collected_tokens)
    assert "Explain self-attention" in assembled_output

    # Verify last chunk emits finish_reason="stop"
    assert chunks[-1].choices[0].finish_reason == "stop"

    # ------------------------------------------------------------
    # Test 4: Exponential Backoff & Rate Limit Resilience
    # ------------------------------------------------------------
    print("  -> Testing exponential backoff retry loop on HTTP 429...")
    flaky_provider = MockLLMProvider(simulate_flakiness=True)

    # Calling directly without retry would raise ConnectionError
    # Calling through execute_with_exponential_backoff retries and succeeds on attempt 2
    res_retry = execute_with_exponential_backoff(
        lambda: flaky_provider.chat_complete("claude-3-5-sonnet", messages),
        max_retries=2
    )
    assert flaky_provider.call_count == 2
    assert "claude-3-5-sonnet" in res_retry["choices"][0]["message"]["content"]

    # ------------------------------------------------------------
    # Test 5: Multi-Turn Conversation History & Pruning
    # ------------------------------------------------------------
    print("  -> Testing conversation history management and context window pruning...")
    conv = ConversationManager(
        system_prompt="You are a helpful coding assistant.",
        max_context_tokens=50  # Very tight budget to force pruning
    )

    conv.add_user_message("Old question 1: How does Python GC work?")
    conv.add_assistant_message("Old answer 1: Python uses reference counting and cyclic GC.")
    conv.add_user_message("New question 2: What is asyncio?")

    pruned = conv.get_pruned_messages()
    assert pruned[0]["role"] == "system"
    assert pruned[0]["content"] == "You are a helpful coding assistant."
    # The newest turn must be preserved
    assert pruned[-1]["content"] == "New question 2: What is asyncio?"
    # The oldest turns must have been pruned due to tight token budget
    assert len(pruned) < 4

    print("[SUCCESS] All 5 Calling LLM APIs & Streaming tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 10 - 01: Calling LLM APIs, SSE Streaming & Rate Limit Retries")
    print("=" * 70)
    run_tests()
    print("=" * 70)
