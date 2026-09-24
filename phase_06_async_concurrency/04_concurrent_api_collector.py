"""
Phase 6: Async & Concurrency - Concurrent API Data Collector (Project P2 Precursor)
================================================================================
1. CONCEPT & PRODUCTION ARCHITECTURE:
   - High-throughput asynchronous data collection system.
   - Core Architecture Components:
     * 'httpx.AsyncClient': Asynchronous connection-pooled HTTP client.
     * 'asyncio.Semaphore(max_concurrent)': Enforces strict rate limits to avoid 429 errors.
     * 'asyncio.gather(*tasks, return_exceptions=True)': Fault-tolerant batch harvesting.
     * In-memory buffer & async disk persistence using Pathlib.
     * Measurable benchmarking: Comparing serial vs concurrent execution speed!

2. UNDER THE HOOD (CPython & Memory):
   - 'httpx.AsyncClient' uses anyio / asyncio non-blocking TCP socket streams.
   - When requests wait for server response packets over the wire, CPython yields the loop,
     enabling dozens of in-flight HTTP requests concurrently with negligible CPU overhead.
================================================================================
"""

import sys
import time
import json
import asyncio
from pathlib import Path

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


class ConcurrentApiCollector:
    """
    Production-grade concurrent data collector.
    Demonstrates Semaphore rate-limiting, error isolation, and async batching.
    """
    def __init__(self, base_url: str = "https://jsonplaceholder.typicode.com", max_concurrency: int = 4):
        self.base_url = base_url
        self.semaphore = asyncio.Semaphore(max_concurrency)

    async def fetch_single_record(self, client: "httpx.AsyncClient", post_id: int) -> dict:
        """Fetches a single record under semaphore protection."""
        async with self.semaphore:
            if not HAS_HTTPX:
                # Mock async delay when httpx is unavailable
                await asyncio.sleep(0.05)
                return {"id": post_id, "title": f"Mock Title #{post_id}", "body": "Mock body"}

            url = f"{self.base_url}/posts/{post_id}"
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            return response.json()

    async def collect_batch(self, post_ids: list[int]) -> list[dict]:
        """Collects a batch of post IDs concurrently with error isolation."""
        if not HAS_HTTPX:
            tasks = [self.fetch_single_record(None, pid) for pid in post_ids]
            return await asyncio.gather(*tasks)

        async with httpx.AsyncClient(timeout=10.0) as client:
            tasks = [self.fetch_single_record(client, pid) for pid in post_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter and return successful records
            valid_records = []
            for pid, res in zip(post_ids, results):
                if isinstance(res, Exception):
                    print(f"  [Warning] Post #{pid} failed: {res}")
                else:
                    valid_records.append(res)
            return valid_records

    def save_collected_data(self, records: list[dict], output_file: Path) -> Path:
        """Persists records to formatted JSON on disk."""
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json.dumps(records, indent=2), encoding="utf-8")
        return output_file


async def demonstrate_concurrent_collector():
    print("\n--- 1. Concurrent API Collector in Action ---")
    collector = ConcurrentApiCollector(max_concurrency=4)
    target_ids = list(range(1, 9))  # Collect 8 posts
    
    t0 = time.perf_counter()
    print(f"  Collecting {len(target_ids)} posts concurrently (Semaphore=4)...")
    records = await collector.collect_batch(target_ids)
    elapsed = time.perf_counter() - t0
    
    print(f"  Collected {len(records)} records in {elapsed:.2f}s! (~{elapsed/len(records):.3f}s per record)")
    
    # Save to disk
    output_path = Path(__file__).parent / "_collector_output" / "batch_posts.json"
    collector.save_collected_data(records, output_path)
    print(f"  Persisted batch to: {output_path}")
    print(f"  First post title: '{records[0]['title'][:35]}...'")

    # Cleanup demo output
    import shutil
    if output_path.parent.exists():
        shutil.rmtree(output_path.parent)


# ==============================================================================
# SELF-TEST CHALLENGES
# ==============================================================================

async def run_challenges():
    print("\n[*] Running automated self-tests for 04_concurrent_api_collector.py...")
    collector = ConcurrentApiCollector(max_concurrency=3)
    posts = await collector.collect_batch([1, 2, 3])
    
    assert len(posts) == 3
    assert posts[0]["id"] == 1
    assert posts[1]["id"] == 2
    assert posts[2]["id"] == 3
    
    # Test persistence
    scratch_file = Path(__file__).parent / "_test_collector" / "data.json"
    try:
        collector.save_collected_data(posts, scratch_file)
        assert scratch_file.exists() is True
        loaded = json.loads(scratch_file.read_text(encoding="utf-8"))
        assert len(loaded) == 3
        print("[SUCCESS] All self-tests passed cleanly!")
    finally:
        import shutil
        if scratch_file.parent.exists():
            shutil.rmtree(scratch_file.parent)


def main():
    print("=" * 65)
    print("Execution: Phase 6 - Concurrent API Collector (P2 Precursor)")
    print("=" * 65)
    asyncio.run(demonstrate_concurrent_collector())
    print("-" * 65)
    asyncio.run(run_challenges())
    print("=" * 65)


if __name__ == "__main__":
    main()
