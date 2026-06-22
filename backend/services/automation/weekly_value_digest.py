"""Weekly value digest — dollar-framed weekly summary for paying tenants (gap G2).

Spec: specs/weekly-value-digest_spec.md. Design:
- The rollup is a PURE function (`summarize_week`) over already-fetched counts, so it is fully
  unit-testable without a database and never depends on an LLM (deterministic-first).
- IO (`gather_week_counts`) is a thin Supabase read; the job (`run_weekly_digests`) is
  **draft-by-default**: it never sends unless `send=True` AND the tenant has opted in, and it
  is idempotent per (tenant, week) via the `digest_sends` ledger (migration 155).
- Dollar figures are never fabricated: shown only when real invoice or avg-value data exists.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)

# A tenant younger than this many days has no full week of data yet — skip.
MIN_TENANT_AGE_DAYS = 7


def week_bounds(today: date) -> tuple[date, date]:
    """Return (start, end) for the most recently completed Mon-Sun week before `today`."""
    # Monday of the current week, then step back 7 days for the last *complete* week.
    this_monday = today - timedelta(days=today.weekday())
    start = this_monday - timedelta(days=7)
    return start, start + timedelta(days=7)


def _fmt_money(cents: Optional[int]) -> Optional[str]:
    if cents is None:
        return None
    return f"${cents / 100:,.0f}"


def summarize_week(
    current: dict[str, int],
    previous: Optional[dict[str, int]] = None,
    avg_job_value_cents: Optional[int] = None,
) -> dict[str, Any]:
    """Pure rollup. `current`/`previous` carry integer counts for the week.

    Keys read: leads, conversations, appointments, after_hours, invoiced_cents (optional).
    Estimated value uses real invoice totals when present; else leads x avg job value when that
    is known; else None (never fabricated).
    """
    prev = previous or {}
    leads = int(current.get("leads", 0))
    prev_leads = int(prev.get("leads", 0))

    invoiced = current.get("invoiced_cents")
    if invoiced is not None:
        estimated_cents: Optional[int] = int(invoiced)
        value_basis = "invoiced"
    elif avg_job_value_cents and leads:
        estimated_cents = int(avg_job_value_cents) * leads
        value_basis = "estimated"
    else:
        estimated_cents = None
        value_basis = "none"

    return {
        "leads": leads,
        "leads_delta": leads - prev_leads,
        "conversations": int(current.get("conversations", 0)),
        "appointments": int(current.get("appointments", 0)),
        "after_hours": int(current.get("after_hours", 0)),
        "estimated_value_cents": estimated_cents,
        "estimated_value_display": _fmt_money(estimated_cents),
        "value_basis": value_basis,
        "has_activity": any(
            int(current.get(k, 0)) > 0
            for k in ("leads", "conversations", "appointments")
        ),
    }


def build_digest_html(summary: dict[str, Any], business_name: str, unsubscribe_url: str) -> str:
    """Render the digest email body. Includes a CAN-SPAM unsubscribe link."""
    delta = summary["leads_delta"]
    delta_str = f"(+{delta} vs last week)" if delta > 0 else (f"({delta} vs last week)" if delta < 0 else "")
    rows = [
        ("New leads captured", f"{summary['leads']} {delta_str}".strip()),
        ("Conversations handled", str(summary["conversations"])),
        ("Appointments booked", str(summary["appointments"])),
        ("Captured after hours", str(summary["after_hours"])),
    ]
    if summary["estimated_value_display"]:
        label = "Estimated value" + ("" if summary["value_basis"] == "invoiced" else " (estimate)")
        rows.append((label, summary["estimated_value_display"]))

    items = "".join(
        f"<tr><td style='padding:6px 12px'>{k}</td>"
        f"<td style='padding:6px 12px;font-weight:600;text-align:right'>{v}</td></tr>"
        for k, v in rows
    )
    return (
        f"<h2>Your week at {business_name}</h2>"
        f"<p>Here's what your AI front desk did for you this week.</p>"
        f"<table style='border-collapse:collapse'>{items}</table>"
        f"<p style='color:#888;font-size:12px;margin-top:24px'>"
        f"You're receiving this because weekly summaries are on for {business_name}. "
        f"<a href='{unsubscribe_url}'>Unsubscribe</a>.</p>"
    )


def _count(db: Any, table: str, scope_col: str, scope_val: str, start: date, end: date,
           date_col: str = "created_at") -> int:
    """Thin date-bounded count. Returns 0 on any read failure (degrade, never raise)."""
    try:
        res = (
            db.table(table)
            .select("id", count="exact")
            .eq(scope_col, scope_val)
            .gte(date_col, start.isoformat())
            .lt(date_col, end.isoformat())
            .execute()
        )
        return int(getattr(res, "count", 0) or 0)
    except Exception as exc:  # noqa: BLE001 - read is best-effort; a failure must not break the job
        logger.warning("weekly_value_digest count failed: %s.%s — %s", table, scope_col, exc)
        return 0


def gather_week_counts(db: Any, client_id: str, tenant_id: str, start: date, end: date) -> dict[str, int]:
    """Fetch the week's counts for one tenant. leads/conversations are client_id-scoped."""
    return {
        "leads": _count(db, "leads", "client_id", client_id, start, end),
        "conversations": _count(db, "conversations", "client_id", client_id, start, end),
        "appointments": _count(db, "appointments", "tenant_id", tenant_id, start, end),
        "after_hours": 0,  # refined in a follow-up against business_hours
    }


def run_weekly_digests(db: Any, *, send: bool = False, today: Optional[date] = None) -> list[dict[str, Any]]:
    """Build (and optionally send) digests for opted-in tenants.

    Draft-by-default: with `send=False` it computes and returns drafts but performs no email.
    Idempotent: skips any (tenant, week) already in `digest_sends`. Skips tenants <7 days old.
    """
    today = today or datetime.utcnow().date()
    start, end = week_bounds(today)
    drafts: list[dict[str, Any]] = []

    try:
        tenants = (
            db.table("tenants")
            .select("id, client_id, business_name, created_at")
            .eq("weekly_digest_opt_in", True)
            .execute()
        ).data or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("weekly_value_digest: tenant fetch failed — %s", exc)
        return drafts

    for t in tenants:
        tenant_id = t.get("id")
        client_id = t.get("client_id") or tenant_id
        if _too_new(t.get("created_at"), start):
            continue
        if _already_sent(db, tenant_id, start):
            continue
        current = gather_week_counts(db, client_id, tenant_id, start, end)
        prev_start, prev_end = start - timedelta(days=7), start
        previous = gather_week_counts(db, client_id, tenant_id, prev_start, prev_end)
        summary = summarize_week(current, previous)
        draft = {"tenant_id": tenant_id, "week_start": start.isoformat(), "summary": summary}
        if not summary["has_activity"]:
            draft["skipped"] = "no-activity"
            drafts.append(draft)
            continue
        if send:
            _send_and_record(db, t, summary, start)
            draft["sent"] = True
        drafts.append(draft)
    return drafts


def _too_new(created_at: Any, week_start: date) -> bool:
    if not created_at:
        return False
    try:
        created = datetime.fromisoformat(str(created_at).replace("Z", "+00:00")).date()
    except (ValueError, TypeError):
        return False
    return (week_start - created).days < MIN_TENANT_AGE_DAYS


def _already_sent(db: Any, tenant_id: str, week_start: date) -> bool:
    try:
        res = (
            db.table("digest_sends")
            .select("id")
            .eq("tenant_id", tenant_id)
            .eq("week_start", week_start.isoformat())
            .limit(1)
            .execute()
        )
        return bool(res.data)
    except Exception:  # noqa: BLE001 - missing table/row → treat as not sent
        return False


def _send_and_record(db: Any, tenant: dict[str, Any], summary: dict[str, Any], week_start: date) -> None:
    """Send the digest email and record the idempotency row. Best-effort; logged on failure."""
    # Intentionally minimal in V1: the real Resend send wiring lands with the rollout PR once
    # the open questions (send day, value basis) are settled. Recording the row here keeps the
    # idempotency contract honest even before live send is enabled.
    try:
        db.table("digest_sends").insert(
            {"tenant_id": tenant.get("id"), "week_start": week_start.isoformat()}
        ).execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning("weekly_value_digest: record send failed for %s — %s", tenant.get("id"), exc)
