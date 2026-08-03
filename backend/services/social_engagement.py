"""Engagement metrics ingestion for published social posts.

For recently published posts on instagram/facebook that carry an
``external_post_id``, fetch one basic-insights GET per post via the Graph
API and merge the result into ``social_posts.engagement_data`` with a
``fetched_at`` stamp. Designed to run on a 30-min automation tier — wiring
into ``backend/main.py``'s automation loop is a follow-up change (this lane
does not edit ``main.py``).

Tenant tokens come from the same ``integrations`` rows the os_actions
publish handlers already use (``social_instagram._load_ig_account``,
``social_facebook._load_fb_page``) — no separate token storage. Every post
is isolated; one Graph API failure never blocks the rest of the batch.

Google Business Profile has no engagement/insights read wired here — GBP's
``localPosts`` API doesn't expose a comparable single-GET engagement
metric, and it isn't in scope for this pass.
"""

import logging
from datetime import datetime, timezone

import httpx

from backend.models.database import get_service_supabase
from backend.services.os_actions.social_facebook import _FB_GRAPH_BASE, _load_fb_page
from backend.services.os_actions.social_instagram import _load_ig_account

logger = logging.getLogger(__name__)

_BATCH_LIMIT = 50
_TIMEOUT_SECONDS = 15.0
_IG_GRAPH_BASE = "https://graph.facebook.com/v21.0"

_ENGAGEMENT_PLATFORMS = ("instagram", "facebook")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _fetch_instagram_insights(client_id: str, media_id: str) -> dict | None:
    """One GET for like_count + comments_count. None on any failure."""
    account = _load_ig_account(client_id)
    if not account:
        return None

    url = f"{_IG_GRAPH_BASE}/{media_id}"
    params = {
        "fields": "like_count,comments_count",
        "access_token": account["access_token"],
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            resp = await client.get(url, params=params)
    except Exception:
        logger.warning(
            "social_engagement.instagram: request failed client_id=%s media_id=%s",
            client_id,
            media_id,
            exc_info=True,
        )
        return None

    if resp.status_code >= 400:
        logger.warning(
            "social_engagement.instagram: status=%d media_id=%s",
            resp.status_code,
            media_id,
        )
        return None

    body = resp.json() if resp.content else {}
    return {"likes": body.get("like_count"), "comments": body.get("comments_count")}


async def _fetch_facebook_insights(client_id: str, post_id: str) -> dict | None:
    """One GET for likes/comments/shares summaries. None on any failure."""
    page = _load_fb_page(client_id)
    if not page:
        return None

    url = f"{_FB_GRAPH_BASE}/{post_id}"
    params = {
        "fields": "likes.summary(true),comments.summary(true),shares",
        "access_token": page["page_access_token"],
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            resp = await client.get(url, params=params)
    except Exception:
        logger.warning(
            "social_engagement.facebook: request failed client_id=%s post_id=%s",
            client_id,
            post_id,
            exc_info=True,
        )
        return None

    if resp.status_code >= 400:
        logger.warning(
            "social_engagement.facebook: status=%d post_id=%s", resp.status_code, post_id
        )
        return None

    body = resp.json() if resp.content else {}
    likes = (body.get("likes") or {}).get("summary") or {}
    comments = (body.get("comments") or {}).get("summary") or {}
    shares = body.get("shares") or {}
    return {
        "likes": likes.get("total_count"),
        "comments": comments.get("total_count"),
        "shares": shares.get("count"),
    }


async def _ingest_one(db, post: dict) -> bool:
    post_id = post["id"]
    tenant_id = post["tenant_id"]
    platform = post["platform"]
    external_id = post.get("external_post_id")
    if not external_id:
        return False

    try:
        if platform == "instagram":
            metrics = await _fetch_instagram_insights(tenant_id, external_id)
        elif platform == "facebook":
            metrics = await _fetch_facebook_insights(tenant_id, external_id)
        else:
            return False
    except Exception:
        logger.exception(
            "social_engagement: unexpected error for post %s (%s)", post_id, platform
        )
        return False

    if metrics is None:
        return False

    existing = post.get("engagement_data")
    if not isinstance(existing, dict):
        existing = {}
    merged = {**existing, **metrics, "fetched_at": _now_iso()}

    try:
        db.table("social_posts").update({"engagement_data": merged}).eq(
            "id", post_id
        ).execute()
    except Exception:
        logger.exception(
            "social_engagement: failed to persist metrics for post %s", post_id
        )
        return False

    logger.info(
        "social_engagement: updated post %s (%s) tenant=%s", post_id, platform, tenant_id
    )
    return True


async def ingest_engagement(limit: int = 50) -> int:
    """Fetch + merge engagement metrics for recently published posts.

    Only instagram/facebook posts with an ``external_post_id`` are
    queried — twitter/linkedin/google_business have no publish integration
    that yields comparable metrics yet (see ``social_publisher.py``).
    Returns the count of posts updated.
    """
    db = get_service_supabase()
    try:
        published = (
            db.table("social_posts")
            .select("id, tenant_id, platform, external_post_id, engagement_data")
            .eq("status", "published")
            .in_("platform", list(_ENGAGEMENT_PLATFORMS))
            .order("published_at", desc=True)
            .limit(limit)
            .execute()
        )
    except Exception:
        logger.exception("social_engagement.ingest_engagement: query failed")
        return 0

    posts = [p for p in (published.data or []) if p.get("external_post_id")]
    if not posts:
        return 0

    updated = 0
    for post in posts:
        try:
            ok = await _ingest_one(db, post)
        except Exception:
            logger.exception("social_engagement: unhandled error for post %s", post.get("id"))
            ok = False
        if ok:
            updated += 1
    return updated
