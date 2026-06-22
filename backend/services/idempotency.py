"""Idempotency key store for webhook deduplication.

Prevents Stripe and Twilio redeliveries from being processed twice.

Usage:
    is_new, cached = await check_and_record(db, "stripe", event_id)
    if not is_new:
        return cached  # return cached response to caller

    # ... process event ...

    await record_response(db, f"stripe:{event_id}", 200, {"status": "ok"})
"""

import logging

logger = logging.getLogger(__name__)


def _build_key(provider: str, event_id: str) -> str:
    return f"{provider}:{event_id}"


async def check_and_record(
    supabase,
    provider: str,
    event_id: str,
) -> tuple[bool, dict | None]:
    """Check whether this event has been seen before and insert if new.

    Returns:
        (True, None)         — event is new; caller should process it
        (False, cached_dict) — duplicate; caller should return cached response

    The row is inserted on first call so that concurrent redeliveries see
    the key and skip processing (last-write-wins on PRIMARY KEY conflict).
    """
    key = _build_key(provider, event_id)

    # Atomic INSERT ... ON CONFLICT DO NOTHING via PostgREST upsert with
    # ignore_duplicates=True. Closes the race where two concurrent webhook
    # redeliveries both pass a SELECT-then-INSERT pattern.
    try:
        result = (
            supabase.table("idempotency_keys")
            .upsert(
                {"key": key, "provider": provider},
                on_conflict="key",
                ignore_duplicates=True,
            )
            .execute()
        )
    except Exception:
        logger.exception("idempotency upsert failed for key=%s", key)
        # Fail open — worst case is a duplicate process. Retries will dedup.
        return True, None

    inserted_rows = getattr(result, "data", None) or []
    if inserted_rows:
        # Row was newly inserted by us — caller proceeds.
        return True, None

    # Row already existed — fetch its current cached response.
    try:
        existing = (
            supabase.table("idempotency_keys")
            .select("key, response_status, response_body")
            .eq("key", key)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("idempotency post-conflict fetch failed key=%s", key)
        return True, None

    if not existing.data:
        # Race: row appeared then disappeared (TTL cleanup mid-flight).
        return True, None

    row = existing.data[0]
    cached = {
        "response_status": row.get("response_status"),
        "response_body": row.get("response_body"),
    }
    if row.get("response_body") is None:
        # First delivery still in flight. Returning is_new=False causes the
        # caller to ack 200 to the provider; the in-flight worker will
        # complete the work. Provider stops redelivering.
        cached["in_flight"] = True
        logger.info("idempotency: in-flight duplicate key=%s", key)
    else:
        logger.info("idempotency: completed duplicate key=%s — returning cached", key)
    return False, cached


async def delete_key(supabase, key: str) -> None:
    """Remove an idempotency row so a failed handler can be retried cleanly.

    The row is written by check_and_record BEFORE the handler runs (so
    concurrent redeliveries dedup). If the handler then raises, the row would
    otherwise persist with a NULL response_body and short-circuit every Stripe
    retry as an "in-flight duplicate" — permanently dropping the event and
    leaving dunning-locked tenants stuck (GH #308). Deleting it on failure lets
    the next delivery reprocess from scratch.
    """
    try:
        supabase.table("idempotency_keys").delete().eq("key", key).execute()
        logger.info("idempotency: released key=%s after handler failure", key)
    except Exception:
        logger.exception("idempotency delete_key failed for key=%s", key)


async def record_response(
    supabase,
    key: str,
    status: int,
    body: dict,
) -> None:
    """Update the idempotency row with the response we returned to the caller.

    Call this after successfully processing the event so that replays
    can return the same cached response.
    """
    try:
        supabase.table("idempotency_keys").update(
            {"response_status": status, "response_body": body}
        ).eq("key", key).execute()
    except Exception:
        logger.exception("idempotency record_response failed for key=%s", key)
