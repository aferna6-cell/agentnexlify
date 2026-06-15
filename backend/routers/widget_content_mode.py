"""Widget chat content-mode handler — detect and repurpose content.

Extracted from widget_chat.py — single concern: detect when the visitor
is trying to repurpose content (YouTube links, long text, explicit keywords)
and run the content repurposer if the tenant plan allows it.

Public API:
    async detect_and_handle_content_mode(...)  -> WidgetChatResponse | None
"""

import logging
import re
from typing import Any

from backend.models.schemas import WidgetChatResponse
from backend.routers.widget_chat_helpers import _save_chat_messages

logger = logging.getLogger(__name__)

_CONTENT_MODE_KEYWORDS = [
    "repurpose",
    "content mode",
    "turn this into",
    "create content from",
]
_YT_PATTERN = re.compile(r"(?:youtube\.com/watch|youtu\.be/)")


async def detect_and_handle_content_mode(
    *,
    tenant: dict[str, Any],
    widget: dict[str, Any],
    session_id: str,
    message: str,
    content_mode_flag: bool,
    db: Any,
) -> "WidgetChatResponse | None":
    """Detect content-mode intent and handle it if triggered.

    Returns a WidgetChatResponse when content mode is active (caller must
    return it), or None to continue with normal chat flow.

    Content mode triggers when:
    - req.content_mode is explicitly True
    - Message contains repurpose keywords
    - Message contains a YouTube URL
    - Message is long (>500 chars) with no question mark
    """
    _msg_lower = message.lower()
    _content_mode = content_mode_flag

    if not _content_mode:
        for _kw in _CONTENT_MODE_KEYWORDS:
            if _kw in _msg_lower:
                _content_mode = True
                break
    if not _content_mode and _YT_PATTERN.search(message):
        _content_mode = True
    if not _content_mode and len(message) > 500 and "?" not in message:
        _content_mode = True

    if not _content_mode:
        return None

    # Content mode triggered — check plan gate
    plan = tenant.get("plan") or "free"
    if plan not in ("professional", "enterprise"):
        _save_chat_messages(tenant["id"], session_id, message, None)
        return WidgetChatResponse(
            response="Content repurposing is available on Professional and Enterprise plans. Upgrade to unlock this feature!",
            session_id=session_id,
            lead_captured=False,
            show_watermark=widget.get("show_watermark", True),
        )

    # Determine source type
    if _YT_PATTERN.search(message):
        _src_type = "youtube"
    elif message.strip().startswith(("http://", "https://")):
        _src_type = "url"
    else:
        _src_type = "text"

    # Run the repurposer
    try:
        from backend.services.content_repurposer import (
            extract_source,
            repurpose as do_repurpose,
        )

        source = await extract_source(_src_type, message.strip())
        outputs = await do_repurpose(
            source_content=source["content"],
            title=source["title"],
            tenant_id=tenant["id"],
            tone="professional",
        )
        db.table("repurpose_jobs").insert(
            {
                "tenant_id": tenant["id"],
                "source_type": _src_type,
                "source_url": source["source_url"],
                "source_content": source["content"],
                "source_title": source["title"],
                "outputs": outputs,
                "status": "completed",
                "created_via": "widget",
            }
        ).execute()
        resp_text = (
            f"Done! I've repurposed \"{source['title']}\" into:\n\n"
            "- X/Twitter thread (7-10 tweets)\n"
            "- LinkedIn carousel\n"
            "- Email sequence (3-5 emails)\n"
            "- TikTok/Reels scripts\n"
            "- Social posts (Facebook, Instagram, Google Business)\n\n"
            "View and edit your results in the Content Repurpose page on your dashboard."
        )
    except Exception as e:
        logger.error("Content mode repurpose failed: %s", e, exc_info=True)
        resp_text = "Sorry, I had trouble repurposing that content. Please try again or paste the text directly."

    _save_chat_messages(tenant["id"], session_id, message, resp_text)
    return WidgetChatResponse(
        response=resp_text,
        session_id=session_id,
        lead_captured=False,
        show_watermark=widget.get("show_watermark", True),
    )
