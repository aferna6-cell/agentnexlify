#!/usr/bin/env python3
"""Loop-health scan for the daily business digest (zero LLM, two secrets).

The automation loops (draft expiry sweep, opportunity scan) now run
themselves; this scan proves they KEEP running. It mirrors the
prod-error-scan pattern in .github/workflows/daily-business-digest.yml:
query Supabase REST directly, print vitals to the job log every day, and
write loop-health-alert.md ONLY when something needs a human:

  ALERT 1 — sweep rot: a pending_approval draft older than 16 days on an
            active paid tenant. The expiry sweep clears these at 14 days;
            if one is older, the sweep is broken or skipping tenants it
            should cover.
  ALERT 2 — suggestion rot: the oldest pending opportunity suggestion is
            over 21 days old. Cards now surface in the dashboard and
            notify by email; three weeks undecided means the loop is not
            reaching the owner.

The GitHub-side step files one deduped issue per day when the alert file
exists — quiet days produce log lines, not issues.

Pure decision logic lives in evaluate_alerts() so tests can exercise it
without a network. Stdlib only: this runs in a bare Actions runner.
"""

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

# Sweep expires at 14 days; 2 days of grace for loop drift and deploys.
SWEEP_ROT_DAYS = 16
SUGGESTION_ROT_DAYS = 21
# >5 outbound-guard holds in a week smells like a false-positive pattern,
# not five real leak attempts — page a human to review the flag breakdown.
GUARD_HOLD_ALERT_THRESHOLD = 5
# Plans the expiry sweep covers (mirrors os_draft_expiry's tenant query:
# plan != 'free' AND plan_status = 'active').
_FREE_PLAN = "free"


def parse_ts(value):
    """ISO timestamp -> aware datetime, or None."""
    if not value or not isinstance(value, str):
        return None
    try:
        ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def rest_fetch(base_url, key, table, params):
    """One PostgREST GET returning parsed rows."""
    query = urllib.parse.urlencode(params)
    req = urllib.request.Request(
        base_url.rstrip("/") + "/rest/v1/" + table + "?" + query,
        headers={"apikey": key, "Authorization": "Bearer " + key},
    )
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read())
    except Exception as exc:
        # Re-raise without chaining to avoid leaking request headers
        # (Authorization header with service key) in the traceback.
        raise RuntimeError(
            f"Supabase REST fetch failed for {table}: {type(exc).__name__}"
        ) from None


def collect_vitals(fetch):
    """Gather loop vitals via an injected fetch(table, params) callable."""
    drafts = fetch(
        "os_agent_runs",
        {
            "select": "client_id,deliverable_status,updated_at",
            "deliverable_status": "not.is.null",
            "limit": "1000",
        },
    )
    suggestions = fetch(
        "os_backlog_requests",
        {"select": "status,created_at", "limit": "1000"},
    )
    tenants = fetch(
        "tenants",
        {"select": "id,plan,plan_status,business_name", "limit": "1000"},
    )
    guard_events = fetch(
        "activity_log",
        {
            "select": "activity_type,created_at,metadata",
            "activity_type": (
                "in.(outbound_guard_flagged,kb_eval_regression,"
                "os_fast_path_data_answer,os_fast_path_chat_project,"
                "os_research_run,email_action_approve,email_action_reject,email_action_viewed)"
            ),
            "limit": "500",
        },
    )
    return {
        "drafts": drafts,
        "suggestions": suggestions,
        "tenants": tenants,
        "guard_events": guard_events,
    }


def evaluate_alerts(vitals, now):
    """Pure decision logic: vitals dict -> list of alert strings."""
    alerts = []

    # Blind-scan guard. A real deployment always has tenants; zero rows
    # means the key can't actually read prod (RLS row-filtering returns
    # empty silently — no error). First live run caught exactly this: the
    # Actions SUPABASE_SERVICE_KEY held the anon key, every digest job had
    # been reading nothing since the RLS lockdown, and the log looked
    # healthy. Silence must page, so this short-circuits the other rules
    # (their empty inputs would be meaningless).
    if not vitals.get("tenants"):
        return [
            "Loop-health scan is BLIND: the tenants query returned zero "
            "rows, which means the SUPABASE_SERVICE_KEY secret cannot read "
            "prod (RLS row-filtering — this is what the anon key looks "
            "like). Rotate the GitHub Actions secret to the service_role "
            "key; every daily-digest job shares it."
        ]

    tenants = {t.get("id"): t for t in vitals.get("tenants", [])}

    sweep_cutoff = now - timedelta(days=SWEEP_ROT_DAYS)
    rotting = []
    for row in vitals.get("drafts", []):
        if row.get("deliverable_status") != "pending_approval":
            continue
        ts = parse_ts(row.get("updated_at"))
        if ts is None or ts >= sweep_cutoff:
            continue
        tenant = tenants.get(row.get("client_id")) or {}
        plan = (tenant.get("plan") or _FREE_PLAN).lower()
        if plan == _FREE_PLAN or tenant.get("plan_status") != "active":
            # The sweep deliberately skips lapsed/free tenants.
            continue
        rotting.append((tenant.get("business_name") or row.get("client_id"), ts))
    if rotting:
        oldest = min(ts for _, ts in rotting)
        age = (now - oldest).days
        names = ", ".join(sorted({name for name, _ in rotting}))
        alerts.append(
            f"Expiry sweep is not clearing drafts: {len(rotting)} "
            f"pending_approval draft(s) older than {SWEEP_ROT_DAYS} days "
            f"(oldest {age}d) on active paid tenant(s): {names}."
        )

    suggestion_cutoff = now - timedelta(days=SUGGESTION_ROT_DAYS)
    stale = [
        parse_ts(row.get("created_at"))
        for row in vitals.get("suggestions", [])
        if row.get("status") == "pending"
    ]
    stale = [ts for ts in stale if ts is not None and ts < suggestion_cutoff]
    if stale:
        age = (now - min(stale)).days
        alerts.append(
            f"Opportunity suggestions are rotting undecided: {len(stale)} "
            f"pending card(s) older than {SUGGESTION_ROT_DAYS} days "
            f"(oldest {age}d). The notify + cards loop is not reaching owners."
        )

    # Week-one watch on the enterprise-audit guardrail + eval features.
    week_cutoff = now - timedelta(days=7)
    holds = 0
    regressions = 0
    for row in vitals.get("guard_events", []) or []:
        ts = parse_ts(row.get("created_at"))
        if ts is None or ts < week_cutoff:
            continue
        if row.get("activity_type") == "kb_eval_regression":
            regressions += 1
        elif row.get("activity_type") == "outbound_guard_flagged":
            # Explicit branch: the same query now also carries fast-path
            # adoption tags, which must never count as guard holds.
            holds += 1
    if regressions:
        alerts.append(
            f"Golden-question regressions: {regressions} in the last 7 days. "
            "A tenant's knowledge stopped answering a question it used to — "
            "check /api/v1/kb-evals/runs/latest for the affected tenant(s)."
        )
    if holds > GUARD_HOLD_ALERT_THRESHOLD:
        alerts.append(
            f"Outbound guard held {holds} auto-send draft(s) in the last 7 "
            f"days (threshold {GUARD_HOLD_ALERT_THRESHOLD}). Review the flag "
            "breakdown in /api/v1/admin/loop-health guardrails — a spike "
            "usually means a false-positive pattern needs tuning."
        )

    return alerts


def summarize(vitals):
    """One-line vitals for the job log (always printed)."""
    draft_counts = {}
    for row in vitals.get("drafts", []):
        status = row.get("deliverable_status") or "unknown"
        draft_counts[status] = draft_counts.get(status, 0) + 1
    suggestion_counts = {}
    for row in vitals.get("suggestions", []):
        status = row.get("status") or "unknown"
        suggestion_counts[status] = suggestion_counts.get(status, 0) + 1
    # Suite fast-path adoption (round 6): the daily job log answers "is
    # anyone using the fast paths?" without an extra dashboard visit.
    fast_path_counts = {}
    for row in vitals.get("guard_events", []) or []:
        kind = row.get("activity_type") or ""
        if kind.startswith(("os_fast_path", "os_research", "email_action")):
            fast_path_counts[kind] = fast_path_counts.get(kind, 0) + 1
    return (
        "loop_health drafts="
        + json.dumps(draft_counts, sort_keys=True)
        + " suggestions="
        + json.dumps(suggestion_counts, sort_keys=True)
        + " fast_paths="
        + json.dumps(fast_path_counts, sort_keys=True)
    )


def render_report(alerts, vitals, now):
    lines = [
        "## Agent OS loop health -- " + now.strftime("%Y-%m-%d"),
        "",
    ]
    for alert in alerts:
        lines.append("- " + alert)
    lines += [
        "",
        "### Vitals",
        "",
        "```",
        summarize(vitals),
        "```",
        "",
        "Full aggregates: `GET /api/v1/admin/loop-health` (admin secret).",
    ]
    return "\n".join(lines)


def main():
    base_url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not base_url or not key:
        print(
            "::warning::SUPABASE_URL or SUPABASE_SERVICE_KEY not set -- "
            "skipping loop-health scan"
        )
        return 0

    vitals = collect_vitals(
        lambda table, params: rest_fetch(base_url, key, table, params)
    )
    now = datetime.now(timezone.utc)
    print(summarize(vitals))

    alerts = evaluate_alerts(vitals, now)
    if not alerts:
        print("loop_health: no alerts")
        return 0

    report = render_report(alerts, vitals, now)
    with open("loop-health-alert.md", "w", encoding="utf-8") as handle:
        handle.write(report)
    print("loop_health: %d alert(s) written to loop-health-alert.md" % len(alerts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
