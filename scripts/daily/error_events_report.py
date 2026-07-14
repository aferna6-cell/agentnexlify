#!/usr/bin/env python3
"""Deterministic prod-error report for the morning digest.

Reads the ``error_events`` table (the sink main.py's global 500-handler
writes to — it root-caused GH #422 in minutes after two code-reading passes
couldn't) and prints a compact key=value block that health-check.sh captures
and the morning digest surfaces verbatim.

Why deterministic: a silent prod 500 today is only discovered when a customer
hits it. This makes every unhandled exception show up in tomorrow's digest
with zero LLM involvement.

Output contract (stable, machine-greppable):
    error_events_24h=<int>
    error_events_top_paths=<path>:<count>[, ...]   (top 3)
    error_events_latest=<ISO time> <path> <first 120 chars of message>
    error_events=UNAVAILABLE (<reason>)            (creds missing / query failed)

Usage: python scripts/daily/error_events_report.py  [exit 0 always]
"""

import os
import sys
from collections import Counter

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


def main() -> int:
    try:
        from backend.models.database import get_service_supabase
    except Exception as exc:  # backend deps not installed on this machine
        print(f"error_events=UNAVAILABLE (import failed: {type(exc).__name__})")
        return 0

    try:
        from datetime import datetime, timedelta, timezone

        since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        rows = (
            get_service_supabase()
            .table("error_events")
            .select("created_at, path, message, status_code")
            .gte("created_at", since)
            .order("created_at", desc=True)
            .limit(500)
            .execute()
        ).data or []
    except Exception as exc:
        print(f"error_events=UNAVAILABLE (query failed: {type(exc).__name__})")
        return 0

    print(f"error_events_24h={len(rows)}")
    if not rows:
        return 0

    top = Counter((r.get("path") or "?") for r in rows).most_common(3)
    print(
        "error_events_top_paths="
        + ", ".join(f"{path}:{count}" for path, count in top)
    )
    newest = rows[0]
    message = (newest.get("message") or "").replace("\n", " ")[:120]
    print(
        f"error_events_latest={newest.get('created_at')} "
        f"{newest.get('path')} {message}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
