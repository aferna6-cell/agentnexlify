"""Agent OS action handler: crm.contact_upsert.

Upserts a contact row in the tenant's ``leads`` table after the owner
approves a lead-capture or follow-up deliverable that produced new contact
info. Dedup by email (case-insensitive); falls back to phone if no email.

Required connectors: none — writes directly to ``leads``.
"""

import json
import logging
import re

from backend.services.hubspot_tenant import is_connected as hubspot_is_connected
from backend.services.hubspot_tenant import upsert_contact as hubspot_upsert_contact
from backend.services.llm_runtime import call_claude_messages
from backend.services.os_actions.base import ActionContext, ActionResult, ActionSpec
from backend.services.tenant_scope import tenant_insert, tenant_select, tenant_update

# Re-export for test patching (`patch.object(crm, "hubspot_is_connected", ...)`).
__all__ = ["hubspot_is_connected", "hubspot_upsert_contact", "SPEC"]

logger = logging.getLogger(__name__)

_EXTRACTION_SYSTEM = """\
You extract a CRM contact payload from an approved message.
Return STRICT JSON with these keys:
- name (string or null)
- email (string or null)
- phone (string or null, digits + +)
- notes (string or null, short summary of the conversation)
- areas_of_interest (array of strings or null)

If you cannot extract at least one of email or phone, return
{"error": "no contact identifier"}.\
"""

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def _parse_json_block(text: str) -> dict | None:
    if not text:
        return None
    stripped = text.strip()
    if stripped.startswith("```"):
        match = re.search(r"```(?:json)?\s*(.+?)```", stripped, re.DOTALL)
        if match:
            stripped = match.group(1).strip()
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
    except (json.JSONDecodeError, ValueError):
        pass
    return None


async def _extract_contact(body: str, client_id: str) -> dict:
    response = await call_claude_messages(
        operation="os_action_crm_extract",
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        system=_EXTRACTION_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": f"Approved deliverable:\n\n{body}",
            }
        ],
        metadata={"client_id": client_id},
    )
    return _parse_json_block(response.text) or {}


def _find_existing(
    db, client_id: str, email: str | None, phone: str | None
) -> dict | None:
    if email:
        rows = (
            tenant_select(db, "leads", client_id, "id, name, email, phone, notes")
            .ilike("email", email)
            .limit(1)
            .execute()
        )
        if rows.data:
            return rows.data[0]
    if phone:
        rows = (
            tenant_select(db, "leads", client_id, "id, name, email, phone, notes")
            .eq("phone", phone)
            .limit(1)
            .execute()
        )
        if rows.data:
            return rows.data[0]
    return None


async def _run(ctx: ActionContext) -> ActionResult:
    body = (ctx.deliverable.get("body") or "").strip()
    if not body:
        return ActionResult(
            status="failed",
            error_detail={"message": "deliverable has empty body"},
        )

    try:
        payload = await _extract_contact(body, ctx.client_id)
    except Exception as e:
        logger.warning(
            "os_action_crm: extraction failed client_id=%s deliverable_id=%s",
            ctx.client_id,
            ctx.deliverable_id,
            exc_info=True,
        )
        return ActionResult(
            status="failed",
            error_detail={"stage": "extract", "message": str(e)[:300]},
        )

    if "error" in payload:
        return ActionResult(
            status="failed",
            error_detail={"stage": "extract", "message": payload["error"]},
        )

    email = (payload.get("email") or "").strip() or None
    phone = (payload.get("phone") or "").strip() or None
    name = (payload.get("name") or "").strip() or None
    notes = (payload.get("notes") or "").strip() or None
    interests = payload.get("areas_of_interest") or None
    if isinstance(interests, str):
        interests = [interests]

    if not email and not phone:
        return ActionResult(
            status="failed",
            request_payload=payload,
            error_detail={"stage": "validate", "message": "no contact identifier"},
        )
    if email and not _EMAIL_RE.match(email):
        return ActionResult(
            status="failed",
            request_payload=payload,
            error_detail={"stage": "validate", "message": "invalid email format"},
        )

    request_payload = {
        "name": name,
        "email": email,
        "phone": phone,
        "notes": notes,
        "areas_of_interest": interests,
    }

    try:
        existing = _find_existing(ctx.db, ctx.client_id, email, phone)
    except Exception as e:
        logger.exception("os_action_crm: lookup failed client_id=%s", ctx.client_id)
        return ActionResult(
            status="failed",
            request_payload=request_payload,
            error_detail={"stage": "lookup", "message": str(e)[:300]},
        )

    try:
        if existing:
            update_payload: dict = {}
            if name and not existing.get("name"):
                update_payload["name"] = name
            if email and not existing.get("email"):
                update_payload["email"] = email
            if phone and not existing.get("phone"):
                update_payload["phone"] = phone
            if interests:
                update_payload["areas_of_interest"] = interests
            if notes:
                existing_notes = (existing.get("notes") or "").strip()
                combined = (
                    (existing_notes + "\n\n" + notes).strip()
                    if existing_notes
                    else notes
                )
                update_payload["notes"] = combined[:4000]
            if update_payload:
                tenant_update(ctx.db, "leads", ctx.client_id, update_payload).eq(
                    "id", existing["id"]
                ).execute()
            lead_id = existing["id"]
            operation = "updated"
        else:
            insert_row = {
                k: v
                for k, v in {
                    "name": name or "Lead from agent",
                    "email": email,
                    "phone": phone,
                    "notes": notes,
                    "areas_of_interest": interests,
                    "status": "new",
                    "source": "agent_os",
                }.items()
                if v is not None
            }
            result = tenant_insert(ctx.db, "leads", ctx.client_id, insert_row).execute()
            rows = result.data or []
            lead_id = rows[0].get("id") if rows else None
            operation = "inserted"
    except Exception as e:
        logger.exception("os_action_crm: upsert failed client_id=%s", ctx.client_id)
        return ActionResult(
            status="failed",
            request_payload=request_payload,
            error_detail={"stage": "upsert", "message": str(e)[:300]},
        )

    response_payload: dict = {"lead_id": lead_id, "operation": operation}

    # ── HubSpot runtime dispatch ─────────────────────────────────
    # If the tenant has connected HubSpot, ALSO push the contact to HubSpot.
    # Hard-fail the whole action on push failure — internal lead_id stays in
    # response_payload for observability, owner sees clear error, forces fix.
    try:
        hubspot_connected = hubspot_is_connected(ctx.client_id)
    except Exception:
        logger.warning(
            "os_action_crm: hubspot_is_connected check failed client_id=%s",
            ctx.client_id,
            exc_info=True,
        )
        hubspot_connected = False

    if hubspot_connected:
        try:
            hubspot_result = await hubspot_upsert_contact(
                tenant_id=ctx.client_id, payload=request_payload
            )
        except Exception as e:
            logger.exception(
                "os_action_crm: hubspot push raised client_id=%s", ctx.client_id
            )
            hubspot_result = {
                "success": False,
                "detail": f"unexpected exception: {str(e)[:200]}",
            }

        response_payload["hubspot_push"] = hubspot_result
        if not hubspot_result.get("success"):
            return ActionResult(
                status="failed",
                request_payload=request_payload,
                response_payload=response_payload,
                error_detail={
                    "stage": "hubspot_push",
                    "message": str(
                        hubspot_result.get("detail") or "hubspot push failed"
                    )[:300],
                },
            )
        response_payload["hubspot_contact_id"] = hubspot_result.get("contact_id")

    return ActionResult(
        status="succeeded",
        request_payload=request_payload,
        response_payload=response_payload,
    )


SPEC = ActionSpec(
    name="crm.contact_upsert",
    worker="lead_nurture",
    run=_run,
    required_connectors=[],
    description="Upsert a contact in leads table, dedup by email then phone.",
)
