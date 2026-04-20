"""Measure MTOptions Phase 5 rollout metrics from Supabase.

The script reads credentials from the normal env/config path and does not
embed any secrets. It prints four rollout metrics:

1. Lead-field completion rate in the last 7 days
2. `lead_enriched` activity events in the last 24 hours
3. Widget chat / automation error events in the last 48 hours
4. Estimated monthly enrichment cost from the 24h enrichment rate

Usage:
    python scripts/mtoptions_phase5_measurement.py
    python scripts/mtoptions_phase5_measurement.py --tenant-id <uuid>

Environment:
    SUPABASE_URL
    SUPABASE_SERVICE_KEY
    MTOPTIONS_CLIENT_ID (optional, preferred if set)
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import os
from typing import Any

import httpx
from supabase import create_client
from supabase.lib.client_options import SyncClientOptions
from supabase_auth import SyncMemoryStorage

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MetricSnapshot:
    tenant_id: str
    tenant_label: str
    total_leads_7d: int
    complete_leads_7d: int
    lead_enriched_24h: int
    error_events_48h: int
    estimated_monthly_cost: float

    @property
    def completion_rate(self) -> float | None:
        if self.total_leads_7d == 0:
            return None
        return 100.0 * self.complete_leads_7d / self.total_leads_7d


def _fetch_rows(query: Any) -> list[dict[str, Any]]:
    result = query.execute()
    return list(result.data or [])


def _format_percent(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1f}%"


def _create_supabase_client(url: str, key: str) -> Any:
    options = SyncClientOptions(
        storage=SyncMemoryStorage(),
        httpx_client=httpx.Client(timeout=120.0),
    )
    return create_client(url, key, options)


def _resolve_tenant_id(db: Any, explicit_tenant_id: str | None) -> tuple[str, str]:
    if explicit_tenant_id:
        rows = _fetch_rows(
            db.table("tenants").select("id,business_name,plan,owner_email").eq(
                "id", explicit_tenant_id
            )
        )
        if not rows:
            raise SystemExit(f"No tenant found for id={explicit_tenant_id}")
        row = rows[0]
        label = " / ".join(
            str(part)
            for part in (
                row.get("business_name") or "MTOptions",
                row.get("plan") or "unknown-plan",
                row.get("owner_email") or "unknown-owner",
            )
        )
        return explicit_tenant_id, label

    candidates = []
    for field, value in (
        ("owner_email", "support@mtoptions.com"),
        ("business_name", "%MTOptions%"),
        ("business_slug", "mtoptions"),
    ):
        try:
            if field == "business_name":
                rows = _fetch_rows(
                    db.table("tenants")
                    .select("id,business_name,plan,owner_email")
                    .ilike(field, value)
                )
            else:
                rows = _fetch_rows(
                    db.table("tenants")
                    .select("id,business_name,plan,owner_email")
                    .eq(field, value)
                )
        except Exception as exc:  # pragma: no cover - query backend failure is surfaced in caller
            logger.warning("Lookup by %s failed: %s", field, exc)
            continue
        candidates.extend(rows)

    deduped: dict[str, dict[str, Any]] = {row["id"]: row for row in candidates if row.get("id")}
    if not deduped:
        raise SystemExit(
            "Could not resolve MTOptions automatically. Pass --tenant-id or set MTOPTIONS_CLIENT_ID."
        )
    if len(deduped) > 1:
        lines = []
        for row in deduped.values():
            lines.append(
                f"- {row.get('id')} | {row.get('business_name')} | {row.get('plan')} | {row.get('owner_email')}"
            )
        joined = "\n".join(lines)
        raise SystemExit(
            "MTOptions lookup is ambiguous. Pass --tenant-id or set MTOPTIONS_CLIENT_ID.\n"
            f"Candidates:\n{joined}"
        )

    row = next(iter(deduped.values()))
    label = " / ".join(
        str(part)
        for part in (
            row.get("business_name") or "MTOptions",
            row.get("plan") or "unknown-plan",
            row.get("owner_email") or "unknown-owner",
        )
    )
    return row["id"], label


def _build_snapshot(db: Any, tenant_id: str, tenant_label: str, *, enrichment_cost_per_event: float) -> MetricSnapshot:
    now = datetime.now(timezone.utc)
    since_7d = (now - timedelta(days=7)).isoformat()
    since_24h = (now - timedelta(hours=24)).isoformat()
    since_48h = (now - timedelta(hours=48)).isoformat()

    lead_rows = _fetch_rows(
        db.table("leads")
        .select("id,name,email,phone,created_at")
        .eq("client_id", tenant_id)
        .gte("created_at", since_7d)
    )
    total_leads_7d = len(lead_rows)
    complete_leads_7d = sum(
        1
        for row in lead_rows
        if row.get("name") and row.get("email") and row.get("phone")
    )

    enriched_rows = _fetch_rows(
        db.table("activity_log")
        .select("id,activity_type,tenant_id,created_at")
        .eq("tenant_id", tenant_id)
        .eq("activity_type", "lead_enriched")
        .gte("created_at", since_24h)
    )
    lead_enriched_24h = len(enriched_rows)

    error_rows = _fetch_rows(
        db.table("activity_log")
        .select("id,activity_type,tenant_id,created_at")
        .eq("tenant_id", tenant_id)
        .in_("activity_type", ["widget_chat_error", "automation_error"])
        .gte("created_at", since_48h)
    )
    error_events_48h = len(error_rows)

    estimated_monthly_cost = lead_enriched_24h * 30 * enrichment_cost_per_event

    return MetricSnapshot(
        tenant_id=tenant_id,
        tenant_label=tenant_label,
        total_leads_7d=total_leads_7d,
        complete_leads_7d=complete_leads_7d,
        lead_enriched_24h=lead_enriched_24h,
        error_events_48h=error_events_48h,
        estimated_monthly_cost=estimated_monthly_cost,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant-id", default=None, help="MTOptions tenant UUID to measure.")
    parser.add_argument(
        "--enrichment-cost-per-event",
        type=float,
        default=0.002,
        help="Estimated cost per enrichment call used for the monthly cost projection.",
    )
    args = parser.parse_args()

    supabase_url = os.environ.get("SUPABASE_URL", "").strip()
    supabase_service_key = os.environ.get("SUPABASE_SERVICE_KEY", "").strip()
    if not supabase_url or not supabase_service_key:
        logger.error(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY are required for live measurement."
        )
        return 1

    db = _create_supabase_client(supabase_url, supabase_service_key)
    explicit_tenant_id = args.tenant_id or os.environ.get("MTOPTIONS_CLIENT_ID")
    try:
        tenant_id, tenant_label = _resolve_tenant_id(db, explicit_tenant_id)
        snapshot = _build_snapshot(
            db,
            tenant_id,
            tenant_label,
            enrichment_cost_per_event=args.enrichment_cost_per_event,
        )
    except Exception as exc:
        logger.error("Measurement failed: %s", exc)
        return 1

    print(f"tenant_id: {snapshot.tenant_id}")
    print(f"tenant: {snapshot.tenant_label}")
    print(f"lead_field_completion_rate_7d: {_format_percent(snapshot.completion_rate)}")
    print(f"lead_enriched_events_24h: {snapshot.lead_enriched_24h}")
    print(f"widget_chat_error_events_48h: {snapshot.error_events_48h}")
    print(f"estimated_monthly_enrichment_cost: ${snapshot.estimated_monthly_cost:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
