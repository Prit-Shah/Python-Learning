"""
Phase 10: Calling LLM APIs & Streaming Responses
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - Concept: LLM APIs (OpenAI, Anthropic, Gemini) follow a common pattern:
     you send messages (system + user + assistant), set parameters (temperature,
     max_tokens, top_p), and receive generated text. Streaming uses Server-Sent
     Events (SSE) to deliver tokens incrementally as they're generated.
   - JS/TS Equivalent: In Node.js you'd use `fetch()` or the official SDK:
     `openai.chat.completions.create({stream: true})` and iterate over chunks.
     Python SDKs follow the exact same pattern but use `for chunk in response:`
     instead of `for await (const chunk of response)`.
   - Key concepts: Tokens (subword units, ~4 chars), context window (input +
     output token limit), temperature (0 = deterministic, 1 = creative),
     top_p (nucleus sampling), stop sequences, system prompts.

2. UNDER THE HOOD (CPython & Memory):
   - SDK clients use httpx internally. Streaming responses use HTTP chunked
     transfer encoding — the server sends `data: {json}\n\n` lines (SSE format).
   - The Python SDK yields delta objects lazily from a generator. Each chunk
     is a small dict with `choices[0].delta.content`. Memory usage is O(1)
     per chunk, not O(total_response), which matters for long outputs.
   - Non-streaming: the entire response is buffered in memory before returning.
     For a 4096-token response at ~4 chars/token, that's ~16KB — trivial.
     Streaming matters for UX (time-to-first-token), not memory.

3. COMMON GOTCHA:
   - Forgetting to handle rate limits (429 errors). LLM APIs have strict
     rate limits (tokens/min, requests/min). You MUST implement exponential
     backoff. The SDKs have built-in retry, but you should understand it.
   - Confusing temperature with top_p: setting both high gives unpredictable
     results. Best practice: adjust one, leave the other at default.

4. INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   - Interview Question: "How do you integrate an LLM API into a production
     Python backend?"
   - How to Answer Out Loud (60-90 sec verbal script):
     * "I use the official SDK — for OpenAI it's the `openai` package with
       async support via `AsyncOpenAI`. I configure it with API keys from
       environment variables, never hardcoded."
     * "For the API call, I construct a messages array with system, user,
       and optionally assistant messages for multi-turn context. I set
       temperature based on the task — 0 for deterministic extraction,
       0.7 for creative generation."
     * "In production, I always use streaming for user-facing responses to
       reduce time-to-first-token. The stream yields delta chunks that I
       forward via SSE to the frontend. For background processing, I use
       non-streaming and parse the full response."
     * "Error handling includes retry with exponential backoff for 429/500
       errors, timeout configuration, and fallback to a secondary model
       if the primary is unavailable."
================================================================================
"""

import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass

import json
import time
import asyncio
from dataclasses import dataclass, field
from typing import AsyncIterator, Iterator
from enum import Enum


# ══════════════════════════════════════════════════════════════════════
# MOCK LLM CLIENT — Simulates the OpenAI/Anthropic SDK interface
# We mock the API to teach the PATTERNS without requiring API keys.
# The real SDK call is nearly identical to our mock interface.
# ══════════════════════════════════════════════════════════════════════

class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    """Mirrors openai.types.chat.ChatCompletionMessage."""
    role: str
    content: str


@dataclass
class Choice:
    index: int
    message: Message
    finish_reason: str = "stop"


@dataclass
class Usage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class ChatCompletion:
    """Mirrors openai.types.chat.ChatCompletion."""
    id: str
    model: str
    choices: list[Choice]
    usage: Usage


@dataclass
class DeltaContent:
    content: str = ""


@dataclass
class StreamChoice:
    index: int
    delta: DeltaContent
    finish_reason: str | None = None


@dataclass
class ChatCompletionChunk:
    """Mirrors openai.types.chat.ChatCompletionChunk."""
    id: str
    model: str
    choices: list[StreamChoice]


class MockLLMClient:
    """
    Simulates the OpenAI Python SDK interface.

    REAL CODE (with actual openai package):
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Hello!"}],
            temperature=0.7,
        )
        print(response.choices[0].message.content)
    """

    def __init__(self, model: str = "mock-gpt-4o", api_key: str = "mock-key"):
        self.model = model
        self.api_key = api_key
        self._request_count = 0

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation: ~4 chars per token (GPT tokenizer average)."""
        return max(1, len(text) // 4)

    def _generate_response(self, messages: list[dict], temperature: float) -> str:
        """Simulates LLM response generation."""
        last_msg = messages[-1]["content"] if messages else ""
        system_msg = next(
            (m["content"] for m in messages if m["role"] == "system"), ""
        )

        # Simple mock responses based on input
        if "hello" in last_msg.lower():
            return "Hello! I'm a mock LLM. How can I help you today?"
        elif "explain" in last_msg.lower():
            return ("Sure! Let me explain. LLMs work by predicting the next "
                    "token in a sequence. They use transformer architecture "
                    "with attention mechanisms to weigh the relevance of each "
                    "input token when generating output.")
        elif "json" in last_msg.lower():
            return json.dumps({"answer": "Mock structured response", "confidence": 0.95})
        else:
            return f"Mock response to: {last_msg[:50]}..."

    def create(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        top_p: float = 1.0,
        stop: list[str] | None = None,
        stream: bool = False,
    ) -> ChatCompletion | Iterator[ChatCompletionChunk]:
        """
        Mirrors: client.chat.completions.create(...)

        Parameters explained:
        - messages: List of {role, content} dicts. Roles: system, user, assistant.
        - temperature: 0.0 = deterministic, 1.0 = creative. Controls randomness.
        - max_tokens: Maximum tokens in the response.
        - top_p: Nucleus sampling. 0.1 = only top 10% probability mass.
        - stop: Sequences that halt generation (e.g., ["\n\n"]).
        - stream: If True, yields chunks incrementally (SSE-like).
        """
        self._request_count += 1
        used_model = model or self.model
        response_text = self._generate_response(messages, temperature)

        if stream:
            return self._stream_response(response_text, used_model)
        else:
            return self._non_stream_response(response_text, messages, used_model)

    def _non_stream_response(
        self, text: str, messages: list[dict], model: str
    ) -> ChatCompletion:
        prompt_text = " ".join(m["content"] for m in messages)
        return ChatCompletion(
            id=f"chatcmpl-mock-{self._request_count}",
            model=model,
            choices=[
                Choice(
                    index=0,
                    message=Message(role="assistant", content=text),
                    finish_reason="stop",
                )
            ],
            usage=Usage(
                prompt_tokens=self._estimate_tokens(prompt_text),
                completion_tokens=self._estimate_tokens(text),
                total_tokens=self._estimate_tokens(prompt_text) + self._estimate_tokens(text),
            ),
        )

    def _stream_response(
        self, text: str, model: str
    ) -> Iterator[ChatCompletionChunk]:
        """Yields chunks word-by-word, simulating SSE streaming."""
        words = text.split(" ")
        for i, word in enumerate(words):
            content = word + (" " if i < len(words) - 1 else "")
            yield ChatCompletionChunk(
                id=f"chatcmpl-mock-{self._request_count}",
                model=model,
                choices=[
                    StreamChoice(
                        index=0,
                        delta=DeltaContent(content=content),
                        finish_reason=None if i < len(words) - 1 else "stop",
                    )
                ],
            )


# ── Demonstration Functions ──────────────────────────────────────────────

def demonstrate_basic_api_call():
    """Non-streaming completion — the simplest LLM call."""
    client = MockLLMClient(model="mock-gpt-4o")

    # The messages array — core of every LLM API call
    messages = [
        {"role": "system", "content": "You are a helpful coding assistant."},
        {"role": "user", "content": "Hello, can you help me with Python?"},
    ]

    response = client.create(
        messages=messages,
        temperature=0.7,   # Moderate creativity
        max_tokens=256,     # Limit response length
    )

    print(f"  Model: {response.model}")
    print(f"  Response: {response.choices[0].message.content}")
    print(f"  Finish reason: {response.choices[0].finish_reason}")
    print(f"  Usage: {response.usage.prompt_tokens} prompt + "
          f"{response.usage.completion_tokens} completion = "
          f"{response.usage.total_tokens} total tokens")

    return response


def demonstrate_streaming():
    """Streaming completion — token-by-token delivery for UX."""
    client = MockLLMClient()

    messages = [
        {"role": "user", "content": "Explain how LLMs work briefly."},
    ]

    print("  Streaming response: ", end="", flush=True)
    full_response = []

    # REAL CODE: for chunk in client.chat.completions.create(..., stream=True):
    stream = client.create(messages=messages, stream=True)
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            print(delta, end="", flush=True)
            full_response.append(delta)

    print()  # newline
    assembled = "".join(full_response)
    print(f"  Full assembled response length: {len(assembled)} chars")

    return assembled


def demonstrate_multi_turn_conversation():
    """Multi-turn context — maintaining conversation history."""
    client = MockLLMClient()

    # Conversation history — the client manages this, not the API
    conversation: list[dict] = [
        {"role": "system", "content": "You are a Python tutor."},
    ]

    # Turn 1
    conversation.append({"role": "user", "content": "Hello!"})
    response1 = client.create(messages=conversation)
    assistant_msg1 = response1.choices[0].message.content
    conversation.append({"role": "assistant", "content": assistant_msg1})
    print(f"  Turn 1 - User: Hello!")
    print(f"  Turn 1 - Assistant: {assistant_msg1}")

    # Turn 2 — includes full history for context
    conversation.append({"role": "user", "content": "Explain decorators."})
    response2 = client.create(messages=conversation)
    assistant_msg2 = response2.choices[0].message.content
    conversation.append({"role": "assistant", "content": assistant_msg2})
    print(f"  Turn 2 - User: Explain decorators.")
    print(f"  Turn 2 - Assistant: {assistant_msg2}")

    # The conversation list now has 5 messages (system + 2 turns)
    print(f"  Conversation length: {len(conversation)} messages")
    # In production, you'd trim old messages when approaching context window limit

    return conversation


def demonstrate_temperature_and_parameters():
    """Understanding temperature, top_p, and generation parameters."""
    client = MockLLMClient()

    print("  === Temperature Effects ===")
    print("  temperature=0.0 : Deterministic, always same output. Use for:")
    print("    - Data extraction, classification, code generation")
    print("  temperature=0.3 : Low creativity. Use for:")
    print("    - Summarization, factual Q&A")
    print("  temperature=0.7 : Moderate creativity (DEFAULT). Use for:")
    print("    - General chat, content writing")
    print("  temperature=1.0 : High creativity. Use for:")
    print("    - Brainstorming, creative writing")
    print()
    print("  === top_p (Nucleus Sampling) ===")
    print("  top_p=0.1 : Only consider top 10% probability mass")
    print("  top_p=1.0 : Consider all tokens (DEFAULT)")
    print("  Rule: Adjust temperature OR top_p, not both")
    print()
    print("  === Token Estimation ===")
    samples = [
        "Hello world",
        "The quick brown fox jumps over the lazy dog",
        "def fibonacci(n): return n if n < 2 else fibonacci(n-1) + fibonacci(n-2)",
    ]
    for text in samples:
        estimated = client._estimate_tokens(text)
        print(f"    '{text[:40]}...' ~{estimated} tokens")


def demonstrate_error_handling_and_retry():
    """Production error handling with exponential backoff."""

    class RetryConfig:
        max_retries: int = 3
        base_delay: float = 1.0     # seconds
        max_delay: float = 60.0     # cap
        retry_on: tuple = (429, 500, 502, 503)

    def call_with_retry(client, messages, config=RetryConfig()):
        """
        Exponential backoff retry — production pattern for LLM APIs.

        REAL CODE would use the `tenacity` library:
            from tenacity import retry, wait_exponential, retry_if_exception_type
            @retry(wait=wait_exponential(min=1, max=60),
                   retry=retry_if_exception_type(openai.RateLimitError))
            def call_llm(messages): ...
        """
        last_error = None
        for attempt in range(config.max_retries + 1):
            try:
                response = client.create(messages=messages)
                return response
            except Exception as e:
                last_error = e
                if attempt < config.max_retries:
                    delay = min(
                        config.base_delay * (2 ** attempt),  # 1, 2, 4, 8...
                        config.max_delay,
                    )
                    print(f"    Attempt {attempt + 1} failed: {e}")
                    print(f"    Retrying in {delay:.1f}s...")
                    # time.sleep(delay)  # Would actually sleep in production
        raise last_error  # type: ignore

    client = MockLLMClient()
    messages = [{"role": "user", "content": "Hello"}]
    response = call_with_retry(client, messages)
    print(f"  Retry pattern succeeded: {response.choices[0].message.content}")

    # Key error types in real OpenAI SDK:
    print("\n  === Common API Errors ===")
    print("  - RateLimitError (429): Too many requests. Back off exponentially.")
    print("  - APITimeoutError: Request took too long. Increase timeout or retry.")
    print("  - AuthenticationError (401): Invalid API key.")
    print("  - BadRequestError (400): Invalid parameters (e.g., too many tokens).")
    print("  - InternalServerError (500): Provider issue. Retry or failover.")

    return response


def demonstrate_prompt_engineering():
    """Prompt design patterns for production."""
    client = MockLLMClient()

    # Pattern 1: System prompt as behavioral guardrails
    system_prompts = {
        "extractor": (
            "You are a data extraction assistant. "
            "Extract the requested fields from the text. "
            "Return ONLY valid JSON. No explanations."
        ),
        "classifier": (
            "You are a sentiment classifier. "
            "Classify the given text as: positive, negative, or neutral. "
            "Respond with a single word."
        ),
        "coder": (
            "You are a senior Python developer. "
            "Write clean, typed, PEP 8 code. "
            "Include docstrings and error handling. "
            "No explanations unless asked."
        ),
    }

    print("  === Prompt Design Patterns ===")
    for name, prompt in system_prompts.items():
        print(f"  [{name}] {prompt[:60]}...")

    # Pattern 2: Few-shot prompting
    few_shot_messages = [
        {"role": "system", "content": "Classify sentiment as positive/negative/neutral."},
        {"role": "user", "content": "This product is amazing!"},
        {"role": "assistant", "content": "positive"},
        {"role": "user", "content": "Terrible experience, waste of money."},
        {"role": "assistant", "content": "negative"},
        # Actual query:
        {"role": "user", "content": "The food was okay, nothing special."},
    ]
    print(f"\n  Few-shot example: {len(few_shot_messages)} messages")
    print(f"  (2 examples + 1 query = few-shot prompting)")

    # Pattern 3: Prompt injection defense
    print("\n  === Prompt Injection Defense ===")
    print("  - Never put user input directly in system prompt")
    print("  - Use delimiters: 'Analyze the text between <text></text> tags'")
    print("  - Validate/sanitize user input before inclusion")
    print("  - Use separate system instructions for guardrails")
    print("  - Consider output validation (does response match expected schema?)")

    return system_prompts


# ══════════════════════════════════════════════════════════════════════
# SELF-TEST CHALLENGES
# ══════════════════════════════════════════════════════════════════════

def run_tests():
    """Automated verification."""
    print("\n[*] Running automated self-tests...")

    client = MockLLMClient(model="test-model")

    # Test 1: Basic completion returns ChatCompletion
    messages = [{"role": "user", "content": "Hello"}]
    response = client.create(messages=messages)
    assert isinstance(response, ChatCompletion), "Should return ChatCompletion"
    assert response.model == "test-model", "Model should match"

    # Test 2: Response has correct structure
    assert len(response.choices) == 1, "Should have 1 choice"
    assert response.choices[0].message.role == "assistant", "Role should be assistant"
    assert len(response.choices[0].message.content) > 0, "Content should not be empty"
    assert response.choices[0].finish_reason == "stop", "Should finish with stop"

    # Test 3: Usage tracking
    assert response.usage.prompt_tokens > 0, "Should have prompt tokens"
    assert response.usage.completion_tokens > 0, "Should have completion tokens"
    assert response.usage.total_tokens == (
        response.usage.prompt_tokens + response.usage.completion_tokens
    ), "Total should be sum of prompt + completion"

    # Test 4: Streaming yields chunks
    stream = client.create(messages=messages, stream=True)
    chunks = list(stream)
    assert len(chunks) > 0, "Stream should yield chunks"
    assert all(isinstance(c, ChatCompletionChunk) for c in chunks), "All should be chunks"

    # Test 5: Streaming assembles to full response
    full_text = "".join(c.choices[0].delta.content for c in chunks if c.choices[0].delta.content)
    assert len(full_text) > 0, "Assembled stream should have content"

    # Test 6: Last chunk has finish_reason
    assert chunks[-1].choices[0].finish_reason == "stop", "Last chunk should be stop"

    # Test 7: System message affects nothing structurally
    messages_with_system = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello"},
    ]
    response2 = client.create(messages=messages_with_system)
    assert isinstance(response2, ChatCompletion), "Should work with system message"

    # Test 8: Token estimation
    assert client._estimate_tokens("Hello world") > 0, "Token estimation should be positive"
    assert client._estimate_tokens("A" * 100) == 25, "100 chars ~ 25 tokens"

    # Test 9: Multi-turn message list
    multi_turn = [
        {"role": "system", "content": "You are a tutor."},
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello!"},
        {"role": "user", "content": "Explain Python"},
    ]
    response3 = client.create(messages=multi_turn)
    assert isinstance(response3, ChatCompletion), "Multi-turn should work"

    # Test 10: Request counting
    count_before = client._request_count
    client.create(messages=[{"role": "user", "content": "test"}])
    assert client._request_count == count_before + 1, "Request counter should increment"

    print("[SUCCESS] All 10 LLM API self-tests passed!")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 10: Calling LLM APIs & Streaming Responses")
    print("=" * 70)
    print("\n--- Basic API Call ---")
    demonstrate_basic_api_call()
    print("\n--- Streaming ---")
    demonstrate_streaming()
    print("\n--- Multi-Turn Conversation ---")
    demonstrate_multi_turn_conversation()
    print("\n--- Temperature & Parameters ---")
    demonstrate_temperature_and_parameters()
    print("\n--- Error Handling & Retry ---")
    demonstrate_error_handling_and_retry()
    print("\n--- Prompt Engineering ---")
    demonstrate_prompt_engineering()
    print("-" * 70)
    run_tests()
    print("=" * 70)
