"""
Project P7: Production AI Platform FastAPI Service
"""
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from .gateway import gateway
from .cache import semantic_cache
from .agent import platform_agent
from .streamer import sse_chat_streamer

app = FastAPI(
    title="P7: Enterprise AI Knowledge & Assistant Platform",
    version="1.0.0",
)


class ChatRequest(BaseModel):
    prompt: str


class AgentRequest(BaseModel):
    task: str


@app.get("/healthz")
async def health_check():
    return {"status": "healthy", "service": "ai_platform"}


@app.post("/api/v1/chat")
async def direct_chat(req: ChatRequest):
    cached = semantic_cache.get(req.prompt)
    if cached:
        return {"response": cached, "source": "cache"}

    result = await gateway.complete(req.prompt)
    semantic_cache.set(req.prompt, result.content)
    return {"response": result.content, "source": result.provider, "cost_usd": result.cost_usd}


@app.post("/api/v1/chat/stream")
async def stream_chat(req: ChatRequest):
    return StreamingResponse(
        sse_chat_streamer(req.prompt),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/v1/agent/run")
async def run_agent_task(req: AgentRequest):
    outcome = platform_agent.execute_task(req.task)
    return {
        "success": outcome.success,
        "answer": outcome.answer,
        "iterations": outcome.iterations,
        "steps_count": len(outcome.steps),
    }


@app.get("/api/v1/metrics/spend")
async def get_spend_metrics():
    return {
        "total_cost_usd": round(gateway.total_cost_usd, 6),
        "total_tokens": gateway.total_tokens,
        "provider_calls": gateway.calls_by_provider,
        "cache_hits": semantic_cache.hits,
        "cache_misses": semantic_cache.misses,
    }
