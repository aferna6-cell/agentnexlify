"""Monthly Conversation Insights auto-run.

The ``conversation_insights`` agent (registered on the customer_service
department in agent-service) declares ``triggers_supported: ["manual",
"scheduled"]`` with a monthly cron hint. The engine only runs it on demand
today. This job dispatches it once per month per eligible tenant through the
same orchestration path the dashboard uses (``process_user_turn`` with
``force_agent_id``), so the resulting run + report land in os_agent_runs and
surface in the AI Workforce thread list automatically.

Cadence: the automation loop ticks every 60s and runs the 30-min tier often,
so monthly cadence is enforced inside this job: it no-ops unless today is the
first of the month, and a per-tenant ``activity_log`` dedup tag stops a second
dispatch within the same month even across worker restarts.

Eligibility: tenants on the ``agent_os`` plan (the tier that has the Agent OS
workforce). Per-tenant work is best-effort: one tenant failing never aborts
the batch, and the monthly cap gate is respected so the auto-run never pushes
a tenant past their plan's agent-run allowance.
"""

import logging
from datetime import datetime, timezone

from backend.models.database import get_service_supabase
from backend.services import agent_sdk_client, usage_meter
from backend.services.automation.trigger import BATCH_LIMIT
from backend.services.os_thread_runner import process_user_turn
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

# Exact agent_id as registered in agent-service
# (agent-service/src/agent-os/agents/conversation_insights/agent.ts).
CONVERSATION_INSIGHTS_AGENT_ID = "conversation_insights"

# Only this plan tier has the Agent OS workforce.
ELIGIBLE_PLAN = "agent_os"

# Thread title + owner-voiced prompt for the monthly run. The prompt is what
# the engine routes; the customer_service department maps these keywords to
# the conversation_insights skill, and force_agent_id pins it regardless.
_THREAD_TITLE = "Monthly conversation insights"
_RUN_PROMPT = (
    "Give me this month's conversation insights report: what customers asked "
    "most, common questions, capture rate, and chat trends."
)


def _month_tag(now: datetime) -> str:
    return f"conversation_insights_monthly_{now.strftime('%Y-%m')}"


def _already_ran_this_month(db, tenant_id: str, tag: str) -> bool:
    """True when a monthly insights run was already logged for this tenant.

    Fails closed (treats an errored check as "already ran") so a transient DB
    error never causes a duplicate dispatch + duplicate Claude spend.
    """
    try:
        existing = (
            db.table("activity_log")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .eq("activity_type", tag)
            .limit(1)
            .execute()
        )
        return bool(existing.count and existing.count > 0)
    except Exception:
        logger.warning(
            "conversation_insights_job: dedup check failed for tenant %s", tenant_id
        )
        return True


def _resolve_thread_id(db, client_id: str) -> str:
    """Find the monthly-insights thread for this tenant, or create one.

    Reusing one thread keeps every monthly report in a single timeline rather
    than spawning a new thread each month.
    """
    existing = (
        tenant_table(db, "os_threads", client_id)
        .select("id")
        .eq("title", _THREAD_TITLE)
        .limit(1)
        .execute()
    ).data or []
    if existing:
        return existing[0]["id"]
    created = (
        tenant_table(db, "os_threads", client_id)
        .insert({"title": _THREAD_TITLE})
        .execute()
    )
    return created.data[0]["id"]


async def _dispatch_for_tenant(db, client_id: str) -> bool:
    """Run one monthly conversation_insights turn for a tenant.

    Returns True when a run was dispatched. Respects the plan-tier monthly cap
    the same way the orchestrate endpoint does.
    """
    if usage_meter.cap_reached(db, client_id):
        logger.info(
            "conversation_insights_job: cap reached, skipping tenant %s", client_id
        )
        return False

    thread_id = _resolve_thread_id(db, client_id)
    user_message = (
        tenant_table(db, "os_messages", client_id)
        .insert({"thread_id": thread_id, "role": "user", "content": _RUN_PROMPT})
        .execute()
        .data[0]
    )
    usage_meter.record_message(db, client_id)

    await process_user_turn(
        db,
        client_id,
        thread_id,
        user_message,
        background_tasks=None,
        force_agent_id=CONVERSATION_INSIGHTS_AGENT_ID,
    )
    return True


async def run_monthly_conversation_insights() -> int:
    """Dispatch the conversation_insights agent once per month per eligible tenant.

    No-ops unless today is the first of the month and the engine is configured.
    Returns the count of tenants a run was dispatched for.
    """
    if not agent_sdk_client.is_configured():
        return 0

    now = datetime.now(timezone.utc)
    if now.day != 1:
        return 0

    tag = _month_tag(now)
    db = get_service_supabase()

    try:
        tenants = (
            db.table("tenants")
            .select("id, business_name, plan")
            .eq("plan", ELIGIBLE_PLAN)
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("conversation_insights_job: failed to query tenants")
        return 0

    dispatched = 0
    for tenant in tenants.data or []:
        tid = tenant.get("id")
        if not tid:
            continue
        if _already_ran_this_month(db, tid, tag):
            continue
        try:
            ran = await _dispatch_for_tenant(db, tid)
        except Exception:
            logger.exception(
                "conversation_insights_job: dispatch failed for tenant %s", tid
            )
            continue
        if not ran:
            continue

        dispatched += 1
        # Dedup marker — written only after a successful dispatch so a failed
        # turn retries next tick rather than being silently skipped all month.
        from backend.services.activity import log_activity

        log_activity(
            tenant_id=tid,
            activity_type=tag,
            description="Monthly conversation insights run dispatched",
        )

    if dispatched:
        logger.info(
            "conversation_insights_job: dispatched %d monthly insight runs", dispatched
        )
    return dispatched
