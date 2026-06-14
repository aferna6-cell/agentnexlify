"""Agent OS sync: google_calendar — pull upcoming events into memory.

Reads upcoming events from the tenant's connected Google Calendar (next
``_WINDOW_DAYS``), renders a short summary per event, and upserts into
``os_memory_entries`` with ``source_ref='gcal:<event_id>'``. Past events
that fall outside the window are NOT removed — they age out via the
content's mention of the start_time only.

Cursor: ISO timestamp of the most recent event ``updated`` field we've
seen. ``backfill=True`` ignores the cursor and re-syncs the whole window.

Required connectors: ``google_calendar``.
"""

import logging
from datetime import datetime, timedelta, timezone

from backend.services.embeddings import embed_text
from backend.services.google_calendar import _build_service
from backend.services.os_sync.base import SyncContext, SyncResult, SyncSpec, now_iso
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

_WINDOW_DAYS = 60
_MAX_EVENTS = 250


def _summarize_event(event: dict) -> str:
    summary = (event.get("summary") or "").strip() or "Untitled event"
    parts: list[str] = [f"Calendar event: {summary}"]
    start = event.get("start") or {}
    end = event.get("end") or {}
    start_at = start.get("dateTime") or start.get("date")
    end_at = end.get("dateTime") or end.get("date")
    if start_at:
        parts.append(f"start={start_at}")
    if end_at:
        parts.append(f"end={end_at}")
    location = (event.get("location") or "").strip()
    if location:
        parts.append(f"location={location[:120]}")
    status = (event.get("status") or "").strip()
    if status and status != "confirmed":
        parts.append(f"status={status}")
    attendees = event.get("attendees") or []
    if attendees:
        emails = [a.get("email") for a in attendees if a.get("email")][:5]
        if emails:
            parts.append("attendees=" + ", ".join(emails))
    description = (event.get("description") or "").strip()
    if description:
        parts.append("notes: " + description[:280])
    return ". ".join(parts)


def _fetch_events(tenant_id: str, time_min: datetime, time_max: datetime) -> list[dict]:
    service = _build_service(tenant_id)
    if not service:
        return []
    result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=time_min.isoformat(),
            timeMax=time_max.isoformat(),
            singleEvents=True,
            orderBy="updated",
            maxResults=_MAX_EVENTS,
        )
        .execute()
    )
    return result.get("items") or []


async def _upsert_event_memory(db, client_id: str, event: dict) -> None:
    event_id = event.get("id")
    if not event_id:
        return
    source_ref = f"gcal:{event_id}"
    content = _summarize_event(event)
    try:
        embedding = await embed_text(content)
    except Exception:
        logger.warning(
            "os_sync.google_calendar: embed failed client_id=%s event_id=%s",
            client_id,
            event_id,
            exc_info=True,
        )
        embedding = None

    existing = (
        tenant_table(db, "os_memory_entries", client_id)
        .select("id")
        .eq("source_ref", source_ref)
        .limit(1)
        .execute()
    )
    if existing.data:
        tenant_table(db, "os_memory_entries", client_id).update(
            {
                "content": content,
                "embedding": embedding,
                "updated_at": now_iso(),
            }
        ).eq("id", existing.data[0]["id"]).execute()
        return

    tenant_table(db, "os_memory_entries", client_id).insert(
        {
            "kind": "fact",
            "content": content,
            "embedding": embedding,
            "source": "sync:google_calendar",
            "source_ref": source_ref,
        }
    ).execute()


async def _run(ctx: SyncContext) -> SyncResult:
    client_id = ctx.client_id
    db = ctx.db
    cursor = ctx.state_row.get("last_seen_cursor")

    time_min = datetime.now(timezone.utc) - timedelta(days=1)
    time_max = time_min + timedelta(days=_WINDOW_DAYS + 1)

    try:
        events = _fetch_events(client_id, time_min, time_max)
    except Exception as e:
        logger.exception(
            "os_sync.google_calendar: fetch failed client_id=%s", client_id
        )
        return SyncResult(status="error", error_detail=str(e)[:300])

    if not events:
        return SyncResult(status="ok", rows_seen=0, new_cursor=cursor)

    if cursor and not ctx.backfill:
        events = [e for e in events if (e.get("updated") or "") > cursor]
        if not events:
            return SyncResult(status="ok", rows_seen=0, new_cursor=cursor)

    max_cursor = cursor
    processed = 0
    for event in events:
        try:
            await _upsert_event_memory(db, client_id, event)
        except Exception:
            logger.exception(
                "os_sync.google_calendar: upsert failed client_id=%s event_id=%s",
                client_id,
                event.get("id"),
            )
            continue
        processed += 1
        updated = event.get("updated")
        if updated and (max_cursor is None or updated > max_cursor):
            max_cursor = updated

    return SyncResult(status="ok", rows_seen=processed, new_cursor=max_cursor)


SPEC = SyncSpec(
    name="google_calendar",
    run=_run,
    description=(
        "Pull upcoming Google Calendar events into semantic memory, dedup by event id."
    ),
    required_connectors=["google_calendar"],
)
