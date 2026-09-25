"""
Automated Pytest Suite for Project P7: AI Knowledge Platform
"""
import pytest
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
from fastapi.testclient import TestClient
from ..app import app
from ..gateway import gateway
from ..cache import semantic_cache

client = TestClient(app)


def test_healthz():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_gateway_failover():
    import asyncio
    # Happy path
    res1 = asyncio.run(gateway.complete("Hello", force_fail_primary=False))
    assert res1.provider == "openai"

    # Failover path
    res2 = asyncio.run(gateway.complete("Hello", force_fail_primary=True))
    assert res2.provider == "anthropic"


def test_chat_and_semantic_cache():
    # Clear cache
    semantic_cache.entries.clear()

    # 1. Miss -> Model Gateway
    r1 = client.post("/api/v1/chat", json={"prompt": "Explain decorators in Python"})
    assert r1.status_code == 200
    assert r1.json()["source"] == "openai"

    # 2. Hit -> Semantic Cache
    r2 = client.post("/api/v1/chat", json={"prompt": "Explain decorators in Python"})
    assert r2.status_code == 200
    assert r2.json()["source"] == "cache"


def test_agent_task_execution():
    resp = client.post("/api/v1/agent/run", json={"task": "Please calculate the total"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["iterations"] >= 1


def test_metrics_reporting():
    resp = client.get("/api/v1/metrics/spend")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_cost_usd" in data
    assert "provider_calls" in data
