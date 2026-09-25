"""
Project P2: Batch Collector Orchestrator & Storage
"""
import asyncio
import json
import logging
import time
from pathlib import Path
import httpx
from .models import FetchResult, CollectionBatchSummary
from .client import ResilientAsyncClient

logger = logging.getLogger("api_collector")


class DataCollector:
    def __init__(self, client_engine: ResilientAsyncClient):
        self.client_engine = client_engine

    async def collect_urls(
        self,
        urls: list[str],
        headers: dict[str, str] | None = None,
    ) -> tuple[list[FetchResult], CollectionBatchSummary]:
        """Runs concurrent gathering over a list of target URLs."""
        t0 = time.perf_counter()

        async with httpx.AsyncClient(headers=headers) as http_client:
            tasks = [self.client_engine.fetch_one(http_client, url) for url in urls]
            results: list[FetchResult] = await asyncio.gather(*tasks)

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        successes = sum(1 for r in results if r.is_success)
        failures = len(results) - successes
        avg_lat = sum(r.latency_ms for r in results) / len(results) if results else 0.0

        summary = CollectionBatchSummary(
            total_requested=len(results),
            successful=successes,
            failed=failures,
            total_elapsed_ms=round(elapsed_ms, 2),
            avg_latency_ms=round(avg_lat, 2),
            success_rate_pct=round((successes / len(results)) * 100.0, 1) if results else 0.0,
        )

        return results, summary

    def save_jsonl(self, results: list[FetchResult], destination: Path | str) -> None:
        """Persists collection results in JSON-Lines format (1 record per line)."""
        dest_path = Path(destination).resolve()
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        with open(dest_path, "w", encoding="utf-8") as f:
            for item in results:
                f.write(json.dumps(item.to_dict()) + "\n")
