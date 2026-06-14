"""Pricing A/B experiment readout (rubric 9.3 follow-through).

Usage:
    python ops/evals/run_pricing_ab_report.py [--days 30] [--json]

Reads pricing_ab_events and reports, per variant: unique visitors who viewed
the pricing section, unique visitors who clicked a CTA, and the view -> click
conversion rate. Read-only.

Interpretation guardrails printed with the report: don't call a winner under
~100 views per variant, and remember variant assignment is deterministic per
visitor (sha256), so returning visitors don't switch arms.
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


def build_report(rows: list[dict]) -> dict:
    per_variant: dict[str, dict[str, set]] = defaultdict(lambda: {"view": set(), "cta_click": set()})
    for row in rows:
        variant = row.get("variant") or "unknown"
        event = row.get("event")
        visitor = row.get("visitor_id")
        if event in ("view", "cta_click") and visitor:
            per_variant[variant][event].add(visitor)

    report = {}
    for variant, events in sorted(per_variant.items()):
        views = len(events["view"])
        clicks = len(events["cta_click"] & events["view"]) or len(events["cta_click"])
        report[variant] = {
            "unique_viewers": views,
            "unique_clickers": clicks,
            "conversion_pct": round(100.0 * clicks / views, 2) if views else None,
            "sample_warning": views < 100,
        }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    from backend.models.database import get_service_supabase

    db = get_service_supabase()
    since = (datetime.now(timezone.utc) - timedelta(days=args.days)).isoformat()
    result = (
        db.table("pricing_ab_events")
        .select("visitor_id, variant, event")
        .gte("created_at", since)
        .limit(10000)
        .execute()
    )
    report = build_report(result.data or [])

    if args.json:
        print(json.dumps({"days": args.days, "variants": report}, indent=2))
        return 0

    print(f"Pricing A/B report — last {args.days} days (experiment pricing_page_cta_2026_06)")
    if not report:
        print("  No events yet.")
        return 0
    for variant, stats in report.items():
        conv = f"{stats['conversion_pct']}%" if stats["conversion_pct"] is not None else "n/a"
        warn = "  [LOW SAMPLE <100 views — do not call a winner]" if stats["sample_warning"] else ""
        print(
            f"  {variant:<10} viewers={stats['unique_viewers']:<6} "
            f"cta_clicks={stats['unique_clickers']:<6} conversion={conv}{warn}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
