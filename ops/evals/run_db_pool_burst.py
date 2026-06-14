"""DB connection-pool burst check (launch rubric 5.2).

Bursts concurrent requests at /api/health — which performs a real Supabase
(PostgREST) round-trip per request — to prove the per-process httpx pool and
Supabase-side pooling hold up under concurrency well above normal load.

Stdlib only so it runs anywhere:

    python3 ops/evals/run_db_pool_burst.py [--requests 150] [--concurrency 25]

Exit 1 if error rate > 1% or p95 > 2000 ms (cold-start tolerant gate; the
health path includes a real DB query, not a static response).
"""

import argparse
import json
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.request import urlopen

DEFAULT_URL = "https://agentnexlify-production.up.railway.app/api/health"
P95_GATE_MS = 2000.0
ERROR_RATE_GATE = 0.01


def _one(url: str, timeout: float) -> tuple[bool, float]:
    start = time.perf_counter()
    try:
        with urlopen(url, timeout=timeout) as resp:  # noqa: S310 - operator-owned endpoint
            body = json.loads(resp.read())
        ok = resp.status == 200 and body.get("checks", {}).get("supabase") == "connected"
    except Exception:
        ok = False
    return ok, (time.perf_counter() - start) * 1000.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--requests", type=int, default=150)
    parser.add_argument("--concurrency", type=int, default=25)
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()

    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        results = list(pool.map(lambda _: _one(args.url, args.timeout), range(args.requests)))

    latencies = sorted(ms for _, ms in results)
    failures = sum(1 for ok, _ in results if not ok)
    error_rate = failures / len(results)
    p50 = statistics.median(latencies)
    p95 = latencies[max(0, int(len(latencies) * 0.95) - 1)]

    summary = {
        "url": args.url,
        "requests": args.requests,
        "concurrency": args.concurrency,
        "failures": failures,
        "error_rate": round(error_rate, 4),
        "p50_ms": round(p50, 1),
        "p95_ms": round(p95, 1),
        "max_ms": round(latencies[-1], 1),
        "gate": {"p95_ms": P95_GATE_MS, "error_rate": ERROR_RATE_GATE},
    }
    passed = error_rate <= ERROR_RATE_GATE and p95 <= P95_GATE_MS
    summary["result"] = "PASS" if passed else "FAIL"
    print(json.dumps(summary, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
