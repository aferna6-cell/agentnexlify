"""Invoice Action Executor data plane — L1 draft apply + L2 send/reminder.

Distinct from ``backend/services/os_actions/`` deliverable handlers and from
the scheduled ``send_invoice_payment_reminders`` job (that job auto-sends).
These tools reach here only through the Action Executor: L1 Collecting persist
or claim-gated owner approve (L2).

Hard rules:
- INVOICE_ACTIONS_ENABLED defaults off.
- Payment confirmation is stored Stripe/webhook state, never guessed.
- Agents cannot mark invoices paid.
- Reminders never go to paid invoices and cannot spam (one per invoice/day).
- Provider failure is not reported as success.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from backend.services.invoice_helpers import compute_invoice_totals
from backend.services.m8_action_flags import (
    INVOICE_ACTIONS_FLAG,
    invoice_actions_enabled,
)
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

INVOICE_L0_TOOL_IDS = frozenset({"list_overdue_invoices", "get_invoice"})
INVOICE_L1_TOOL_IDS = frozenset({"create_invoice_draft"})
INVOICE_L2_TOOL_IDS = frozenset({"send_invoice", "send_invoice_reminder"})
INVOICE_TOOL_IDS = INVOICE_L0_TOOL_IDS | INVOICE_L1_TOOL_IDS | INVOICE_L2_TOOL_IDS
PAID_OR_CANCELLED = frozenset({"paid", "cancelled"})


def refuse_invoice_tool(*, tool_id: str | None = None) -> str | None:
    if tool_id and tool_id not in INVOICE_TOOL_IDS:
        return None
    if not invoice_actions_enabled():
        return f"invoice actions are disabled ({INVOICE_ACTIONS_FLAG} defaults off)"
    return None


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _items_from_bundle(raw: Any) -> list[dict]:
    items = []
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        items.append(
            {
                "description": str(item.get("description") or ""),
                "quantity": float(item.get("quantity") or item.get("Quantity") or 1),
                "unit_price": float(
                    item.get("unit_price")
                    if item.get("unit_price") is not None
                    else item.get("unitPrice") or 0
                ),
            }
        )
    return items


def _next_invoice_number(db: Any, client_id: str, attempt: int = 0) -> str:
    """Sync sequential invoice number — same shape as ``get_next_invoice_number``."""
    try:
        result = (
            tenant_table(db, "invoices", client_id)
            .select("invoice_number")
            .eq("tenant_id", client_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            last_num = result.data[0].get("invoice_number", "INV-XXXX-000")
            parts = last_num.rsplit("-", 1)
            if len(parts) == 2 and parts[1].isdigit():
                seq = int(parts[1]) + 1 + attempt
            else:
                seq = 1 + attempt
        else:
            seq = 1 + attempt
    except Exception:
        logger.warning(
            "Could not determine next invoice number for tenant %s",
            client_id,
            exc_info=True,
        )
        seq = 1 + attempt
    prefix = client_id[:4].upper()
    return f"INV-{prefix}-{seq:03d}"


def _as_uuid(value: Any) -> str | None:
    if not value:
        return None
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        return None


def _fingerprint(customer_id: str, items: list[dict], due_date: str | None, total: float, key: str | None) -> str:
    if key:
        return key
    parts = [customer_id]
    for item in items:
        parts.append(f"{item['description']}|{item['quantity']}|{item['unit_price']}")
    parts.append(due_date or "")
    parts.append(str(round(float(total), 2)))
    return "|".join(parts)


def _load_invoice(db: Any, client_id: str, invoice_id: str) -> dict | None:
    result = (
        tenant_table(db, "invoices", client_id)
        .select("*")
        .eq("id", invoice_id)
        .eq("tenant_id", client_id)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return rows[0] if rows else None


def _load_lead(db: Any, client_id: str, lead_id: str) -> dict | None:
    result = (
        tenant_table(db, "leads", client_id)
        .select("id, name, email, phone")
        .eq("id", lead_id)
        .eq("client_id", client_id)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return rows[0] if rows else None


def _find_draft_by_fingerprint(
    db: Any,
    client_id: str,
    customer_id: str,
    items: list[dict],
    due_date: str | None,
    total: float,
    idempotency_key: str | None,
) -> dict | None:
    result = (
        tenant_table(db, "invoices", client_id)
        .select("*")
        .eq("tenant_id", client_id)
        .eq("lead_id", customer_id)
        .eq("status", "draft")
        .execute()
    )
    wanted = _fingerprint(customer_id, items, due_date, total, idempotency_key)
    for row in result.data or []:
        notes = row.get("notes") or ""
        if idempotency_key and f"idempotency:{idempotency_key}" in notes:
            return row
        existing_items = row.get("items_json") or []
        existing_due = row.get("due_date")
        existing_total = float(row.get("total") or 0)
        if (
            _fingerprint(customer_id, existing_items, existing_due, existing_total, None)
            == wanted
        ):
            return row
    return None


def apply_invoice_mutations(
    db: Any,
    client_id: str,
    invoices: list[dict],
    executions: list[dict] | None = None,
) -> list[dict]:
    """Apply Collecting invoice draft creates to ``invoices`` with read-back."""
    if not invoice_actions_enabled():
        logger.info("apply_invoice_mutations skipped — INVOICE_ACTIONS_ENABLED off")
        return []

    outcomes: list[dict] = []
    for inv in invoices:
        if (inv.get("_op") or inv.get("op") or "create").lower() != "create":
            outcomes.append(
                {"invoice_id": inv.get("id"), "applied": False, "detail": "unsupported_op"}
            )
            continue
        try:
            applied, detail, row = _create_draft(db, client_id, inv)
        except Exception as exc:
            logger.exception("invoice apply failed invoice_id=%s", inv.get("id"))
            applied, detail, row = False, f"error:{exc}", None
        outcomes.append(
            {
                "invoice_id": (row or {}).get("id") or inv.get("id"),
                "applied": applied,
                "detail": detail,
            }
        )
    return outcomes


def _create_draft(db: Any, client_id: str, inv: dict) -> tuple[bool, str, dict | None]:
    customer_id = inv.get("customerId") or inv.get("customer_id") or ""
    if not customer_id:
        return False, "customer_not_found", None
    lead = _load_lead(db, client_id, customer_id)
    if not lead:
        return False, "customer_not_found", None

    items = _items_from_bundle(inv.get("items") or inv.get("items_json"))
    if not items:
        return False, "missing_items", None
    tax_rate = float(inv.get("taxRate") if inv.get("taxRate") is not None else inv.get("tax_rate") or 0)
    subtotal, tax_amount, total = compute_invoice_totals(items, tax_rate)
    expected_total = inv.get("total")
    if expected_total is not None and abs(float(expected_total) - total) > 0.01:
        return False, "amount_mismatch", None

    due_date = inv.get("dueDate") or inv.get("due_date")
    idempotency_key = inv.get("idempotencyKey") or inv.get("idempotency_key")
    existing = _find_draft_by_fingerprint(
        db, client_id, customer_id, items, due_date, total, idempotency_key
    )
    if existing:
        return True, "deduplicated", existing

    invoice_number = inv.get("invoiceNumber") or inv.get("invoice_number")
    if not invoice_number or str(invoice_number).startswith("INV-MEM-"):
        invoice_number = _next_invoice_number(db, client_id)

    notes = inv.get("notes") or ""
    if idempotency_key and f"idempotency:{idempotency_key}" not in notes:
        notes = f"{notes}\nidempotency:{idempotency_key}".strip()

    data = {
        "tenant_id": client_id,
        "lead_id": customer_id,
        "invoice_number": invoice_number,
        "items_json": items,
        "subtotal": subtotal,
        "tax_rate": tax_rate,
        "tax_amount": tax_amount,
        "total": total,
        "status": "draft",
        "notes": notes or None,
    }
    if due_date:
        data["due_date"] = due_date
    data["id"] = _as_uuid(inv.get("id")) or str(uuid.uuid4())

    result = tenant_table(db, "invoices", client_id).insert(data).execute()
    row = (result.data or [None])[0]
    if not row:
        return False, "insert_failed", None
    read_back = _load_invoice(db, client_id, row["id"])
    if not read_back:
        return False, "verification_failed", row
    if abs(float(read_back.get("total") or 0) - total) > 0.01:
        return False, "verification_failed", read_back
    if read_back.get("lead_id") != customer_id:
        return False, "verification_failed", read_back
    if read_back.get("status") == "paid":
        return False, "verification_failed", read_back
    return True, "created", read_back


def _reminder_tag(day: str | None = None) -> str:
    return f"invoice_reminder_{day or _today()}"


def _reminder_already_sent(db: Any, client_id: str, invoice_id: str, lead_id: str | None) -> bool:
    tag = _reminder_tag()
    result = (
        tenant_table(db, "activity_log", client_id)
        .select("id, metadata, activity_type")
        .eq("tenant_id", client_id)
        .eq("activity_type", tag)
        .execute()
    )
    for row in result.data or []:
        meta = row.get("metadata") or {}
        if meta.get("invoice_id") == invoice_id:
            return True
    return False


def _log_reminder(db: Any, client_id: str, invoice: dict) -> None:
    tenant_table(db, "activity_log", client_id).insert(
        {
            "tenant_id": client_id,
            "lead_id": invoice.get("lead_id"),
            "activity_type": _reminder_tag(),
            "description": (
                f"Overdue reminder sent for Invoice "
                f"{invoice.get('invoice_number')} (${float(invoice.get('total') or 0):.2f})"
            ),
            "metadata": {"invoice_id": invoice.get("id"), "is_overdue": True},
        }
    ).execute()


def _is_overdue(invoice: dict, today: str | None = None) -> bool:
    if invoice.get("status") in PAID_OR_CANCELLED or invoice.get("status") == "draft":
        return False
    if invoice.get("status") == "overdue":
        return True
    due = invoice.get("due_date")
    if not due:
        return False
    return str(due)[:10] < (today or _today())


async def _send_channels(
    db: Any,
    client_id: str,
    invoice: dict,
    method: str,
    *,
    reminder: bool,
) -> dict:
    from backend.services.email_sender import send_email
    from backend.services.invoice_email import build_invoice_email_html
    from backend.services.invoice_helpers import get_or_create_stripe_payment_link
    from backend.services.twilio_service import send_sms

    lead: dict = {}
    if invoice.get("lead_id"):
        lead = _load_lead(db, client_id, invoice["lead_id"]) or {}

    business: dict = {}
    try:
        tenant_result = (
            tenant_table(db, "tenants", client_id)
            .select("business_name, owner_email, phone")
            .eq("id", client_id)
            .limit(1)
            .execute()
        )
        if tenant_result.data:
            business = tenant_result.data[0]
    except Exception:
        logger.warning("invoice action: tenant lookup failed %s", client_id, exc_info=True)

    payment_link = invoice.get("stripe_payment_link") or ""
    total = float(invoice.get("total") or 0)
    if not payment_link and total > 0:
        payment_link = (
            await get_or_create_stripe_payment_link(
                invoice_id=invoice["id"],
                tenant_id=client_id,
                invoice_number=invoice.get("invoice_number", invoice["id"]),
                total=total,
            )
            or ""
        )

    invoice_for_email = {**invoice, "stripe_payment_link": payment_link}
    email_sent = False
    sms_sent = False
    errors: list[str] = []
    inv_num = invoice.get("invoice_number") or ""
    biz_name = business.get("business_name") or "Your Service Provider"
    due = invoice.get("due_date") or ""

    if method in ("email", "both"):
        recipient = (lead.get("email") or "").strip()
        if not recipient:
            errors.append("No email address on file for this lead")
        else:
            if reminder:
                subject = f"Payment overdue — Invoice {inv_num} from {biz_name}"
            else:
                subject = f"Invoice {inv_num} from {biz_name}"
            body_html = build_invoice_email_html(invoice_for_email, business, lead)
            result = await send_email(
                to=recipient,
                subject=subject,
                body_html=body_html,
                tenant_id=client_id,
            )
            if result.get("success"):
                email_sent = True
            else:
                errors.append(f"Email failed: {result.get('detail', 'unknown error')}")

    if method in ("sms", "both"):
        phone = (lead.get("phone") or "").strip()
        if not phone:
            errors.append("No phone number on file for this lead")
        else:
            if payment_link:
                sms_body = (
                    f"Hi {lead.get('name', 'there')}! Invoice {inv_num} for ${total:,.2f} "
                    f"from {biz_name} is ready. Pay online: {payment_link}"
                )
            else:
                sms_body = (
                    f"Hi {lead.get('name', 'there')}! Invoice {inv_num} for ${total:,.2f} "
                    f"from {biz_name} is ready. Please contact us to complete payment."
                )
            if reminder and due:
                sms_body = (
                    f"Hi {lead.get('name', 'there')}, reminder that Invoice {inv_num} "
                    f"for ${total:,.2f} was due on {due}."
                    + (f" Pay now: {payment_link}" if payment_link else "")
                )
            ok = await send_sms(to=phone, body=sms_body, tenant_id=client_id)
            if ok:
                sms_sent = True
            else:
                errors.append("SMS delivery failed")

    return {
        "email_sent": email_sent,
        "sms_sent": sms_sent,
        "payment_link": payment_link,
        "errors": errors,
        "lead": lead,
    }


def run_invoice_l2(db: Any, client_id: str, claimed: dict) -> dict:
    """Claim-gated L2 send / reminder. Sync wrapper for ``run_in_threadpool``."""
    import asyncio

    refused = refuse_invoice_tool(tool_id=claimed.get("tool_id"))
    if refused:
        return {"executed": False, "refused": True, "reason": refused}

    return asyncio.run(_run_invoice_l2_async(db, client_id, claimed))


async def _run_invoice_l2_async(db: Any, client_id: str, claimed: dict) -> dict:
    tool_id = claimed.get("tool_id")
    payload = claimed.get("input") or {}
    invoice_id = payload.get("invoice_id") or payload.get("invoiceId")
    method = payload.get("method") or "email"
    if method not in ("email", "sms", "both"):
        method = "email"
    if not invoice_id:
        return {"executed": False, "refused": True, "reason": "invoice_id required"}

    invoice = _load_invoice(db, client_id, invoice_id)
    if not invoice:
        return {
            "executed": False,
            "refused": True,
            "reason": "invoice_not_found",
            "code": "invoice_not_found",
        }

    if invoice.get("status") == "paid":
        return {
            "executed": False,
            "refused": True,
            "reason": "invoice_already_paid",
            "code": "invoice_already_paid",
        }
    if invoice.get("status") == "cancelled":
        return {
            "executed": False,
            "refused": True,
            "reason": "invoice_cancelled",
            "code": "invoice_cancelled",
        }

    if tool_id == "send_invoice_reminder":
        return await _run_reminder(db, client_id, invoice, method)
    return await _run_send(db, client_id, invoice, method)


async def _run_send(db: Any, client_id: str, invoice: dict, method: str) -> dict:
    if invoice.get("status") == "sent" and invoice.get("stripe_payment_link"):
        return {
            "executed": False,
            "adopted": True,
            "verified": True,
            "reason": "already_sent",
            "result": {
                "id": invoice["id"],
                "invoice_number": invoice.get("invoice_number"),
                "payment_link": invoice.get("stripe_payment_link"),
                "email_sent": False,
                "sms_sent": False,
                "deduplicated": True,
            },
        }

    try:
        sent = await _send_channels(db, client_id, invoice, method, reminder=False)
    except TimeoutError:
        return {
            "executed": True,
            "unknown": True,
            "reason": "invoice send timed out; outcome unknown",
        }
    except Exception as exc:
        logger.exception("invoice send failed invoice_id=%s", invoice.get("id"))
        return {
            "executed": False,
            "reason": f"provider_error:{exc}",
            "code": "provider_error",
        }

    delivered = sent["email_sent"] or sent["sms_sent"]
    payment_link = sent["payment_link"]
    total = float(invoice.get("total") or 0)
    if not delivered:
        return {
            "executed": True,
            "verified": False,
            "reason": "; ".join(sent["errors"]) or "send failed",
            "code": "send_failed",
            "result": {
                "id": invoice["id"],
                "errors": sent["errors"],
                "payment_link": payment_link,
            },
        }

    update = {
        "status": "sent",
        "sent_at": _now(),
        "sent_via": method,
        "updated_at": _now(),
    }
    if payment_link:
        update["stripe_payment_link"] = payment_link
    tenant_table(db, "invoices", client_id).update(update).eq("id", invoice["id"]).eq(
        "tenant_id", client_id
    ).execute()

    read_back = _load_invoice(db, client_id, invoice["id"])
    if not read_back or read_back.get("status") not in ("sent", "viewed", "overdue"):
        return {
            "executed": True,
            "verified": False,
            "reason": "invoice send could not be verified on read-back",
            "code": "invoice_verify_failed",
        }
    if total > 0 and not (read_back.get("stripe_payment_link") or payment_link):
        return {
            "executed": True,
            "verified": False,
            "reason": "payment link was not created",
            "code": "payment_link_missing",
        }

    return {
        "executed": True,
        "adopted": False,
        "verified": True,
        "reason": "sent",
        "result": {
            "id": invoice["id"],
            "invoice_number": read_back.get("invoice_number"),
            "payment_link": read_back.get("stripe_payment_link") or payment_link,
            "email_sent": sent["email_sent"],
            "sms_sent": sent["sms_sent"],
            "deduplicated": False,
        },
    }


async def _run_reminder(db: Any, client_id: str, invoice: dict, method: str) -> dict:
    if not _is_overdue(invoice):
        return {
            "executed": False,
            "refused": True,
            "reason": "invoice_not_overdue",
            "code": "invoice_not_overdue",
        }
    if _reminder_already_sent(db, client_id, invoice["id"], invoice.get("lead_id")):
        return {
            "executed": False,
            "adopted": True,
            "verified": True,
            "reason": "reminder_already_sent_today",
            "result": {
                "id": invoice["id"],
                "invoice_number": invoice.get("invoice_number"),
                "deduplicated": True,
            },
        }

    try:
        sent = await _send_channels(db, client_id, invoice, method, reminder=True)
    except TimeoutError:
        return {
            "executed": True,
            "unknown": True,
            "reason": "invoice reminder timed out; outcome unknown",
        }
    except Exception as exc:
        logger.exception("invoice reminder failed invoice_id=%s", invoice.get("id"))
        return {
            "executed": False,
            "reason": f"provider_error:{exc}",
            "code": "provider_error",
        }

    if not (sent["email_sent"] or sent["sms_sent"]):
        return {
            "executed": True,
            "verified": False,
            "reason": "; ".join(sent["errors"]) or "reminder send failed",
            "code": "send_failed",
        }

    try:
        _log_reminder(db, client_id, invoice)
    except Exception:
        logger.warning("invoice reminder activity log failed", exc_info=True)

    read_back = _load_invoice(db, client_id, invoice["id"])
    if read_back and read_back.get("status") == "paid":
        return {
            "executed": True,
            "verified": False,
            "reason": "invoice became paid; reminder must not claim a paid send",
            "code": "invoice_already_paid",
        }

    return {
        "executed": True,
        "adopted": False,
        "verified": True,
        "reason": "reminder_sent",
        "result": {
            "id": invoice["id"],
            "invoice_number": invoice.get("invoice_number"),
            "payment_link": sent["payment_link"] or invoice.get("stripe_payment_link"),
            "email_sent": sent["email_sent"],
            "sms_sent": sent["sms_sent"],
            "deduplicated": False,
        },
    }
