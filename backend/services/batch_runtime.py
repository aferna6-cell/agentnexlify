"""Anthropic Message Batches helper — offline-only, 50% off, async.

Message Batches trade latency for cost: a batch of independent requests is
submitted once, processed by Anthropic over minutes-to-hours (hard cap 24h),
then polled/collected. That tradeoff is a win for cron/background jobs and a
non-starter for anything a user is waiting on.

STRICT RULE — offline callers only. Never call this module from a request a
user is waiting on (widget chat, a dashboard action, a webhook that must
answer synchronously). Good candidates: nightly compiles, batch re-scoring,
periodic classification jobs already running on a scheduler tick — see
`backend/services/conversation_enrichment_job.py::run_pending_enrichment_batch`
for the first wired caller.

SDK shapes verified against the pinned `anthropic` SDK (0.116.0, same version
`llm_runtime.py` targets) by introspecting the installed package directly —
not guessed:

- `client.messages.batches.create(requests=[...])` — `requests` is
  `Iterable[Request]` where `Request` (a `TypedDict`,
  `anthropic.types.messages.batch_create_params.Request`) has exactly two
  keys: `custom_id: str` and `params: MessageCreateParamsNonStreaming` (the
  same kwargs shape as a normal single-message create call — `model`,
  `max_tokens`, `messages`, optional `system`, etc.). Returns a `MessageBatch`
  (`anthropic.types.messages.message_batch.MessageBatch`) with fields: `id`,
  `processing_status` (`Literal["in_progress", "canceling", "ended"]`),
  `request_counts` (`MessageBatchRequestCounts`: `processing`, `succeeded`,
  `errored`, `canceled`, `expired`), `results_url`, `created_at`, `ended_at`,
  `expires_at`, `cancel_initiated_at`, `archived_at`, `type`.
- `client.messages.batches.retrieve(message_batch_id)` — same `MessageBatch`
  shape as `.create()`; poll this until `processing_status == "ended"`.
- `client.messages.batches.results(message_batch_id)` — returns an iterator
  of `MessageBatchIndividualResponse` (`custom_id`, `result`). `result` is a
  discriminated union on `.type`: `"succeeded"` (`.message` is a full
  `Message`, the same shape a single-message create returns — extract text from
  `.content` blocks same as `llm_runtime._extract_text`), `"errored"`
  (`.error`), `"canceled"`, `"expired"` (no message payload on the last
  three).

No beta header is required for Message Batches on this SDK version — unlike
the extended-cache-ttl opt-in in `llm_runtime.py`, batches are GA on the
Messages API.
"""

import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any

import anthropic

from backend.config import settings

logger = logging.getLogger(__name__)

# Anthropic accepts a max of 100,000 requests per batch (and a 256MB request
# body cap). We never expect to be anywhere near that from a single tenant
# scan, but guard against a caller accidentally handing us an unbounded list.
MAX_BATCH_REQUESTS = 10_000


@dataclass
class BatchStatus:
    """Snapshot of a batch's processing state — the `poll_batch()` return shape."""

    batch_id: str
    processing_status: str  # "in_progress" | "canceling" | "ended" | "unknown"
    succeeded: int
    errored: int
    canceled: int
    expired: int
    processing: int
    results_url: str | None
    ended: bool


@dataclass
class BatchResultItem:
    """One `custom_id`'s outcome — the value shape in `get_batch_results()`."""

    custom_id: str
    status: str  # "succeeded" | "errored" | "canceled" | "expired" | "unknown"
    text: str | None
    error: str | None


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _extract_text(message: Any) -> str | None:
    """Pull concatenated text out of a succeeded batch result's `.message`.

    Mirrors `llm_runtime._extract_text` (kept local/duplicated on purpose —
    this module intentionally does not import from `llm_runtime.py` so the
    two runtimes stay independently editable this round).
    """
    blocks = getattr(message, "content", None) or []
    parts: list[str] = []
    for block in blocks:
        text = getattr(block, "text", None)
        if isinstance(text, str):
            parts.append(text)
    joined = "".join(parts).strip()
    return joined or None


def _safe_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    """Redact anything that looks like message/content/secret before logging."""
    if not metadata:
        return {}
    safe: dict[str, Any] = {}
    for key, value in metadata.items():
        key_l = str(key).lower()
        if any(
            token in key_l
            for token in ("message", "content", "text", "body", "api_key", "token", "secret", "password")
        ):
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[key] = value if not isinstance(value, str) or len(value) <= 200 else value[:197] + "..."
        else:
            safe[key] = {"type": type(value).__name__}
    return safe


def submit_batch(
    requests: list[dict[str, Any]],
    *,
    metadata: dict[str, Any] | None = None,
) -> str | None:
    """Submit a Message Batch. Returns the batch id, or `None` on failure.

    `requests` — list of `{"custom_id": str, "params": {"model": ..., "max_tokens": ...,
    "messages": [...], ...}}` dicts, one per independent Claude call you want
    batched together. `custom_id` must be unique within the batch — use it to
    line results back up to whatever domain object (lead id, conversation
    session_id, etc.) the request was for.

    Never raises. Any failure (empty input, malformed requests, network,
    auth, rate limit) is logged and this returns `None` — offline callers
    should treat `None` as "batch didn't submit, try again next tick" and
    keep going, never crash the calling cron job.
    """
    if not requests:
        logger.warning("batch.submit.empty_requests")
        return None
    if len(requests) > MAX_BATCH_REQUESTS:
        logger.warning(
            "batch.submit.too_many_requests count=%d max=%d", len(requests), MAX_BATCH_REQUESTS
        )
        return None

    call_id = uuid.uuid4().hex[:12]
    started = time.perf_counter()
    logger.info(
        "batch.submit.start id=%s request_count=%d metadata=%s",
        call_id,
        len(requests),
        _safe_metadata(metadata),
    )

    try:
        client = _client()
        batch = client.messages.batches.create(requests=requests)
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        logger.warning(
            "batch.submit.error id=%s duration_ms=%d request_count=%d error_type=%s error=%s",
            call_id,
            duration_ms,
            len(requests),
            type(exc).__name__,
            str(exc)[:300],
            exc_info=True,
        )
        return None

    duration_ms = int((time.perf_counter() - started) * 1000)
    logger.info(
        "batch.submit.finish id=%s batch_id=%s duration_ms=%d processing_status=%s request_count=%d",
        call_id,
        batch.id,
        duration_ms,
        batch.processing_status,
        len(requests),
    )
    return batch.id


def poll_batch(batch_id: str) -> BatchStatus | None:
    """Fetch current processing status for a batch. Returns `None` on failure.

    Check `status.ended` (equivalent to `processing_status == "ended"`)
    before calling `get_batch_results()` — results are only complete once
    the batch has ended. Never raises; a poll failure is logged and returns
    `None` so the caller can just retry on the next tick.
    """
    if not batch_id:
        logger.warning("batch.poll.missing_batch_id")
        return None

    call_id = uuid.uuid4().hex[:12]
    try:
        client = _client()
        batch = client.messages.batches.retrieve(batch_id)
    except Exception as exc:
        logger.warning(
            "batch.poll.error id=%s batch_id=%s error_type=%s error=%s",
            call_id,
            batch_id,
            type(exc).__name__,
            str(exc)[:300],
            exc_info=True,
        )
        return None

    counts = getattr(batch, "request_counts", None)
    processing_status = getattr(batch, "processing_status", None) or "unknown"
    status = BatchStatus(
        batch_id=batch.id,
        processing_status=processing_status,
        succeeded=getattr(counts, "succeeded", 0) or 0,
        errored=getattr(counts, "errored", 0) or 0,
        canceled=getattr(counts, "canceled", 0) or 0,
        expired=getattr(counts, "expired", 0) or 0,
        processing=getattr(counts, "processing", 0) or 0,
        results_url=getattr(batch, "results_url", None),
        ended=(processing_status == "ended"),
    )
    logger.info(
        "batch.poll.finish id=%s batch_id=%s processing_status=%s succeeded=%d errored=%d "
        "canceled=%d expired=%d processing=%d",
        call_id,
        batch_id,
        status.processing_status,
        status.succeeded,
        status.errored,
        status.canceled,
        status.expired,
        status.processing,
    )
    return status


def get_batch_results(batch_id: str) -> dict[str, BatchResultItem]:
    """Fetch per-`custom_id` results for an ended batch.

    Returns `{}` on total failure (network/auth error before any row was
    read) or a partial dict if the results stream broke partway through —
    either way this never raises. Callers should only call this once
    `poll_batch(batch_id).ended` is `True`; calling it earlier returns
    whatever has completed so far, per Anthropic's streaming results
    behavior.
    """
    if not batch_id:
        logger.warning("batch.results.missing_batch_id")
        return {}

    call_id = uuid.uuid4().hex[:12]
    results: dict[str, BatchResultItem] = {}
    try:
        client = _client()
        for entry in client.messages.batches.results(batch_id):
            custom_id = getattr(entry, "custom_id", None)
            if not custom_id:
                continue
            result = getattr(entry, "result", None)
            result_type = getattr(result, "type", "unknown") if result is not None else "unknown"

            text: str | None = None
            error_text: str | None = None
            if result_type == "succeeded":
                message = getattr(result, "message", None)
                text = _extract_text(message) if message is not None else None
            elif result_type == "errored":
                error_obj = getattr(result, "error", None)
                error_text = str(error_obj)[:300] if error_obj is not None else "unknown_error"

            results[custom_id] = BatchResultItem(
                custom_id=custom_id,
                status=result_type,
                text=text,
                error=error_text,
            )
    except Exception as exc:
        logger.warning(
            "batch.results.error id=%s batch_id=%s error_type=%s error=%s partial_count=%d",
            call_id,
            batch_id,
            type(exc).__name__,
            str(exc)[:300],
            len(results),
            exc_info=True,
        )
        return results

    logger.info(
        "batch.results.finish id=%s batch_id=%s result_count=%d",
        call_id,
        batch_id,
        len(results),
    )
    return results
