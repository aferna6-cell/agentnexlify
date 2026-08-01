"""Real scheduled-post publisher for Social Media Marketing.

``backend/main.py::_process_scheduled_posts`` today just flips
``status='scheduled' -> 'published'`` without ever calling a platform API
(see ADR "Scheduled content auto-execution via automation loop" in
``docs/dev-knowledge/architecture-decisions.md``). This module is the real
publisher it was always meant to hand off to. Wiring ``main.py``'s
automation loop to call ``process_scheduled_posts()`` below instead of the
old status-flip logic is a follow-up change — this lane does not edit
``main.py``.

Each due post is dispatched to the connected-integration publish call for
its platform (instagram/facebook/google_business today, reusing the raw
publish functions factored into ``backend/services/os_actions/``). On
success: ``status='published'``, ``published_at`` set, ``external_post_id``
set. On failure: ``status='failed'``, with a reason recorded under
``engagement_data.publish_error`` (``social_posts`` has no dedicated error
column — see migration 050). Every post is isolated; one failure never
blocks the rest of the batch.

X/Twitter and LinkedIn have no publish integration in this codebase.
X/Twitter is explicitly deferred (see
``plans/nexlify-capabilities-roadmap_plan.md`` Phase 4a) — posts scheduled
on either platform are marked ``failed`` with reason
``platform_not_supported``, never silently flipped to ``published``.
"""

import logging
from datetime import datetime, timezone

from backend.models.database import get_service_supabase
from backend.services.os_actions import gbp, social_facebook, social_instagram

logger = logging.getLogger(__name__)

_BATCH_LIMIT = 100

# Platforms with a real publish integration below. Anything in
# VALID_PLATFORMS (social_media_ai.py) but not here fails cleanly with
# platform_not_supported instead of silently publishing.
_SUPPORTED_PLATFORMS = {"instagram", "facebook", "google_business"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mark_failed(db, post_id: str, reason: str, message: str) -> bool:
    """Persist a failed publish attempt. Always returns False."""
    try:
        db.table("social_posts").update(
            {
                "status": "failed",
                "engagement_data": {
                    "publish_error": {
                        "reason": reason,
                        "message": (message or "")[:500],
                        "failed_at": _now_iso(),
                    }
                },
            }
        ).eq("id", post_id).execute()
    except Exception:
        logger.exception(
            "social_publisher: failed to persist failure for post %s", post_id
        )
    logger.warning("social_publisher: post %s failed reason=%s", post_id, reason)
    return False


def _mark_published(db, post_id: str, external_id: str) -> bool:
    try:
        db.table("social_posts").update(
            {
                "status": "published",
                "published_at": _now_iso(),
                "external_post_id": str(external_id),
            }
        ).eq("id", post_id).execute()
    except Exception:
        logger.exception(
            "social_publisher: failed to persist success for post %s", post_id
        )
        return False
    return True


async def _dispatch(post: dict) -> tuple[str | None, dict]:
    """Call the platform publish function for one post.

    Returns ``(external_id, response_or_error)`` — mirrors the shape the
    os_actions publish helpers already return.
    """
    tenant_id = post["tenant_id"]
    platform = post["platform"]
    content = post.get("content") or ""
    media_urls = post.get("media_urls") or []
    first_media = media_urls[0] if media_urls else None

    if platform == "instagram":
        if not first_media:
            return None, {
                "stage": "validate",
                "reason": "missing_image",
                "message": "Instagram posts require an image in media_urls",
            }
        return await social_instagram.publish_image_post(tenant_id, first_media, content)

    if platform == "facebook":
        return await social_facebook.publish_text_post(tenant_id, content, link=first_media)

    if platform == "google_business":
        return await gbp.publish_post(tenant_id, content)

    return None, {
        "stage": "validate",
        "reason": "platform_not_supported",
        "message": f"{platform} publishing is not supported yet",
    }


async def _publish_one(db, post: dict) -> bool:
    """Publish a single post. Never raises — every failure path writes
    status='failed' and returns False; success writes status='published'
    and returns True."""
    post_id = post["id"]
    platform = post["platform"]

    if platform not in _SUPPORTED_PLATFORMS:
        return _mark_failed(
            db,
            post_id,
            "platform_not_supported",
            f"{platform} publishing is not supported yet",
        )

    try:
        external_id, response = await _dispatch(post)
    except Exception:
        logger.exception(
            "social_publisher: unexpected error publishing post %s (%s)",
            post_id,
            platform,
        )
        return _mark_failed(
            db, post_id, "publish_exception", "Unexpected error during publish"
        )

    if not external_id:
        response = response or {}
        reason = response.get("reason") or (
            "not_connected" if response.get("stage") == "connector" else "publish_failed"
        )
        message = response.get("message", "publish failed")
        return _mark_failed(db, post_id, reason, message)

    logger.info(
        "social_publisher: published post %s (%s) tenant=%s external_id=%s",
        post_id,
        platform,
        post["tenant_id"],
        external_id,
    )
    return _mark_published(db, post_id, external_id)


async def publish_due_posts(limit: int = 100) -> int:
    """Publish all due scheduled posts (``status='scheduled'``,
    ``scheduled_for <= now()``).

    Returns the count of posts successfully published. Each post is
    isolated — one failure never blocks the rest of the batch, and a
    platform with no connected integration is marked failed/not_connected
    rather than silently flipped to published.
    """
    db = get_service_supabase()
    now_iso = _now_iso()
    try:
        due = (
            db.table("social_posts")
            .select("id, tenant_id, platform, content, media_urls")
            .eq("status", "scheduled")
            .lte("scheduled_for", now_iso)
            .limit(limit)
            .execute()
        )
    except Exception:
        logger.exception("social_publisher.publish_due_posts: query failed")
        return 0

    posts = due.data or []
    if not posts:
        return 0

    published = 0
    for post in posts:
        try:
            ok = await _publish_one(db, post)
        except Exception:
            logger.exception(
                "social_publisher: unhandled error for post %s", post.get("id")
            )
            ok = False
        if ok:
            published += 1
    return published


async def process_scheduled_posts() -> int:
    """Entry point for the automation loop's 5-min tier.

    Same return semantics as the (now-superseded) status-flip logic in
    ``backend/main.py::_process_scheduled_posts`` — the count of posts
    moved to ``published``.
    """
    return await publish_due_posts(limit=_BATCH_LIMIT)
