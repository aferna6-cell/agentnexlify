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
    try:
        existing = (
            supabase.table("idempotency_keys")
            .select("key, response_status, response_body")
            .eq("key", key)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("idempotency check failed for key=%s", key)
        # Fail open — let the caller process; worst case is a duplicate
        return True, None

    if existing.data:
        row = existing.data[0]
        cached = {
            "response_status": row.get("response_status"),
            "response_body": row.get("response_body"),
        }
        logger.info("idempotency: duplicate webhook key=%s — returning cached", key)
        return False, cached

    # Insert the key immediately (before processing) to lock it
    try:
        supabase.table("idempotency_keys").insert(
            {"key": key, "provider": provider}
        ).execute()
    except Exception:
        # Another concurrent request may have just inserted — check again
        logger.warning("idempotency insert conflict for key=%s — re-checking", key)
        try:
            recheck = (
                supabase.table("idempotency_keys")
                .select("key, response_status, response_body")
                .eq("key", key)
                .limit(1)
                .execute()
            )
            if recheck.data:
                row = recheck.data[0]
                return False, {
                    "response_status": row.get("response_status"),
                    "response_body": row.get("response_body"),
                }
        except Exception:
            logger.exception("idempotency re-check failed for key=%s", key)
        # Still fail open
        return True, None

    return True, None


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
