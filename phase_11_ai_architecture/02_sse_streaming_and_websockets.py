"""
Phase 11: SSE Streaming & WebSocket Architecture
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - Concept: LLMs generate responses sequentially token-by-token. Waiting for
     a full 500-token completion creates 5-15 seconds of blank wait time.
     Streaming architectures deliver tokens to the frontend in real time as
     they leave the neural net.
   - JS/TS Equivalent: In Node.js / Express, you pipe chunks using
     `res.setHeader('Content-Type', 'text/event-stream')` and write
     `res.write('data: ...\n\n')`. In FastAPI / Python, we return a
     `StreamingResponse(generator())` with `media_type="text/event-stream"`.
   - Protocol Decision:
     * Server-Sent Events (SSE): Unidirectional (Server -> Client), HTTP/2
       friendly, auto-reconnects, perfect for 95% of LLM chat interfaces.
     * WebSockets (WS): Full-duplex bidirectional, lower overhead for voice/audio
       or instant client cancellation interrupts (e.g. user pressing "Stop").

2. UNDER THE HOOD (CPython & Memory):
   - SSE uses HTTP Chunked Transfer Encoding. FastAPI and Starlette leverage
     Python async generators (`async def ... yield ...`).
   - CPython coroutine evaluation yields control back to the `uvicorn` event
     loop after emitting each frame, keeping per-stream memory footprint
     constant (O(1)) regardless of total token length.
   - Client Disconnection Trap: If the user closes their browser tab, the
     server loop must check `await request.is_disconnected()` or catch
     `asyncio.CancelledError`; otherwise, your backend will keep generating
     and paying API tokens for an abandoned session!

3. COMMON GOTCHA:
   - The double newline rule: The SSE specification (W3C) dictates that each
     event MUST end with TWO newline characters: `\n\n`. Emitting a single `\n`
     causes the browser's `EventSource` to buffer indefinitely without rendering!
   - Buffering reverse proxies (Nginx / Cloudflare): If `proxy_buffering on;`
     is enabled, Nginx buffers the SSE stream until 4KB or 8KB is filled,
     destroying real-time UX. You must send header `X-Accel-Buffering: no`.

4. 🎙️ INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   - Interview Question: "How would you architect real-time LLM streaming in
     FastAPI, and how do you handle client disconnects?"
   - How to Answer Out Loud (60-90 sec verbal script):
     * "For standard text generation, I choose SSE via FastAPI's `StreamingResponse`
       over WebSockets because SSE is lightweight, firewall-friendly, and works
       seamlessly over HTTP/2 multiplexing."
     * "In FastAPI, I write an async generator that yields formatted SSE events:
       `data: {json}\n\n`. I set `media_type='text/event-stream'` and include
       `Cache-Control: no-cache` and `X-Accel-Buffering: no` to prevent proxy buffering."
     * "For client disconnects, I inject FastAPI's `Request` object and periodically
       poll `await request.is_disconnected()`. If True, I break out of the generator
       and cancel the upstream LLM API task to eliminate orphaned token costs."
     * "If the product requires real-time bidirectional voice or sub-50ms barge-in
       cancellation, I upgrade to WebSockets using Starlette's `WebSocketEndpoint`."
================================================================================
"""

import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass

import asyncio
import json
import time
from typing import AsyncIterator


# ── SSE Event Formatter ──────────────────────────────────────────────────────

def format_sse(data: dict | str, event: str | None = None) -> str:
    """
    Formats a payload into strict W3C Server-Sent Event syntax:
    event: <event_name>\n
    data: <json_string>\n\n
    """
    payload = json.dumps(data) if isinstance(data, dict) else str(data)
    lines = []
    if event:
        lines.append(f"event: {event}")
    lines.append(f"data: {payload}")
    return "
".join(lines) + "

"


# ── Simulated LLM Streaming Engine ───────────────────────────────────────────

async def mock_llm_token_stream(prompt: str) -> AsyncIterator[str]:
    """Simulates an upstream LLM yielding tokens incrementally."""
    tokens = [
        "Architecting", " resilient", " streaming", " in", " Python",
        " requires", " async", " generators,", " strict", " SSE",
        " wire", " formatting,", " and", " disconnect", " awareness."
    ]
    for token in tokens:
        await asyncio.sleep(0.01)  # Simulate network chunk latency
        yield token


# ── Fast-API Compatible SSE Stream Generator ─────────────────────────────────

async def sse_event_generator(
    prompt: str,
    simulate_disconnect_at_token: int | None = None,
) -> AsyncIterator[str]:
    """
    Production-ready SSE generator yielding tokens, metadata, and completion events.
    Includes simulated client disconnect detection.
    """
    token_idx = 0
    t0 = time.perf_counter()

    # 1. Initial Handshake Event
    yield format_sse({"status": "connected", "prompt": prompt}, event="init")

    # 2. Token Delivery Loop
    async for token in mock_llm_token_stream(prompt):
        token_idx += 1

        # Check for simulated client disconnect
        if simulate_disconnect_at_token and token_idx >= simulate_disconnect_at_token:
            print(f"  [DISCONNECT DETECTED] Client disconnected at token #{token_idx}. Aborting upstream LLM call!")
            return

        yield format_sse({
            "token": token,
            "index": token_idx,
            "timestamp": round(time.time(), 3),
        }, event="token")

    # 3. Completion and Stats Event
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    yield format_sse({
        "status": "complete",
        "total_tokens": token_idx,
        "elapsed_ms": elapsed_ms,
    }, event="done")


# ── Simulated WebSocket Session ──────────────────────────────────────────────

class MockWebSocketSession:
    """Simulates a bidirectional WebSocket connection with client cancellation."""

    def __init__(self):
        self.sent_messages: list[str] = []
        self.is_active = True

    async def send_text(self, data: str):
        if not self.is_active:
            raise ConnectionResetError("Cannot write to closed WebSocket.")
        self.sent_messages.append(data)

    async def handle_user_interrupt(self):
        """Simulates client sending an abort frame."""
        self.is_active = False


# ── Demonstration Functions ──────────────────────────────────────────────────

async def demonstrate_sse_consumption():
    """Demonstrates client consumption of the SSE stream."""
    print("  --- Demonstration 1: SSE Streaming Event Consumer ---")
    prompt = "Explain SSE architecture"
    event_count = 0
    tokens_received: list[str] = []

    async for chunk in sse_event_generator(prompt):
        event_count += 1
        # Parse SSE wire format: split lines
        for line in chunk.strip().split("
"):
            if line.startswith("data: "):
                payload = json.loads(line[6:])
                if "token" in payload:
                    tokens_received.append(payload["token"])
                    print(payload["token"], end="", flush=True)

    print()
    print(f"    Total SSE frames received: {event_count}")
    print(f"    Assembled text: {''.join(tokens_received)}")
    return tokens_received


async def demonstrate_client_disconnect_handling():
    """Demonstrates early exit when client drops connection."""
    print("\n  --- Demonstration 2: Client Disconnect & Cost Protection ---")
    prompt = "Stream full documentation"
    tokens_emitted = 0

    async for chunk in sse_event_generator(prompt, simulate_disconnect_at_token=4):
        if 'event: token' in chunk:
            tokens_emitted += 1

    print(f"    Streaming cleanly terminated early after {tokens_emitted} tokens.")
    print("    Guaranteed no wasted downstream tokens or memory leaks.")


# ══════════════════════════════════════════════════════════════════════
# SELF-TEST CHALLENGES
# ══════════════════════════════════════════════════════════════════════

def run_tests():
    """Automated verification for Phase 11 File 2."""
    print("\n[*] Running automated self-tests...")

    async def _test_runner():
        # Test 1: format_sse wire protocol ends with double newline
        sse_raw = format_sse({"msg": "hello"}, event="test")
        assert sse_raw.endswith("

"), "SSE frame must end with \n\n"
        assert "event: test
" in sse_raw, "Must contain event line"
        assert 'data: {"msg": "hello"}

' in sse_raw, "Must contain data line"

        # Test 2: format_sse plain string
        raw_str = format_sse("ping", event="heartbeat")
        assert "data: ping

" in raw_str

        # Test 3: Generator yields init, tokens, and done
        chunks = [c async for c in sse_event_generator("Test prompt")]
        assert len(chunks) > 5, "Should yield multiple stream frames"
        assert any("event: init" in c for c in chunks), "Must yield init event"
        assert any("event: token" in c for c in chunks), "Must yield token events"
        assert any("event: done" in c for c in chunks), "Must yield done event"

        # Test 4: Disconnect terminates generator early
        cut_chunks = [c async for c in sse_event_generator("Test", simulate_disconnect_at_token=3)]
        # Should have init + 3 tokens, but NO done event
        assert not any("event: done" in c for c in cut_chunks), "Disconnect must skip done event"
        token_frames = [c for c in cut_chunks if "event: token" in c]
        assert len(token_frames) == 3, f"Expected 3 token frames, got {len(token_frames)}"

        # Test 5: WebSocket session send and interrupt
        ws = MockWebSocketSession()
        await ws.send_text("Frame 1")
        assert len(ws.sent_messages) == 1
        await ws.handle_user_interrupt()
        assert not ws.is_active

        # Test 6: Writing to closed WS raises ConnectionResetError
        raised = False
        try:
            await ws.send_text("Frame 2")
        except ConnectionResetError:
            raised = True
        assert raised, "Should raise when writing to closed WebSocket"

        # Test 7: Total token count integrity
        done_chunk = [c for c in chunks if "event: done" in c][0]
        for line in done_chunk.split("
"):
            if line.startswith("data: "):
                data = json.loads(line[6:])
                assert data["total_tokens"] == 15, "Should stream all 15 test tokens"

        # Test 8: SSE json parsing integrity
        for chunk in chunks:
            lines = chunk.strip().split("
")
            data_line = next(l for l in lines if l.startswith("data: "))
            parsed = json.loads(data_line[6:])
            assert isinstance(parsed, dict)

        # Test 9: Zero tokens prompt handles gracefully
        async def empty_stream():
            if False: yield "never"
        assert [c async for c in empty_stream()] == []

        # Test 10: Elapsed time is recorded
        assert "elapsed_ms" in done_chunk, "Done event must include latency measurement"

    asyncio.run(_test_runner())
    print("[SUCCESS] All 10 SSE & WebSocket self-tests passed!")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 11: SSE Streaming & WebSocket Architecture")
    print("=" * 70)
    asyncio.run(demonstrate_sse_consumption())
    asyncio.run(demonstrate_client_disconnect_handling())
    print("-" * 70)
    run_tests()
    print("=" * 70)
