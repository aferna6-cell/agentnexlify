"""In-memory rate limiter for Zapier API keys.

Per-process counter keyed on `key_prefix:minute_bucket`. Effective limit is
`limit_per_minute * num_workers` system-wide (4 workers in production = 4x).
Acceptable for B2B Zapier polling (low abuse risk, typical poll rate is
1 rpm). Trivial to swap to a distributed backend (Redis) later — same
public surface.

Issue: #58 — substituted in-memory for Redis-based per spec discussion
(Redis not yet in stack; user-approved 2026-04-28).

Fail-open: any internal error returns (allowed=True, count=0) and logs warn.
Outage of the limiter must not block paying tenants' Zapier integrations.
"""

import logging
import threading
import time

logger = logging.getLogger(__name__)


_BUCKETS: dict[str, dict[int, int]] = {}
_LOCK = threading.Lock()
_GC_KEEP_BUCKETS = 2  # keep current + previous bucket only


def check_and_increment(key_prefix: str, limit_per_minute: int = 100) -> tuple[bool, int]:
    """Increment counter for the current minute bucket and return (allowed, count).

    `allowed` is True when count <= limit_per_minute, False when over.
    `count` is the post-increment count for the current bucket.

    Fail-open on any exception: returns (True, 0) and logs warn.
    """
    try:
        bucket = int(time.time() // 60)
        with _LOCK:
            buckets = _BUCKETS.setdefault(key_prefix, {})
            # GC: drop buckets older than (current - _GC_KEEP_BUCKETS)
            cutoff = bucket - _GC_KEEP_BUCKETS
            stale = [b for b in buckets if b < cutoff]
            for b in stale:
                del buckets[b]

            count = buckets.get(bucket, 0) + 1
            buckets[bucket] = count
            return count <= limit_per_minute, count
    except Exception:
        logger.warning("Rate limit check failed; failing open", exc_info=True)
        return True, 0


def reset_for_tests() -> None:
    """Test helper — clear all buckets. Do not call in production code."""
    with _LOCK:
        _BUCKETS.clear()
