"""Photo-triage (#R1) — Claude vision assesses urgency + scope from widget
photo uploads.

A widget visitor uploads 1-3 photos (broken pipe, roof, dented car). This
module builds a multimodal Claude message (text + image blocks) via
`backend.services.llm_runtime.call_claude_messages` and returns a structured
assessment the widget/dashboard can use to route to booking or attach to a
lead (`leads.ai_triage` — migrations/171_photo_triage_and_quotes.sql).

Fault-tolerant like `backend/services/review_responder.py`: never raises.
Any LLM or parse failure returns None (logged), so a triage failure never
blocks lead capture — the widget falls back to its normal flow.
"""

import json
import logging
import re
from typing import Any

from backend.services.llm_runtime import call_claude_messages

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-5"
MAX_IMAGES = 3
MAX_TOKENS = 500
VALID_URGENCY = {"low", "medium", "high", "emergency"}

_SYSTEM_PROMPT = (
    "You are a photo-triage assistant for a {business_type} business. A "
    "website visitor uploaded 1-3 photos of a problem (for example: a "
    "broken pipe, roof damage, a dented car). Assess urgency and scope from "
    "the photos and any note the visitor provided.\n\n"
    "Respond with ONLY a JSON object, no markdown fences, no extra text:\n"
    '{{"urgency": "low"|"medium"|"high"|"emergency", "category": "<short '
    'category, e.g. plumbing leak, roof damage, auto body damage>", '
    '"scope_summary": "<1-3 sentence description of what you see>", '
    '"recommended_action": "<what the business should do next, e.g. book an '
    'emergency visit, schedule a standard inspection, request more photos>"}}\n\n'
    'Use "emergency" only for situations with active/ongoing damage risk '
    '(active flooding, structural collapse risk, fire/electrical hazard). '
    'Use "high" for urgent-but-not-emergency issues. Use "medium" for '
    'standard service needs. Use "low" for cosmetic/non-urgent issues.'
)


def _strip_json_fence(text: str) -> str:
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _validate_urgency(value: Any) -> str:
    """Normalize the model's urgency claim, defaulting to 'medium' on junk."""
    if isinstance(value, str) and value.strip().lower() in VALID_URGENCY:
        return value.strip().lower()
    return "medium"


async def triage_photos(
    *,
    business_type: str,
    images: list[dict[str, str]],
    note: str | None = None,
) -> dict[str, Any] | None:
    """Assess urgency + scope from 1-3 uploaded photos via Claude vision.

    `images` items: `{"media_type": "image/jpeg"|"image/png"|..., "data":
    <base64 str>}`. Only the first `MAX_IMAGES` entries are used; anything
    beyond that (or malformed entries missing media_type/data) is ignored.

    Never raises. Returns a dict `{urgency, category, scope_summary,
    recommended_action}` on success, or None (logged) on any LLM failure,
    unparseable response, or missing usable images.
    """
    if not images:
        logger.warning("photo_triage: no images provided")
        return None

    usable_images = [
        img
        for img in images[:MAX_IMAGES]
        if isinstance(img, dict) and img.get("media_type") and img.get("data")
    ]
    if not usable_images:
        logger.warning("photo_triage: no usable images (missing media_type/data)")
        return None

    content_blocks: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": (
                f"Note from visitor: {note.strip()}"
                if note and note.strip()
                else "No additional note from visitor."
            ),
        }
    ]
    for img in usable_images:
        content_blocks.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": img["media_type"],
                    "data": img["data"],
                },
            }
        )

    system_prompt = _SYSTEM_PROMPT.format(business_type=business_type or "service")

    try:
        result = await call_claude_messages(
            operation="photo_triage.assess",
            model=MODEL,
            max_tokens=MAX_TOKENS,
            temperature=0.2,
            timeout=45.0,
            system=system_prompt,
            messages=[{"role": "user", "content": content_blocks}],
            metadata={
                "business_type": business_type,
                "image_count": len(usable_images),
            },
        )
        raw_text = result.text
    except Exception:
        logger.error("photo_triage: LLM call failed", exc_info=True)
        return None

    cleaned = _strip_json_fence(raw_text)
    try:
        parsed = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        logger.warning("photo_triage: unparseable LLM response: %r", raw_text[:300])
        return None

    if not isinstance(parsed, dict):
        logger.warning("photo_triage: LLM response was not a JSON object: %r", parsed)
        return None

    triage = {
        "urgency": _validate_urgency(parsed.get("urgency")),
        "category": str(parsed.get("category") or "").strip()[:200] or "general",
        "scope_summary": str(parsed.get("scope_summary") or "").strip()[:1000],
        "recommended_action": str(parsed.get("recommended_action") or "").strip()[:500],
    }
    logger.info(
        "photo_triage: assessed urgency=%s category=%s image_count=%d",
        triage["urgency"],
        triage["category"],
        len(usable_images),
    )
    return triage
