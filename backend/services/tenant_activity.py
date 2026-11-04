"""One definition of tenant activity for dashboard, billing, analytics, and pipeline.

Tenant scope
    leads and conversations use ``client_id``. chat_messages uses ``tenant_id``.
    ``tenant_select`` applies that column. Callers must not pass another tenant's rows.

Conversation
    One session_id. Counted when it appears on ``conversations`` or ``chat_messages``.
    Timestamps are ``started_at``, ``last_message_at``, and message ``created_at``.
    A session in both tables counts once.

Lead / opportunity / deal
    One ``leads`` row for that client_id. Dashboard "opportunities", analytics
    "leads captured", and pipeline "deals" are this stock, not a rolling window.

Usage window
    Billing, the dashboard conversation card, and analytics period ``month``
    are the UTC calendar month ``[month_start, now)``. Rolling periods
    ``7d`` / ``14d`` / ``30d`` / ``90d`` use the same inclusion rule.

Last activity
    The newest of those conversation timestamps and lead ``created_at`` /
    ``updated_at``. A stale chat_messages row cannot hide a newer lead or
    conversation.
"""

import logging
from datetime import datetime, timedelta, timezone

from backend.services.tenant_scope import tenant_select

logger = logging.getLogger(__name__)

_ROW_LIMIT = 5000


def parse_ts(value) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def activity_window(
    period: str, now: datetime | None = None
) -> tuple[datetime, datetime, datetime]:
    """Return ``(start, end, previous_start)``. ``end`` is exclusive.

    ``previous_start`` opens a window of the same length immediately before
    ``start``. ``period`` ``all`` has no lower bound (``start`` is None-like:
    year 1970) so callers can still pass the triple into ``in_window``.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    if period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        prev_start = (start - timedelta(days=1)).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        return start, now, prev_start

    if period == "all":
        start = datetime(1970, 1, 1, tzinfo=timezone.utc)
        return start, now, start

    days = {"7d": 7, "14d": 14, "30d": 30, "90d": 90}.get(period, 30)
    start = now - timedelta(days=days)
    prev_start = now - timedelta(days=days * 2)
    return start, now, prev_start


def in_window(ts: datetime | None, start: datetime | None, end: datetime | None) -> bool:
    if ts is None:
        return False
    if start is not None and ts < start:
        return False
    if end is not None and ts >= end:
        return False
    return True


def session_timestamps(
    conversation_rows: list[dict], message_rows: list[dict]
) -> dict[str, list[datetime]]:
    """Map session id → every activity timestamp from both tables."""
    sessions: dict[str, list[datetime]] = {}

    def add(session_id, ts: datetime | None) -> None:
        if not session_id or ts is None:
            return
        sessions.setdefault(str(session_id), []).append(ts)

    for row in conversation_rows:
        session_id = row.get("session_id") or row.get("id")
        add(session_id, parse_ts(row.get("started_at")))
        add(session_id, parse_ts(row.get("last_message_at")))
        add(session_id, parse_ts(row.get("created_at")))

    for row in message_rows:
        add(row.get("session_id"), parse_ts(row.get("created_at")))

    return sessions


def count_conversations(
    conversation_rows: list[dict],
    message_rows: list[dict],
    start: datetime | None,
    end: datetime | None,
) -> int:
    """Distinct sessions with any activity timestamp inside ``[start, end)``."""
    total = 0
    for stamps in session_timestamps(conversation_rows, message_rows).values():
        if any(in_window(ts, start, end) for ts in stamps):
            total += 1
    return total


def count_messages(
    message_rows: list[dict], start: datetime | None, end: datetime | None
) -> int:
    total = 0
    for row in message_rows:
        if in_window(parse_ts(row.get("created_at")), start, end):
            total += 1
    return total


def count_leads_created(
    lead_rows: list[dict], start: datetime | None, end: datetime | None
) -> int:
    """Leads whose ``created_at`` falls in the window. No window → every row."""
    if start is None and end is None:
        return len(lead_rows)
    total = 0
    for row in lead_rows:
        if in_window(parse_ts(row.get("created_at")), start, end):
            total += 1
    return total


def last_activity_at(
    conversation_rows: list[dict],
    message_rows: list[dict],
    lead_rows: list[dict],
) -> datetime | None:
    stamps: list[datetime] = []
    for group in session_timestamps(conversation_rows, message_rows).values():
        stamps.extend(group)
    for row in lead_rows:
        created = parse_ts(row.get("created_at"))
        updated = parse_ts(row.get("updated_at"))
        if created is not None:
            stamps.append(created)
        if updated is not None:
            stamps.append(updated)
    if not stamps:
        return None
    return max(stamps)


def conversation_trend(
    conversation_rows: list[dict],
    message_rows: list[dict],
    start: datetime,
    end: datetime,
) -> dict[str, int]:
    """Day → sessions whose earliest in-window timestamp falls on that day.

    Each session is counted once, so the sum matches ``count_conversations``.
    """
    counts: dict[str, int] = {}
    for stamps in session_timestamps(conversation_rows, message_rows).values():
        in_period = [ts for ts in stamps if in_window(ts, start, end)]
        if not in_period:
            continue
        day = min(in_period).date().isoformat()
        counts[day] = counts.get(day, 0) + 1
    return counts


def _select(
    db, table: str, tenant_id: str, columns: str, order_column: str | None = None
) -> list[dict] | None:
    try:
        query = tenant_select(db, table, tenant_id, columns)
        if order_column:
            query = query.order(order_column, desc=True)
        result = query.limit(_ROW_LIMIT).execute()
        return result.data or []
    except Exception:
        logger.warning(
            "tenant activity: %s read failed for tenant %s",
            table,
            tenant_id,
            exc_info=True,
        )
        return None


def load_activity_rows(db, tenant_id: str) -> dict[str, list[dict]]:
    """Load the rows the shared counters read. Scoped by ``tenant_select``."""
    conversations = _select(
        db,
        "conversations",
        tenant_id,
        "session_id, started_at, last_message_at",
        "last_message_at",
    )
    if conversations is None:
        conversations = _select(
            db, "conversations", tenant_id, "session_id, started_at", "started_at"
        )
    messages = _select(
        db, "chat_messages", tenant_id, "session_id, created_at", "created_at"
    )
    leads = _select(
        db,
        "leads",
        tenant_id,
        "id, status, deal_value, lead_score, created_at, updated_at",
        "updated_at",
    )
    if leads is None:
        leads = _select(
            db,
            "leads",
            tenant_id,
            "id, status, deal_value, lead_score, created_at",
            "created_at",
        )
    return {
        "conversations": conversations or [],
        "messages": messages or [],
        "leads": leads or [],
    }


def exact_lead_count(db, tenant_id: str) -> int | None:
    """All-time lead stock for this tenant. None when the count query fails."""
    try:
        result = (
            tenant_select(db, "leads", tenant_id, "id", count="exact")
            .limit(1)
            .execute()
        )
        if result.count is not None:
            return int(result.count)
        return len(result.data or [])
    except Exception:
        logger.warning(
            "tenant activity: lead count failed for tenant %s",
            tenant_id,
            exc_info=True,
        )
        return None
