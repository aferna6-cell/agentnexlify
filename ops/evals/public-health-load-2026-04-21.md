# Public Health Load Burst - 2026-04-21

**Script:** `ops/evals/run_public_health_load.py`  
**Target:** `https://agentnexlify-production.up.railway.app/api/health`

## Summary

Ran a simple burst test against the public backend health endpoint to establish a dated latency baseline.

This is not a full widget/chat load test. It is a lightweight external availability and latency check that proves the public backend can absorb a short burst cleanly.

## Result

```json
{
  "url": "https://agentnexlify-production.up.railway.app/api/health",
  "total_requests": 100,
  "concurrency": 10,
  "success_count": 100,
  "failure_count": 0,
  "success_rate": 100.0,
  "avg_latency_ms": 161.0,
  "p50_latency_ms": 138.4,
  "p95_latency_ms": 291.2,
  "max_latency_ms": 507.0,
  "min_latency_ms": 60.0,
  "status_counts": {
    "200": 100
  }
}
```

## Interpretation

- Public health endpoint handled 100/100 requests successfully.
- p95 stayed under 300 ms for this burst.
- This improves confidence in the public backend path, but it does **not** replace a widget/chat or authenticated flow load test.

## Next Step

Run a tenant-safe widget/chat burst next, using a disposable widget API key and Railway HTTP logs for deeper path latency analysis.
