"""Data-plane bridge between FastAPI/Supabase and the agent-service engine.

The vendored Agent OS engine (the standalone demo's framework) runs in the Node
``agent-service`` as pure compute. This module is the data plane it pulls from
and writes back through:

1. ``assemble_shared_context`` reads Supabase and builds the engine's
   ``SharedContext`` shape (camelCase keys) for one tenant — this is where the
   chat widget becomes "a source of data the Agent OS pulls from"
   (``chat_messages`` -> ``widgetHistory``). Cold-start caps keep it cheap.
2. ``agent_sdk_client.orchestrate_sync`` POSTs that context to the engine.
3. ``persist_orchestration`` writes the returned run record into ``os_*``.

Every query is ``client_id``-scoped via ``tenant_scope`` helpers; ``client_id``
is always the JWT ``tenant_id`` — never a path/body value. Mappers are pure
functions so they unit-test without a database.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

# Cold-start caps (mirror the standalone's PrismaSharedContextProvider takes).
_WIDGET_DAYS = 30
_WIDGET_MSG_CAP = 200
_LEADS_CAP = 100
_APPTS_CAP = 100
_INVOICES_CAP = 100
_RUN_HISTORY_DAYS = 14
_RUN_HISTORY_CAP = 50

# Demo run status -> os_agent_runs.status (queued|running|succeeded|failed).
_STATUS_MAP = {
    "completed": "succeeded",
    "no_draft": "succeeded",
    "failed": "failed",
    "running": "running",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _since(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


# --- pure mappers (Supabase row -> engine SharedContext shape) --------------


def map_business_profile(row: dict | None) -> dict:
    """tenants row -> BusinessProfileData. All fields optional; omit missing."""
    if not row:
        return {}
    out = {
        "businessName": row.get("business_name"),
        "ownerName": row.get("owner_name"),
        "industry": row.get("business_type"),
        "businessType": row.get("business_type"),
        "city": row.get("city"),
        "phone": row.get("phone"),
        "email": row.get("owner_email"),
        "reviewLinkGoogle": row.get("google_review_link"),
    }
    return {k: v for k, v in out.items() if v is not None}


def map_widget_history(messages: list[dict]) -> list[dict]:
    """chat_messages rows -> WidgetConversationData[], grouped by session.

    chat_messages is per-message; the engine wants per-conversation summaries.
    Group by session_id, summarize with the first user message, and use the
    last message time as closedAt. Honest + lossy: no intent/topics in the
    canonical store, so those stay empty rather than fabricated.
    """
    by_session: dict[str, list[dict]] = {}
    for m in messages:
        sid = m.get("session_id") or "unknown"
        by_session.setdefault(sid, []).append(m)

    conversations: list[dict] = []
    for sid, msgs in by_session.items():
        ordered = sorted(msgs, key=lambda m: m.get("created_at") or "")
        first_user = next((m for m in ordered if m.get("role") == "user"), None)
        summary = (first_user or ordered[-1] if ordered else {}).get("content", "") or ""
        conversations.append(
            {
                "id": sid,
                "summary": summary[:500],
                "topics": [],
                "closedAt": (ordered[-1].get("created_at") if ordered else None) or _now(),
            }
        )
    # Most-recent conversation first.
    conversations.sort(key=lambda c: c["closedAt"], reverse=True)
    return conversations


def map_lead(row: dict) -> dict:
    out = {
        "id": row.get("id"),
        "name": row.get("name") or "Unknown",
        "status": row.get("status") or "new",
        "subject": row.get("areas_of_interest"),
        "quoteAmount": row.get("deal_value"),
        "lastContactDate": row.get("updated_at"),
    }
    return {k: v for k, v in out.items() if v is not None}


def map_appointment(row: dict) -> dict:
    return {
        "id": row.get("id"),
        "customerName": row.get("customer_name") or "",
        "scheduledFor": row.get("start_time") or _now(),
        "status": row.get("status") or "confirmed",
        "reviewRequested": False,
    }


def map_invoice(row: dict) -> dict:
    return {
        "id": row.get("id"),
        "customerName": row.get("customer_name") or "",
        "number": row.get("invoice_number") or "",
        "amount": row.get("total") or 0,
        "issuedAt": row.get("created_at") or _now(),
        "dueAt": row.get("due_date") or _now(),
        "status": row.get("status") or "draft",
    }


def map_agent_run_history(row: dict) -> dict:
    deliverable = row.get("deliverable") or {}
    title = deliverable.get("title") if isinstance(deliverable, dict) else None
    return {
        "agentId": row.get("agent_name") or "",
        "title": title or row.get("agent_name") or "run",
        "status": row.get("status") or "",
        "createdAt": row.get("created_at") or _now(),
        "kbGap": False,
    }


def reply_text(result: dict) -> str:
    """Assistant-message text for one orchestration result."""
    answer = result.get("answer")
    if answer:
        return answer
    notes = [n for n in (result.get("orchestratorNotes") or []) if n]
    draft = result.get("draft")
    if draft and draft.get("title"):
        prefix = " ".join(notes)
        line = f"Draft ready for review: {draft['title']}"
        return f"{prefix}\n\n{line}".strip() if prefix else line
    if notes:
        return " ".join(notes)
    return result.get("noDraftReason") or "Done."


# --- data access ------------------------------------------------------------


def assemble_shared_context(db: Any, client_id: str) -> dict:
    """Build the engine's SharedContext for one tenant from Supabase."""
    profile_resp = (
        db.table("tenants").select("*").eq("id", client_id).limit(1).execute()
    )
    profile_row = (getattr(profile_resp, "data", None) or [None])[0]

    widget_msgs = (
        tenant_table(db, "chat_messages", client_id)
        .select("session_id, role, content, created_at")
        .gte("created_at", _since(_WIDGET_DAYS))
        .order("created_at", desc=True)
        .limit(_WIDGET_MSG_CAP)
        .execute()
    ).data or []

    leads = (
        tenant_table(db, "leads", client_id)
        .select("*")
        .order("created_at", desc=True)
        .limit(_LEADS_CAP)
        .execute()
    ).data or []

    appts = (
        tenant_table(db, "appointments", client_id)
        .select("*")
        .order("start_time", desc=True)
        .limit(_APPTS_CAP)
        .execute()
    ).data or []

    invoices = (
        tenant_table(db, "invoices", client_id)
        .select("*")
        .order("created_at", desc=True)
        .limit(_INVOICES_CAP)
        .execute()
    ).data or []

    runs = (
        tenant_table(db, "os_agent_runs", client_id)
        .select("agent_name, status, deliverable, created_at")
        .gte("created_at", _since(_RUN_HISTORY_DAYS))
        .order("created_at", desc=True)
        .limit(_RUN_HISTORY_CAP)
        .execute()
    ).data or []

    return {
        "businessProfile": map_business_profile(profile_row),
        "widgetHistory": map_widget_history(widget_msgs),
        "pipelineLeads": [map_lead(r) for r in leads],
        "appointments": [map_appointment(r) for r in appts],
        "invoices": [map_invoice(r) for r in invoices],
        "agentRunHistory": [map_agent_run_history(r) for r in runs],
        "kb": [],
    }


def persist_orchestration(
    db: Any, client_id: str, thread_id: str, out: dict
) -> dict:
    """Persist an agent-service orchestration result into os_* tables.

    Inserts at most one os_agent_runs row (the engine runs one agent per turn)
    plus the assistant os_messages reply, then bumps the thread. Returns the
    assistant message + agent run for the caller's response.
    """
    result = out.get("result") or {}
    record = out.get("record") or {}
    runs = record.get("runs") or []
    drafts = record.get("drafts") or []
    trace = record.get("traceSteps") or []

    agent_run = None
    agent_run_id = None
    if runs:
        run = runs[0]
        draft = next((d for d in drafts if d.get("runId") == run.get("id")), None)
        deliverable = None
        deliverable_status = None
        if draft:
            deliverable = {
                "title": draft.get("title"),
                "body": draft.get("body"),
                "channel": draft.get("channel"),
                "metadata": draft.get("metadata"),
            }
            deliverable_status = (
                "pending_approval" if draft.get("requiresApproval", True) else "approved"
            )
        row = {
            "thread_id": thread_id,
            "agent_name": run.get("agentId") or result.get("agentId") or "orchestrator",
            "status": _STATUS_MAP.get(run.get("status", ""), "succeeded"),
            "thought_process": trace,
            "completed_at": _now(),
        }
        if deliverable is not None:
            row["deliverable"] = deliverable
            row["deliverable_status"] = deliverable_status
        agent_run = (
            tenant_table(db, "os_agent_runs", client_id).insert(row).execute().data[0]
        )
        agent_run_id = agent_run["id"]

    message_row: dict = {
        "thread_id": thread_id,
        "role": "assistant",
        "content": reply_text(result),
    }
    if agent_run_id:
        message_row["agent_run_id"] = agent_run_id
    assistant_message = (
        tenant_table(db, "os_messages", client_id).insert(message_row).execute().data[0]
    )

    tenant_table(db, "os_threads", client_id).update({"updated_at": _now()}).eq(
        "id", thread_id
    ).execute()

    return {
        "assistant_message": assistant_message,
        "agent_run": agent_run,
        "status": result.get("status"),
        "agent_id": result.get("agentId"),
    }
