"""Milestone 8 Calendar + CRM data-plane apply / L2 runners.

Distinct from ``backend/services/os_actions/`` deliverable handlers.
Action Executor tools reach here only through claim-gated approve (L2) or
``persist_tool_executions`` apply (L1 Collecting bundles).

Honest guarantees:
- Idempotency is claim-gate + fingerprint / idempotency_key (best-effort).
- Google has no native idempotency token — do not claim exactly-once.
- Verification is an independent GET / lead read-back; unknown stays non-success.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.services.m8_action_flags import (
    calendar_actions_enabled,
    crm_actions_enabled,
)
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

CANONICAL_LEAD_STATUSES = frozenset(
    {"new", "contacted", "appointment_booked", "closed", "lost"}
)

CALENDAR_L2_TOOL_IDS = frozenset(
    {
        "create_calendar_event",
        "reschedule_calendar_event",
        "cancel_calendar_event",
    }
)
CRM_MUTATION_TOOL_IDS = frozenset(
    {"update_customer", "create_customer", "update_lead_stage"}
)


def refuse_calendar_tool(*, tool_id: str | None = None) -> str | None:
    if tool_id and tool_id not in CALENDAR_L2_TOOL_IDS and tool_id != (
        "get_calendar_availability"
    ):
        return None
    if not calendar_actions_enabled():
        return "calendar actions are disabled (CALENDAR_ACTIONS_ENABLED defaults off)"
    return None


def refuse_crm_tool(*, tool_id: str | None = None) -> str | None:
    if tool_id and tool_id not in CRM_MUTATION_TOOL_IDS and tool_id not in (
        "get_customer",
        "search_customers",
    ):
        return None
    if not crm_actions_enabled():
        return "CRM actions are disabled (CRM_ACTIONS_ENABLED defaults off)"
    return None


def fetch_calendar_busy_snapshot(
    client_id: str,
    *,
    days: int = 7,
) -> list[dict[str, str]]:
    """Busy intervals for SharedContext seeding. Empty if unverifiable."""
    try:
        from backend.services.google_calendar import get_busy_times, get_integration

        if not get_integration(client_id):
            return []
        now = datetime.now(timezone.utc)
        busy = get_busy_times(client_id, now, now + timedelta(days=days))
        if busy is None:
            return []
        return [
            {"start": start.isoformat(), "end": end.isoformat()} for start, end in busy
        ]
    except Exception:
        logger.warning(
            "calendar busy snapshot failed client_id=%s", client_id, exc_info=True
        )
        return []


def fetch_availability(
    client_id: str,
    *,
    start: str,
    end: str,
    duration_minutes: int,
    timezone_name: str | None = None,
) -> dict[str, Any]:
    """Real availability via booking slots + Google freebusy (fail-closed)."""
    from backend.services import booking
    from backend.services.google_calendar import get_busy_times, get_integration

    try:
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
    except ValueError as exc:
        return {
            "available_slots": [],
            "busy_intervals": [],
            "provider": "error",
            "timezone": timezone_name or "UTC",
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "error": f"invalid_window:{exc}",
        }

    tz_name = timezone_name
    hours = booking.get_business_hours(client_id)
    if hours and not tz_name:
        tz_name = hours.get("timezone") or "America/New_York"
    tz_name = tz_name or "America/New_York"

    busy_intervals: list[dict[str, str]] = []
    provider = "local_appointments"
    if get_integration(client_id):
        gbusy = get_busy_times(client_id, start_dt, end_dt)
        if gbusy is None:
            return {
                "available_slots": [],
                "busy_intervals": [],
                "provider": "google_calendar",
                "timezone": tz_name,
                "verified_at": datetime.now(timezone.utc).isoformat(),
                "error": "freebusy_unverifiable",
            }
        busy_intervals = [
            {"start": s.isoformat(), "end": e.isoformat()} for s, e in gbusy
        ]
        provider = "google_calendar"

    slots: list[dict[str, str]] = []
    day = start_dt.date()
    last = end_dt.date()
    while day <= last:
        for s in booking.generate_available_slots(client_id, day):
            slot_start = s.get("start_utc") or ""
            slot_end = s.get("end_utc") or ""
            if not slot_start or not slot_end:
                continue
            if slot_start < start or slot_end > end:
                continue
            try:
                dur = (
                    datetime.fromisoformat(slot_end.replace("Z", "+00:00"))
                    - datetime.fromisoformat(slot_start.replace("Z", "+00:00"))
                ).total_seconds() / 60
            except ValueError:
                continue
            if dur + 0.1 < duration_minutes:
                continue
            if any(
                b["end"] > slot_start and b["start"] < slot_end for b in busy_intervals
            ):
                continue
            slots.append({"start": slot_start, "end": slot_end})
        day = day + timedelta(days=1)

    return {
        "available_slots": slots,
        "busy_intervals": busy_intervals,
        "provider": provider,
        "timezone": tz_name,
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }


def apply_crm_mutations(
    db: Any,
    client_id: str,
    customers: list[dict],
    executions: list[dict] | None = None,
) -> list[dict]:
    """Apply CRM Collecting mutations to ``leads`` with read-back verification."""
    if not crm_actions_enabled():
        logger.info("apply_crm_mutations skipped — CRM_ACTIONS_ENABLED off")
        return []

    outcomes: list[dict] = []
    for cust in customers:
        customer_id = cust.get("id") or cust.get("customerId")
        if not customer_id:
            outcomes.append(
                {"customer_id": None, "applied": False, "detail": "missing id"}
            )
            continue
        op = (cust.get("_op") or cust.get("op") or "upsert").lower()
        try:
            if op == "create":
                applied, detail, row = _create_lead(db, client_id, cust)
            elif op == "stage":
                applied, detail, row = _update_lead_stage(
                    db, client_id, customer_id, cust.get("status") or ""
                )
            else:
                applied, detail, row = _update_lead_fields(
                    db, client_id, customer_id, cust
                )
        except Exception as exc:
            logger.exception("CRM apply failed customer_id=%s", customer_id)
            applied, detail, row = False, f"error:{exc}", None

        outcomes.append(
            {
                "customer_id": customer_id,
                "applied": applied,
                "detail": detail,
                "row": row,
            }
        )
        if not applied:
            _mark_execution_unverified(
                db,
                client_id,
                customer_id,
                detail,
                executions,
                match_field="customerId",
            )
    return outcomes


def _create_lead(db: Any, client_id: str, cust: dict) -> tuple[bool, str, dict | None]:
    email = (cust.get("email") or "").strip().lower() or None
    phone = (cust.get("phone") or "").strip() or None
    name = (cust.get("name") or "").strip()
    if not name:
        return False, "name_required", None

    existing = None
    if email:
        hit = (
            tenant_table(db, "leads", client_id)
            .select("*")
            .eq("email", email)
            .limit(1)
            .execute()
        )
        existing = (hit.data or [None])[0]
    if existing is None and phone:
        hit = (
            tenant_table(db, "leads", client_id)
            .select("*")
            .eq("phone", phone)
            .limit(1)
            .execute()
        )
        existing = (hit.data or [None])[0]
    if existing:
        return True, "deduplicated", existing

    payload = {
        "client_id": client_id,
        "name": name,
        "email": email,
        "phone": phone,
        "status": (cust.get("status") or "new").strip().lower(),
    }
    inserted = tenant_table(db, "leads", client_id).insert(payload).execute()
    row = (inserted.data or [None])[0]
    if not row:
        return False, "insert_failed", None
    got = (
        tenant_table(db, "leads", client_id)
        .select("*")
        .eq("id", row["id"])
        .limit(1)
        .execute()
    )
    verified = (got.data or [None])[0]
    if not verified or verified.get("name") != name:
        return False, "readback_mismatch", row
    return True, "created", verified


def _update_lead_fields(
    db: Any, client_id: str, customer_id: str, cust: dict
) -> tuple[bool, str, dict | None]:
    existing = (
        tenant_table(db, "leads", client_id)
        .select("*")
        .eq("id", customer_id)
        .limit(1)
        .execute()
    )
    before = (existing.data or [None])[0]
    if not before:
        return False, "customer_not_found", None

    fields = cust.get("fields") or cust
    patch: dict[str, Any] = {}
    for key in ("phone", "email", "name"):
        if key in fields and fields[key] is not None:
            patch[key] = fields[key]
    if not patch:
        return True, "no_field_changes", before

    tenant_table(db, "leads", client_id).update(patch).eq("id", customer_id).execute()
    got = (
        tenant_table(db, "leads", client_id)
        .select("*")
        .eq("id", customer_id)
        .limit(1)
        .execute()
    )
    after = (got.data or [None])[0]
    if not after:
        return False, "readback_missing", None
    for k, v in patch.items():
        if after.get(k) != v:
            return False, f"readback_mismatch:{k}", after
    for k in ("email", "phone", "name", "status"):
        if k not in patch and before.get(k) != after.get(k):
            return False, f"field_not_preserved:{k}", after
    return True, "updated", after


def _update_lead_stage(
    db: Any, client_id: str, customer_id: str, status: str
) -> tuple[bool, str, dict | None]:
    status = (status or "").strip().lower()
    allowed = set(CANONICAL_LEAD_STATUSES)
    try:
        stages = (
            tenant_table(db, "pipeline_stages", client_id).select("name").execute().data
            or []
        )
        names = {
            str(s.get("name") or "").strip().lower() for s in stages if s.get("name")
        }
        if names:
            allowed |= names
    except Exception:
        pass
    if status not in allowed:
        return False, "invalid_lead_stage", None

    existing = (
        tenant_table(db, "leads", client_id)
        .select("*")
        .eq("id", customer_id)
        .limit(1)
        .execute()
    )
    before = (existing.data or [None])[0]
    if not before:
        return False, "customer_not_found", None

    tenant_table(db, "leads", client_id).update({"status": status}).eq(
        "id", customer_id
    ).execute()
    got = (
        tenant_table(db, "leads", client_id)
        .select("*")
        .eq("id", customer_id)
        .limit(1)
        .execute()
    )
    after = (got.data or [None])[0]
    if not after or (after.get("status") or "").lower() != status:
        return False, "readback_mismatch", after
    return True, "stage_updated", after


def apply_calendar_mutations(
    db: Any,
    client_id: str,
    events: list[dict],
    executions: list[dict] | None = None,
) -> list[dict]:
    """Apply Collecting calendar events to appointments (+ optional Google)."""
    if not calendar_actions_enabled():
        logger.info("apply_calendar_mutations skipped — CALENDAR_ACTIONS_ENABLED off")
        return []

    outcomes: list[dict] = []
    for ev in events:
        event_id = ev.get("id") or ev.get("eventId")
        status = (ev.get("status") or "confirmed").lower()
        try:
            if status == "cancelled":
                applied, detail, row = _cancel_local_event(db, client_id, ev)
            else:
                applied, detail, row = _upsert_local_event(db, client_id, ev)
        except Exception as exc:
            logger.exception("calendar apply failed event_id=%s", event_id)
            applied, detail, row = False, f"error:{exc}", None
        outcomes.append(
            {"event_id": event_id, "applied": applied, "detail": detail, "row": row}
        )
        if not applied:
            _mark_execution_unverified(
                db, client_id, event_id, detail, executions, match_field="eventId"
            )
    return outcomes


def _upsert_local_event(
    db: Any, client_id: str, ev: dict
) -> tuple[bool, str, dict | None]:
    from backend.services import booking
    from backend.services.google_calendar import (
        create_calendar_event,
        get_calendar_event,
        get_integration,
    )

    start = ev.get("start")
    end = ev.get("end")
    title = ev.get("title") or "Appointment"
    if not (start and end):
        return False, "missing_time", None

    existing = (
        tenant_table(db, "appointments", client_id)
        .select("*")
        .eq("start_time", start)
        .eq("end_time", end)
        .neq("status", "cancelled")
        .limit(5)
        .execute()
        .data
        or []
    )
    match = None
    for row in existing:
        if title and title in (row.get("notes") or ""):
            match = row
            break
    if match:
        return True, "deduplicated", match

    customer_name = "Customer"
    customer_email = "noreply@agentnexlify.local"
    attendees = ev.get("attendees") or []
    if attendees and attendees[0].get("email"):
        customer_email = attendees[0]["email"]
        customer_name = attendees[0].get("displayName") or customer_name
    if ev.get("customerId"):
        lead = (
            tenant_table(db, "leads", client_id)
            .select("name,email")
            .eq("id", ev["customerId"])
            .limit(1)
            .execute()
        )
        lead_row = (lead.data or [None])[0]
        if lead_row:
            customer_name = lead_row.get("name") or customer_name
            customer_email = lead_row.get("email") or customer_email

    send_invites = bool(ev.get("sendInvitations"))
    appt = booking.create_appointment(
        tenant_id=client_id,
        customer_name=customer_name,
        customer_email=customer_email,
        start_time=start,
        end_time=end,
        notes=title,
    )
    google_id = appt.get("google_event_id")
    if send_invites and get_integration(client_id) and not google_id:
        google_id = create_calendar_event(
            client_id,
            summary=title,
            start_utc=start,
            end_utc=end,
            attendee_email=customer_email,
            description=ev.get("description"),
        )
        if google_id:
            tenant_table(db, "appointments", client_id).update(
                {"google_event_id": google_id}
            ).eq("id", appt["id"]).execute()
            appt["google_event_id"] = google_id

    if google_id:
        fetched = get_calendar_event(client_id, google_id)
        if not fetched:
            return False, "google_verify_missing", appt
        if fetched.get("start") and start[:16] not in (fetched.get("start") or ""):
            return False, "google_verify_time_mismatch", appt
    return True, "created", appt


def _cancel_local_event(
    db: Any, client_id: str, ev: dict
) -> tuple[bool, str, dict | None]:
    from backend.services import booking
    from backend.services.google_calendar import (
        delete_calendar_event,
        get_calendar_event,
        get_integration,
    )

    appt_id = ev.get("appointmentId") or ev.get("id")
    google_id = ev.get("providerEventId") or ev.get("google_event_id")
    row = None
    if appt_id:
        hit = (
            tenant_table(db, "appointments", client_id)
            .select("*")
            .eq("id", appt_id)
            .limit(1)
            .execute()
        )
        row = (hit.data or [None])[0]
    if row is None and google_id:
        hit = (
            tenant_table(db, "appointments", client_id)
            .select("*")
            .eq("google_event_id", google_id)
            .limit(1)
            .execute()
        )
        row = (hit.data or [None])[0]
    if row is None:
        return False, "event_not_found", None

    cancelled = booking.cancel_appointment(client_id, row["id"])
    gid = cancelled.get("google_event_id") or google_id
    if gid and get_integration(client_id):
        delete_calendar_event(client_id, gid)
        fetched = get_calendar_event(client_id, gid)
        if fetched and (fetched.get("status") or "").lower() not in (
            "cancelled",
            "canceled",
        ):
            return False, "google_still_active", cancelled
    return True, "cancelled", cancelled


def run_calendar_l2(db: Any, client_id: str, execution: dict) -> dict[str, Any]:
    """Execute a claimed L2 calendar tool against booking/Google + verify."""
    reason = refuse_calendar_tool(tool_id=execution.get("tool_id"))
    if reason:
        return {
            "executed": False,
            "refused": True,
            "reason": reason,
            "unknown": False,
        }

    tool_id = execution.get("tool_id") or ""
    inp = execution.get("input") or {}
    try:
        if tool_id == "create_calendar_event":
            applied, detail, row = _upsert_local_event(
                db,
                client_id,
                {
                    "start": inp.get("start"),
                    "end": inp.get("end"),
                    "title": inp.get("title"),
                    "description": inp.get("description"),
                    "attendees": [
                        {
                            "email": a.get("email"),
                            "displayName": a.get("display_name")
                            or a.get("displayName"),
                        }
                        for a in (inp.get("attendees") or [])
                    ],
                    "customerId": inp.get("customer_id"),
                    "sendInvitations": bool(inp.get("send_invitations")),
                },
            )
        elif tool_id == "reschedule_calendar_event":
            applied, detail, row = _reschedule_l2(db, client_id, inp)
        elif tool_id == "cancel_calendar_event":
            applied, detail, row = _cancel_local_event(
                db,
                client_id,
                {
                    "id": inp.get("event_id"),
                    "appointmentId": inp.get("event_id"),
                    "providerEventId": inp.get("provider_event_id"),
                },
            )
        else:
            return {
                "executed": False,
                "refused": True,
                "reason": f"unsupported_calendar_tool:{tool_id}",
                "unknown": False,
            }
    except Exception as exc:
        logger.exception("calendar L2 failed execution_id=%s", execution.get("id"))
        return {
            "executed": False,
            "refused": False,
            "unknown": True,
            "reason": f"provider_error:{exc}",
        }

    return {
        "executed": applied,
        "refused": False,
        "unknown": (not applied) and str(detail).startswith("error:"),
        "reason": detail,
        "result": row,
        "verified": applied,
    }


def _reschedule_l2(
    db: Any, client_id: str, inp: dict
) -> tuple[bool, str, dict | None]:
    from backend.services import booking
    from backend.services.google_calendar import (
        get_calendar_event,
        get_integration,
        update_calendar_event,
    )

    event_id = inp.get("event_id")
    start = inp.get("start")
    end = inp.get("end")
    if not (event_id and start and end):
        return False, "missing_params", None

    hit = (
        tenant_table(db, "appointments", client_id)
        .select("*")
        .eq("id", event_id)
        .limit(1)
        .execute()
    )
    row = (hit.data or [None])[0]
    if row is None:
        hit = (
            tenant_table(db, "appointments", client_id)
            .select("*")
            .eq("google_event_id", event_id)
            .limit(1)
            .execute()
        )
        row = (hit.data or [None])[0]
    if row is None:
        return False, "event_not_found", None

    updated = booking.update_appointment(
        client_id, row["id"], {"start_time": start, "end_time": end}
    )
    gid = updated.get("google_event_id")
    if gid and get_integration(client_id):
        update_calendar_event(client_id, gid, start_utc=start, end_utc=end)
        fetched = get_calendar_event(client_id, gid)
        if not fetched:
            return False, "google_verify_missing", updated
        if fetched.get("start") and start[:16] not in (fetched.get("start") or ""):
            return False, "google_verify_time_mismatch", updated
    return True, "rescheduled", updated


def _mark_execution_unverified(
    db: Any,
    client_id: str,
    match_value: str | None,
    detail: str,
    executions: list[dict] | None,
    *,
    match_field: str,
) -> None:
    if not (match_value and executions):
        return
    for ex in executions:
        result = ex.get("result") or {}
        inp = ex.get("input") or {}
        matched = False
        if isinstance(result, dict) and result.get(match_field) == match_value:
            matched = True
        if match_field == "customerId" and inp.get("customer_id") == match_value:
            matched = True
        if match_field == "eventId" and (
            inp.get("event_id") == match_value or result.get("eventId") == match_value
        ):
            matched = True
        if not matched:
            continue
        eid = ex.get("id")
        if not eid:
            continue
        try:
            tenant_table(db, "os_tool_executions", client_id).update(
                {
                    "status": "verification_failed",
                    "verification_state": "failed",
                    "verification_detail": detail,
                }
            ).eq("id", eid).execute()
        except Exception:
            logger.exception("failed to mark verification_failed id=%s", eid)
        return
