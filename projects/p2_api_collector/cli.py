"""
Project P2: CLI Application Entrypoint
================================================================================
Usage:
  python cli.py --urls https://httpbin.org/get https://httpbin.org/delay/1
  python cli.py --file target_urls.txt --concurrency 4 --output results.jsonl
================================================================================
"""
import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass

import argparse
import asyncio
import logging
from pathlib import Path
from .client import ResilientAsyncClient
from .collector import DataCollector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="collector",
        description="P2: High-Throughput Concurrent Async API Data Collector",
    )
    parser.add_argument("--urls", nargs="*", help="List of URLs to fetch")
    parser.add_argument("--file", "-f", help="File containing target URLs (one per line)")
    parser.add_argument("--concurrency", "-c", type=int, default=5, help="Maximum concurrent requests (Semaphore)")
    parser.add_argument("--retries", "-r", type=int, default=3, help="Max retry attempts per failed URL")
    parser.add_argument("--output", "-o", default="collected_data.jsonl", help="Destination JSONL path")
    return parser


async def run_async_main(args) -> int:
    target_urls: list[str] = []
    if args.urls:
        target_urls.extend(args.urls)
    if args.file:
        p = Path(args.file)
        if p.exists():
            target_urls.extend([line.strip() for line in p.read_text().splitlines() if line.strip()])

    if not target_urls:
        print("[ERROR] No URLs provided. Use --urls or --file.")
        return 1

    print(f"[*] Starting concurrent collection of {len(target_urls)} URLs (Concurrency: {args.concurrency})...")
    client_engine = ResilientAsyncClient(
        max_concurrency=args.concurrency,
        max_retries=args.retries,
    )
    collector = DataCollector(client_engine)

    results, summary = await collector.collect_urls(target_urls)
    collector.save_jsonl(results, args.output)

    print("
========================================")
    print(" COLLECTION BATCH SUMMARY REPORT")
    print("========================================")
    print(f"Total Requests:      {summary.total_requested}")
    print(f"Successful:          {summary.successful} ({summary.success_rate_pct}%)")
    print(f"Failed:              {summary.failed}")
    print(f"Total Wall Time:     {summary.total_elapsed_ms:.1f}ms")
    print(f"Average URL Latency: {summary.avg_latency_ms:.1f}ms")
    print(f"Output saved to:     {args.output}")

    return 0 if summary.failed == 0 else 1


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return asyncio.run(run_async_main(args))


if __name__ == "__main__":
    sys.exit(main())
