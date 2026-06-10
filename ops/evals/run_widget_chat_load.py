"""Burst load test for the widget chat path (launch rubric 5.1/5.4 note).

Two modes:
- Without TEST_WIDGET_API_KEY: bursts POST /api/v1/widget/chat with an invalid
  key. Exercises the full middleware + auth/validation stack under concurrency
  (expected status 401/403/422) WITHOUT burning Claude tokens or writing
  tenant data — a safe prod burst that measures the stack, not the model.
- With TEST_WIDGET_API_KEY (disposable tenant): real chat turns end to end.
  Run sparingly; each request is a Claude call.

Example:
    python ops/evals/run_widget_chat_load.py \
        --base-url https://agentnexlify-production.up.railway.app \
        --requests 100 --concurrency 10 \
        --output ops/evals/widget-chat-load-$(date +%F).json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
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


async def _single_request(
    client: httpx.AsyncClient, url: str, payload: dict, ok_statuses: set[int]
) -> dict:
    started = time.perf_counter()
    try:
        response = await client.post(url, json=payload)
        latency_ms = (time.perf_counter() - started) * 1000
        return {
            "status": response.status_code,
            "latency_ms": latency_ms,
            # "ok" = the stack answered deterministically within budget, with
            # an expected status for the mode we're running in.
            "ok": response.status_code in ok_statuses,
        }
    except Exception as exc:  # timeout / connection failure = the real signal
        latency_ms = (time.perf_counter() - started) * 1000
        return {"status": "error", "latency_ms": latency_ms, "ok": False, "error": str(exc)[:120]}


async def _run(args: argparse.Namespace) -> dict:
    api_key = os.environ.get("TEST_WIDGET_API_KEY", "")
    real_mode = bool(api_key)
    url = f"{args.base_url.rstrip('/')}/api/v1/widget/chat"
    payload = {
        "api_key": api_key or "anx_load_test_invalid_key",
        "message": "What are your business hours?",
        "session_id": "load-test-session",
    }
    # Auth-path mode: any deterministic 4xx rejection counts as the stack
    # holding up. Real mode: 2xx only.
    ok_statuses = {200} if real_mode else {400, 401, 403, 404, 422, 429}

    semaphore = asyncio.Semaphore(args.concurrency)
    async with httpx.AsyncClient(timeout=args.timeout) as client:

        async def bounded() -> dict:
            async with semaphore:
                return await _single_request(client, url, payload, ok_statuses)

        started = time.perf_counter()
        results = await asyncio.gather(*[bounded() for _ in range(args.requests)])
        wall_s = time.perf_counter() - started

    latencies = [r["latency_ms"] for r in results]
    statuses: dict[str, int] = {}
    for r in results:
        statuses[str(r["status"])] = statuses.get(str(r["status"]), 0) + 1

    return {
        "mode": "real_chat" if real_mode else "auth_path_burst",
        "url": url,
        "requests": args.requests,
        "concurrency": args.concurrency,
        "wall_seconds": round(wall_s, 2),
        "requests_per_second": round(args.requests / wall_s, 2) if wall_s else 0,
        "ok_count": sum(1 for r in results if r["ok"]),
        "statuses": statuses,
        "latency_ms": {
            "p50": round(_percentile(latencies, 0.50), 1),
            "p95": round(_percentile(latencies, 0.95), 1),
            "p99": round(_percentile(latencies, 0.99), 1),
            "mean": round(statistics.fmean(latencies), 1) if latencies else 0,
            "max": round(max(latencies), 1) if latencies else 0,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default="https://agentnexlify-production.up.railway.app",
    )
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    summary = asyncio.run(_run(args))
    print(json.dumps(summary, indent=2))
    if args.output:
        Path(args.output).write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Gate: p95 under 1s and >=95% expected responses (rubric 5.1 bar).
    passed = summary["latency_ms"]["p95"] < 1000 and (
        summary["ok_count"] >= 0.95 * summary["requests"]
    )
    print(f"GATE: {'PASS' if passed else 'FAIL'} (p95<1000ms and >=95% expected statuses)")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
