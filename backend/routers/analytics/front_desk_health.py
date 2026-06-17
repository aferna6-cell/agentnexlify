"""Front Desk Health analytics endpoint.

Surfaces the conversation-level signals captured on the ``conversations`` table
(client_id-scoped) so dashboard owners get a daily glance at how their AI front
desk is performing:

- conversation count + lead capture rate (lead_captured flag, migration 074)
- sentiment breakdown (sentiment column, migration 154)
- top intents / topics (intent column, migration 154)
- KB-gap count: negative-sentiment conversations that never captured a lead --
  a deterministic proxy for "the bot probably could not help" sessions.

Pre-migration safety: the sentiment + intent columns (migration 154) may not
exist on a tenant's database yet. Each read is wrapped so a missing column or
any other Supabase error degrades to zeros and is logged, never raised. The
endpoint never returns a 500 because of an absent column.
"""

from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query

from backend.dependencies import _get_current_tenant, verify_tenant
from backend.models.database import get_service_supabase
from backend.services.tenant_scope import tenant_table
from backend.routers.analytics._common import (
    _QUERY_LIMIT,
    _get_cached,
    _ratio,
    _set_cache,
    logger,
)

router = APIRouter()

# Sentiment vocabulary mirrors migration 154 / the calls table exactly.
_SENTIMENTS = ("positive", "neutral", "negative")

_TOP_INTENTS_LIMIT = 5


@router.get("/{tenant_id}/front-desk-health")
async def get_front_desk_health(
    tenant_id: str,
    period: str = Query("30d", pattern="^(7d|14d|30d|90d)$"),
    claims: dict = Depends(_get_current_tenant),
):
    """Conversation health overview for the dashboard home card.

    Returns conversation count, capture rate, sentiment breakdown, top intents,
    and a KB-gap count. Tenant-scoped via client_id (conversations table). All
    fields fall back to zeros when the underlying data or columns are missing.
    """
    verify_tenant(claims, tenant_id)

    cache_key = f"front_desk_health:{tenant_id}:{period}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    days = {"7d": 7, "14d": 14, "30d": 30, "90d": 90}.get(period, 30)
    start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    db = get_service_supabase()

    # One read of the conversations rows for the period. Selecting the optional
    # columns (sentiment, intent) here means a tenant missing the migration-154
    # columns trips the except branch and we return zeros rather than a 500.
    rows: list[dict] = []
    columns_available = True
    try:
        resp = (
            tenant_table(db, "conversations", tenant_id)
            .select("id, lead_captured, sentiment, intent")
            .eq("client_id", tenant_id)
            .gte("started_at", start)
            .limit(_QUERY_LIMIT)
            .execute()
        )
        rows = resp.data or []
    except Exception:
        # Most likely the sentiment/intent columns do not exist yet (pre-154).
        # Retry without the optional columns so the count + capture rate still
        # work; the breakdowns simply stay empty.
        columns_available = False
        try:
            resp = (
                tenant_table(db, "conversations", tenant_id)
                .select("id, lead_captured")
                .eq("client_id", tenant_id)
                .gte("started_at", start)
                .limit(_QUERY_LIMIT)
                .execute()
            )
            rows = resp.data or []
        except Exception:
            logger.warning(
                "front_desk_health: conversations read failed for %s",
                tenant_id,
                exc_info=True,
            )
            rows = []

    total_conversations = len(rows)
    leads_captured = sum(1 for r in rows if r.get("lead_captured"))
    capture_rate = _ratio(leads_captured, total_conversations)

    sentiment_breakdown = {label: 0 for label in _SENTIMENTS}
    intent_counts: Counter[str] = Counter()
    kb_gap_count = 0

    if columns_available:
        for row in rows:
            sentiment = (row.get("sentiment") or "").strip().lower()
            if sentiment in sentiment_breakdown:
                sentiment_breakdown[sentiment] += 1

            intent = (row.get("intent") or "").strip().lower()
            if intent:
                intent_counts[intent] += 1

            # KB gap: a frustrated customer (negative sentiment) that the bot
            # never converted into a lead -- a likely "could not help" session.
            if sentiment == "negative" and not row.get("lead_captured"):
                kb_gap_count += 1

    top_intents = [
        {"intent": intent, "count": count}
        for intent, count in intent_counts.most_common(_TOP_INTENTS_LIMIT)
    ]

    result = {
        "period": period,
        "total_conversations": total_conversations,
        "leads_captured": leads_captured,
        "capture_rate": capture_rate,
        "sentiment_breakdown": sentiment_breakdown,
        "top_intents": top_intents,
        "kb_gap_count": kb_gap_count,
        # Signals whether sentiment/intent classification data is available so
        # the frontend can show the right empty state for those sub-sections.
        "classification_available": columns_available,
    }

    _set_cache(cache_key, result)
    return result
