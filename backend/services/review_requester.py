"""Review-request Agent OS flow — appointment completed -> SMS review draft.

When an appointment transitions to 'completed', this service files a
review-request SMS draft into the Agent OS inbox for owner approval.

Same fault-tolerant shape as voice_recovery.py:
  - os_threads row  (title: "Review request for <customer>")
  - os_messages row (thread body with appointment context)
  - os_agent_runs row (deliverable: sms.send, agent_name: review_requester)
  - resolve_deliverable_status gates pending_approval vs auto-approved
  - auto-approved drafts dispatch immediately via queue_action_for_run

Deterministic-first: SMS text is composed without an LLM call.

Schema notes:
  - os_* tables use client_id (handled by tenant_table via _TENANT_COLUMN_OVERRIDES)
  - tenants table uses id as tenant column (same mapping)
  - google_review_link column exists on tenants (verified against expected-columns.json)
  - Dedupe: skip if os_agent_runs row already exists for this appointment_id
"""

import logging
from datetime import datetime, timezone
from typing import Any

from backend.services.agent_os_bridge import resolve_deliverable_status
from backend.services.os_action_dispatch import queue_action_for_run
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mask_phone(phone: str) -> str:
    """Mask phone for logging: show first 4 digits + **** + last 4."""
    import re

    stripped = (phone or "").strip()
    prefix = "+" if stripped.startswith("+") else ""
    digits = re.sub(r"\D", "", stripped)
    if len(digits) >= 8:
        visible_start = digits[:-8] if len(digits) > 8 else ""
        if len(digits) >= 9 and len(visible_start) < 4:
            visible_start = digits[:4]
        return prefix + visible_start + "****" + digits[-4:]
    if len(digits) > 4:
        return prefix + "***" + digits[-4:]
    return prefix + digits


def compose_review_sms(
    business_name: str,
    customer_first_name: str,
    review_link: str | None,
) -> str:
    """Deterministic 2-3 sentence SMS asking for a review.

    Args:
        business_name: Tenant's business name.
        customer_first_name: Customer's first name (extracted from full name).
        review_link: Google review URL if configured, else None.

    Returns:
        SMS text ready for the deliverable body.
    """
    name_part = f"Hi {customer_first_name}! " if customer_first_name else "Hi! "
    if review_link:
        return (
            f"{name_part}Thank you for choosing {business_name}. "
            f"We'd love to hear your feedback — it means the world to us. "
            f"Leave us a quick review here: {review_link}"
        )
    return (
        f"{name_part}Thank you for choosing {business_name}. "
        f"We truly appreciate your business and would love to hear how your experience was. "
        f"Feel free to reply and let us know!"
    )


def _first_name(full_name: str) -> str:
    """Extract first name from a full name string."""
    if not full_name:
        return ""
    return full_name.strip().split()[0]


async def create_review_request_draft(
    db: Any,
    *,
    tenant_id: str,
    appointment_id: str,
    lead_id: str | None,
    customer_name: str,
    customer_phone: str,
    business_name: str,
    google_review_link: str | None,
) -> str | None:
    """File a review-request SMS draft into the Agent OS. Returns run id or None.

    Fault-tolerant: every step wrapped in try/except, never raises.
    Dedupes by appointment_id in os_agent_runs metadata.
    """
    if not customer_phone:
        logger.debug(
            "review_requester: no phone for appointment=%s tenant=%s — skipping",
            appointment_id,
            tenant_id,
        )
        return None

    # --- dedupe: skip if a draft was already filed for this appointment ---
    try:
        existing = (
            tenant_table(db, "os_agent_runs", tenant_id)
            .select("id")
            .eq("agent_name", "review_requester")
            .filter(
                "deliverable->metadata->>'appointment_id'", "eq", appointment_id
            )
            .limit(1)
            .execute()
        )
        if existing.data:
            logger.debug(
                "review_requester: duplicate skip appointment=%s tenant=%s run=%s",
                appointment_id,
                tenant_id,
                existing.data[0]["id"],
            )
            return existing.data[0]["id"]
    except Exception:
        logger.warning(
            "review_requester: dedupe check failed tenant=%s appointment=%s — proceeding",
            tenant_id,
            appointment_id,
            exc_info=True,
        )

    # 1. OS thread so owner sees the review-request context in staff inbox
    thread_id = None
    try:
        thread = (
            tenant_table(db, "os_threads", tenant_id)
            .insert(
                {
                    "title": f"Review request for {customer_name or 'customer'}",
                    "source": "appointment",
                    "status": "open",
                    "created_by": "system",
                }
            )
            .execute()
        )
        thread_id = thread.data[0]["id"] if thread.data else None
    except Exception:
        logger.warning(
            "review_requester: thread insert failed tenant=%s appointment=%s",
            tenant_id,
            appointment_id,
            exc_info=True,
        )

    if thread_id:
        try:
            content = f"Appointment completed for {customer_name or 'customer'}."
            content += f"\n\nAppointment ID: {appointment_id}"
            if not google_review_link:
                content += "\n\nNote: no review link configured for this tenant."
            tenant_table(db, "os_messages", tenant_id).insert(
                {
                    "thread_id": thread_id,
                    "role": "user",
                    "content": content,
                    "inbound_kind": "appointment",
                    "source_ref": appointment_id,
                }
            ).execute()
        except Exception:
            logger.warning(
                "review_requester: message insert failed tenant=%s appointment=%s",
                tenant_id,
                appointment_id,
                exc_info=True,
            )

    # 2. Compose SMS draft
    first = _first_name(customer_name)
    sms_body = compose_review_sms(business_name, first, google_review_link)

    deliverable_meta: dict[str, Any] = {
        "recipient": customer_phone,
        "appointment_id": appointment_id,
        "lead_id": lead_id,
        "source": "review_request",
    }
    if not google_review_link:
        deliverable_meta["note"] = "no review link configured"

    deliverable = {
        "title": f"Ask {customer_name or 'customer'} for a review",
        "body": f"{sms_body}\n\nRecipient: {customer_phone}",
        "channel": "sms",
        "metadata": deliverable_meta,
    }

    deliverable_status = resolve_deliverable_status(
        db, tenant_id, "review_requester", requires_approval=False
    )

    run_row: dict[str, Any] = {
        "agent_name": "review_requester",
        "status": "succeeded",
        "action_type": "sms.send",
        "deliverable": deliverable,
        "deliverable_status": deliverable_status,
        "completed_at": _now(),
        "thought_process": [
            {
                "step": "review_request_draft",
                "detail": "Drafted review-request SMS after appointment completion",
            }
        ],
    }
    if thread_id:
        run_row["thread_id"] = thread_id

    try:
        created = (
            tenant_table(db, "os_agent_runs", tenant_id).insert(run_row).execute()
        )
        run = created.data[0] if created.data else None
    except Exception:
        logger.warning(
            "review_requester: run insert failed tenant=%s appointment=%s",
            tenant_id,
            appointment_id,
            exc_info=True,
        )
        return None

    if not run:
        return None

    # 3. Auto-approved per tenant G6 rules -> dispatch now
    if deliverable_status == "approved":
        try:
            await queue_action_for_run(db, tenant_id, run, background=None)
        except Exception:
            logger.warning(
                "review_requester: auto-send dispatch failed tenant=%s run=%s",
                tenant_id,
                run.get("id"),
                exc_info=True,
            )

    logger.info(
        "review_requester: filed draft tenant=%s appointment=%s run=%s status=%s phone=%s",
        tenant_id,
        appointment_id,
        run.get("id"),
        deliverable_status,
        _mask_phone(customer_phone),
    )
    return run.get("id")
