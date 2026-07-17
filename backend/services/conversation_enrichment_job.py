"""Batch driver for conversation sentiment/intent enrichment.

There is no explicit "conversation closed" event in the widget chat flow (chats
are append-only into chat_messages), so enrichment runs as a periodic batch off
the user hot path. This job finds conversations that have gone idle and have not
been classified yet, then enriches each via
``conversation_enrichment.enrich_conversation``.

Kept separate from ``conversation_enrichment`` (single-conversation logic) so
the batch-selection concern lives in its own file. Registered in the scheduler
loop (backend/main.py, 30-min tier).
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.models.database import get_service_supabase
from backend.services import batch_runtime
from backend.services.conversation_enrichment import (
    CLASSIFY_MODEL,
    _CLASSIFY_SYSTEM,
    _MAX_OUTPUT_TOKENS,
    _load_transcript,
    _persist,
    enrich_conversation,
    parse_classification,
)

logger = logging.getLogger(__name__)

# Bounded wait for a batch to end inside one scheduler tick. Message Batches
# have no hard latency guarantee short of 24h, so this is a best-effort short
# poll, not a correctness guarantee -- see run_pending_enrichment_batch below.
_BATCH_POLL_ATTEMPTS = 6
_BATCH_POLL_INTERVAL_SECONDS = 5.0

# A conversation is "settled" once it has had no new message for this long, so
# we classify a complete chat rather than one mid-stream.
_IDLE_MINUTES = 30
# Don't reach back further than this: old, never-classified rows are unlikely to
# matter and keep each batch bounded.
_LOOKBACK_HOURS = 48
# Cap conversations classified per batch tick so one run stays cheap.
_BATCH_CAP = 25


def _idle_before() -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=_IDLE_MINUTES)).isoformat()


def _lookback_after() -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=_LOOKBACK_HOURS)).isoformat()


def _find_pending(db: Any) -> list[dict[str, Any]]:
    """Return idle, unclassified conversation rows (client_id + session_id).

    Cross-tenant by design: this is a service-role batch over all tenants. Each
    row still carries its own client_id, so the downstream enrich call stays
    tenant-scoped.
    """
    resp = (
        db.table("conversations")
        .select("client_id, session_id, last_message_at")
        .is_("sentiment", "null")
        .lte("last_message_at", _idle_before())
        .gte("last_message_at", _lookback_after())
        .order("last_message_at", desc=True)
        .limit(_BATCH_CAP)
        .execute()
    )
    return getattr(resp, "data", None) or []


async def run_pending_enrichment() -> str:
    """Classify a bounded batch of idle, unclassified conversations.

    Returns a short status string for the scheduler log. Degrades gracefully:
    a failure on one conversation is logged and the batch continues.
    """
    db = get_service_supabase()

    try:
        pending = _find_pending(db)
    except Exception:
        logger.warning("conversation_enrichment_job: pending lookup failed", exc_info=True)
        return "enrichment: lookup failed"

    if not pending:
        return "enrichment: nothing pending"

    classified = 0
    for row in pending:
        client_id = row.get("client_id")
        session_id = row.get("session_id")
        if not client_id or not session_id:
            continue
        try:
            result = await enrich_conversation(client_id, session_id, db=db)
        except Exception:
            logger.warning(
                "conversation_enrichment_job: enrich failed session=%s", session_id, exc_info=True
            )
            continue
        if result.get("sentiment") or result.get("intent"):
            classified += 1

    return f"enrichment: classified {classified}/{len(pending)} conversation(s)"


async def run_pending_enrichment_batch(
    *,
    max_poll_attempts: int = _BATCH_POLL_ATTEMPTS,
    poll_interval_seconds: float = _BATCH_POLL_INTERVAL_SECONDS,
) -> str:
    """Batch-API variant of ``run_pending_enrichment`` -- ONE Anthropic Message
    Batch instead of N sequential Claude calls for the same pending
    conversations (#F11: batches bill 50% off and are the right shape for any
    offline/non-realtime workload).

    NOT wired into the scheduler -- ``backend/main.py`` still calls
    ``run_pending_enrichment``, unchanged, as the active scheduled job. This
    function gives ``batch_runtime`` one real, tested caller; deciding whether
    (and when) to swap the scheduler over to this path is a separate decision
    for whoever owns ``backend/main.py``.

    Known limitation (flag before wiring into the scheduler): if the batch
    hasn't ended within ``max_poll_attempts * poll_interval_seconds``, this
    tick gives up and returns a "still processing" status without persisting
    anything. The selection query only looks for conversations with
    ``sentiment IS NULL``, so the next scheduled tick will re-select the same
    rows and submit a NEW, overlapping batch -- there is no ``batch_id``
    tracked across ticks (that needs a DB column + migration, out of scope
    here). Duplicate classification is idempotent and cheap (Haiku, ~120
    output tokens), so this is acceptable for a first wiring, but a real
    integration should either widen the poll window past the expected batch
    duration or add cross-tick ``batch_id`` tracking first.
    """
    db = get_service_supabase()

    try:
        pending = _find_pending(db)
    except Exception:
        logger.warning("conversation_enrichment_job: batch lookup failed", exc_info=True)
        return "enrichment(batch): lookup failed"

    if not pending:
        return "enrichment(batch): nothing pending"

    rows_by_custom_id: dict[str, dict[str, Any]] = {}
    requests: list[dict[str, Any]] = []
    for idx, row in enumerate(pending):
        client_id = row.get("client_id")
        session_id = row.get("session_id")
        if not client_id or not session_id:
            continue
        try:
            transcript = _load_transcript(db, client_id, session_id)
        except Exception:
            logger.warning(
                "conversation_enrichment_job: batch transcript load failed session=%s",
                session_id,
                exc_info=True,
            )
            continue
        if not transcript.strip():
            continue
        custom_id = f"enrich-{idx}-{session_id}"
        rows_by_custom_id[custom_id] = {"client_id": client_id, "session_id": session_id}
        requests.append(
            {
                "custom_id": custom_id,
                "params": {
                    "model": CLASSIFY_MODEL,
                    "max_tokens": _MAX_OUTPUT_TOKENS,
                    "system": _CLASSIFY_SYSTEM,
                    "messages": [{"role": "user", "content": transcript}],
                },
            }
        )

    if not requests:
        return "enrichment(batch): nothing to classify"

    batch_id = batch_runtime.submit_batch(
        requests,
        metadata={"job": "conversation_enrichment_batch", "request_count": len(requests)},
    )
    if not batch_id:
        return "enrichment(batch): submit failed"

    ended = False
    for _ in range(max(1, max_poll_attempts)):
        status = batch_runtime.poll_batch(batch_id)
        if status is None:
            return f"enrichment(batch): poll failed batch_id={batch_id}"
        if status.ended:
            ended = True
            break
        await asyncio.sleep(poll_interval_seconds)

    if not ended:
        logger.warning(
            "conversation_enrichment_job: batch did not end within poll window batch_id=%s",
            batch_id,
        )
        return f"enrichment(batch): still processing batch_id={batch_id}"

    results = batch_runtime.get_batch_results(batch_id)
    classified = 0
    for custom_id, target in rows_by_custom_id.items():
        item = results.get(custom_id)
        if item is None or item.status != "succeeded" or not item.text:
            continue
        classification = parse_classification(item.text)
        values = {k: v for k, v in classification.items() if v is not None}
        if not values:
            continue
        if _persist(db, target["client_id"], target["session_id"], values):
            classified += 1

    return f"enrichment(batch): classified {classified}/{len(requests)} conversation(s)"
