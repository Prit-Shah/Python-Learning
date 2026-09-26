"""
04_concurrent_api_collector.py

============================================================
1. CONCEPT
============================================================

High-throughput asynchronous data harvesting in modern Python integrates
connection pooling, semaphore-gated concurrency, resilient error isolation,
and persistent serialization:

1. Asynchronous Data Collection Pipeline Architecture:
   - Client Pooling: Uses `httpx.AsyncClient` wrapped in an async context manager
     to maintain a persistent, reusable TCP connection pool.
   - Concurrency Throttling: An `asyncio.Semaphore(max_concurrency)` bounds the
     maximum number of simultaneous requests in flight, preventing HTTP 429
     rate-limit rejections and socket exhaustion.
   - Fault-Tolerant Batching: Uses `asyncio.gather(*tasks, return_exceptions=True)`
     so that if an individual network call encounters an error, the rest of the
     batch completes uninterrupted.
   - Result Partitioning: Separates successful records from exceptions, routing
     errors to diagnostic logs or dead-letter queues.

2. Deterministic Testing with MockTransport:
   - High-throughput collectors should be tested deterministically using
     `httpx.MockTransport` without relying on flaky third-party internet APIs.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python (asyncio + httpx)           | JavaScript / TypeScript (Node.js)  |
+------------------------------+------------------------------------+------------------------------------+
| Async HTTP Client            | `httpx.AsyncClient()`              | `axios` / `fetch`                  |
| Concurrency Gate (Throttling)| `asyncio.Semaphore(N)`             | `p-limit(N)` library               |
| Resilient Batch Gathering    | `asyncio.gather(..., ret_exc=True)`| `Promise.allSettled([ ... ])`      |
| In-Memory Transport Mocking  | `httpx.MockTransport(handler)`     | `msw` (Mock Service Worker)        |
| Async File I/O               | `pathlib.Path.write_text` / aiofiles| `fs.promises.writeFile`           |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Pipeline Architecture:
- In Node.js, `p-limit` wraps functions in a queue. In Python, `asyncio.Semaphore`
  is built directly into the standard library `asyncio` module and uses standard
  `async with sem:` context manager syntax.


============================================================
3. UNDER THE HOOD (CPython & Memory)
============================================================

1. Overlapped Socket I/O:
   - When 50 tasks invoke `await client.get()`, CPython issues non-blocking
     socket calls and registers the socket descriptors with the OS event loop.
   - While waiting for packet replies over the wire, CPython executes other tasks
     or idles at 0% CPU consumption.

2. Semaphore Scheduling Order:
   - `asyncio.Semaphore` maintains an internal FIFO wait-queue of paused futures.
   - As active requests finish and exit `async with self.semaphore:`, waiting
     tasks are awakened in order, preventing task starvation.


============================================================
4. COMMON GOTCHAS
============================================================

1. Hitting Real APIs in Automated Test Suites:
   - Hardcoding public endpoints (e.g. `typicode.com`) in unit tests causes tests
     to fail when offline, behind corporate proxies, or when third-party servers undergo downtime.
   - Solution: Inject an `httpx.MockTransport` during automated testing.

2. Unbounded Concurrency:
   - Launching 5,000 tasks simultaneously without a Semaphore exhausts system file
     descriptors (`OSError: [Errno 24] Too many open files`).
   - Always gate concurrent batch requests with a Semaphore sized to downstream capacity.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "How do you design a high-throughput, fault-tolerant concurrent API scraper or data ingestion pipeline in Python?"
Script:
"A production-grade asynchronous ingestion pipeline requires four core architectural pillars:
First, connection reuse via a shared `httpx.AsyncClient` managed within an async context manager,
which prevents the overhead of repeated TCP and TLS handshakes.
Second, concurrency gating using an `asyncio.Semaphore(N)` to enforce strict rate limits
against third-party APIs and prevent local socket exhaustion.
Third, fault isolation using `asyncio.gather(*tasks, return_exceptions=True)` or `asyncio.TaskGroup`,
ensuring that individual record timeouts or HTTP 500 errors do not abort the entire batch.
Fourth, error segregation: partitioning the resulting batch into successful records persisted
to storage and failed tasks routed to dead-letter queues or alert channels."
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path
import httpx

# Ensure UTF-8 standard output across environments
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


class ConcurrentApiCollector:
    """Production-grade asynchronous data harvester with rate limiting and error isolation."""

    def __init__(
        self,
        base_url: str = "https://api.internal.data",
        max_concurrency: int = 4,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.transport = transport
        self.active_in_flight = 0
        self.peak_in_flight = 0

    async def fetch_single_record(self, client: httpx.AsyncClient, item_id: int) -> dict:
        """Fetches a single item record under semaphore concurrency protection."""
        async with self.semaphore:
            self.active_in_flight += 1
            self.peak_in_flight = max(self.peak_in_flight, self.active_in_flight)
            try:
                # Artificial minor delay to verify concurrency overlap
                await asyncio.sleep(0.002)
                url = f"{self.base_url}/items/{item_id}"
                response = await client.get(url, timeout=5.0)
                response.raise_for_status()
                return response.json()
            finally:
                self.active_in_flight -= 1

    async def collect_batch(self, item_ids: list[int]) -> tuple[list[dict], list[Exception]]:
        """Collects a batch of items concurrently, returning (successes, errors)."""
        async with httpx.AsyncClient(transport=self.transport, timeout=10.0) as client:
            tasks = [self.fetch_single_record(client, item_id) for item_id in item_ids]
            raw_results = await asyncio.gather(*tasks, return_exceptions=True)

            successes = []
            errors = []
            for res in raw_results:
                if isinstance(res, Exception):
                    errors.append(res)
                else:
                    successes.append(res)

            return successes, errors

    def save_to_disk(self, records: list[dict], target_path: Path) -> Path:
        """Persists collected records to formatted JSON on disk."""
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
        return target_path


def run_tests():
    # Deterministic mock transport handler simulating an API server
    def mock_transport_handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        # Route /items/1 to /items/5 return valid item data
        for i in range(1, 6):
            if path == f"/items/{i}":
                return httpx.Response(200, json={"item_id": i, "status": "active", "value": i * 100})

        # Route /items/99 returns 404
        if path == "/items/99":
            return httpx.Response(404, json={"error": "Item not found"})

        # Route /items/500 returns 500
        if path == "/items/500":
            return httpx.Response(500, json={"error": "Server error"})

        return httpx.Response(400, json={"error": "Bad request"})

    mock_transport = httpx.MockTransport(mock_transport_handler)

    async def main_suite():
        # ============================================================
        # 1. BATCH DATA HARVESTING & ERROR PARTITIONING
        # ============================================================

        collector = ConcurrentApiCollector(
            base_url="https://api.internal.data",
            max_concurrency=3,
            transport=mock_transport,
        )

        # Batch contains 3 valid IDs, one 404, and one 500
        query_ids = [1, 2, 99, 3, 500]
        successes, errors = await collector.collect_batch(query_ids)

        # 3 items succeeded
        assert len(successes) == 3
        assert [s["item_id"] for s in successes] == [1, 2, 3]

        # 2 items failed, but did NOT abort the batch
        assert len(errors) == 2
        for err in errors:
            assert isinstance(err, httpx.HTTPStatusError)

        # Concurrency check: Semaphore prevented running more than 3 simultaneous requests
        assert collector.peak_in_flight <= 3


        # ============================================================
        # 2. PERSISTENCE & SERIALIZATION
        # ============================================================

        with tempfile.TemporaryDirectory() as temp_dir_str:
            output_file = Path(temp_dir_str) / "harvested" / "output.json"
            collector.save_to_disk(successes, output_file)

            assert output_file.exists() is True
            loaded_data = json.loads(output_file.read_text(encoding="utf-8"))
            assert len(loaded_data) == 3
            assert loaded_data[0] == {"item_id": 1, "status": "active", "value": 100}

    asyncio.run(main_suite())


if __name__ == "__main__":
    run_tests()
    print("04_concurrent_api_collector.py tests passed!")
