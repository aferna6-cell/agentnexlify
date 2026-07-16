"""Accepted opportunity suggestions become real drafts.

The proactive scan (``os_opportunities``) files suggestion cards like
"5 leads went cold this week — want me to follow up? Accept and I'll draft a
friendly check-in for each (you approve every message before it sends)."
Until now, accepting only flipped ``os_backlog_requests.status`` — the AI
staff promised drafts and produced nothing. Prod showed the cost: real
tenants with warm/hot leads sitting untouched and every suggestion pending
forever.

This module keeps the promise. On accept:

  - Cold-leads suggestion -> one follow-up draft per cold warm/hot lead
    that has contact info (email preferred, SMS fallback).
  - Overdue-invoices suggestion -> one payment-reminder draft per overdue
    invoice whose linked lead has an email.

Each draft is an ``os_agent_runs`` deliverable in the EXISTING approval
flow, with ``recipient`` pre-filled from the lead record so the approved
send actually knows who it goes to (the explicit-recipient path). Status is
ALWAYS pending_approval — the card's wording promises the owner approves
every message, so per-agent auto-send rules deliberately do not apply here.

Deterministic-first: draft bodies are composed from data on file — no LLM.
Mirrors the ``voice_recovery`` pattern (thread + run rows created directly).
Every step is fault-tolerant: a failure never breaks the accept request.

Schema notes: leads use client_id; invoices use tenant_id (via
tenant_table's mapping). See .claude/rules/schema-discipline.md.

WARNING: imported by a FastAPI router — do NOT add
``from __future__ import annotations`` here.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.services import os_approval_notify
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

# Same window the scanner used to call the lead cold.
_COLD_DAYS = 7
# Cap per acceptance: a giant approval pile helps nobody.
_MAX_DRAFTS = 10


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso_days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _first_name(full: str) -> str:
    return (full or "").strip().split(" ")[0] or "there"


def _business_identity(db: Any, client_id: str) -> tuple:
    """(business_name, signoff) with safe defaults; never raises."""
    try:
        rows = (
            tenant_table(db, "tenants", client_id)
            .select("business_name, owner_name")
            .limit(1)
            .execute()
        ).data or []
        row = rows[0] if rows else {}
        business = row.get("business_name") or "our team"
        return business, (row.get("owner_name") or business)
    except Exception:
        logger.warning(
            "opportunity_fulfill: tenant lookup failed %s", client_id, exc_info=True
        )
        return "our team", "our team"


def _create_batch_thread(db: Any, client_id: str, title: str, note: str) -> str | None:
    """One OS thread collects the batch so the owner sees what happened."""
    try:
        thread = (
            tenant_table(db, "os_threads", client_id)
            .insert({"title": title, "status": "open", "created_by": "system"})
            .execute()
        )
        thread_id = thread.data[0]["id"] if thread.data else None
    except Exception:
        logger.warning(
            "opportunity_fulfill: thread insert failed %s", client_id, exc_info=True
        )
        return None
    if thread_id:
        try:
            tenant_table(db, "os_messages", client_id).insert(
                {"thread_id": thread_id, "role": "assistant", "content": note}
            ).execute()
        except Exception:
            logger.warning(
                "opportunity_fulfill: message insert failed %s",
                client_id,
                exc_info=True,
            )
    return thread_id


def _insert_draft_run(
    db: Any,
    client_id: str,
    *,
    thread_id: str | None,
    agent_name: str,
    title: str,
    body: str,
    channel: str,
    recipient: str,
    metadata: dict,
) -> bool:
    """One pending-approval deliverable row. Returns True when inserted."""
    run_row: dict[str, Any] = {
        "agent_name": agent_name,
        "status": "succeeded",
        "action_type": "email.send" if channel == "email" else "sms.send",
        "deliverable": {
            "title": title,
            "body": body,
            "channel": channel,
            "recipient": recipient,
            "metadata": metadata,
        },
        # The suggestion card promised "you approve every message before it
        # sends" — so these never auto-send, whatever the per-agent rules say.
        "deliverable_status": "pending_approval",
        "completed_at": _now(),
        "thought_process": [
            {
                "step": "opportunity_fulfillment",
                "detail": "Drafted from an accepted proactive suggestion",
            }
        ],
    }
    if thread_id:
        run_row["thread_id"] = thread_id
    try:
        created = (
            tenant_table(db, "os_agent_runs", client_id).insert(run_row).execute()
        )
        return bool(created.data)
    except Exception:
        logger.warning(
            "opportunity_fulfill: run insert failed %s", client_id, exc_info=True
        )
        return False


async def _notify_batch(db: Any, client_id: str, agent_name: str, count: int) -> None:
    """One owner notification for the whole batch — not one per draft."""
    try:
        await os_approval_notify.notify_pending_approval(
            db,
            client_id,
            agent_name=agent_name,
            channel="email",
            title=f"{count} draft{'s' if count != 1 else ''} ready for your review",
        )
    except Exception:
        logger.warning(
            "opportunity_fulfill: batch notify failed %s", client_id, exc_info=True
        )


async def _draft_lead_followups(db: Any, client_id: str) -> int:
    """Draft a check-in per cold warm/hot lead with contact info."""
    leads = (
        tenant_table(db, "leads", client_id)
        .select("id, name, email, phone, areas_of_interest")
        .in_("lead_temperature", ["warm", "hot"])
        .lt("updated_at", _iso_days_ago(_COLD_DAYS))
        .limit(25)
        .execute()
    ).data or []
    contactable = [
        l for l in leads if (l.get("email") or "").strip() or (l.get("phone") or "").strip()
    ][:_MAX_DRAFTS]
    if not contactable:
        return 0

    business, signoff = _business_identity(db, client_id)
    thread_id = _create_batch_thread(
        db,
        client_id,
        f"Lead follow-ups ({len(contactable)} drafts)",
        (
            f"You accepted the cold-lead suggestion, so I drafted "
            f"{len(contactable)} personalized check-in"
            f"{'s' if len(contactable) != 1 else ''}. Each one is waiting in "
            "your approvals — nothing sends until you approve it."
        ),
    )

    drafted = 0
    for lead in contactable:
        name = lead.get("name") or "there"
        first = _first_name(name)
        email = (lead.get("email") or "").strip()
        phone = (lead.get("phone") or "").strip()
        channel = "email" if email else "sms"
        recipient = email or phone
        interest = (lead.get("areas_of_interest") or "").strip()
        about = f" about {interest}" if interest else ""
        body = (
            f"Hi {first},\n\n"
            f"You reached out to {business}{about} a little while back and I "
            f"wanted to check in — are you still interested? Happy to answer "
            f"any questions or get you scheduled whenever works for you.\n\n"
            f"{signoff}\n{business}"
        )
        if _insert_draft_run(
            db,
            client_id,
            thread_id=thread_id,
            agent_name="sales",
            title=f"Check in with {name}",
            body=body,
            channel=channel,
            recipient=recipient,
            metadata={"lead_id": lead.get("id"), "source": "opportunity_fulfillment"},
        ):
            drafted += 1

    if drafted:
        await _notify_batch(db, client_id, "sales", drafted)
    return drafted


async def _draft_invoice_reminders(db: Any, client_id: str) -> int:
    """Draft a payment reminder per overdue invoice with a reachable lead."""
    today = datetime.now(timezone.utc).date().isoformat()
    overdue = (
        tenant_table(db, "invoices", client_id)
        .select("id, invoice_number, total, due_date, lead_id")
        .eq("status", "sent")
        .lt("due_date", today)
        .limit(25)
        .execute()
    ).data or []
    linked = [i for i in overdue if i.get("lead_id")][:_MAX_DRAFTS]
    if not linked:
        return 0

    business, signoff = _business_identity(db, client_id)
    thread_id = _create_batch_thread(
        db,
        client_id,
        f"Invoice reminders ({len(linked)} drafts)",
        (
            "You accepted the overdue-invoice suggestion, so I drafted polite "
            "payment reminders. Each one is waiting in your approvals — "
            "nothing sends until you approve it."
        ),
    )

    drafted = 0
    for inv in linked:
        try:
            rows = (
                tenant_table(db, "leads", client_id)
                .select("id, name, email")
                .eq("id", inv["lead_id"])
                .limit(1)
                .execute()
            ).data or []
        except Exception:
            logger.warning(
                "opportunity_fulfill: lead lookup failed %s", client_id, exc_info=True
            )
            rows = []
        lead = rows[0] if rows else {}
        email = (lead.get("email") or "").strip()
        if not email:
            continue
        name = lead.get("name") or "there"
        number = inv.get("invoice_number") or "your invoice"
        total = float(inv.get("total") or 0)
        due = inv.get("due_date") or ""
        body = (
            f"Hi {_first_name(name)},\n\n"
            f"Just a friendly reminder that invoice {number} for ${total:,.2f} "
            f"was due on {due}. If you've already sent payment, please ignore "
            f"this — otherwise, is there anything you need from us to get it "
            f"wrapped up?\n\nThank you!\n{signoff}\n{business}"
        )
        if _insert_draft_run(
            db,
            client_id,
            thread_id=thread_id,
            agent_name="invoicing",
            title=f"Payment reminder — {number}",
            body=body,
            channel="email",
            recipient=email,
            metadata={"invoice_id": inv.get("id"), "source": "opportunity_fulfillment"},
        ):
            drafted += 1

    if drafted:
        await _notify_batch(db, client_id, "invoicing", drafted)
    return drafted


async def fulfill_accepted_suggestion(
    db: Any, client_id: str, request_row: dict
) -> int:
    """Turn an accepted opportunity suggestion into drafts. Never raises.

    Dispatch keys on the summary wording our own scanner
    (``os_opportunities.compute_suggestions``) produced — both strings are
    generated and consumed inside this codebase.
    """
    try:
        if (request_row.get("reason") or "") != "opportunity":
            return 0
        summary = (request_row.get("summary") or "").lower()
        if "lead" in summary and "cold" in summary:
            return await _draft_lead_followups(db, client_id)
        if "invoice" in summary:
            return await _draft_invoice_reminders(db, client_id)
        logger.info(
            "opportunity_fulfill: unrecognized suggestion wording client_id=%s",
            client_id,
        )
        return 0
    except Exception:
        logger.warning(
            "opportunity_fulfill: fulfillment failed client_id=%s",
            client_id,
            exc_info=True,
        )
        return 0
