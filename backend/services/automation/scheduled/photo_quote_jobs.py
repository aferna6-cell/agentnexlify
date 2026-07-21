"""Photo-quote image retention purge (#40).

PII hygiene for the photo-quote epic: a customer's uploaded full-resolution
image is deleted from storage 30 days after the request; the thumbnail and all
metadata are kept permanently. Resolved decision #3 in
``specs/photo-quote_spec.md``.

Migration 108 ships a SQL helper (``purge_photo_quote_images_30d()``) that nulls
the DB pointer, but SQL cannot delete the object bytes from Supabase Storage.
This job does both, in the safe order: delete the storage object first, then
null ``image_url`` + stamp ``full_image_purged_at`` on the row. A storage
delete that fails never blocks the DB update — the pointer is still cleared and
the failure is logged and counted, so a stuck object never keeps the row
returning as a purge candidate forever.

Cadence: the automation loop ticks every 60s and runs the 30-min tier often, so
the once-daily 03:00 UTC cadence is enforced inside the job — it no-ops unless
the current UTC hour is 03. The purge is idempotent (only rows not yet purged
are touched), so a second tick inside the window finds nothing new.

Runtime constraints (issue #40):
- Batch size capped at 500 rows/run to bound memory.
- Service-role Supabase client (RLS ``service_role_full_access`` on the table).
- Storage delete failures log + continue; they must not block the DB update.
- Alarm flag when errors exceed 5% of the batch.
"""

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

BUCKET = "photo-quotes"
BATCH_SIZE = 500
RETENTION_DAYS = 30
_RUN_HOUR_UTC = 3
_ERROR_ALARM_RATIO = 0.05


def get_service_supabase():
    """Lazy service-role client accessor.

    Deferred import keeps this module importable without booting the full app,
    and lets tests monkeypatch the client on this module directly.
    """
    from backend.models.database import get_service_supabase as _get

    return _get()


def _object_path(image_url: str) -> str:
    """Extract the ``photo-quotes``-bucket-relative object path from a stored URL.

    Handles a full public URL
    (``.../object/public/photo-quotes/<path>``), a ``photo-quotes/<path>``
    prefixed value, and a already-relative ``<path>``.
    """
    marker = f"/{BUCKET}/"
    if marker in image_url:
        return image_url.split(marker, 1)[1]
    prefix = f"{BUCKET}/"
    if image_url.startswith(prefix):
        return image_url[len(prefix):]
    return image_url


def _elapsed(start: datetime) -> float:
    return (datetime.now(timezone.utc) - start).total_seconds()


async def purge_photo_quote_images_30d() -> dict:
    """Delete full images older than 30 days from storage + null their pointer.

    Returns a summary ``{processed, errors, duration}`` (plus ``alarm`` when any
    row was processed, and ``skipped_reason`` when the daily window gate no-ops).
    """
    start = datetime.now(timezone.utc)

    # Daily 03:00 UTC window gate (see module docstring).
    if start.hour != _RUN_HOUR_UTC:
        return {
            "processed": 0,
            "errors": 0,
            "duration": _elapsed(start),
            "skipped_reason": "outside_window",
        }

    db = get_service_supabase()
    cutoff = (start - timedelta(days=RETENTION_DAYS)).isoformat()

    try:
        candidates = (
            db.table("quote_requests")
            .select("id, image_url")
            .lt("created_at", cutoff)
            .is_("full_image_purged_at", "null")
            .limit(BATCH_SIZE)
            .execute()
        ).data or []
    except Exception:
        logger.exception("purge_photo_quote_images_30d: candidate query failed")
        return {"processed": 0, "errors": 0, "duration": _elapsed(start)}

    if not candidates:
        return {"processed": 0, "errors": 0, "duration": _elapsed(start)}

    bucket = db.storage.from_(BUCKET)
    processed = 0
    errors = 0

    for row in candidates:
        image_url = row.get("image_url")
        row_id = row.get("id")
        if not image_url or not row_id:
            # Nothing to delete (already null) — leave the row for a later pass
            # if it still lacks a purge timestamp; do not count as processed.
            continue

        # 1) Delete the object bytes. Failure is logged + counted, never fatal.
        try:
            bucket.remove([_object_path(image_url)])
        except Exception:
            errors += 1
            logger.warning(
                "purge_photo_quote_images_30d: storage delete failed for one object"
            )

        # 2) Null the pointer + stamp the purge time regardless of storage
        #    outcome, so a stuck object cannot keep re-surfacing the row.
        try:
            (
                db.table("quote_requests")
                .update(
                    {
                        "image_url": None,
                        "full_image_purged_at": start.isoformat(),
                    }
                )
                .eq("id", row_id)
                .execute()
            )
        except Exception:
            errors += 1
            logger.warning(
                "purge_photo_quote_images_30d: db update failed for one row"
            )
            continue

        processed += 1

    result = {"processed": processed, "errors": errors, "duration": _elapsed(start)}
    if processed > 0:
        result["alarm"] = (errors / processed) > _ERROR_ALARM_RATIO
        if result["alarm"]:
            logger.error(
                "purge_photo_quote_images_30d: error rate %d/%d exceeds %.0f%% — alarm",
                errors,
                processed,
                _ERROR_ALARM_RATIO * 100,
            )

    logger.info(
        "purge_photo_quote_images_30d: processed=%d errors=%d duration=%.2fs",
        processed,
        errors,
        result["duration"],
    )
    return result
