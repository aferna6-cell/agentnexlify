"""Billing reconciliation — compare local usage counters against plan caps.

Usage counters tracked locally:
    - tenants.conversations_used_this_month  (widget chat turns)
    - os_tenant_usage.agent_runs             (Agent OS runs, per-cycle row)
    - tenant_ai_usage_monthly.total_tokens   (AI token spend, via ai_usage_guard)

Plan caps come from:
    - usage_meter.PLAN_AGENT_RUN_CAPS        (agent-run limits per plan)
    - ai_usage_guard.PLAN_BASELINE_TOKENS    (AI token baselines; hard limit = 5x)

Public API
----------
    reconcile_tenant_usage(db, tenant_id) -> dict
    reconcile_all(db) -> list[dict]

Each result dict has the shape defined by _Result (see below).

Intended for cron/manual use via ops/evals/run_usage_reconciliation.py.
No writes are made — read-only audit pass.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


# ── plan-cap tables (mirrors usage_meter + ai_usage_guard) ──────────────────

_PLAN_AGENT_RUN_CAPS: dict[str, int] = {
    "free": 25,
    "growth": 200,
    "autopilot": 500,
    "professional": 1500,
    "enterprise": 10000,
}
_DEFAULT_AGENT_RUN_CAP = 100

_PLAN_BASELINE_AI_TOKENS: dict[str, int] = {
    "free": 150_000,
    # New two-plan model (2026-06-15) — mirrors the canonical
    # ai_usage_guard.PLAN_BASELINE_TOKENS so audit reports match enforcement.
    "chatbot": 800_000,
    "agent_os": 5_000_000,
    "agent_os_managed": 8_000_000,
    # Legacy plans (grandfathered tenants on old contracts). Since 2026-07-22
    # ai_usage_guard.PLAN_BASELINE_TOKENS enforces these same values - before
    # that, enforcement silently used the chatbot default for legacy plans.
    "growth": 1_000_000,
    "autopilot": 1_200_000,
    "professional": 2_000_000,
    "enterprise": 5_000_000,
}
_DEFAULT_BASELINE_AI_TOKENS = _PLAN_BASELINE_AI_TOKENS["growth"]
# Agent-run caps for chatbot/agent_os are intentionally absent: the two-plan
# model doesn't cap agent runs the same way, so new plans use
# _DEFAULT_AGENT_RUN_CAP pending a product decision (GH #293).
_HARD_LIMIT_MULTIPLIER = 5

# conversations_used_this_month: plan no longer has a hard cap (migration 013
# removed limits), so we treat None as unlimited.  Flag over-cap only when a
# custom monthly_conversation_limit is set on the tenant row.
_UNLIMITED_CONV = None


# ── internal result dataclass ────────────────────────────────────────────────


@dataclass
class ReconciliationResult:
    tenant_id: str
    plan: str
    period_month: str

    # conversations
    conversations_used: int = 0
    conversations_cap: int | None = None  # None = unlimited
    conversations_over_cap: bool = False
    conversations_drift_pct: float | None = None

    # agent runs
    agent_runs_used: int = 0
    agent_runs_cap: int = 0
    agent_runs_over_cap: bool = False
    agent_runs_drift_pct: float = 0.0

    # AI tokens
    ai_tokens_used: int = 0
    ai_tokens_hard_limit: int = 0
    ai_tokens_over_cap: bool = False
    ai_tokens_drift_pct: float = 0.0

    # overall
    any_over_cap: bool = False
    error: str | None = None


def _to_dict(r: ReconciliationResult) -> dict:
    return {
        "tenant_id": r.tenant_id,
        "plan": r.plan,
        "period_month": r.period_month,
        "conversations": {
            "used": r.conversations_used,
            "cap": r.conversations_cap,
            "over_cap": r.conversations_over_cap,
            "drift_pct": r.conversations_drift_pct,
        },
        "agent_runs": {
            "used": r.agent_runs_used,
            "cap": r.agent_runs_cap,
            "over_cap": r.agent_runs_over_cap,
            "drift_pct": r.agent_runs_drift_pct,
        },
        "ai_tokens": {
            "used": r.ai_tokens_used,
            "hard_limit": r.ai_tokens_hard_limit,
            "over_cap": r.ai_tokens_over_cap,
            "drift_pct": r.ai_tokens_drift_pct,
        },
        "any_over_cap": r.any_over_cap,
        "error": r.error,
    }


# ── helpers ──────────────────────────────────────────────────────────────────


def _current_cycle() -> tuple[str, str]:
    """Return (period_month ISO str, cycle_start ISO date str)."""
    now = datetime.now(timezone.utc)
    first = date(now.year, now.month, 1)
    return first.isoformat(), first.isoformat()


def _drift_pct(used: int, cap: int) -> float:
    if cap <= 0:
        return 0.0
    return round((used / cap) * 100, 2)


def _agent_run_cap(plan: str) -> int:
    return _PLAN_AGENT_RUN_CAPS.get(plan.lower(), _DEFAULT_AGENT_RUN_CAP)


def _ai_token_hard_limit(tenant: dict) -> int:
    """Resolve AI token hard limit from tenant overrides or plan baseline."""
    plan = str(tenant.get("plan") or "free").lower()
    baseline = _PLAN_BASELINE_AI_TOKENS.get(plan, _DEFAULT_BASELINE_AI_TOKENS)
    default_hard = baseline * _HARD_LIMIT_MULTIPLIER
    override = tenant.get("ai_monthly_token_hard_limit")
    if isinstance(override, int) and override > 0:
        return override
    return default_hard


# ── core reconciliation ───────────────────────────────────────────────────────


def reconcile_tenant_usage(db, tenant_id: str) -> dict:
    """Reconcile usage counters for a single tenant.

    Parameters
    ----------
    db:
        Supabase client (service role).
    tenant_id:
        UUID of the tenant to check.

    Returns
    -------
    dict with keys: tenant_id, plan, period_month, conversations, agent_runs,
    ai_tokens, any_over_cap, error.
    """
    period_month, cycle_start = _current_cycle()
    result = ReconciliationResult(
        tenant_id=tenant_id,
        plan="unknown",
        period_month=period_month,
    )

    # ── load tenant row ──────────────────────────────────────────────────────
    try:
        resp = (
            db.table("tenants")
            .select(
                "id, plan, conversations_used_this_month, monthly_conversation_limit, "
                "ai_monthly_token_hard_limit"
            )
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        if not rows:
            result.error = "tenant_not_found"
            return _to_dict(result)
        tenant = rows[0]
    except Exception:
        logger.exception("reconcile_tenant_usage: DB error loading tenant %s", tenant_id)
        result.error = "db_error_tenant"
        return _to_dict(result)

    plan = str(tenant.get("plan") or "free").lower()
    result.plan = plan

    # ── conversations ────────────────────────────────────────────────────────
    conv_used = int(tenant.get("conversations_used_this_month") or 0)
    conv_cap = tenant.get("monthly_conversation_limit")
    if isinstance(conv_cap, int) and conv_cap > 0:
        result.conversations_cap = conv_cap
        result.conversations_over_cap = conv_used > conv_cap
        result.conversations_drift_pct = _drift_pct(conv_used, conv_cap)
    else:
        result.conversations_cap = None  # unlimited
        result.conversations_over_cap = False
        result.conversations_drift_pct = None
    result.conversations_used = conv_used

    # ── agent runs ───────────────────────────────────────────────────────────
    agent_cap = _agent_run_cap(plan)
    result.agent_runs_cap = agent_cap
    try:
        usage_resp = (
            db.table("os_tenant_usage")
            .select("agent_runs")
            .eq("client_id", tenant_id)
            .eq("cycle_start", cycle_start)
            .limit(1)
            .execute()
        )
        usage_rows = getattr(usage_resp, "data", None) or []
        agent_runs = int((usage_rows[0].get("agent_runs") or 0) if usage_rows else 0)
    except Exception:
        logger.warning(
            "reconcile_tenant_usage: could not read os_tenant_usage for %s", tenant_id,
            exc_info=True,
        )
        agent_runs = 0

    result.agent_runs_used = agent_runs
    result.agent_runs_over_cap = agent_runs > agent_cap
    result.agent_runs_drift_pct = _drift_pct(agent_runs, agent_cap)

    # ── AI tokens ────────────────────────────────────────────────────────────
    ai_hard = _ai_token_hard_limit(tenant)
    result.ai_tokens_hard_limit = ai_hard
    try:
        ai_resp = (
            db.table("tenant_ai_usage_monthly")
            .select("total_tokens")
            .eq("tenant_id", tenant_id)
            .eq("period_month", period_month)
            .limit(1)
            .execute()
        )
        ai_rows = getattr(ai_resp, "data", None) or []
        ai_tokens = int((ai_rows[0].get("total_tokens") or 0) if ai_rows else 0)
    except Exception:
        logger.warning(
            "reconcile_tenant_usage: could not read tenant_ai_usage_monthly for %s", tenant_id,
            exc_info=True,
        )
        ai_tokens = 0

    result.ai_tokens_used = ai_tokens
    result.ai_tokens_over_cap = ai_tokens > ai_hard
    result.ai_tokens_drift_pct = _drift_pct(ai_tokens, ai_hard)

    # ── overall ──────────────────────────────────────────────────────────────
    result.any_over_cap = (
        result.conversations_over_cap
        or result.agent_runs_over_cap
        or result.ai_tokens_over_cap
    )

    return _to_dict(result)


def reconcile_all(db) -> list[dict]:
    """Reconcile all tenants in the current billing cycle.

    Intended for cron use. Returns a list of result dicts (one per tenant).
    DB errors for individual tenants are captured in result["error"] rather
    than propagating — the loop always completes.
    """
    try:
        resp = db.table("tenants").select("id").execute()
        tenant_ids = [row["id"] for row in (getattr(resp, "data", None) or [])]
    except Exception:
        logger.exception("reconcile_all: failed to list tenants")
        return [{"error": "db_error_list_tenants"}]

    results = []
    for tid in tenant_ids:
        try:
            results.append(reconcile_tenant_usage(db, tid))
        except Exception:
            logger.exception("reconcile_all: unexpected error for tenant %s", tid)
            results.append({"tenant_id": tid, "error": "unexpected"})

    return results
