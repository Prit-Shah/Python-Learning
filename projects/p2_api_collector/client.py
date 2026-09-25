"""
Project P2: Resilient Async HTTP Client
================================================================================
Implements:
1. Concurrency throttling via asyncio.Semaphore (prevents socket exhaustion)
2. Exponential backoff with jitter on 429/500/network failures
3. Explicit timeouts per request
================================================================================
"""
import asyncio
import logging
import random
import time
from typing import Any
import httpx
from .models import FetchResult

logger = logging.getLogger("api_collector")


class ResilientAsyncClient:
    def __init__(
        self,
        max_concurrency: int = 5,
        max_retries: int = 3,
        base_delay_sec: float = 0.5,
        timeout_sec: float = 5.0,
    ):
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.max_retries = max_retries
        self.base_delay_sec = base_delay_sec
        self.timeout_sec = timeout_sec

    async def fetch_one(
        self,
        client: httpx.AsyncClient,
        url: str,
    ) -> FetchResult:
        """Fetches a single URL with concurrency throttling and retry backoff."""
        async with self.semaphore:
            attempts = 0
            t_start = time.perf_counter()

            for attempt in range(1, self.max_retries + 1):
                attempts = attempt
                try:
                    t_req = time.perf_counter()
                    response = await client.get(url, timeout=self.timeout_sec)
                    latency = (time.perf_counter() - t_req) * 1000.0

                    if response.status_code == 429 or response.status_code >= 500:
                        raise httpx.HTTPStatusError(
                            f"HTTP {response.status_code}",
                            request=response.request,
                            response=response,
                        )

                    response.raise_for_status()
                    data = response.json() if "application/json" in response.headers.get("content-type", "") else {"text": response.text[:200]}

                    return FetchResult(
                        url=url,
                        status_code=response.status_code,
                        latency_ms=round(latency, 2),
                        data=data,
                        attempts=attempts,
                    )

                except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                    latency = (time.perf_counter() - t_start) * 1000.0
                    status = getattr(getattr(exc, "response", None), "status_code", None)

                    if attempt < self.max_retries:
                        # Full jitter exponential backoff: delay = random between 0 and base * 2^attempt
                        delay = random.uniform(0, self.base_delay_sec * (2 ** (attempt - 1)))
                        logger.warning(
                            f"[RETRY {attempt}/{self.max_retries}] {url} failed ({exc}). Retrying in {delay:.2f}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"[FAILED] {url} exceeded max retries. Error: {exc}")
                        return FetchResult(
                            url=url,
                            status_code=status,
                            latency_ms=round(latency, 2),
                            error=str(exc),
                            attempts=attempts,
                        )

            return FetchResult(
                url=url,
                status_code=None,
                latency_ms=round((time.perf_counter() - t_start) * 1000.0, 2),
                error="Exhausted retry loop",
                attempts=attempts,
            )
