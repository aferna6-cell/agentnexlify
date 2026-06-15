"""Per-tenant usage metering for Agent OS.

One os_tenant_usage row per client per billing cycle (calendar month). The
turn entry points check the agent-run cap before scheduling a run; counters
are incremented as messages are posted and agent runs complete.

Caps are plan-tier aware: ``tenants.plan`` resolves through PLAN_AGENT_RUN_CAPS
(two purchasable plans: chatbot / agent_os; free = lapsed state).
Unknown or unreadable plans fall back to DEFAULT_AGENT_RUN_CAP.
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone

from backend.services.tenant_scope import tenant_select, tenant_table

logger = logging.getLogger(__name__)

DEFAULT_AGENT_RUN_CAP = 100

# Monthly agent-run allowance by plan tier (2026-06-15 repricing).
# free     = lapsed/no-active-subscription state — minimal cap.
# chatbot  = widget/chatbot features only.
# agent_os = full platform (Agent OS + marketing + everything).
PLAN_AGENT_RUN_CAPS = {
    "free": 25,
    "chatbot": 100,
    "agent_os": 2000,
}


def plan_cap(db, client_id: str) -> int:
    """Resolve the tenant's monthly agent-run cap from its plan.

    Read failures fall back to DEFAULT_AGENT_RUN_CAP so metering can never
    take down a turn.
    """
    try:
        resp = (
            db.table("tenants")
            .select("plan")
            .eq("id", client_id)
            .limit(1)
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        plan = (rows[0].get("plan") or "").lower() if rows else ""
        return PLAN_AGENT_RUN_CAPS.get(plan, DEFAULT_AGENT_RUN_CAP)
    except Exception:
        logger.warning("usage_meter: plan lookup failed; using default cap", exc_info=True)
        return DEFAULT_AGENT_RUN_CAP


@dataclass
class UsageSnapshot:
    cycle_start: str
    agent_runs: int
    messages: int
    input_tokens: int
    output_tokens: int
    cap: int

    @property
    def cap_reached(self) -> bool:
        return self.agent_runs >= self.cap


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def current_cycle_start() -> str:
    """First day of the current calendar month, ISO date."""
    today = date.today()
    return date(today.year, today.month, 1).isoformat()


def _fetch_or_create(db, client_id: str) -> dict:
    cycle = current_cycle_start()
    existing = (
        tenant_select(db, "os_tenant_usage", client_id, "*")
        .eq("cycle_start", cycle)
        .limit(1)
        .execute()
    )
    if existing.data:
        return existing.data[0]
    created = (
        tenant_table(db, "os_tenant_usage", client_id)
        .insert({"cycle_start": cycle})
        .execute()
    )
    return created.data[0]


def get_usage(db, client_id: str) -> UsageSnapshot:
    row = _fetch_or_create(db, client_id)
    return UsageSnapshot(
        cycle_start=str(row["cycle_start"]),
        agent_runs=row.get("agent_runs", 0) or 0,
        messages=row.get("messages", 0) or 0,
        input_tokens=row.get("input_tokens", 0) or 0,
        output_tokens=row.get("output_tokens", 0) or 0,
        cap=plan_cap(db, client_id),
    )


def cap_reached(db, client_id: str) -> bool:
    return get_usage(db, client_id).cap_reached


def record_message(db, client_id: str) -> None:
    row = _fetch_or_create(db, client_id)
    tenant_table(db, "os_tenant_usage", client_id).update(
        {"messages": (row.get("messages", 0) or 0) + 1, "updated_at": _now()}
    ).eq("cycle_start", row["cycle_start"]).execute()


def record_agent_run(
    db, client_id: str, input_tokens: int = 0, output_tokens: int = 0
) -> None:
    row = _fetch_or_create(db, client_id)
    tenant_table(db, "os_tenant_usage", client_id).update(
        {
            "agent_runs": (row.get("agent_runs", 0) or 0) + 1,
            "input_tokens": (row.get("input_tokens", 0) or 0) + input_tokens,
            "output_tokens": (row.get("output_tokens", 0) or 0) + output_tokens,
            "updated_at": _now(),
        }
    ).eq("cycle_start", row["cycle_start"]).execute()
