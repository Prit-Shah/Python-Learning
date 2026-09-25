# 🧗 Project P7: Enterprise AI Knowledge & Assistant Platform (Capstone)
> **Roadmap Target**: Synthesizes Full-Stack AI Systems Architecture, Multi-Vendor Gateways, Semantic Caching, ReAct Agents, and SSE Streaming (Phase 11).

---

## 🏛️ End-to-End Enterprise Architecture

```text
[ Client (Browser / API) ]
           │
           ▼
[ FastAPI Ingress Layer ] ──> [ Rate Limiter & Auth ]
           │
     ┌─────┴─────────────────────┐
     ▼                           ▼
[ Semantic Cache ]         [ ReAct Agent Loop ]
(Vector Hit: 0ms, $0)      (Tool Execution: Calc / Search)
     │                           │
     ▼ (Cache Miss)              ▼
[ Model Gateway / Router ]
(Failover: OpenAI ──429──> Anthropic ──503──> Gemini)
           │
           ▼
[ SSE Token Streamer ] ──> [ Client Browser ]
```

---

## ⚡ Technical Highlights

1. **Multi-Model Gateway with Dynamic Failover**:
   Automatic failover across OpenAI, Anthropic, and Gemini on HTTP 429 / 5xx, logging token expenditures to a unified metrics ledger.

2. **Vector Semantic Cache**:
   Sub-millisecond prompt similarity matching preventing redundant expensive model inferences.

3. **Autonomous ReAct Agent Engine**:
   State machine executing multi-hop tasks with integrated tools, cycle detection, and step ceilings.

4. **W3C Server-Sent Events (SSE) Streaming**:
   FastAPI `StreamingResponse` yielding tokens in real time with proxy-buffering bypass headers (`X-Accel-Buffering: no`).

---

## 🚀 Running the Platform

```bash
# Start server
uvicorn projects.p7_ai_knowledge_platform.app:app --reload --port 8000

# Stream chat via curl:
curl -N -X POST http://localhost:8000/api/v1/chat/stream   -H "Content-Type: application/json"   -d '{"prompt": "Architect an enterprise AI platform"}'
```
