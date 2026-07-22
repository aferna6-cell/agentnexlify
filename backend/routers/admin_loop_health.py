"""Admin loop-health board — one endpoint for the automation-loop vitals.

Every operations review re-derived the same numbers with ad-hoc SQL against
prod: how many drafts are pending and how old, whether opportunity
suggestions are piling up undecided, whether the Agent OS is being used at
all, whether any tenant has an inbound bridge on, and whether errors are
accumulating. This endpoint computes those aggregates deterministically so
dashboards, digests, and future reviews read one JSON instead of hand-run
queries.

Protected by the platform admin secret (internal only, not tenant-facing),
same guard as admin_health. Each section is fault-isolated: a failing query
nulls that section and the endpoint still returns 200 — partial vitals beat
a 500.

Schema notes: os_agent_runs / os_backlog_requests / os_threads use
client_id; error_events is global. See .claude/rules/schema-discipline.md.
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Header, Request

from backend.limiter import limiter
from backend.models.database import get_service_supabase
from backend.routers.admin_health import _parse_ts, _verify_admin_secret

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["platform-admin"])

_RECENT_DAYS = 7
_FILED_HOURS = 24


def _age_days(ts: datetime | None, now: datetime) -> float | None:
    if ts is None:
        return None
    return round((now - ts).total_seconds() / 86400, 1)


def _deliverables_section(db, now: datetime) -> dict | None:
    """Status counts, oldest pending age, and expiries in the last 7 days."""
    try:
        rows = (
            db.table("os_agent_runs")
            .select("deliverable_status, updated_at")
            .filter("deliverable_status", "not.is", "null")
            .execute()
        ).data or []
    except Exception:
        logger.warning("loop-health: deliverables query failed", exc_info=True)
        return None

    by_status: dict[str, int] = {}
    oldest_pending: datetime | None = None
    expired_7d = 0
    recent_cutoff = now - timedelta(days=_RECENT_DAYS)
    for row in rows:
        status = row.get("deliverable_status") or "unknown"
        by_status[status] = by_status.get(status, 0) + 1
        ts = _parse_ts(row.get("updated_at"))
        if status == "pending_approval" and ts is not None:
            if oldest_pending is None or ts < oldest_pending:
                oldest_pending = ts
        if status == "expired" and ts is not None and ts >= recent_cutoff:
            expired_7d += 1

    return {
        "by_status": by_status,
        "pending_oldest_age_days": _age_days(oldest_pending, now),
        "expired_7d": expired_7d,
    }


def _suggestions_section(db, now: datetime) -> dict | None:
    """Backlog status counts, oldest pending age, and filing freshness."""
    try:
        rows = (
            db.table("os_backlog_requests")
            .select("status, created_at")
            .execute()
        ).data or []
    except Exception:
        logger.warning("loop-health: suggestions query failed", exc_info=True)
        return None

    by_status: dict[str, int] = {}
    oldest_pending: datetime | None = None
    last_filed: datetime | None = None
    filed_24h = 0
    filed_cutoff = now - timedelta(hours=_FILED_HOURS)
    for row in rows:
        status = row.get("status") or "unknown"
        by_status[status] = by_status.get(status, 0) + 1
        ts = _parse_ts(row.get("created_at"))
        if ts is None:
            continue
        if status == "pending" and (oldest_pending is None or ts < oldest_pending):
            oldest_pending = ts
        if last_filed is None or ts > last_filed:
            last_filed = ts
        if ts >= filed_cutoff:
            filed_24h += 1

    return {
        "by_status": by_status,
        "pending_oldest_age_days": _age_days(oldest_pending, now),
        "filed_24h": filed_24h,
        "last_filed_at": last_filed.isoformat() if last_filed else None,
    }


def _os_activity_section(db, now: datetime) -> dict | None:
    """Is anyone actually using the Agent OS? Threads + runs in 7 days."""
    cutoff = (now - timedelta(days=_RECENT_DAYS)).isoformat()
    try:
        threads = (
            db.table("os_threads")
            .select("id", count="exact")
            .gte("created_at", cutoff)
            .limit(1)
            .execute()
        )
        runs = (
            db.table("os_agent_runs")
            .select("id", count="exact")
            .gte("created_at", cutoff)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.warning("loop-health: os activity query failed", exc_info=True)
        return None
    return {
        "threads_7d": int(threads.count or 0),
        "runs_7d": int(runs.count or 0),
    }


def _bridges_section(db) -> dict | None:
    """How many tenants have at least one inbound bridge switched on."""
    try:
        rows = (
            db.table("tenant_integrations")
            .select("client_id, enabled, config_jsonb")
            .eq("provider", "os_inbound_bridges")
            .execute()
        ).data or []
    except Exception:
        logger.warning("loop-health: bridges query failed", exc_info=True)
        return None

    enabled_tenants = set()
    for row in rows:
        if not row.get("enabled", True):
            continue
        cfg = row.get("config_jsonb") or {}
        if any(
            bool(value)
            for key, value in cfg.items()
            if key.endswith("_enabled")
        ):
            enabled_tenants.add(row.get("client_id"))

    return {
        "tenants_configured": len(rows),
        "tenants_enabled": len(enabled_tenants),
    }


def _guardrails_section(db, now: datetime) -> dict | None:
    """7-day outbound-guard holds + eval regressions from activity_log.

    Week-one watching for the enterprise-audit guardrail + eval features:
    surfaces how often the outbound guard held a draft (with per-flag counts
    so false-positive patterns are visible) and how many golden-question
    regressions fired. Both ride the daily digest via this endpoint.
    """
    cutoff = (now - timedelta(days=_RECENT_DAYS)).isoformat()
    try:
        rows = (
            db.table("activity_log")
            .select("activity_type, metadata")
            .in_("activity_type", ["outbound_guard_flagged", "kb_eval_regression"])
            .gte("created_at", cutoff)
            .limit(500)
            .execute()
        ).data or []
    except Exception:
        logger.warning("loop-health: guardrails query failed", exc_info=True)
        return None

    guard_holds = 0
    flag_counts: dict[str, int] = {}
    eval_regressions = 0
    for row in rows:
        if row.get("activity_type") == "outbound_guard_flagged":
            guard_holds += 1
            meta = row.get("metadata") or {}
            for flag in meta.get("flags") or []:
                flag_counts[str(flag)] = flag_counts.get(str(flag), 0) + 1
        else:
            eval_regressions += 1
    return {
        "outbound_guard_holds_7d": guard_holds,
        "guard_flag_counts": flag_counts,
        "kb_eval_regressions_7d": eval_regressions,
    }


def _routing_quality_section(db, now: datetime) -> dict | None:
    """7-day orchestrator routing quality (round-6 item 4).

    os_routing_decision gives free ground truth: `accepted=false` marks a
    decision the owner re-routed (a misroute), `owner_override` rows are the
    corrected re-runs, and `ambiguous` decisions are clarify prompts. Turns
    "does the orchestrator route well?" into tracked rates.
    """
    cutoff = (now - timedelta(days=_RECENT_DAYS)).isoformat()
    try:
        rows = (
            db.table("os_routing_decision")
            .select("decision, accepted")
            .gte("created_at", cutoff)
            .limit(2000)
            .execute()
        ).data or []
    except Exception:
        logger.warning("loop-health: routing query failed", exc_info=True)
        return None
    total = len(rows)
    routed = sum(1 for r in rows if r.get("decision") == "routed")
    ambiguous = sum(1 for r in rows if r.get("decision") == "ambiguous")
    overrides = sum(1 for r in rows if r.get("decision") == "owner_override")
    misroutes = sum(1 for r in rows if r.get("accepted") is False)
    return {
        "decisions_7d": total,
        "routed_7d": routed,
        "ambiguous_7d": ambiguous,
        "owner_overrides_7d": overrides,
        "misroutes_7d": misroutes,
        "misroute_rate_pct": round(misroutes * 100 / routed, 1) if routed else 0.0,
        "clarify_rate_pct": round(ambiguous * 100 / total, 1) if total else 0.0,
    }


_FAST_PATH_TYPES = [
    "os_fast_path_data_answer",
    "os_fast_path_chat_project",
    "os_research_run",
    "email_action_approve",
    "email_action_reject",
]


def _fast_paths_section(db, now: datetime) -> dict | None:
    """7-day adoption counts for the suite fast paths (round-5 item 6).

    Answers "is anyone using this?" with data instead of guesses: chat BI
    answers, chat-queued projects, research briefs, and email one-click
    approvals, each tagged in activity_log at the moment they fire.
    """
    cutoff = (now - timedelta(days=_RECENT_DAYS)).isoformat()
    try:
        rows = (
            db.table("activity_log")
            .select("activity_type")
            .in_("activity_type", _FAST_PATH_TYPES)
            .gte("created_at", cutoff)
            .limit(2000)
            .execute()
        ).data or []
    except Exception:
        logger.warning("loop-health: fast-paths query failed", exc_info=True)
        return None
    counts = {t: 0 for t in _FAST_PATH_TYPES}
    for row in rows:
        t = row.get("activity_type")
        if t in counts:
            counts[t] += 1
    return counts


def _errors_section(db, now: datetime) -> int | None:
    cutoff = (now - timedelta(days=_RECENT_DAYS)).isoformat()
    try:
        result = (
            db.table("error_events")
            .select("id", count="exact")
            .gte("created_at", cutoff)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.warning("loop-health: errors query failed", exc_info=True)
        return None
    return int(result.count or 0)


@router.get("/loop-health")
@limiter.limit("10/minute")
async def get_loop_health(
    request: Request,
    x_api_secret: str | None = Header(None),
):
    """Automation-loop vitals in one payload.

    Sections: deliverables (draft statuses + rot), suggestions (backlog
    statuses + filing freshness), os_activity (7-day usage), bridges
    (inbound adoption), errors_7d. A section is null when its query
    failed — the rest still comes back.
    """
    _verify_admin_secret(x_api_secret)

    now = datetime.now(timezone.utc)
    db = get_service_supabase()

    return {
        "generated_at": now.isoformat(),
        "deliverables": _deliverables_section(db, now),
        "suggestions": _suggestions_section(db, now),
        "os_activity": _os_activity_section(db, now),
        "bridges": _bridges_section(db),
        "guardrails": _guardrails_section(db, now),
        "fast_paths_7d": _fast_paths_section(db, now),
        "routing_quality": _routing_quality_section(db, now),
        "errors_7d": _errors_section(db, now),
    }
