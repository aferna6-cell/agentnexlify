"""Agent OS action handler: calendar.event.create.

Fires after a booking deliverable is approved. Extracts a structured event
payload (summary, start_utc, end_utc, attendee_email, description) from the
approved deliverable via a cheap Haiku call, then creates a Google Calendar
event using the tenant's stored OAuth credentials.

Required connectors: ``google_calendar``. If the tenant has no Google
Calendar integration the run is marked ``failed`` with a clear error_detail
so the UI can prompt the owner to connect.
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta, timezone

from backend.services import google_calendar
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


async def _run(ctx: ActionContext) -> ActionResult:
    body = (ctx.deliverable.get("body") or "").strip()
    if not body:
        return ActionResult(
            status="failed",
            error_detail={"message": "deliverable has empty body"},
        )

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
    description = payload.get("description") or body[:500]

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

    integration = google_calendar.get_integration(ctx.client_id)
    if not integration:
        return ActionResult(
            status="failed",
            request_payload=request_payload,
            error_detail={
                "stage": "connector",
                "message": "google_calendar not connected for this tenant",
            },
        )

    try:
        event_id = await asyncio.to_thread(
            google_calendar.create_calendar_event,
            ctx.client_id,
            summary,
            start_utc,
            end_utc,
            attendee_email,
            description,
        )
    except Exception as e:
        logger.exception(
            "os_action_calendar: gcal create failed client_id=%s", ctx.client_id
        )
        return ActionResult(
            status="failed",
            request_payload=request_payload,
            error_detail={"stage": "gcal_create", "message": str(e)[:300]},
        )

    if not event_id:
        return ActionResult(
            status="failed",
            request_payload=request_payload,
            error_detail={
                "stage": "gcal_create",
                "message": "Google Calendar returned no event id (auth or API error)",
            },
        )

    return ActionResult(
        status="succeeded",
        request_payload=request_payload,
        response_payload={"event_id": event_id, "calendar": "primary"},
    )


SPEC = ActionSpec(
    name="calendar.event.create",
    worker="booking",
    run=_run,
    required_connectors=["google_calendar"],
    description="Create a Google Calendar event from an approved booking deliverable.",
)
