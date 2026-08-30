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

from backend.services import os_tool_executions, usage_meter
from backend.services.os_outbound_guard import apply_outbound_guard
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

# Draft channel -> registered action handler (backend/services/os_actions/).
# Channels with no entry (sequence/report/post/internal) stay display-only:
# approving them records the decision but fires no side effect.
CHANNEL_ACTION_MAP = {
    "sms": "sms.send",
    "email": "email.send",
    "widget_reply": "widget.message",
}

# Server-side defense-in-depth: departments whose drafts can NEVER auto-send,
# even if the owner enables auto-send. Keyed by the engine's department id — the
# value persisted to os_agent_runs.agent_name that resolve_deliverable_status
# looks up. customer_service owns the complaint-safety skills; invoicing owns
# money movement. The primary gate is still each skill's own
# requiresApproval=true (see resolve_deliverable_status); this set guards
# against an engine regression.
#
# Pre-refactor this set also listed skill ids (complaint_handler,
# quote_follow_up, payment_follow_up) that never match a persisted agent_name —
# dead entries removed 2026-07-15.
NEVER_AUTO_SEND_AGENTS = {
    "customer_service",
    "invoicing",
}

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
        # state/website/hours feed the engine's system-prompt block
        # (_authoring.ts PROFILE_FIELDS). Without them, every agent apologizes
        # ("I don't have your hours on file") even for tenants who set them.
        "state": row.get("business_state"),
        "phone": row.get("phone"),
        "email": row.get("owner_email"),
        "website": row.get("website_url"),
        "hoursSummary": row.get("business_hours_display"),
        "reviewLinkGoogle": row.get("google_review_link"),
    }
    return {k: v for k, v in out.items() if v is not None}


def map_widget_history(
    messages: list[dict], sentiment_by_session: dict[str, dict] | None = None
) -> list[dict]:
    """chat_messages rows -> WidgetConversationData[], grouped by session.

    chat_messages is per-message; the engine wants per-conversation summaries.
    Group by session_id, summarize with the first user message, and use the
    last message time as closedAt. Topics stay empty (not in the canonical
    store). When ``sentiment_by_session`` carries a stored classification for a
    session (see conversation_enrichment), its sentiment + intent are attached;
    otherwise those keys are omitted rather than fabricated.
    """
    sentiment_by_session = sentiment_by_session or {}
    by_session: dict[str, list[dict]] = {}
    for m in messages:
        sid = m.get("session_id") or "unknown"
        by_session.setdefault(sid, []).append(m)

    conversations: list[dict] = []
    for sid, msgs in by_session.items():
        ordered = sorted(msgs, key=lambda m: m.get("created_at") or "")
        first_user = next((m for m in ordered if m.get("role") == "user"), None)
        summary = (first_user or ordered[-1] if ordered else {}).get("content", "") or ""
        convo: dict = {
            "id": sid,
            "summary": summary[:500],
            "topics": [],
            "closedAt": (ordered[-1].get("created_at") if ordered else None) or _now(),
        }
        stored = sentiment_by_session.get(sid) or {}
        sentiment = stored.get("sentiment")
        if sentiment:
            convo["sentiment"] = sentiment
        intent = stored.get("intent")
        if intent:
            convo["intent"] = intent
        conversations.append(convo)
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


def resolve_deliverable_status(
    db: Any, client_id: str, agent_name: str, requires_approval: bool
) -> str:
    """Decide pending_approval vs approved for an engine draft.

    A draft may only auto-approve when ALL hold:
    1. the engine itself says it needs no approval,
    2. the tenant opted in — a per-agent rule in
       ``tenants.os_auto_send_rules`` keyed by the engine's department id
       (e.g. {"sales": true}) wins over the global ``os_auto_send_enabled``
       flag (both default to off),
    3. the agent is not in the never-auto-send set (rules cannot override it).

    Any read failure resolves to pending_approval — the safe side.
    """
    if requires_approval or agent_name in NEVER_AUTO_SEND_AGENTS:
        return "pending_approval"
    try:
        resp = (
            db.table("tenants")
            .select("os_auto_send_enabled, os_auto_send_rules")
            .eq("id", client_id)
            .limit(1)
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        if rows:
            rules = rows[0].get("os_auto_send_rules") or {}
            per_agent = rules.get(agent_name) if isinstance(rules, dict) else None
            if isinstance(per_agent, bool):
                return "approved" if per_agent else "pending_approval"
            if bool(rows[0].get("os_auto_send_enabled")):
                return "approved"
    except Exception:
        logger.warning(
            "agent_os_bridge: auto-send flag read failed; forcing approval gate",
            exc_info=True,
        )
    return "pending_approval"


# --- data access ------------------------------------------------------------


def _load_conversation_sentiment(db: Any, client_id: str) -> dict[str, dict]:
    """session_id -> {'sentiment', 'intent'} from conversations (client_id-scoped).

    Degrades to an empty map if the columns do not exist yet (pre-migration) or
    the query fails, so the bridge keeps working before migration 154 is applied.
    """
    try:
        rows = (
            tenant_table(db, "conversations", client_id)
            .select("session_id, sentiment, intent")
            .gte("last_message_at", _since(_WIDGET_DAYS))
            .limit(_WIDGET_MSG_CAP)
            .execute()
        ).data or []
    except Exception:
        logger.warning(
            "agent_os_bridge: conversation sentiment load failed for %s", client_id, exc_info=True
        )
        return {}

    out: dict[str, dict] = {}
    for row in rows:
        sid = row.get("session_id")
        if not sid:
            continue
        entry: dict = {}
        if row.get("sentiment"):
            entry["sentiment"] = row["sentiment"]
        if row.get("intent"):
            entry["intent"] = row["intent"]
        if entry:
            out[sid] = entry
    return out


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

    sentiment_by_session = _load_conversation_sentiment(db, client_id)

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
        "widgetHistory": map_widget_history(widget_msgs, sentiment_by_session),
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
        agent_name = run.get("agentId") or result.get("agentId") or "orchestrator"
        draft = next((d for d in drafts if d.get("runId") == run.get("id")), None)
        deliverable = None
        deliverable_status = None
        action_type = None
        if draft:
            deliverable = {
                "title": draft.get("title"),
                "body": draft.get("body"),
                "channel": draft.get("channel"),
                "metadata": draft.get("metadata"),
            }
            action_type = CHANNEL_ACTION_MAP.get(draft.get("channel") or "")
            deliverable_status = resolve_deliverable_status(
                db,
                client_id,
                agent_name,
                requires_approval=draft.get("requiresApproval", True),
            )
            # Outbound guardrail (enterprise-audit item 6): a draft that
            # matched a secret/SSN/card/payment-redirect pattern never
            # auto-sends — it parks at the human gate with the flags stored
            # on the deliverable so the approval UI can say why.
            deliverable_status, guard_flags = apply_outbound_guard(
                client_id, agent_name, deliverable, deliverable_status
            )
            if guard_flags:
                deliverable["guard_flags"] = guard_flags
        row = {
            "thread_id": thread_id,
            "agent_name": agent_name,
            "status": _STATUS_MAP.get(run.get("status", ""), "succeeded"),
            "thought_process": trace,
            "completed_at": _now(),
        }
        if deliverable is not None:
            row["deliverable"] = deliverable
            row["deliverable_status"] = deliverable_status
        if action_type is not None:
            row["action_type"] = action_type
        agent_run = (
            tenant_table(db, "os_agent_runs", client_id).insert(row).execute().data[0]
        )
        agent_run_id = agent_run["id"]

        # Engine path owns metering now that the legacy os_workers layer is
        # retired. Best-effort: a metering failure never breaks the turn.
        try:
            calls = record.get("modelCalls") or []
            usage_meter.record_agent_run(
                db,
                client_id,
                input_tokens=sum(c.get("inputTokens") or 0 for c in calls),
                output_tokens=sum(c.get("outputTokens") or 0 for c in calls),
            )
        except Exception:
            logger.warning("agent_os_bridge: usage metering failed", exc_info=True)

    # Persist action audits before the owner-facing reply. If an L2 row cannot
    # be written, fail before promising that an approval is queued.
    try:
        os_tool_executions.persist_tool_executions(
            db, client_id, agent_run_id, record
        )
    except os_tool_executions.ToolExecutionAuditError:
        raise
    except Exception:
        logger.warning(
            "agent_os_bridge: tool execution persist failed", exc_info=True
        )

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

    # Telemetry (routing decisions + model-call cost ledger) is best-effort:
    # a failure here never breaks the owner's turn.
    try:
        _persist_telemetry(db, client_id, agent_run_id, record)
    except Exception:
        logger.warning("agent_os_bridge: telemetry persist failed", exc_info=True)

    tenant_table(db, "os_threads", client_id).update({"updated_at": _now()}).eq(
        "id", thread_id
    ).execute()

    return {
        "assistant_message": assistant_message,
        "agent_run": agent_run,
        "status": result.get("status"),
        "agent_id": result.get("agentId"),
        # When the engine is torn between two departments it returns
        # status="needs_clarification" + the two near-tied candidates. Surface
        # them (and the decision id) so the UI can offer a one-click re-route
        # via force_agent_id instead of making the owner retype.
        "clarify_between": clarify_options(result),
        "decision_id": result.get("decisionId"),
    }


def clarify_options(result: dict) -> list[dict]:
    """Extract the needs_clarification candidates as [{agent_id}, ...].

    Empty for any non-clarification result. Candidates carry agentId; the UI
    maps that to a human label.
    """
    return [
        {"agent_id": c.get("agentId")}
        for c in (result.get("clarifyBetween") or [])
        if isinstance(c, dict) and c.get("agentId")
    ]


def map_routing_decision_row(decision: dict, run_id: str | None) -> dict:
    """RunRecordBundle decision -> os_routing_decision row (no client_id/id)."""
    return {
        "run_id": run_id,
        "ask": decision.get("ask") or "",
        "classifier": decision.get("classifier") or "heuristic",
        "decision": decision.get("decision") or "",
        "chosen_agent": decision.get("chosenAgent") or "",
        "confidence": decision.get("confidence") or 0,
        "alternates": decision.get("alternates"),
        "accepted": decision.get("accepted"),
        "changed_to": decision.get("changedTo"),
    }


def map_model_call_row(call: dict, run_id: str | None) -> dict:
    """RunRecordBundle model call -> os_model_call_log row (no client_id/id)."""
    return {
        "run_id": run_id,
        "purpose": call.get("purpose") or "other",
        "model": call.get("model") or "",
        "input_tokens": call.get("inputTokens") or 0,
        "output_tokens": call.get("outputTokens") or 0,
        "cost_usd": call.get("costUsd") or 0,
        "ok": call.get("ok", True),
        "error": call.get("error"),
    }


def _persist_telemetry(
    db: Any, client_id: str, agent_run_id: str | None, record: dict
) -> None:
    """Write the run record's routing decisions + model-call logs to os_*.

    All rows share the turn's single persisted agent_run_id (or None for
    answer/decline turns). client_id is injected by tenant_insert.
    """
    decisions = record.get("decisions") or []
    if decisions:
        tenant_table(db, "os_routing_decision", client_id).insert(
            [map_routing_decision_row(d, agent_run_id) for d in decisions]
        ).execute()

    calls = record.get("modelCalls") or []
    if calls:
        tenant_table(db, "os_model_call_log", client_id).insert(
            [map_model_call_row(c, agent_run_id) for c in calls]
        ).execute()
