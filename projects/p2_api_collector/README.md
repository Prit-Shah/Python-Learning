# 🧗 Project P2: Resilient Async API Data Collector
> **Roadmap Target**: Synthesizes HTTP Requests, Asyncio, Semaphore Concurrency, and Error Retries (Phases 4–6).

---

## 🏛️ Architecture & Component Design

```text
p2_api_collector/
├── models.py       # Domain Entities (FetchResult, CollectionBatchSummary)
├── client.py       # ResilientAsyncClient with Semaphore & Jittered Backoff
├── collector.py    # DataCollector (batch orchestration & JSONL persistence)
├── cli.py          # Command-line interface with argparse
└── tests/          # Pytest async test suite
```

---

## ⚡ Technical Highlights

1. **Asyncio Semaphore Rate Throttling**:
   Firing 500 requests at once crashes servers and exhausts OS file descriptors (socket limits). We use an `asyncio.Semaphore(max_concurrency)` to cap simultaneous in-flight connections.

2. **Full Jitter Exponential Backoff**:
   When receiving HTTP 429 (Rate Limit) or 5xx, retrying simultaneously from all threads creates a "thundering herd" problem. We implement randomized jitter:
   $$	ext{delay} = 	ext{random.uniform}(0, 	ext{base} 	imes 2^{	ext{attempt}-1})$$

3. **Streaming JSONL Storage**:
   Data is saved in line-delimited JSON (`.jsonl`), allowing downstream pipelines (Spark, Pandas, DuckDB) to stream large datasets without loading the full file into memory.

---

## 🚀 Usage Guide

```bash
# Fetch URLs directly
python -m projects.p2_api_collector.cli --urls https://httpbin.org/get https://httpbin.org/delay/1 --concurrency 2

# Fetch from URL list with output
python -m projects.p2_api_collector.cli --file urls.txt --concurrency 5 --output data.jsonl
```

---

## 🎙️ Senior Interview Script: Async HTTP & Concurrency Control

- **Interview Question**: *"How do you fetch thousands of URLs concurrently without overwhelming the server or running out of memory?"*
- **60-Second Verbal Answer Script**:
  * *"In Python, I use `httpx.AsyncClient` with `asyncio.gather()` inside an async coroutine. However, unrestricted gathering causes socket exhaustion and triggers 429 rate limits."*
  * *"To prevent this, I wrap requests in an `asyncio.Semaphore(concurrency_limit)` which throttles simultaneous active HTTP handshakes while keeping the event loop non-blocking."*
  * *"For transient errors, I implement exponential backoff with full jitter to avoid the thundering herd effect. Results are written directly to JSONL, ensuring $O(1)$ memory usage regardless of dataset size."*
