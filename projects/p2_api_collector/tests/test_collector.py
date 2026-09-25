"""
Automated Pytest Suite for Project P2: Async API Data Collector
"""
import pytest
import asyncio
from pathlib import Path
import httpx
from ..models import FetchResult, CollectionBatchSummary
from ..client import ResilientAsyncClient
from ..collector import DataCollector


@pytest.mark.asyncio
async def test_fetch_success(monkeypatch):
    """Test successful mock response."""
    async def mock_get(self, url, **kwargs):
        class MockResponse:
            status_code = 200
            headers = {"content-type": "application/json"}
            def json(self): return {"result": "success", "url": url}
            def raise_for_status(self): pass
        return MockResponse()

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    engine = ResilientAsyncClient(max_concurrency=2)
    collector = DataCollector(engine)

    results, summary = await collector.collect_urls(["https://mock.api/1", "https://mock.api/2"])
    assert len(results) == 2
    assert summary.successful == 2
    assert summary.failed == 0
    assert summary.success_rate_pct == 100.0
    assert results[0].data["result"] == "success"


@pytest.mark.asyncio
async def test_fetch_retry_and_recovery(monkeypatch):
    """Test retry recovery on initial failures."""
    call_counts = {}

    async def mock_flaky_get(self, url, **kwargs):
        call_counts[url] = call_counts.get(url, 0) + 1
        if call_counts[url] < 2:
            # First attempt fails with 500
            req = httpx.Request("GET", url)
            resp = httpx.Response(500, request=req)
            raise httpx.HTTPStatusError("Server Error", request=req, response=resp)

        # Second attempt succeeds
        class MockResponse:
            status_code = 200
            headers = {"content-type": "application/json"}
            def json(self): return {"recovered": True}
            def raise_for_status(self): pass
        return MockResponse()

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_flaky_get)

    engine = ResilientAsyncClient(max_retries=3, base_delay_sec=0.01)
    collector = DataCollector(engine)

    results, summary = await collector.collect_urls(["https://flaky.api/item"])
    assert len(results) == 1
    assert results[0].is_success is True
    assert results[0].attempts == 2
    assert summary.successful == 1


@pytest.mark.asyncio
async def test_save_jsonl(tmp_path):
    dest = tmp_path / "output.jsonl"
    engine = ResilientAsyncClient()
    collector = DataCollector(engine)

    mock_results = [
        FetchResult(url="https://api.test/1", status_code=200, latency_ms=15.2, data={"id": 1}),
        FetchResult(url="https://api.test/2", status_code=404, latency_ms=8.5, error="Not Found"),
    ]

    collector.save_jsonl(mock_results, dest)
    assert dest.exists()

    lines = dest.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    assert "https://api.test/1" in lines[0]
    assert "404" in lines[1]
