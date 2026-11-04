"""Owner-chat Google Calendar read and approval-gated booking.

Workforce chat used to answer "what's on my calendar" and "book X tomorrow
at 10am" from the internal appointment-count template. This path runs
first, only on owner threads:

- A read calls Google Calendar ``events.list`` (calendar.readonly) and
  reports those events.
- A booking parses a draft and parks an ``os_agent_runs`` deliverable at
  ``pending_approval`` with ``action_type=calendar.event.create``.
  ``events.insert`` runs only when that deliverable is approved.

``classify()`` in agent-service is not involved. This is a deterministic
fast path, same shape as the BI answers it used to lose to.
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi.concurrency import run_in_threadpool

from backend.services.os_constants import INBOUND_THREAD_SOURCES
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

_MAX_LEN = 500
_DEFAULT_TZ = "America/New_York"

_METRIC_RE = re.compile(
    r"\b(how many|how much|were created|was created|were booked|number of|count of|total)\b",
    re.I,
)
_BOOK_RE = re.compile(r"\b(book|schedule)\b", re.I)
_DONT_BOOK_RE = re.compile(r"\b(don'?t|do not)\s+(book|schedule)\b", re.I)
_CLOCK_RE = re.compile(
    r"\b(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)\b",
    re.I,
)
_READ_RE = re.compile(
    r"("
    r"what(?:'s| is| are) on (?:my |the |our )?(?:google )?calendar"
    r"|on my (?:google )?calendar"
    r"|what appointments do i have"
    r"|(?:show|list|pull up) (?:my |the |our )?(?:google )?calendar"
    r"|my google calendar"
    r")",
    re.I,
)
_DURATION_RE = re.compile(r"\b(\d+)\s*-?\s*min(?:ute)?s?\b", re.I)
_TITLE_RE = re.compile(
    r"""(?:called|named|titled)\s+["“']([^"”']+)["”']""",
    re.I,
)
_WEEKDAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def classify_calendar_ask(question: str) -> str | None:
    """Return ``read``, ``book``, or None. Pure — no I/O, no model."""
    q = (question or "").strip()
    if not q or len(q) > _MAX_LEN:
        return None
    is_read = _READ_RE.search(q) is not None
    if _METRIC_RE.search(q) and not is_read:
        return None
    if (
        not _METRIC_RE.search(q)
        and _BOOK_RE.search(q)
        and not _DONT_BOOK_RE.search(q)
        and _CLOCK_RE.search(q)
    ):
        return "book"
    if is_read:
        return "read"
    return None


def _zone(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name or _DEFAULT_TZ)
    except Exception:
        return ZoneInfo(_DEFAULT_TZ)


def _local_now(tz: ZoneInfo, now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(tz)
    if now.tzinfo is None:
        return now.replace(tzinfo=tz)
    return now.astimezone(tz)


def _timezone_name(client_id: str) -> str:
    try:
        from backend.services.booking import get_business_hours

        hours = get_business_hours(client_id) or {}
        if hours.get("timezone"):
            return str(hours["timezone"])
    except Exception:
        logger.warning(
            "os_calendar_chat: timezone lookup failed client_id=%s",
            client_id,
            exc_info=True,
        )
    return _DEFAULT_TZ


def _fmt_local(dt: datetime) -> str:
    hour = dt.strftime("%I").lstrip("0") or "12"
    return f"{dt.strftime('%a %b')} {dt.day}, {hour}:{dt.strftime('%M %p')}"


def _utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _parse_iso(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def read_window(question: str, now_local: datetime) -> tuple[datetime, datetime, str]:
    """Inclusive-start exclusive-end window in ``now_local``'s timezone."""
    q = question.lower()
    if re.search(r"\btomorrow\b", q) and "week" not in q and "month" not in q:
        start = (now_local + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return start, start + timedelta(days=1), "tomorrow"
    if re.search(r"\btoday\b", q) and "week" not in q and "month" not in q:
        start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        return start, start + timedelta(days=1), "today"
    if "month" in q and "week" not in q:
        start = now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
        return start, end, "this month"
    start = (now_local - timedelta(days=now_local.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return start, start + timedelta(days=7), "this week"


def _to_24(hour: str, minute: str | None, ampm: str) -> tuple[int, int] | None:
    h = int(hour)
    m = int(minute or 0)
    if h > 12 or m > 59:
        return None
    ap = ampm.lower().replace(".", "")
    if ap == "pm" and h != 12:
        h += 12
    if ap == "am" and h == 12:
        h = 0
    if h > 23:
        return None
    return h, m


def _resolve_day(question: str, now_local: datetime):
    q = question.lower()
    if "tomorrow" in q:
        return (now_local + timedelta(days=1)).date()
    if "today" in q:
        return now_local.date()
    for index, name in enumerate(_WEEKDAYS):
        if re.search(rf"\b{name}\b", q):
            delta = (index - now_local.weekday()) % 7
            if delta == 0:
                delta = 7
            return (now_local + timedelta(days=delta)).date()
    return None


def parse_booking(question: str, now_local: datetime) -> dict | None:
    """Pull title, start, and duration. None when the day or clock is missing."""
    clock = _CLOCK_RE.search(question)
    if not clock:
        return None
    hm = _to_24(clock.group(1), clock.group(2), clock.group(3))
    day = _resolve_day(question, now_local)
    if hm is None or day is None:
        return None
    hour, minute = hm
    start_local = datetime(
        day.year, day.month, day.day, hour, minute, tzinfo=now_local.tzinfo
    )
    duration_match = _DURATION_RE.search(question)
    minutes = int(duration_match.group(1)) if duration_match else 60
    if minutes <= 0 or minutes > 24 * 60:
        return None
    title_match = _TITLE_RE.search(question)
    summary = title_match.group(1).strip() if title_match else "Appointment"
    if not summary:
        summary = "Appointment"
    end_local = start_local + timedelta(minutes=minutes)
    return {
        "summary": summary,
        "minutes": minutes,
        "start_local": start_local,
        "end_local": end_local,
        "start_utc": _utc_iso(start_local),
        "end_utc": _utc_iso(end_local),
    }


def _is_owner_thread(db, client_id: str, thread_id: str) -> bool:
    try:
        rows = (
            tenant_table(db, "os_threads", client_id)
            .select("source")
            .eq("id", thread_id)
            .limit(1)
            .execute()
            .data
            or []
        )
    except Exception:
        logger.warning(
            "os_calendar_chat: thread lookup failed client_id=%s",
            client_id,
            exc_info=True,
        )
        return False
    if not rows:
        return False
    source = rows[0].get("source") or "chat"
    return source not in INBOUND_THREAD_SOURCES


def _audit(client_id: str, activity_type: str, description: str, metadata: dict) -> None:
    try:
        from backend.services.activity import log_activity

        log_activity(
            tenant_id=client_id,
            activity_type=activity_type,
            description=description,
            metadata=metadata,
        )
    except Exception:
        logger.warning("os_calendar_chat: audit log failed", exc_info=True)


def _persist_reply(
    db, client_id: str, thread_id: str, content: str, agent_run_id: str | None = None
) -> dict | None:
    row = {"thread_id": thread_id, "role": "assistant", "content": content}
    if agent_run_id:
        row["agent_run_id"] = agent_run_id
    try:
        assistant = (
            tenant_table(db, "os_messages", client_id).insert(row).execute().data[0]
        )
        tenant_table(db, "os_threads", client_id).update(
            {"updated_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", thread_id).execute()
    except Exception:
        logger.warning(
            "os_calendar_chat: persist failed client_id=%s", client_id, exc_info=True
        )
        return None
    return assistant


def _not_connected_reply() -> str:
    return (
        "Google Calendar isn't connected, so I can't read or book on it. "
        "Connect it on the Integrations page. Nothing was written."
    )


def _format_events(events: list[dict], tz: ZoneInfo, label: str, start, end) -> str:
    lines = [
        f"On your Google Calendar {label} "
        f"({_fmt_local(start)} – {_fmt_local(end - timedelta(minutes=1))}, {tz.key}):"
    ]
    if not events:
        lines.append("Nothing is scheduled in that window.")
    else:
        shown = events[:20]
        for event in shown:
            when = _parse_iso(event.get("start") or "")
            if when is None:
                when_label = "time not set"
            elif when.tzinfo is None:
                when_label = f"{when.strftime('%a %b')} {when.day} (all day)"
            else:
                when_label = _fmt_local(when.astimezone(tz))
            title = event.get("summary") or "(no title)"
            lines.append(f"- {title} — {when_label}")
        extra = len(events) - len(shown)
        if extra:
            lines.append(f"- {extra} more not shown")
    lines.append(
        f"{len(events)} event(s). Read from Google Calendar. Nothing was changed."
    )
    return "\n".join(lines)


async def try_calendar_turn(
    db,
    client_id: str,
    thread_id: str,
    user_message_row: dict,
    now: datetime | None = None,
) -> dict | None:
    """Answer a calendar read or park a booking draft. None if this isn't one."""
    content = str(user_message_row.get("content") or "").strip()
    kind = classify_calendar_ask(content)
    if kind is None:
        return None
    if not _is_owner_thread(db, client_id, thread_id):
        return None

    from backend.services import google_calendar

    tz = _zone(await run_in_threadpool(_timezone_name, client_id))
    now_local = _local_now(tz, now)
    connected = False
    try:
        integration = await run_in_threadpool(google_calendar.get_integration, client_id)
        connected = integration is not None
    except Exception:
        logger.warning(
            "os_calendar_chat: integration lookup failed client_id=%s",
            client_id,
            exc_info=True,
        )
        connected = False

    if kind == "read":
        return await _answer_read(
            db, client_id, thread_id, user_message_row, content,
            tz, now_local, connected,
        )
    return await _draft_booking(
        db, client_id, thread_id, user_message_row, content,
        tz, now_local, connected,
    )


async def _answer_read(
    db, client_id, thread_id, user_message_row, content, tz, now_local, connected
) -> dict | None:
    from backend.services import google_calendar

    start_local, end_local, label = read_window(content, now_local)
    if not connected:
        reply = _not_connected_reply()
        assistant = _persist_reply(db, client_id, thread_id, reply)
        if assistant is None:
            return None
        _audit(
            client_id,
            "os_calendar_read",
            "Google Calendar read skipped — not connected",
            {"connected": False, "window": label},
        )
        return _turn(user_message_row, assistant, read=True)

    listed = await run_in_threadpool(
        google_calendar.list_calendar_events_in_window,
        client_id,
        start_local.astimezone(timezone.utc),
        end_local.astimezone(timezone.utc),
    )
    if listed.get("state") != "ok":
        reason = listed.get("reason") or "unknown"
        if reason == "no_credentials":
            reply = (
                "Google Calendar access expired or was revoked. Reconnect it "
                "on the Integrations page. Nothing was changed."
            )
        elif reason in ("http_401", "http_403"):
            reply = (
                "Google Calendar refused the read (access denied). Reconnect "
                "Google Calendar. Nothing was changed."
            )
        else:
            reply = (
                "I couldn't read Google Calendar just now. I didn't guess "
                "from internal appointments, and nothing was changed."
            )
        assistant = _persist_reply(db, client_id, thread_id, reply)
        if assistant is None:
            return None
        _audit(
            client_id,
            "os_calendar_read",
            "Google Calendar read failed",
            {"connected": True, "window": label, "state": listed.get("state"), "reason": reason},
        )
        return _turn(user_message_row, assistant, read=True)

    events = sorted(listed.get("events") or [], key=lambda ev: ev.get("start") or "")
    reply = _format_events(events, tz, label, start_local, end_local)
    assistant = _persist_reply(db, client_id, thread_id, reply)
    if assistant is None:
        return None
    _audit(
        client_id,
        "os_calendar_read",
        "Listed Google Calendar events",
        {"connected": True, "window": label, "event_count": len(events)},
    )
    return _turn(user_message_row, assistant, read=True)


async def _draft_booking(
    db, client_id, thread_id, user_message_row, content, tz, now_local, connected
) -> dict | None:
    if not connected:
        assistant = _persist_reply(db, client_id, thread_id, _not_connected_reply())
        if assistant is None:
            return None
        _audit(
            client_id,
            "os_calendar_booking_draft",
            "Google Calendar booking skipped — not connected",
            {"connected": False},
        )
        return _turn(user_message_row, assistant, booking=True)

    parsed = parse_booking(content, now_local)
    if parsed is None:
        reply = (
            "I can draft that on Google Calendar, but I need a day and a time "
            '(for example, tomorrow at 10am). Nothing was written.'
        )
        assistant = _persist_reply(db, client_id, thread_id, reply)
        if assistant is None:
            return None
        return _turn(user_message_row, assistant, booking=True)

    body = (
        "Google Calendar event — not created yet. Approve to add it.\n\n"
        f"Title: {parsed['summary']}\n"
        f"When: {_fmt_local(parsed['start_local'])} – {_fmt_local(parsed['end_local'])} "
        f"({tz.key})\n"
        f"Duration: {parsed['minutes']} minutes\n\n"
        "Nothing is written to Google Calendar until you approve."
    )
    deliverable = {
        "title": f"Book: {parsed['summary']}",
        "body": body,
        "channel": "calendar",
        "calendar_event": {
            "summary": parsed["summary"],
            "start_utc": parsed["start_utc"],
            "end_utc": parsed["end_utc"],
            "duration_minutes": parsed["minutes"],
            "timezone": tz.key,
            "attendee_email": None,
            "description": content[:500],
            "card_body": body,
        },
    }
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        agent_run = (
            tenant_table(db, "os_agent_runs", client_id)
            .insert(
                {
                    "thread_id": thread_id,
                    "agent_name": "booking",
                    "status": "succeeded",
                    "thought_process": [
                        {
                            "step": 1,
                            "label": "Draft Google Calendar event",
                            "status": "done",
                            "detail": "Parked for approval. events.insert has not run.",
                            "at": now_iso,
                        }
                    ],
                    "deliverable": deliverable,
                    "deliverable_status": "pending_approval",
                    "action_type": "calendar.event.create",
                    "completed_at": now_iso,
                }
            )
            .execute()
            .data[0]
        )
    except Exception:
        logger.warning(
            "os_calendar_chat: draft insert failed client_id=%s",
            client_id,
            exc_info=True,
        )
        return None

    reply = (
        "I drafted a Google Calendar event and parked it for your approval. "
        "Nothing is on your calendar until you approve.\n\n"
        f"{parsed['summary']}\n"
        f"{_fmt_local(parsed['start_local'])} – {_fmt_local(parsed['end_local'])} "
        f"({tz.key})\n"
        f"Duration: {parsed['minutes']} minutes\n\n"
        "Open Review draft and approve to create it on Google Calendar."
    )
    assistant = _persist_reply(
        db, client_id, thread_id, reply, agent_run_id=agent_run.get("id")
    )
    if assistant is None:
        return None
    _audit(
        client_id,
        "os_calendar_booking_draft",
        "Parked Google Calendar booking for approval",
        {
            "connected": True,
            "summary": parsed["summary"],
            "start_utc": parsed["start_utc"],
            "end_utc": parsed["end_utc"],
        },
    )
    return _turn(user_message_row, assistant, agent_run=agent_run, booking=True)


def cancel_pending_calendar_approvals(db, client_id: str) -> int:
    """Reject pending calendar cards so Disconnect cannot be followed by an insert."""
    try:
        rows = (
            tenant_table(db, "os_agent_runs", client_id)
            .select("id")
            .eq("action_type", "calendar.event.create")
            .eq("deliverable_status", "pending_approval")
            .execute()
            .data
            or []
        )
    except Exception:
        logger.warning(
            "os_calendar_chat: pending-approval lookup failed client_id=%s",
            client_id,
            exc_info=True,
        )
        return 0
    cancelled = 0
    now_iso = datetime.now(timezone.utc).isoformat()
    for row in rows:
        try:
            updated = (
                tenant_table(db, "os_agent_runs", client_id)
                .update(
                    {
                        "deliverable_status": "rejected",
                        "error_detail": "Google Calendar was disconnected",
                        "updated_at": now_iso,
                    }
                )
                .eq("id", row["id"])
                .eq("deliverable_status", "pending_approval")
                .execute()
                .data
            )
        except Exception:
            logger.warning(
                "os_calendar_chat: cancel pending failed client_id=%s",
                client_id,
                exc_info=True,
            )
            continue
        if updated:
            cancelled += 1
    return cancelled


def _turn(user_message_row, assistant, agent_run=None, read=False, booking=False) -> dict:
    return {
        "user_message": user_message_row,
        "assistant_message": assistant,
        "action": "delegate" if agent_run else "answer",
        "agent_runs": [agent_run] if agent_run else [],
        "calendar_read": read,
        "calendar_booking_draft": booking,
    }
