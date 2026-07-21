"""Read-side helpers for the Quote Requests dashboard (#42).

Lists a tenant's ``quote_requests`` (newest first) with optional filters, shaped
for the dashboard table. Kept separate from the write-side metering
(``photo_quote_usage.py``) per Rule 12. ``client_id``-scoped (migration 108).
"""

import logging

logger = logging.getLogger(__name__)

_DEFAULT_LIMIT = 100
_MAX_LIMIT = 500
_SELECT = (
    "id, conversation_id, image_url, thumbnail_url, full_image_purged_at, "
    "quote_low, quote_high, severity, confidence, claude_summary, "
    "needs_human, created_at"
)


def list_quote_requests(
    client_id: str,
    *,
    db=None,
    limit: int = _DEFAULT_LIMIT,
    industry: str = None,
    needs_human: bool = None,
    start_date: str = None,
    end_date: str = None,
) -> list:
    """Return the tenant's quote requests (newest first), filtered.

    Each row includes an ``image_purged`` flag (full image gone after 30 days,
    thumbnail retained) so the UI can show "image purged after 30d" instead of a
    dead link. Fail-open: a query error returns ``[]``.
    """
    limit = max(1, min(int(limit or _DEFAULT_LIMIT), _MAX_LIMIT))
    if db is None:
        from backend.models.database import get_service_supabase

        db = get_service_supabase()
    try:
        q = (
            db.table("quote_requests")
            .select(_SELECT)
            .eq("client_id", client_id)
        )
        if needs_human is not None:
            q = q.eq("needs_human", needs_human)
        if start_date:
            q = q.gte("created_at", start_date)
        if end_date:
            q = q.lte("created_at", end_date)
        q = q.order("created_at", desc=True).limit(limit)
        rows = q.execute().data or []
    except Exception:
        logger.warning("photo_quote_admin: list failed for %s", client_id)
        return []

    out = []
    for row in rows:
        # `industry` isn't stored on the row; it comes from the tenant's pricing
        # rule. The optional industry filter is applied client-side by the caller
        # when a single-industry tenant is the norm — kept here as a pass-through.
        out.append(
            {
                "id": row.get("id"),
                "conversation_id": row.get("conversation_id"),
                "thumbnail_url": row.get("thumbnail_url"),
                "image_url": row.get("image_url"),
                "image_purged": bool(row.get("full_image_purged_at"))
                or not row.get("image_url"),
                "quote_low": row.get("quote_low"),
                "quote_high": row.get("quote_high"),
                "severity": row.get("severity"),
                "confidence": row.get("confidence"),
                "summary": row.get("claude_summary"),
                "needs_human": bool(row.get("needs_human")),
                "created_at": row.get("created_at"),
            }
        )
    if industry:  # pass-through filter hook (industry not on the row today)
        return out
    return out
