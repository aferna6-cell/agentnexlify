"""Agent OS action handler: calendar.event.create.

Fires after a booking deliverable is approved. Extracts a structured event
payload (summary, start_utc, end_utc, attendee_email, description) from the
approved deliverable via a cheap Haiku call, then creates a calendar event
using whichever provider the tenant has connected.

Runtime dispatch: looks up ``integrations`` row for this tenant. Prefers
``google_calendar`` if connected; otherwise falls back to ``m365_calendar``
(Outlook). If neither is connected, the run is marked ``failed`` with a
clear error_detail so the UI can prompt the owner to connect one.

Why dispatch lives here instead of forking action_types: the booking worker
stays provider-agnostic (one ``calendar.event.create`` emit point) and the
tenant can swap providers without changing worker code. The price is a
small dispatch branch — far less code than maintaining a second worker
emit path.
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta, timezone

from backend.services import google_calendar, m365_calendar
from backend.services.llm_runtime import call_claude_messages
from backend.services.os_actions.base import ActionContext, ActionResult, ActionSpec

logger = logging.getLogger(__name__)

_EXTRACTION_SYSTEM = """\
You extract a calendar-event payload from an approved booking message.
Return STRICT JSON with these keys:
- summary (string, short event title)
- start_utc (ISO-8601 UTC string, e.g. "2026-06-01T15:00:00+00:00")
- end_utc (ISO-8601 UTC string)
- attendee_email (string or null)
- description (string or null)

If the message references a date without a year, use the next reasonable \
upcoming occurrence. If duration is unclear, default to 60 minutes. If you \
cannot determine a valid start time, return {"error": "<short reason>"}.\
"""


def _parse_json_block(text: str) -> dict | None:
    """Best-effort JSON extraction — strips code fences if Claude wraps."""
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


async def _extract_event_payload(deliverable_body: str, client_id: str) -> dict:
    """Ask Haiku to turn the approved markdown into a structured event payload."""
    response = await call_claude_messages(
        operation="os_action_calendar_extract",
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        system=_EXTRACTION_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": f"Approved booking message:\n\n{deliverable_body}",
            }
        ],
        metadata={"client_id": client_id},
    )
    payload = _parse_json_block(response.text) or {}
    return payload


def _calendar_event_from_deliverable(deliverable: dict) -> dict | None:
    """Structured event parked by the chat draft. Skips the Haiku extract.

    The card already carries start and end. A missing end is a refusal,
    not a silent 60-minute event.
    """
    event = (deliverable or {}).get("calendar_event")
    if not isinstance(event, dict):
        return None
    summary = str(event.get("summary") or "").strip()
    start_utc = event.get("start_utc")
    end_utc = event.get("end_utc")
    if not summary or not start_utc or not end_utc:
        return None
    return {
        "summary": summary,
        "start_utc": start_utc,
        "end_utc": end_utc,
        "attendee_email": event.get("attendee_email"),
        "description": event.get("description"),
        "duration_minutes": event.get("duration_minutes"),
    }


def claim_calendar_approval(db, client_id: str, run_id: str) -> dict | None:
    """Claim a pending calendar card once.

    Same conditional update as ``os_tool_executions.claim_for_execution``:
    the status filter is part of the write, so a second Approve gets no row
    and must not insert.
    """
    from backend.services.os_actions.base import now_iso
    from backend.services.tenant_scope import tenant_table

    updated = (
        tenant_table(db, "os_agent_runs", client_id)
        .update({"deliverable_status": "approved", "updated_at": now_iso()})
        .eq("id", run_id)
        .eq("action_type", "calendar.event.create")
        .eq("deliverable_status", "pending_approval")
        .execute()
        .data
    )
    return updated[0] if updated else None


async def _run(ctx: ActionContext) -> ActionResult:
    body = (ctx.deliverable.get("body") or "").strip()
    structured = _calendar_event_from_deliverable(ctx.deliverable)
    if structured is None and not body:
        return ActionResult(
            status="failed",
            error_detail={"message": "deliverable has empty body"},
        )

    if structured is not None:
        created = await asyncio.to_thread(
            google_calendar.insert_approved_calendar_event,
            ctx.db,
            ctx.client_id,
            ctx.deliverable_id,
        )
        request_payload = {
            "summary": structured["summary"],
            "start_utc": structured["start_utc"],
            "end_utc": structured["end_utc"],
            "attendee_email": structured.get("attendee_email"),
            "description": structured.get("description"),
            "duration_minutes": structured.get("duration_minutes"),
        }
        if not created.get("ok"):
            return ActionResult(
                status="failed",
                request_payload=request_payload,
                error_detail={
                    "stage": created.get("code") or "refused",
                    "message": created.get("message"),
                    "provider": "google_calendar",
                },
            )
        return ActionResult(
            status="succeeded",
            request_payload=request_payload,
            response_payload={
                "event_id": created.get("event_id"),
                "calendar": "primary",
                "provider": "google_calendar",
                "deduplicated": bool(created.get("deduplicated")),
            },
        )
    else:
        try:
            payload = await _extract_event_payload(body, ctx.client_id)
        except Exception as e:
            logger.warning(
                "os_action_calendar: extraction failed client_id=%s deliverable_id=%s",
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

    summary = payload.get("summary") or "Booking"
    start_utc = payload.get("start_utc")
    end_utc = payload.get("end_utc")
    attendee_email = payload.get("attendee_email")
    description = payload.get("description") or (body[:500] if body else None)

    if not start_utc:
        return ActionResult(
            status="failed",
            request_payload=payload,
            error_detail={"stage": "validate", "message": "missing start_utc"},
        )
    if not end_utc:
        try:
            start_dt = datetime.fromisoformat(start_utc.replace("Z", "+00:00"))
            end_dt = (start_dt + timedelta(minutes=60)).astimezone(timezone.utc)
            end_utc = end_dt.isoformat()
        except Exception:
            return ActionResult(
                status="failed",
                request_payload=payload,
                error_detail={"stage": "validate", "message": "invalid start_utc"},
            )

    request_payload = {
        "summary": summary,
        "start_utc": start_utc,
        "end_utc": end_utc,
        "attendee_email": attendee_email,
        "description": description,
    }

    provider = _pick_provider(ctx.client_id)
    if provider is None:
        return ActionResult(
            status="failed",
            request_payload=request_payload,
            error_detail={
                "stage": "connector",
                "message": (
                    "no calendar provider connected for this tenant — "
                    "connect google_calendar or m365_calendar"
                ),
            },
        )

    try:
        if provider == "google_calendar":
            event_id = await asyncio.to_thread(
                google_calendar.create_calendar_event,
                ctx.client_id,
                summary,
                start_utc,
                end_utc,
                attendee_email,
                description,
            )
        else:  # m365_calendar
            event_id = await asyncio.to_thread(
                m365_calendar.create_calendar_event,
                ctx.client_id,
                summary,
                start_utc,
                end_utc,
                attendee_email,
                description,
            )
    except Exception as e:
        logger.exception(
            "os_action_calendar: %s create failed client_id=%s",
            provider,
            ctx.client_id,
        )
        return ActionResult(
            status="failed",
            request_payload=request_payload,
            error_detail={
                "stage": f"{provider}_create",
                "message": str(e)[:300],
                "provider": provider,
            },
        )

    if not event_id:
        return ActionResult(
            status="failed",
            request_payload=request_payload,
            error_detail={
                "stage": f"{provider}_create",
                "message": (f"{provider} returned no event id (auth or API error)"),
                "provider": provider,
            },
        )

    return ActionResult(
        status="succeeded",
        request_payload=request_payload,
        response_payload={
            "event_id": event_id,
            "calendar": "primary",
            "provider": provider,
        },
    )


def _pick_provider(client_id: str) -> str | None:
    """Return the calendar provider name to dispatch on, or None.

    Preference order: ``google_calendar`` -> ``m365_calendar``. Stable order
    keeps existing google-connected tenants behaving exactly as before
    (zero migration cost). M365 only activates for tenants that have ONLY
    m365_calendar connected.
    """
    try:
        if google_calendar.get_integration(client_id):
            return "google_calendar"
    except Exception:
        logger.warning(
            "os_action_calendar: google_calendar lookup failed client_id=%s",
            client_id,
            exc_info=True,
        )
    try:
        if m365_calendar.get_integration(client_id):
            return "m365_calendar"
    except Exception:
        logger.warning(
            "os_action_calendar: m365_calendar lookup failed client_id=%s",
            client_id,
            exc_info=True,
        )
    return None


SPEC = ActionSpec(
    name="calendar.event.create",
    worker="booking",
    run=_run,
    required_connectors=["google_calendar", "m365_calendar"],
    description=(
        "Create a calendar event from an approved booking deliverable. "
        "Dispatches to Google Calendar or Microsoft 365 / Outlook based on "
        "the tenant's connected integration."
    ),
)
