"""Simple burst load test for the public health endpoint.

Example:
    python ops/evals/run_public_health_load.py --output ops/evals/public-health-load-2026-04-21.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from pathlib import Path

import httpx


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * percentile
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    if lower == upper:
        return ordered[lower]
    fraction = index - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


async def _single_request(client: httpx.AsyncClient, url: str) -> dict[str, float | int | str]:
    started = time.perf_counter()
    try:
        response = await client.get(url)
        latency_ms = (time.perf_counter() - started) * 1000
        return {
            "status": response.status_code,
            "latency_ms": latency_ms,
            "ok": 200 <= response.status_code < 400,
        }
    except Exception as exc:  # pragma: no cover - exercised by real network runs
        latency_ms = (time.perf_counter() - started) * 1000
        return {
            "status": 0,
            "latency_ms": latency_ms,
            "ok": False,
            "error": type(exc).__name__,
        }


async def _run_load(url: str, total_requests: int, concurrency: int, timeout_seconds: float) -> list[dict[str, float | int | str]]:
    semaphore = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
        async def guarded_request() -> dict[str, float | int | str]:
            async with semaphore:
                return await _single_request(client, url)

        tasks = [asyncio.create_task(guarded_request()) for _ in range(total_requests)]
        return await asyncio.gather(*tasks)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url",
        default="https://agentnexlify-production.up.railway.app/api/health",
        help="Public endpoint to hit.",
    )
    parser.add_argument("--requests", type=int, default=100, help="Total requests to send.")
    parser.add_argument("--concurrency", type=int, default=10, help="Number of in-flight requests.")
    parser.add_argument("--timeout-seconds", type=float, default=10.0, help="Per-request timeout.")
    parser.add_argument("--output", help="Optional JSON output path.")
    args = parser.parse_args()

    results = asyncio.run(
        _run_load(
            args.url,
            total_requests=args.requests,
            concurrency=args.concurrency,
            timeout_seconds=args.timeout_seconds,
        )
    )

    latencies = [float(item["latency_ms"]) for item in results]
    success_count = sum(1 for item in results if item["ok"])
    failure_count = len(results) - success_count
    status_counts: dict[str, int] = {}
    for item in results:
        key = str(item["status"])
        status_counts[key] = status_counts.get(key, 0) + 1

    summary = {
        "url": args.url,
        "total_requests": len(results),
        "concurrency": args.concurrency,
        "success_count": success_count,
        "failure_count": failure_count,
        "success_rate": round((success_count / len(results)) * 100, 1) if results else 0.0,
        "avg_latency_ms": round(statistics.fmean(latencies), 1) if latencies else 0.0,
        "p50_latency_ms": round(_percentile(latencies, 0.50), 1),
        "p95_latency_ms": round(_percentile(latencies, 0.95), 1),
        "max_latency_ms": round(max(latencies), 1) if latencies else 0.0,
        "min_latency_ms": round(min(latencies), 1) if latencies else 0.0,
        "status_counts": status_counts,
    }

    print(json.dumps(summary, indent=2))

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(f"Saved summary to {output_path}")

    return 0 if failure_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
