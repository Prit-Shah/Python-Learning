r"""
02_sse_streaming_and_websockets.py

============================================================
1. CONCEPT
============================================================

Delivering real-time generative AI interactions requires choosing between two fundamental
streaming transport protocols: Server-Sent Events (SSE) and WebSockets:

1. Server-Sent Events (SSE) Architecture:
   - Unidirectional streaming (Server -> Client) over standard HTTP/1.1 or HTTP/2.
   - The Gold Standard for LLM text generation:
     * Minimal protocol overhead: Operates on standard HTTP request/response semantics.
     * Automatic Client Reconnection: Native browser `EventSource` API handles reconnection
       and tracks the last received event ID (`Last-Event-ID`).
     * Stateless: Traverses corporate firewalls, API gateways, and load balancers seamlessly.
   - SSE Wire Protocol:
     ```http
     HTTP/1.1 200 OK
     Content-Type: text/event-stream
     Cache-Control: no-cache
     Connection: keep-alive
     X-Accel-Buffering: no

     event: delta
     data: {"token": "Hello"}

     event: delta
     data: {"token": " world"}

     event: done
     data: {"finish_reason": "stop"}

     ```

2. WebSockets Architecture:
   - Full-Duplex Bidirectional transport over a persistent TCP connection initiated via HTTP Upgrade.
   - Best for: Voice AI agents (full-duplex audio in/out), real-time collaborative canvas,
     continuous client sensor streams.
   - Tradeoffs: Stateful connections require sticky sessions, complex socket cluster managers
     (Redis Pub/Sub), and custom heartbeat/ping-pong mechanisms.

3. Client Disconnect Detection & Token Waste Prevention:
   - If a user closes their browser tab 2 seconds into a 30-second LLM generation, an unmonitored
     backend will continue generating tokens and burning API budget!
   - In FastAPI/Starlette, endpoints must poll `await request.is_disconnected()` between chunks
     to terminate upstream LLM generation immediately.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python (FastAPI / Starlette)       | JavaScript / TypeScript (Node.js)  |
+------------------------------+------------------------------------+------------------------------------+
| SSE Response Generator       | `StreamingResponse(gen, media_...)`| `res.write("data: ...\n\n")`       |
| Event Framing Protocol       | Double newline `\n\n` terminator   | Double newline `\n\n` terminator   |
| Disconnect Listener          | `await request.is_disconnected()`  | `req.on('close', ...)`             |
| Reverse Proxy Header         | `X-Accel-Buffering: no`            | `X-Accel-Buffering: no`            |
| WebSocket Handler            | `@app.websocket("/ws")`            | `ws` / `socket.io` / NestJS gateway|
| WebSocket Lifecycle          | `await ws.accept()`, `ws.receive()`| `ws.on('message', ...)`            |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Architecture Differences:
1. In Node.js, SSE is implemented by manually calling `res.write()` on the raw Express/Node
   response socket.
2. In FastAPI, SSE is implemented via asynchronous generators (`async def stream_generator()`)
   passed to `StreamingResponse`. Starlette handles chunked transfer encoding framing and
   co-routines on the ASGI event loop.


============================================================
3. UNDER THE HOOD (ASGI Channels & Reverse Proxy Traps)
============================================================

1. The Nginx / Reverse-Proxy Buffering Trap:
   - By default, reverse proxies like Nginx or AWS CloudFront buffer incoming HTTP responses
     in 4KB or 16KB blocks before transmitting packets to clients to optimize TCP efficiency.
   - In an AI chat application, this destroys the real-time "typewriter" effect: the user sees
     a spinner for 10 seconds, followed by an abrupt block of text all at once.
   - FIX: Always inject the header `X-Accel-Buffering: no` in FastAPI `StreamingResponse`. This
     instructs Nginx to disable response buffering and flush every token packet immediately.

2. ASGI Disconnect Monitoring:
   - The ASGI protocol passes events to the application via an async `receive` callable.
   - When a client socket closes, the ASGI server (Uvicorn) places an `{"type": "http.disconnect"}`
     event into the receive queue.
   - Calling `await request.is_disconnected()` checks this channel non-blockingly, allowing
     the generator loop to break and cancel background tasks.


============================================================
4. COMMON GOTCHAS
============================================================

1. Malformed SSE Newline Delimiters:
   - Emitting a single newline `\n` instead of `\n\n` between events.
   - The client `EventSource` parser buffers indefinitely, waiting for the double newline
     boundary, causing the client UI to hang.
   - FIX: Every SSE frame MUST terminate with `\n\n`.

2. Over-engineering with WebSockets for Simple Text Chat:
   - Choosing WebSockets when all you need is text streaming. WebSockets introduce stateful
     reconnection logic, load-balancer routing hurdles, and memory leaks.
   - FIX: Use SSE for 95% of LLM text generation; reserve WebSockets strictly for bidirectional
     real-time audio or collaborative tools.

3. Blocking the ASGI Loop Inside WebSocket Handlers:
   - Calling synchronous blocking code inside `async def websocket_endpoint` halts all concurrent
     WebSocket connections on that worker.
   - FIX: Always use non-blocking async calls: `await websocket.receive_text()`.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "When should you choose Server-Sent Events (SSE) versus WebSockets for an AI system?"
A1: "For standard LLM chat interfaces, Server-Sent Events (SSE) is the superior architectural choice.
     SSE operates over standard HTTP/1.1 or HTTP/2, requires zero stateful connection management on
     the server, traverses corporate proxies and firewalls without custom protocol upgrades, and
     features native automatic reconnection in browser clients via `EventSource`.
     I choose WebSockets only when the application requires full-duplex, bidirectional communication—such
     as real-time voice-to-voice agents where the client is continuously streaming microphone audio
     chunks while simultaneously listening for AI audio output, or collaborative multiplayer AI canvas
     interfaces."

Q2: "How do you prevent burning LLM token costs when a user closes their browser mid-generation?"
A2: "In FastAPI, when streaming responses using `StreamingResponse`, I monitor the client connection
     state on every loop iteration using `await request.is_disconnected()`.
     If `is_disconnected()` returns `True`, the user has navigated away, closed the tab, or lost network.
     I immediately break out of the generator loop. If using an external client like `AsyncOpenAI`,
     I cancel the upstream streaming request or task. This aborts generation on the GPU cluster, saving
     tokens and preventing wasted API spend."

Q3: "What headers and reverse-proxy configurations are required for production streaming?"
A3: "Production streaming requires three critical headers:
     First, `Content-Type: text/event-stream` to establish SSE semantics.
     Second, `Cache-Control: no-cache` to ensure intermediary caches do not store dynamic tokens.
     Third, `X-Accel-Buffering: no` to instruct reverse proxies like Nginx to disable response buffering;
     without this header, Nginx buffers chunks until 4KB is accumulated, destroying the real-time
     typewriter effect for the end-user."
"""

import sys
import asyncio
import json
import warnings
warnings.filterwarnings("ignore")
from typing import Any, AsyncGenerator, Dict, List

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, status
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ==============================================================================
# 1. SSE WIRE PROTOCOL FORMATTER
# ==============================================================================

class SSEFormatter:
    """Formats event payloads into the standard W3C Server-Sent Events wire format."""

    @staticmethod
    def format_event(data: Dict[str, Any], event: str = "delta", event_id: str = "") -> str:
        """
        Produces formatted SSE string:
        event: <event>\n
        id: <event_id>\n
        data: <json>\n\n
        """
        lines = []
        if event:
            lines.append(f"event: {event}")
        if event_id:
            lines.append(f"id: {event_id}")

        lines.append(f"data: {json.dumps(data)}")
        # Every SSE block must end with double newline
        return "\n".join(lines) + "\n\n"


# ==============================================================================
# 2. FASTAPI APPLICATION WITH SSE & WEBSOCKETS
# ==============================================================================

app = FastAPI(title="Streaming Protocols Engine: SSE vs WebSockets")


async def simulate_token_stream(prompt: str, request: Request) -> AsyncGenerator[str, None]:
    """
    Simulates token generation with client disconnect monitoring.
    """
    tokens = ["Deep", " Learning", " architectures", " leverage", " attention", " mechanisms."]

    for idx, token in enumerate(tokens):
        # 1. Production Disconnect Check
        if await request.is_disconnected():
            print(f"[Streaming] Client disconnected. Aborting generation at token {idx}.")
            break

        yield SSEFormatter.format_event(
            data={"token": token, "index": idx},
            event="delta",
            event_id=str(idx)
        )
        await asyncio.sleep(0.01)

    # Final completion event
    yield SSEFormatter.format_event(
        data={"finish_reason": "stop"},
        event="done"
    )


@app.get("/api/v1/chat/sse")
async def chat_sse_endpoint(prompt: str, request: Request):
    """
    Server-Sent Events endpoint with anti-buffering headers.
    """
    return StreamingResponse(
        simulate_token_stream(prompt, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Crucial for Nginx buffering bypass
        }
    )


@app.websocket("/ws/chat")
async def chat_websocket_endpoint(websocket: WebSocket):
    """
    Full-duplex WebSocket endpoint for bidirectional interaction.
    """
    await websocket.accept()
    try:
        while True:
            # Receive client prompt
            incoming_text = await websocket.receive_text()
            data = json.loads(incoming_text)
            user_msg = data.get("message", "")

            # Echo token-by-token back to client
            words = user_msg.split()
            for idx, word in enumerate(words):
                await websocket.send_json({
                    "type": "token",
                    "content": word + " ",
                    "index": idx
                })
                await asyncio.sleep(0.01)

            # Signal completion
            await websocket.send_json({"type": "complete", "status": "SUCCESS"})

    except WebSocketDisconnect:
        print("[WebSocket] Client closed connection gracefully.")


# ==============================================================================
# 3. SELF-TESTING SUITE
# ==============================================================================

def run_tests() -> None:
    print("\n[*] Starting automated test suite for 02_sse_streaming_and_websockets.py...")

    # ------------------------------------------------------------
    # Test 1: SSE Wire Protocol Formatting
    # ------------------------------------------------------------
    print("  -> Testing SSE framing format and double newline delimiters...")
    formatted = SSEFormatter.format_event({"token": "Python"}, event="delta", event_id="101")
    assert formatted.endswith("\n\n"), "SSE event must terminate with double newline"
    assert "event: delta\n" in formatted
    assert "id: 101\n" in formatted
    assert 'data: {"token": "Python"}' in formatted

    # ------------------------------------------------------------
    # Test 2: FastAPI SSE Endpoint & Anti-Buffering Headers
    # ------------------------------------------------------------
    print("  -> Testing SSE endpoint headers (X-Accel-Buffering, Cache-Control)...")
    with TestClient(app) as client:
        res = client.get("/api/v1/chat/sse?prompt=Hello")
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/event-stream")
        assert res.headers["x-accel-buffering"] == "no"
        assert res.headers["cache-control"] == "no-cache"

        # Verify stream content contains tokens and done event
        stream_text = res.text
        assert "event: delta" in stream_text
        assert "event: done" in stream_text
        assert "attention" in stream_text

    # ------------------------------------------------------------
    # Test 3: WebSocket Bidirectional Communication
    # ------------------------------------------------------------
    print("  -> Testing WebSocket full-duplex messaging and token streaming...")
    with TestClient(app) as client:
        with client.websocket_connect("/ws/chat") as ws:
            # Send message to WebSocket
            ws.send_text(json.dumps({"message": "Async Python WebSocket"}))

            # Receive streamed tokens
            received_tokens = []
            while True:
                msg = ws.receive_json()
                if msg["type"] == "complete":
                    break
                assert msg["type"] == "token"
                received_tokens.append(msg["content"])

            assembled = "".join(received_tokens)
            assert "Async Python WebSocket" in assembled

    print("[SUCCESS] All 3 SSE Streaming & WebSockets tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 11 - 02: Real-Time AI Streaming: SSE vs WebSockets")
    print("=" * 70)
    run_tests()
    print("=" * 70)
