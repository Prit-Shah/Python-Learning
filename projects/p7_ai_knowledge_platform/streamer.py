"""
Project P7: Server-Sent Events (SSE) Streamer
"""
import json
from typing import AsyncIterator
from .gateway import gateway


def format_sse(data: dict, event: str = "token") -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def sse_chat_streamer(prompt: str) -> AsyncIterator[str]:
    # 1. Emit init event
    yield format_sse({"status": "generating", "prompt": prompt}, event="init")

    # 2. Stream tokens
    response = await gateway.complete(prompt)
    async for token in gateway.stream_tokens(response.content):
        yield format_sse({"token": token}, event="token")

    # 3. Emit done event
    yield format_sse({"status": "complete", "provider": response.provider, "cost_usd": response.cost_usd}, event="done")
